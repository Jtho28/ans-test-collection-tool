import sys
import os
from datetime import datetime
from datetime import timedelta
import yaml
import json
import re
import pickle
from dotenv import load_dotenv
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

'''
Determines recommended versions of collections based on 
role dependencies and ansible-core version. Then, it installs
the collections to the role as specified in the molecule/
structure.

This script is NOT meant for ad-hoc use, it was designed strictly
for use in pipelines.

If the script has been ran in the past 30 days, the script will use
cached json files for data if they exist.

    Parameters:
        None
    
    Cmdline Args:.
        1: Version of ansible core the user (more likely script) needs a recommendation for.

    Returns:
        None
'''
def main():
    
    url = "https://api.github.com/graphql"
    load_dotenv(".env")
    token = os.environ.get("TOKEN")
    headers = {'Authorization': f"Bearer {token}"}
    transport = AIOHTTPTransport(url=url, headers=headers)
    client = Client(transport=transport)

    formated = {'ans': {}, 'coll': {}}
    deps = {}
    response = {}
    hit_api = False

    try:
        with open('./time_cache.pkl', 'rb') as file:
            last_ran = pickle.load(file)
    except:
        last_ran = datetime.utcnow()
        hit_api = True


    with open('./molecule/shared/collections.yml', 'r') as file:
        data = yaml.safe_load(file)
    
    collections = []
    for node in data['collections']:
        collections.extend(node['name'].split('.'))
        collections.append(node['name'])

    collections = [x for i, x in enumerate(collections) if x not in collections[:i]]

    # Query for ansible versions
    ans_query = gql("""
                    query Ans {
                      ans: repository(owner: "ansible", name: "ansible") {
                        refs(refPrefix: "refs/tags/", first:1, orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
                          nodes {
                            repository {
                              releases (first: 100) {
                                nodes {
                                  isPrerelease
                                    name
                                    createdAt
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                    """)
    
    response = client.execute(ans_query)

    for node in response['ans']['refs']['nodes'][0]['repository']['releases']['nodes']:
                if (node['isPrerelease'] == False):
                    formated['ans'][node['name']] = node['createdAt']

    
    # Loop through potential collction name and query for release names
    for potential_coll_name in collections:

        # If thirty days have passed since last run, or the script has
        # never been run, hit the api
        if ((datetime.utcnow() - last_ran).days >= 30 or hit_api):

            
            query = gql(f"""
                        query Ans {{
                          coll: repository(owner: "ansible-collections", name: "{potential_coll_name}") {{
                            refs(refPrefix: "refs/tags/", first:1, orderBy: {{field: TAG_COMMIT_DATE, direction: DESC}}) {{
                              nodes {{
                                repository {{
                                  releases (first: 10) {{
                                    nodes {{
                                      isPrerelease
                                      name
                                      createdAt
                                    }}
                                  }}
                                }}
                              }}
                            }}
                          }}
                        }}         
                        """)
            
            try:
                formated['coll'][potential_coll_name] = {}
                response = client.execute(query)  
            except:
                continue

                        
            if response['coll'] == None or not response['coll']['refs']['nodes']:
                continue
            else:
                for node in response['coll']['refs']['nodes'][0]['repository']['releases']['nodes']:
                    if (node['isPrerelease'] == False):
                        record = {node['createdAt']: node['name']}
                        formated['coll'][potential_coll_name].update(record)


        # if the script has been run recently, load from json
        else:
            try:
                with open(f'./cached_resp.json', 'r') as json_file:
                    formated = json.load(json_file)

            except FileNotFoundError:
                continue


        pre = timedelta(days=-30)
        post = timedelta(days=30)
        

        ans_publish_date = datetime.strptime(formated['ans'][f"v{sys.argv[1]}"], "%Y-%m-%dT%H:%M:%SZ")

        recommended_versions = []
        canonical_versions = []
        for coll_publish_date in list(formated['coll'][potential_coll_name].keys()):

            if (datetime.strptime(coll_publish_date, "%Y-%m-%dT%H:%M:%SZ") - ans_publish_date >= post
                or datetime.strptime(coll_publish_date, "%Y-%m-%dT%H:%M:%SZ") - ans_publish_date >= pre):

                match = re.search("\d+\.\d+\.\d+", formated['coll'][potential_coll_name][coll_publish_date])
                ver_span = match.span()
                recommended_versions.append(formated['coll'][potential_coll_name][coll_publish_date][ver_span[0]:ver_span[1]])
                canonical_versions.append(formated['coll'][potential_coll_name][coll_publish_date])

        if len(recommended_versions) != 0: 
            print(f"{max(recommended_versions)}")
            deps[potential_coll_name] = max(canonical_versions)
            os.system(f"ansible-galaxy collection install git+https://github.com/ansible-collections/{potential_coll_name},{deps[potential_coll_name]} -p molecule/resources/collections")

        recommended_versions = []
        canonical_versions = []

    
    last_ran = datetime.utcnow()
    with open('./time_cache.pkl', 'wb') as file:
        pickle.dump(last_ran, file)
    with open(f'cached_resp.json', 'w') as json_file:
            json.dump(formated, json_file)

    
if __name__ == "__main__":
    main()