import requests
from requests.auth import HTTPBasicAuth
import configparser

def connect_bitbucket(config):
    """
    Connects to Bitbucket API using config object.
    Expects [bitbucket] section with url, user, password/token.
    """
    try:
        base_url = config.get('bitbucket', 'url')
        user = config.get('bitbucket', 'user')
        token = config.get('bitbucket', 'token')

        # Example endpoint: List projects
        url = f"{base_url}/rest/api/1.0/projects" 
        print(f"[*] Connecting to Bitbucket: {url}")
        
        # Real call - might fail without VPN/Creds so we catch exception
        response = requests.get(url, auth=HTTPBasicAuth(user, token), timeout=5)
        
        if response.status_code == 200:
            print("[Bitbucket] Connection Successful")
            return response.json()
        else:
            print(f"[-] Bitbucket Connection Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"[-] Bitbucket Error: {e}")
        return None

def connect_artifactory(config):
    """
    Connects to Artifactory using API Key.
    Expects [artifactory] section with url, api_key.
    """
    try:
        base_url = config.get('artifactory', 'url')
        api_key = config.get('artifactory', 'api_key')
        
        headers = {"X-JFrog-Art-Api": api_key}
        url = f"{base_url}/api/system/ping"
        print(f"[*] Connecting to Artifactory: {url}")
        
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
             print("[Artifactory] Connection Successful")
             return True
        else:
             print(f"[-] Artifactory Ping Failed: {response.status_code}")
             return False
    except Exception as e:
         print(f"[-] Artifactory Error: {e}")
         return False

def connect_jenkins(config):
    """
    Connects to Jenkins using User/Token.
    Expects [jenkins] section with url, user, token.
    """
    try:
        base_url = config.get('jenkins', 'url')
        user = config.get('jenkins', 'user')
        token = config.get('jenkins', 'token')
        
        url = f"{base_url}/api/json"
        print(f"[*] Connecting to Jenkins: {url}")
        
        response = requests.get(url, auth=HTTPBasicAuth(user, token), timeout=5)
        
        if response.status_code == 200:
            print("[Jenkins] Connection Successful")
            return response.json()
        else:
             print(f"[-] Jenkins Connection Failed: {response.status_code}")
             return None
    except Exception as e:
         print(f"[-] Jenkins Error: {e}")
         return None
