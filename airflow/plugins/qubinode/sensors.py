"""
Qubinode Navigator Airflow Sensors
Sensors for monitoring VM status and readiness
"""

from typing import Dict, Any
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
from qubinode.hooks import KcliHook


class KcliVMStatusSensor(BaseSensorOperator):
    """
    Sensor to wait for a VM to reach a specific status

    Example:
        wait_for_vm = KcliVMStatusSensor(
            task_id='wait_for_vm_running',
            vm_name='centos-stream-10-vm',
            expected_status='running',
            timeout=300,
            poke_interval=30
        )
    """

    template_fields = ("vm_name", "expected_status")
    ui_color = "#FF9800"

    @apply_defaults
    def __init__(
        self,
        vm_name: str,
        expected_status: str = "running",
        kcli_conn_id: str = "kcli_default",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.vm_name = vm_name
        self.expected_status = expected_status
        self.kcli_conn_id = kcli_conn_id

    def poke(self, context: Dict[str, Any]) -> bool:
        """Check if VM has reached expected status"""
        self.log.info(f"Checking status of VM: {self.vm_name}")

        kcli_hook = KcliHook(kcli_conn_id=self.kcli_conn_id)
        status = kcli_hook.get_vm_status(self.vm_name)

        if status == self.expected_status:
            self.log.info(f"✅ VM {self.vm_name} is {self.expected_status}")
            return True
        else:
            self.log.info(
                f"⏳ VM {self.vm_name} is {status}, waiting for {self.expected_status}"
            )
            return False
