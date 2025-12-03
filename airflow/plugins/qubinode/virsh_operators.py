"""
Virsh Operators for Direct libvirt Management
Provides operators for virsh commands alongside kcli operators
"""

import subprocess
from typing import Any, Dict, List, Optional

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults


class VirshCommandOperator(BaseOperator):
    """
    Generic operator to run any virsh command

    Example:
        virsh_list = VirshCommandOperator(
            task_id='list_vms',
            command=['list', '--all']
        )
    """

    template_fields = ("command",)
    ui_color = "#FF6B6B"

    @apply_defaults
    def __init__(
        self,
        command: List[str],
        connection_uri: str = "qemu:///system",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.command = command
        self.connection_uri = connection_uri

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute virsh command"""
        full_command = ["virsh", "-c", self.connection_uri] + self.command
        self.log.info(f"Running virsh command: {' '.join(full_command)}")

        try:
            result = subprocess.run(
                full_command, capture_output=True, text=True, check=True
            )

            self.log.info(f"✅ Command succeeded")
            self.log.info(f"Output:\n{result.stdout}")

            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": True,
            }

        except subprocess.CalledProcessError as e:
            self.log.error(f"❌ Command failed: {e}")
            self.log.error(f"Error output:\n{e.stderr}")
            raise


class VirshVMStartOperator(BaseOperator):
    """
    Start a VM using virsh

    Example:
        start_vm = VirshVMStartOperator(
            task_id='start_vm',
            vm_name='centos-stream-10'
        )
    """

    template_fields = ("vm_name",)
    ui_color = "#4CAF50"

    @apply_defaults
    def __init__(
        self, vm_name: str, connection_uri: str = "qemu:///system", *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.vm_name = vm_name
        self.connection_uri = connection_uri

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Start VM"""
        self.log.info(f"Starting VM: {self.vm_name}")

        result = subprocess.run(
            ["virsh", "-c", self.connection_uri, "start", self.vm_name],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            self.log.info(f"✅ VM {self.vm_name} started successfully")
            return {"vm_name": self.vm_name, "status": "started"}
        else:
            self.log.error(f"❌ Failed to start VM: {result.stderr}")
            raise RuntimeError(f"Failed to start VM: {result.stderr}")


class VirshVMStopOperator(BaseOperator):
    """
    Stop a VM using virsh

    Example:
        stop_vm = VirshVMStopOperator(
            task_id='stop_vm',
            vm_name='centos-stream-10',
            force=False
        )
    """

    template_fields = ("vm_name",)
    ui_color = "#F44336"

    @apply_defaults
    def __init__(
        self,
        vm_name: str,
        force: bool = False,
        connection_uri: str = "qemu:///system",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.vm_name = vm_name
        self.force = force
        self.connection_uri = connection_uri

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Stop VM"""
        command = ["virsh", "-c", self.connection_uri]

        if self.force:
            command.extend(["destroy", self.vm_name])
            self.log.info(f"Force stopping VM: {self.vm_name}")
        else:
            command.extend(["shutdown", self.vm_name])
            self.log.info(f"Gracefully stopping VM: {self.vm_name}")

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode == 0:
            self.log.info(f"✅ VM {self.vm_name} stopped successfully")
            return {"vm_name": self.vm_name, "status": "stopped"}
        else:
            self.log.error(f"❌ Failed to stop VM: {result.stderr}")
            raise RuntimeError(f"Failed to stop VM: {result.stderr}")


class VirshVMInfoOperator(BaseOperator):
    """
    Get VM information using virsh dominfo

    Example:
        vm_info = VirshVMInfoOperator(
            task_id='get_vm_info',
            vm_name='centos-stream-10'
        )
    """

    template_fields = ("vm_name",)
    ui_color = "#2196F3"

    @apply_defaults
    def __init__(
        self, vm_name: str, connection_uri: str = "qemu:///system", *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.vm_name = vm_name
        self.connection_uri = connection_uri

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get VM info"""
        self.log.info(f"Getting info for VM: {self.vm_name}")

        result = subprocess.run(
            ["virsh", "-c", self.connection_uri, "dominfo", self.vm_name],
            capture_output=True,
            text=True,
            check=True,
        )

        self.log.info(f"VM Info:\n{result.stdout}")

        # Parse output into dict
        info = {}
        for line in result.stdout.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                info[key.strip()] = value.strip()

        return {"vm_name": self.vm_name, "info": info, "raw_output": result.stdout}


class VirshNetworkListOperator(BaseOperator):
    """
    List libvirt networks using virsh

    Example:
        list_networks = VirshNetworkListOperator(
            task_id='list_networks',
            show_inactive=True
        )
    """

    ui_color = "#9C27B0"

    @apply_defaults
    def __init__(
        self,
        show_inactive: bool = True,
        connection_uri: str = "qemu:///system",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.show_inactive = show_inactive
        self.connection_uri = connection_uri

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """List networks"""
        command = ["virsh", "-c", self.connection_uri, "net-list"]

        if self.show_inactive:
            command.append("--all")

        self.log.info(f"Listing libvirt networks")

        result = subprocess.run(command, capture_output=True, text=True, check=True)

        self.log.info(f"Networks:\n{result.stdout}")

        return {
            "status": "success",
            "output": result.stdout,
            "network_count": result.stdout.count("\n") - 2,  # Exclude header
        }
