import requests 
import os 

FM_PORT = os.getenv("FM_PORT")
FM_VERSION = os.getenv("FM_TAG")
response = requests.get(f"http://localhost:{FM_PORT}/openapi.json")
resp_json = response.json()


show_only = ["/api/v1/trips"]
show_all = False

print(f"FM Version: {FM_VERSION}")

if not show_all:
    print(f"**This doc would only show apis that start with any of {show_only}**\n\n")


all_path_details= resp_json["paths"]
all_components = resp_json["components"]

count = 1
for url, details in all_path_details.items():
    if any([item in url for item in show_only]) or show_all:
        print(f"{count}) URL: {url}")
        req_method = list(details.keys())[0]
        print(f"METHOD: {req_method}")

        other_details = details[req_method]
        req_body = other_details.get("requestBody")
        params = other_details.get("parameters")
        
        print(f"Parameters required")
        param_count=0
        for param in params:
            param_count+=1
            p_title= param["schema"].get("title")
            p_type = param["schema"].get("type")
            to_be_sent_in = param["in"]
            print(f"\t\t{param_count}) {p_title}: {p_type}, \t  in: {to_be_sent_in}")

        if req_body:
            contents = req_body.get("content")
            for content_type, content_details in contents.items():
                print(f"Content-Type: {content_type}")
                schemas = content_details["schema"]
                for schema_val in schemas.values():
                    component_name = schema_val.rsplit("/", 1)[-1]
                    req_schema = all_components["schemas"].get(component_name)
                    req_props = req_schema["properties"]
                    print(f"Request Body Schema:")
                    for req_key, req_prop in req_props.items():
                        try:
                            title = req_prop["title"]
                            temp_type = req_prop["type"]
                            print(f"\t\t{title}: {temp_type}")
                        except:
                            pass
        print("\n\n\n")
        count+=1

