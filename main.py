import pandas as pd
import requests
from pprint import pprint
import yaml
from urllib3.exceptions import HTTPError

def make_request(verb, base_url, uri, parameters: dict = {}, token = ""):
    """make request, return response"""
    try:
        request_headers = {}
        if token != "":
            request_headers = {
                "accept": "application/json",
                "authorization": f"Bearer {token}"
            }
        r = requests.request(method = verb, url = base_url + uri, json = parameters, headers=request_headers)
        r.raise_for_status()
        return r
    except requests.exceptions.RequestException as e:
        pprint(f"""Something happened with the request.
Status Code: {r.status_code}
Exception: {e.__class__.__name__} {e}""")
        pprint(r.json())
    except Exception as e:
        print(f"Something went wrong: {e.__class__.__name__} {e}")

def load_yaml(filename):
    with open(file = filename, mode = "r") as f:
        loaded = yaml.safe_load(f)
    return loaded

def refresh_token(api_gateway_file: str = "apis.yaml", secrets_file: str = "secrets.yaml") -> dict:
    """refresh token and update secrets file"""
    #import gateway url and uri's from yaml
    api_gateway_uri = load_yaml(api_gateway_file)
    rest_gateway = api_gateway_uri["rest_gateway"]["url"]
    refresh_method = api_gateway_uri["refresh"]["method"]
    refresh_uri = api_gateway_uri["refresh"]["uri"]
    #import secrets from yaml
    secrets = load_yaml(secrets_file)
    refresh_params= {"client_id" : secrets["client_id"],
                       "client_secret" : secrets["client_secret"],
                       "grant_type" : "refresh_token",
                       "refresh_token" : secrets["refresh_token"]}
    #request refresh
    refresh_token = make_request(refresh_method, rest_gateway, refresh_uri, refresh_params)
    if refresh_token != None:
        refresh_token = refresh_token.json()
    else:
        raise TypeError("The call to refresh your token failed. Double check your secret parameters in secrets.yaml and your api gateway in apis.yaml.")
#update secrets
    secrets["access_token"] = refresh_token["access_token"]
    secrets["refresh_token"] = refresh_token["refresh_token"]
    with open(file = secrets_file, mode = "w") as yf:
        yaml.dump(secrets, yf, default_flow_style=False)
        print("secret update successful")

def main():
#refresh token and update secrets file

    refresh_token()
    
#load fresh secrets and apis for work

    secrets = load_yaml("secrets.yaml")
    apis = load_yaml("apis.yaml")
    base_rest_gateway = apis["rest_gateway"]["url"]
    data = pd.read_excel("aps_serials.xlsx").fillna("").to_dict()
    delete_ap_site_method = apis["delete_ap_site"]["method"]
    delete_ap_site_uri = apis["delete_ap_site"]["uri"]
    post_ap_site_method = apis["post_ap_site"]["method"]
    post_ap_site_uri = apis["post_ap_site"]["uri"]
    get_site_method = apis["get_site"]["method"]
    get_site_uri = apis["get_site"]["uri"]
    
#get sites

    site_info = make_request(get_site_method, base_rest_gateway, get_site_uri, token = secrets["access_token"]).json()
    pprint(site_info)
    site_name_to_id = {}
    for site in site_info["sites"]:
        site_name_to_id[site["site_name"]] = site["site_id"]

# remove existing site assignment; skip is old_site empty as would be the case with Unassigned APs. 

    for index, serial in data["serial number"].items():
        print(f"index {index} serial {serial}")
        print(data["old_site"][index])
        if data["old_site"][index] != "":
            payload = {
        "device_type": "IAP",
        "device_id": f"{serial}",
        "site_id": site_name_to_id[data["old_site"][index]]
            }
            r = make_request(delete_ap_site_method, base_rest_gateway, delete_ap_site_uri, payload, token = secrets["access_token"])
            if r != None:
                if r.status_code == 200:
                    print(f"successfully deleted ap with serial {serial} from old site {data["old_site"][index]}")
                else:
                    print(f"Something went wrong:")
                    print(r.status_code)
                    print(r.headers)
        else:
            print(f"site not assigned to serial {serial}; skipping")
            next
            
        
#add new site assignment 
    
    for index, serial in data["serial number"].items():
        print(f"index {index} serial {serial}")
        payload = {
    "device_type": "IAP",
    "device_id": f"{serial}",
    "site_id": site_name_to_id[data["new_site"][index]]
        }
        r = make_request(post_ap_site_method, base_rest_gateway, post_ap_site_uri, payload, token = secrets["access_token"])
        if r != None:
            if r.status_code == 200:
                print(f"successfully updated ap with serial {serial} to new site {data["new_site"][index]}")
            else:
                print(f"Something went wrong:")
                print(r.status_code)
                print(r.headers)

if __name__ == "__main__":
    main()