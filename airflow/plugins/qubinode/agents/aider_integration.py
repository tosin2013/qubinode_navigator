"""
Aider Integration for Qubinode Multi-Agent System
ADR-0049: Multi-Agent LLM Memory Architecture

Provides integration with Aider for complex code modifications.
Aider is used by the Developer Agent for file-based code changes
that require understanding of project context.

Features:
- Non-interactive mode for automation
- RAG context injection
- Dry-run mode for preview
- Git integration for change tracking

Usage:
    from qubinode.agents.aider_integration import AiderClient

    client = AiderClient()
    result = await client.modify_files(
        instruction="Add error handling to the DAG",
        files=["dags/my_dag.py"],
        context="Error handling should include retries..."
    )
"""

import os
import logging
import subprocess
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)

# Configuration
AIDER_ENABLED = os.getenv("AIDER_ENABLED", "true").lower() == "true"
AIDER_MODEL = os.getenv("AIDER_MODEL", "ollama/granite-code:8b")
AIDER_TIMEOUT = int(os.getenv("AIDER_TIMEOUT", "300"))
DAGS_PATH = os.getenv("AIRFLOW_DAGS_PATH", "/opt/airflow/dags")
PLUGINS_PATH = os.getenv("AIRFLOW_PLUGINS_PATH", "/opt/airflow/plugins")


