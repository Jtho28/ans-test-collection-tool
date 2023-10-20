import requests
import sys
from datetime import datetime
from datetime import timedelta
import yaml

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

    print(collections)

    collection = f"https://api.github.com/repos/ansible-collections/{sys.argv[1]}/releases"
    ansible_ver = f"https://api.github.com/repos/ansible/ansible/releases"

    payload = {}
    headers = {}

    coll_resp = requests.request("GET", collection, headers=headers, data=payload).json()
    ans_resp = requests.request("GET", ansible_ver, headers=headers, data=payload).json()

    pre = timedelta(days=-30)
    post = timedelta(days=30)

    recommended_versions = []

    for ans in ans_resp:
        if (ans['name'] == f"v{sys.argv[2]}"):  
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
                recommended_versions.append(coll['name'][1:])

    print(max(recommended_versions))


if __name__ == "__main__":
    main()