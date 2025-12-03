#!/usr/bin/env python3

# =============================================================================
# GitLab Pipeline Trigger - The "CI/CD Orchestrator"
# =============================================================================
#
# 🎯 PURPOSE FOR LLMs:
# This script triggers GitLab CI/CD pipelines remotely with dynamic variables,
# enabling automated deployment workflows and infrastructure provisioning from
# external systems or manual triggers.
#
# 🧠 ARCHITECTURE OVERVIEW FOR AI ASSISTANTS:
# This script implements GitLab API integration:
# 1. [PHASE 1]: Parameter Collection - Gathers project ID, token, and variables
# 2. [PHASE 2]: API Request Building - Constructs GitLab API pipeline trigger request
# 3. [PHASE 3]: Variable Injection - Passes dynamic variables to pipeline execution
# 4. [PHASE 4]: Pipeline Execution - Triggers remote GitLab pipeline with variables
#
# 🔧 HOW IT CONNECTS TO QUBINODE NAVIGATOR:
# - [CI/CD Integration]: Enables remote triggering of deployment pipelines
# - [Variable Passing]: Injects environment-specific variables into pipelines
# - [External Triggers]: Allows triggering from external systems or scripts
# - [GitLab Integration]: Integrates with GitLab-based CI/CD workflows
# - [Automation Bridge]: Connects manual processes with automated pipelines
#
# 📊 KEY DESIGN PRINCIPLES FOR LLMs TO UNDERSTAND:
# - [API-Driven]: Uses GitLab REST API for pipeline triggering
# - [Variable Injection]: Supports dynamic variable passing to pipelines
# - [Flexible Parameters]: Accepts arbitrary keyword arguments as pipeline variables
# - [Error Handling]: Provides clear feedback on pipeline trigger success/failure
# - [Security Aware]: Uses private tokens for GitLab authentication
#
# 💡 WHEN TO MODIFY THIS SCRIPT (for future LLMs):
# - [API Updates]: Update for new GitLab API versions or endpoints
# - [Authentication]: Add support for new GitLab authentication methods
# - [Variable Handling]: Enhance variable validation or transformation
# - [Error Handling]: Improve error reporting and retry mechanisms
# - [Integration Features]: Add support for pipeline status monitoring
#
# 🚨 IMPORTANT FOR LLMs: This script requires GitLab private tokens and triggers
# remote CI/CD pipelines. It can initiate infrastructure deployments and should be
# used carefully. Variables passed may contain sensitive information.

## Usage Example:
## python3 trigger-gitlab-pipeline.py --project_id=1 --token=glpt-mytoken --ref=main --target_server=servername --ssh_host=server.example.com --ssh_password=PASSWORD

import json

import fire
import requests


# Pipeline Trigger Engine - The "Remote Deployment Initiator"
def trigger_pipeline(project_id: str, token: str, ref: str, **kwargs):
    """
    🎯 FOR LLMs: This function triggers GitLab CI/CD pipelines remotely using the
    GitLab API, passing dynamic variables to enable environment-specific deployments.

    🔄 WORKFLOW:
    1. Constructs GitLab API endpoint URL for pipeline triggering
    2. Builds authentication headers with private token
    3. Converts keyword arguments to GitLab pipeline variables
    4. Sends POST request to trigger pipeline execution
    5. Reports success/failure status with pipeline URL

    📊 INPUTS/OUTPUTS:
    - INPUT: project_id (GitLab project ID), token (private token), ref (branch/tag), **kwargs (pipeline variables)
    - OUTPUT: Triggered GitLab pipeline with injected variables

    ⚠️  SIDE EFFECTS: Triggers remote CI/CD pipeline, may initiate infrastructure deployments
    """
    # 🔧 CONFIGURATION CONSTANTS FOR LLMs:
    GITLAB_HOST = "https://gitlab.tosins-cloudlabs.com"  # GitLab instance URL

    # Build the API endpoint URL
    url = f"{GITLAB_HOST}/api/v4/projects/{project_id}/pipeline"

    # Create the request headers with the private token
    headers = {"Content-Type": "application/json", "PRIVATE-TOKEN": token}

    # Create the request data with the ref and variables
    # Convert all kwargs to uppercase GitLab variables
    variables = [{"key": k.upper(), "value": v} for k, v in kwargs.items()]
    data = {
        "ref": ref,
        "variables": variables,
    }

    # Send the request to trigger the pipeline
    response = requests.post(url, headers=headers, data=json.dumps(data))
    print(data)

    # Check if the request was successful
    if response.status_code == 201:
        print(f"Pipeline triggered successfully: {response.json()['web_url']}")
    else:
        print(f"Failed to trigger pipeline: {response.text}")


if __name__ == "__main__":
    fire.Fire(trigger_pipeline)