class AiderClient:
    """
    Client for interacting with Aider code assistant.

    Aider is used for complex code modifications that require
    understanding of multiple files and project context.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        working_dir: Optional[str] = None,
        auto_commit: bool = False
    ):
        """
        Initialize the Aider client.

        Args:
            model: LLM model for Aider to use
            working_dir: Working directory for Aider
            auto_commit: Whether to auto-commit changes
        """
        self.model = model or AIDER_MODEL
        self.working_dir = working_dir or DAGS_PATH
        self.auto_commit = auto_commit
        self._aider_available: Optional[bool] = None

        logger.info(f"AiderClient initialized: model={self.model}, dir={self.working_dir}")

    def is_available(self) -> bool:
        """Check if Aider is available."""
        if self._aider_available is None:
            try:
                result = subprocess.run(
                    ["aider", "--version"],
                    capture_output=True,
                    timeout=5
                )
                self._aider_available = result.returncode == 0
                if self._aider_available:
                    logger.info(f"Aider version: {result.stdout.decode().strip()}")
            except Exception as e:
                logger.warning(f"Aider not available: {e}")
                self._aider_available = False
        return self._aider_available and AIDER_ENABLED

    async def modify_files(
        self,
        instruction: str,
        files: List[str],
        context: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Use Aider to modify files based on instruction.

        Args:
            instruction: What to do to the files
            files: List of file paths to modify
            context: Additional context for the modification
            dry_run: Preview changes without applying

        Returns:
            Dictionary with success status and output
        """
        if not self.is_available():
            return {
                "success": False,
                "error": "Aider not available",
                "output": ""
            }

        # Build the prompt
        prompt = instruction
        if context:
            prompt = f"{context}\n\n{instruction}"

        # Create temporary file for prompt
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            # Build Aider command
            cmd = [
                "aider",
                "--yes",  # Non-interactive
                "--message-file", prompt_file,
                "--model", self.model
            ]

            if not self.auto_commit:
                cmd.append("--no-auto-commits")

            if dry_run:
                cmd.append("--dry-run")

            # Add files
            for file_path in files:
                # Ensure path is relative to working dir or absolute
                if not os.path.isabs(file_path):
                    file_path = os.path.join(self.working_dir, file_path)
                cmd.append(file_path)

            logger.info(f"Running Aider: {' '.join(cmd[:5])}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=AIDER_TIMEOUT,
                cwd=self.working_dir
            )

            success = result.returncode == 0
            output = result.stdout if success else result.stderr

            return {
                "success": success,
                "output": output,
                "return_code": result.returncode,
                "files_modified": files,
                "dry_run": dry_run
            }

        except subprocess.TimeoutExpired:
            logger.error("Aider timed out")
            return {
                "success": False,
                "error": f"Aider timed out after {AIDER_TIMEOUT} seconds",
                "output": ""
            }
        except Exception as e:
            logger.error(f"Aider execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }
        finally:
            # Clean up temp file
            try:
                os.unlink(prompt_file)
            except Exception:
                pass

    async def create_file(
        self,
        instruction: str,
        file_path: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use Aider to create a new file.

        Args:
            instruction: What the file should contain/do
            file_path: Path for the new file
            context: Additional context

        Returns:
            Dictionary with success status and output
        """
        # Ensure parent directory exists
        full_path = file_path if os.path.isabs(file_path) else os.path.join(self.working_dir, file_path)
        parent_dir = os.path.dirname(full_path)
        os.makedirs(parent_dir, exist_ok=True)

        # Create empty file so Aider can modify it
        Path(full_path).touch()

        result = await self.modify_files(
            instruction=f"Create the file {file_path} with the following:\n{instruction}",
            files=[file_path],
            context=context
        )

        return result

    async def add_to_file(
        self,
        file_path: str,
        content: str,
        position: str = "end"
    ) -> Dict[str, Any]:
        """
        Add content to an existing file.

        Args:
            file_path: Path to the file
            content: Content to add
            position: Where to add ('start', 'end', or line number)

        Returns:
            Dictionary with success status
        """
        instruction = f"Add the following to the {position} of the file:\n\n{content}"

        return await self.modify_files(
            instruction=instruction,
            files=[file_path]
        )

    async def refactor(
        self,
        files: List[str],
        refactor_type: str,
        target: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform a refactoring operation.

        Args:
            files: Files to refactor
            refactor_type: Type of refactoring (rename, extract, inline, etc.)
            target: What to refactor
            context: Additional context

        Returns:
            Dictionary with success status
        """
        refactor_instructions = {
            "rename": f"Rename '{target}' to a more descriptive name",
            "extract": f"Extract '{target}' into a separate function/class",
            "inline": f"Inline the function/variable '{target}'",
            "simplify": f"Simplify the code in '{target}'",
            "add_docstring": f"Add comprehensive docstrings to '{target}'",
            "add_tests": f"Add unit tests for '{target}'"
        }

        instruction = refactor_instructions.get(
            refactor_type,
            f"Perform {refactor_type} refactoring on '{target}'"
        )

        return await self.modify_files(
            instruction=instruction,
            files=files,
            context=context
        )

    async def fix_error(
        self,
        file_path: str,
        error_message: str,
        error_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use Aider to fix an error in code.

        Args:
            file_path: File with the error
            error_message: The error message
            error_context: Additional context about the error

        Returns:
            Dictionary with success status
        """
        instruction = f"""Fix the following error in the code:

Error: {error_message}
"""
        if error_context:
            instruction += f"\nContext: {error_context}"

        return await self.modify_files(
            instruction=instruction,
            files=[file_path]
        )

    async def generate_dag(
        self,
        dag_name: str,
        description: str,
        tasks: List[Dict[str, str]],
        template: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a new DAG file using Aider.

        Args:
            dag_name: Name for the DAG
            description: What the DAG does
            tasks: List of task definitions
            template: Optional template to base on

        Returns:
            Dictionary with success status and file path
        """
        file_path = f"dags/{dag_name}.py"

        # Build task descriptions
        task_desc = "\n".join([
            f"- {t.get('name', 'task')}: {t.get('description', '')}"
            for t in tasks
        ])

        instruction = f"""Create an Airflow DAG named '{dag_name}' that:

{description}

Tasks to include:
{task_desc}

Requirements:
- Use the project's DAG Factory pattern if applicable
- Include proper error handling with retries
- Add docstrings and comments
- Follow Provider-First rule for operators
- Set appropriate task dependencies
"""

        if template:
            instruction += f"\n\nBase on this template:\n```python\n{template}\n```"

        # Create the file first
        full_path = os.path.join(self.working_dir, file_path)
        parent_dir = os.path.dirname(full_path)
        os.makedirs(parent_dir, exist_ok=True)
        Path(full_path).touch()

        result = await self.modify_files(
            instruction=instruction,
            files=[file_path]
        )

        result["file_path"] = file_path
        return result


class AiderBatchProcessor:
    """
    Batch processor for multiple Aider operations.

    Useful for large-scale refactoring or multi-file changes.
    """

    def __init__(self, client: Optional[AiderClient] = None):
        self.client = client or AiderClient()
        self.results: List[Dict[str, Any]] = []

    async def process_batch(
        self,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a batch of operations.

        Args:
            operations: List of operation dictionaries
                Each should have 'type' and relevant parameters

        Returns:
            Batch result summary
        """
        self.results = []
        success_count = 0
        failure_count = 0

        for op in operations:
            op_type = op.get("type")

            try:
                if op_type == "modify":
                    result = await self.client.modify_files(
                        instruction=op.get("instruction", ""),
                        files=op.get("files", []),
                        context=op.get("context")
                    )
                elif op_type == "create":
                    result = await self.client.create_file(
                        instruction=op.get("instruction", ""),
                        file_path=op.get("file_path", ""),
                        context=op.get("context")
                    )
                elif op_type == "refactor":
                    result = await self.client.refactor(
                        files=op.get("files", []),
                        refactor_type=op.get("refactor_type", "simplify"),
                        target=op.get("target", ""),
                        context=op.get("context")
                    )
                elif op_type == "fix":
                    result = await self.client.fix_error(
                        file_path=op.get("file_path", ""),
                        error_message=op.get("error_message", ""),
                        error_context=op.get("error_context")
                    )
                else:
                    result = {
                        "success": False,
                        "error": f"Unknown operation type: {op_type}"
                    }

                if result.get("success"):
                    success_count += 1
                else:
                    failure_count += 1

                self.results.append({
                    "operation": op,
                    "result": result
                })

            except Exception as e:
                failure_count += 1
                self.results.append({
                    "operation": op,
                    "result": {"success": False, "error": str(e)}
                })

        return {
            "total": len(operations),
            "success": success_count,
            "failed": failure_count,
            "results": self.results
        }


# Singleton instance
_aider_client: Optional[AiderClient] = None


def get_aider_client() -> AiderClient:
    """Get or create the default Aider client singleton."""
    global _aider_client
    if _aider_client is None:
        _aider_client = AiderClient()
    return _aider_client


__version__ = "1.0.0"
__all__ = [
    "AiderClient",
    "AiderBatchProcessor",
    "get_aider_client"
]
