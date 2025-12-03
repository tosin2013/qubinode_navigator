"""
Qubinode Navigator Airflow Plugins
Phase 6 Goal 2: Custom operators, sensors, and hooks for infrastructure automation
Based on: ADR-0036 (Airflow Integration)
"""

from airflow.plugins_manager import AirflowPlugin
from qubinode.operators import (
    KcliVMCreateOperator,
    KcliVMDeleteOperator,
    KcliVMListOperator,
)
from qubinode.virsh_operators import (
    VirshCommandOperator,
    VirshVMStartOperator,
    VirshVMStopOperator,
    VirshVMInfoOperator,
    VirshNetworkListOperator,
)
from qubinode.sensors import KcliVMStatusSensor
from qubinode.hooks import KcliHook, QuibinodeAIAssistantHook


class QuibinodePlugin(AirflowPlugin):
    """Qubinode Navigator plugin for Airflow"""

    name = "qubinode"
    operators = [
        # kcli operators
        KcliVMCreateOperator,
        KcliVMDeleteOperator,
        KcliVMListOperator,
        # virsh operators
        VirshCommandOperator,
        VirshVMStartOperator,
        VirshVMStopOperator,
        VirshVMInfoOperator,
        VirshNetworkListOperator,
    ]
    sensors = [KcliVMStatusSensor]
    hooks = [KcliHook, QuibinodeAIAssistantHook]
