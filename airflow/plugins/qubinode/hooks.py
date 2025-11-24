"""
Qubinode Navigator Airflow Hooks
Hooks provide interfaces to external systems (kcli, AI Assistant)
"""

import subprocess
import requests
from typing import Dict, List, Any, Optional
from airflow.hooks.base import BaseHook


class KcliHook(BaseHook):
    """
    Hook for interacting with kcli CLI
    Provides methods for VM lifecycle management
    """
    
    conn_name_attr = 'kcli_conn_id'
    default_conn_name = 'kcli_default'
    conn_type = 'kcli'
    hook_name = 'Kcli'
    
    def __init__(self, kcli_conn_id: str = default_conn_name, **kwargs):
        super().__init__(**kwargs)
        self.kcli_conn_id = kcli_conn_id
    
    def run_kcli_command(self, command: List[str], check: bool = True) -> Dict[str, Any]:
        """
        Run a kcli command and return the result
        
        Args:
            command: List of command arguments (e.g., ['list', 'vm'])
            check: Whether to raise exception on non-zero exit code
            
        Returns:
            Dict with 'returncode', 'stdout', 'stderr'
        """
        full_command = ['kcli'] + command
        self.log.info(f"Running kcli command: {' '.join(full_command)}")
        
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=check
            )
            
            return {
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
        except subprocess.CalledProcessError as e:
            self.log.error(f"kcli command failed: {e}")
            return {
                'returncode': e.returncode,
                'stdout': e.stdout,
                'stderr': e.stderr,
                'success': False
            }
    
    def create_vm(self, vm_name: str, **kwargs) -> Dict[str, Any]:
        """
        Create a VM using kcli
        
        kcli uses -P for parameters and -i for image:
        kcli create vm <name> -i <image> -P memory=<MB> -P numcpus=<num> -P disks=[<size>]
        """
        command = ['create', 'vm', vm_name]
        
        # Add image (required)
        if 'image' in kwargs:
            command.extend(['-i', kwargs['image']])
        
        # Add parameters using -P flag (kcli parameter syntax)
        if 'memory' in kwargs:
            command.extend(['-P', f"memory={kwargs['memory']}"])
        if 'cpus' in kwargs:
            command.extend(['-P', f"numcpus={kwargs['cpus']}"])
        if 'disk_size' in kwargs:
            # kcli expects disk size without 'G' suffix in the parameter
            disk_size = str(kwargs['disk_size']).replace('G', '')
            command.extend(['-P', f"disks=[{disk_size}]"])
        
        return self.run_kcli_command(command)
    
    def delete_vm(self, vm_name: str, force: bool = False) -> Dict[str, Any]:
        """Delete a VM using kcli"""
        command = ['delete', 'vm', vm_name]
        if force:
            command.append('-y')
        return self.run_kcli_command(command)
    
    def list_vms(self) -> Dict[str, Any]:
        """List all VMs"""
        return self.run_kcli_command(['list', 'vm'])
    
    def get_vm_status(self, vm_name: str) -> Optional[str]:
        """Get status of a specific VM"""
        result = self.list_vms()
        if result['success']:
            # Parse output to find VM status
            # This is simplified - real implementation would parse the table output
            return 'running'  # Placeholder
        return None


class QuibinodeAIAssistantHook(BaseHook):
    """
    Hook for interacting with Qubinode Navigator AI Assistant
    Provides methods for AI-powered guidance and workflow generation
    """
    
    conn_name_attr = 'ai_assistant_conn_id'
    default_conn_name = 'qubinode_ai_default'
    conn_type = 'http'
    hook_name = 'Qubinode AI Assistant'
    
    def __init__(self, ai_assistant_conn_id: str = default_conn_name, **kwargs):
        super().__init__(**kwargs)
        self.ai_assistant_conn_id = ai_assistant_conn_id
        # Use container name for communication within the same Podman network
        self.base_url = 'http://qubinode-ai-assistant:8080'
    
    def ask_ai(self, question: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Ask the AI Assistant a question
        
        Args:
            question: The question to ask
            context: Optional context dictionary
            
        Returns:
            AI response dictionary
        """
        try:
            response = requests.post(
                f"{self.base_url}/chat",
                json={'message': question, 'context': context or {}},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.log.error(f"AI Assistant request failed: {e}")
            return {'error': str(e), 'success': False}
    
    def get_kcli_guidance(self, task_description: str) -> Dict[str, Any]:
        """
        Get AI guidance for a kcli task
        
        Args:
            task_description: Description of the kcli task
            
        Returns:
            AI guidance dictionary
        """
        question = f"How do I use kcli to {task_description}? Provide a step-by-step guide."
        return self.ask_ai(question, context={'tool': 'kcli', 'task_type': 'vm_provisioning'})
    
    def analyze_workflow_results(self, workflow_results: Dict) -> Dict[str, Any]:
        """
        Analyze workflow execution results using AI
        
        Args:
            workflow_results: Dictionary of workflow execution results
            
        Returns:
            AI analysis dictionary
        """
        question = f"Analyze these workflow results and provide recommendations: {workflow_results}"
        return self.ask_ai(question, context={'analysis_type': 'workflow_results'})
