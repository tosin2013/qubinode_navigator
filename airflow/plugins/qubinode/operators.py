"""
Qubinode Navigator Airflow Operators
Custom operators for kcli VM lifecycle management
"""

from typing import Dict, Any, Optional
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from qubinode.hooks import KcliHook, QuibinodeAIAssistantHook


class KcliVMCreateOperator(BaseOperator):
    """
    Operator to create a VM using kcli

    Example:
        create_vm = KcliVMCreateOperator(
            task_id='create_centos_vm',
            vm_name='centos-stream-10-vm',
            image='centos-stream-10',
            memory=4096,
            cpus=2,
            disk_size='20G'
        )
    """

    template_fields = ("vm_name", "image")
    ui_color = "#4CAF50"

    @apply_defaults
    def __init__(
        self,
        vm_name: str,
        image: Optional[str] = None,
        memory: Optional[int] = None,
        cpus: Optional[int] = None,
        disk_size: Optional[str] = None,
        kcli_conn_id: str = "kcli_default",
        ai_assistance: bool = True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.vm_name = vm_name
        self.image = image
        self.memory = memory
        self.cpus = cpus
        self.disk_size = disk_size
        self.kcli_conn_id = kcli_conn_id
        self.ai_assistance = ai_assistance

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute VM creation"""
        self.log.info(f"Creating VM: {self.vm_name}")

        # Get AI guidance if enabled
        if self.ai_assistance:
            ai_hook = QuibinodeAIAssistantHook()
            guidance = ai_hook.get_kcli_guidance(f"create a VM named {self.vm_name}")
            self.log.info(f"AI Guidance: {guidance}")

        # Create VM using kcli
        kcli_hook = KcliHook(kcli_conn_id=self.kcli_conn_id)
        result = kcli_hook.create_vm(
            vm_name=self.vm_name,
            image=self.image,
            memory=self.memory,
            cpus=self.cpus,
            disk_size=self.disk_size,
        )

        if result["success"]:
            self.log.info(f"✅ VM {self.vm_name} created successfully")
            return {
                "vm_name": self.vm_name,
                "status": "created",
                "output": result["stdout"],
            }
        else:
            self.log.error(f"❌ Failed to create VM {self.vm_name}: {result['stderr']}")
            raise RuntimeError(f"VM creation failed: {result['stderr']}")


class KcliVMDeleteOperator(BaseOperator):
    """
    Operator to delete a VM using kcli

    Example:
        delete_vm = KcliVMDeleteOperator(
            task_id='delete_vm',
            vm_name='centos-stream-10-vm',
            force=True
        )
    """

    template_fields = ("vm_name",)
    ui_color = "#F44336"

    @apply_defaults
    def __init__(
        self,
        vm_name: str,
        force: bool = False,
        kcli_conn_id: str = "kcli_default",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.vm_name = vm_name
        self.force = force
        self.kcli_conn_id = kcli_conn_id

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute VM deletion"""
        self.log.info(f"Deleting VM: {self.vm_name}")

        kcli_hook = KcliHook(kcli_conn_id=self.kcli_conn_id)
        result = kcli_hook.delete_vm(vm_name=self.vm_name, force=self.force)

        if result["success"]:
            self.log.info(f"✅ VM {self.vm_name} deleted successfully")
            return {
                "vm_name": self.vm_name,
                "status": "deleted",
                "output": result["stdout"],
            }
        else:
            self.log.error(f"❌ Failed to delete VM {self.vm_name}: {result['stderr']}")
            raise RuntimeError(f"VM deletion failed: {result['stderr']}")


class KcliVMListOperator(BaseOperator):
    """
    Operator to list VMs using kcli

    Example:
        list_vms = KcliVMListOperator(
            task_id='list_all_vms'
        )
    """

    ui_color = "#2196F3"

    @apply_defaults
    def __init__(self, kcli_conn_id: str = "kcli_default", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kcli_conn_id = kcli_conn_id

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute VM listing"""
        self.log.info("Listing all VMs")

        kcli_hook = KcliHook(kcli_conn_id=self.kcli_conn_id)
        result = kcli_hook.list_vms()

        if result["success"]:
            self.log.info("✅ VM list retrieved successfully")
            self.log.info(f"VMs:\n{result['stdout']}")
            return {
                "status": "success",
                "output": result["stdout"],
                "vm_count": result["stdout"].count("\n")
                - 2,  # Rough count excluding header
            }
        else:
            self.log.error(f"❌ Failed to list VMs: {result['stderr']}")
            raise RuntimeError(f"VM listing failed: {result['stderr']}")
