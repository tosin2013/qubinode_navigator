## python3 trigger-gitlab-pipeline.py --project_id=1 --token=glpt-mytoken --ref=main --target_server=servername --ssh_host=server.example.com --ssh_password=PASSWORD
import requests
import json
import fire

def trigger_pipeline(project_id: str, token: str, ref: str, **kwargs):
    # Replace the values below with your own
    GITLAB_HOST = 'https://gitlab.tosins-cloudlabs.com'

    # Build the API endpoint URL
    url = f"{GITLAB_HOST}/api/v4/projects/{project_id}/pipeline"

    # Create the request headers with the private token
    headers = {
        'Content-Type': 'application/json',
        'PRIVATE-TOKEN': token
    }

    # Create the request data with the ref and variables
    variables = [{"key": k.upper(), "value": v} for k, v in kwargs.items()]
    data = {
        'ref': ref,
        'variables': variables,
    }

    # Send the request to trigger the pipeline
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(data)

    # Check if the request was successful
    if response.status_code == 201:
        print(f"Pipeline triggered successfully: {response.json()['web_url']}")
    else:
        print(f"Failed to trigger pipeline: {response.text}")

if __name__ == '__main__':
    fire.Fire(trigger_pipeline)
