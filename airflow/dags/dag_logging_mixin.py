"""
DAG Logging Mixin - Enhanced logging for all Qubinode DAGs
Provides consistent, detailed logging across all workflows
"""

import logging
from datetime import datetime
from typing import Any, Dict


class DAGLoggingMixin:
    """
    Mixin to add enhanced logging to all DAG tasks
    Automatically logs task start, end, parameters, and results
    """

    @staticmethod
    def setup_task_logging(task_id: str, **kwargs) -> logging.Logger:
        """
        Set up enhanced logging for a task with context
        """
        logger = logging.getLogger(f"airflow.task.{task_id}")
        logger.setLevel(logging.INFO)

        # Log task context
        logger.info("=" * 80)
        logger.info(f"🚀 Starting Task: {task_id}")
        logger.info(f"⏰ Execution Date: {kwargs.get('execution_date', 'N/A')}")
        logger.info(f"🔄 Try Number: {kwargs.get('try_number', 1)}")
        logger.info(f"📋 DAG ID: {kwargs.get('dag', {}).get('dag_id', 'N/A')}")
        logger.info("=" * 80)

        return logger

    @staticmethod
    def log_parameters(logger: logging.Logger, params: Dict[str, Any]):
        """Log task parameters"""
        logger.info("📝 Task Parameters:")
        for key, value in params.items():
            logger.info(f"   • {key}: {value}")

    @staticmethod
    def log_result(logger: logging.Logger, result: Any, task_id: str):
        """Log task result"""
        logger.info("=" * 80)
        logger.info(f"✅ Task {task_id} Completed Successfully")
        logger.info(f"📊 Result: {result}")
        logger.info(f"⏱️  Completed At: {datetime.now().isoformat()}")
        logger.info("=" * 80)

    @staticmethod
    def log_error(logger: logging.Logger, error: Exception, task_id: str):
        """Log task error with context"""
        logger.error("=" * 80)
        logger.error(f"❌ Task {task_id} Failed")
        logger.error(f"🔴 Error Type: {type(error).__name__}")
        logger.error(f"💥 Error Message: {str(error)}")
        logger.error(f"⏱️  Failed At: {datetime.now().isoformat()}")
        logger.error("=" * 80)
        logger.exception("Full Traceback:")


def log_task_start(task_id: str, **context):
    """Decorator-friendly logging function"""
    logger = DAGLoggingMixin.setup_task_logging(task_id, **context)
    return logger


def create_logging_callback(**kwargs):
    """
    Callback to add to any operator for automatic logging
    Usage in DAG:
        task = MyOperator(
            task_id='my_task',
            on_execute_callback=create_logging_callback
        )
    """
    task_instance = kwargs.get("task_instance")
    logger = logging.getLogger(f"airflow.task.{task_instance.task_id}")

    logger.info("📋 Task Context:")
    logger.info(f"   • DAG: {task_instance.dag_id}")
    logger.info(f"   • Task: {task_instance.task_id}")
    logger.info(f"   • Execution Date: {task_instance.execution_date}")
    logger.info(f"   • Try: {task_instance.try_number}")
    logger.info(f"   • State: {task_instance.state}")

    return logger
