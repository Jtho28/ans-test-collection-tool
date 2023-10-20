import requests
import sys
from datetime import datetime
from datetime import timedelta
import yaml
import json
import re

'''
Prints the recommend collection version for a specified collection,
given a particular version of ansible. This was designed as a very small
tool to determine which collection version should be tested for an ansible
testing suite.

    Parameters:
        None
    
    Cmdline Args:
        1: Name of collection as specified by github repository name.
        2: Version of ansible core the user (more likely script) needs a recommendation for.

    Returns:
        None
'''
def main():

    with open('./molecule/shared/collections.yml', 'r') as file:
        data = yaml.safe_load(file)
    
    collections = []
    for node in data['collections']:
        collections.extend(node['name'].split('.'))
        collections.append(node['name'])

    collections = [x for i, x in enumerate(collections) if x not in collections[:i]]

    print(collections)

    for potential_coll_name in collections:

        collection_url = f"https://api.github.com/repos/ansible-collections/{potential_coll_name}/releases"
        ansible_ver_url = f"https://api.github.com/repos/ansible/ansible/releases"

        payload = {}
        headers = {}

        coll_resp = requests.request("GET", collection_url, headers=headers, data=payload).json()
        
        try:
            if (coll_resp['message'] == "Not Found"):
                continue
        except:
            pass

        with open(f'{potential_coll_name}.json', 'w') as json_file:
            json.dump(coll_resp, json_file)

        ans_resp = requests.request("GET", ansible_ver_url, headers=headers, data=payload).json()

        with open(f'ansible-releases.json', 'w') as json_file:
            json.dump(ans_resp, json_file)

        pre = timedelta(days=-30)
        post = timedelta(days=30)

        recommended_versions = []

        for ans in ans_resp:
            if (ans['name'] == f"v{sys.argv[1]}"):  
                ans_publish_date = ans['published_at']
                ans_publish_date = datetime.strptime(ans_publish_date, "%Y-%m-%dT%H:%M:%SZ")
            else:
                continue

            for coll in coll_resp:
                coll_publish_date = datetime.strptime(coll['published_at'], "%Y-%m-%dT%H:%M:%SZ")

                if (coll_publish_date - ans_publish_date >= post
                    or coll_publish_date - ans_publish_date >= pre
                    and ans['prerelease'] != 'true'):
                    #print(f"Collection: {coll['name']} Ansible: {ans['name']}")
                    match = re.search("\d+\.\d+\.\d+", coll['name'])
                    ver_span = match.span()
                    recommended_versions.append(coll['name'][ver_span[0]:ver_span[1]])

        if len(recommended_versions) != 0: print(f"{max(recommended_versions)}")


if __name__ == "__main__":
    main()