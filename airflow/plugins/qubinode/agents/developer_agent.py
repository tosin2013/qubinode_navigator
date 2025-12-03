"""
Developer Agent for Qubinode Multi-Agent System
ADR-0049: Multi-Agent LLM Memory Architecture

The Developer Agent handles code generation and execution tasks,
augmented by RAG context. It integrates with Aider for complex
code modifications and can use MCP tools for DAG operations.

Responsibilities:
- RAG-augmented code generation
- Aider integration for code modifications
- Provider-compliant implementations
- Code validation and testing
- Troubleshooting with historical context

Usage:
    from qubinode.agents import DeveloperAgent

    developer = DeveloperAgent()
    result = await developer.execute_task(
        task="Create SSH health check task",
        rag_context={"documents": [...], "troubleshooting": [...]},
        session_id="uuid-here"
    )
"""

import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuration
AIDER_ENABLED = os.getenv("AIDER_ENABLED", "true").lower() == "true"
DAGS_PATH = os.getenv("AIRFLOW_DAGS_PATH", "/opt/airflow/dags")
PLUGINS_PATH = os.getenv("AIRFLOW_PLUGINS_PATH", "/opt/airflow/plugins")


class DeveloperAgent:
    """
    Developer Agent for RAG-augmented code generation.

    The Developer Agent:
    1. Receives tasks from Manager Agent
    2. Uses RAG context to inform code generation
    3. Leverages Aider for complex code changes
    4. Validates generated code
    5. Logs troubleshooting attempts
    """

    def __init__(self, rag_store=None, llm_router=None, model: str = "developer"):
        """
        Initialize the Developer Agent.

        Args:
            rag_store: RAGStore instance for knowledge queries
            llm_router: LLMRouter instance for LLM calls
            model: Model to use for code generation
        """
        self.rag_store = rag_store
        self.llm_router = llm_router
        self.model = model
        self._aider_available = None

        logger.info("DeveloperAgent initialized")

    def _get_rag_store(self):
        """Lazy load RAG store."""
        if self.rag_store is None:
            try:
                from qubinode.rag_store import get_rag_store

                self.rag_store = get_rag_store()
            except Exception as e:
                logger.warning(f"Could not load RAG store: {e}")
        return self.rag_store

    def _get_llm_router(self):
        """Lazy load LLM router."""
        if self.llm_router is None:
            try:
                from qubinode.llm_router import get_router

                self.llm_router = get_router()
            except Exception as e:
                logger.warning(f"Could not load LLM router: {e}")
        return self.llm_router

    def _check_aider_available(self) -> bool:
        """Check if Aider is available."""
        if self._aider_available is None:
            try:
                result = subprocess.run(
                    ["aider", "--version"], capture_output=True, timeout=5
                )
                self._aider_available = result.returncode == 0
            except Exception:
                self._aider_available = False
        return self._aider_available and AIDER_ENABLED

    async def execute_task(
        self, task: str, rag_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """
        Execute a development task with RAG augmentation.

        Args:
            task: Task description
            rag_context: Context from RAG queries
            session_id: Session ID for tracking

        Returns:
            Dictionary with success status and output
        """
        logger.info(f"Executing task: {task[:100]}...")

        try:
            # Analyze task to determine approach
            task_type = self._classify_task(task)

            if task_type == "dag_creation":
                return await self._create_dag(task, rag_context, session_id)
            elif task_type == "code_modification":
                return await self._modify_code(task, rag_context, session_id)
            elif task_type == "troubleshooting":
                return await self._troubleshoot(task, rag_context, session_id)
            else:
                return await self._generate_code(task, rag_context, session_id)

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            await self._log_troubleshooting(
                session_id=session_id,
                task=task,
                solution=f"Attempted: {task_type}",
                result="failed",
                error=str(e),
            )
            return {"success": False, "output": "", "error": str(e)}

    def _classify_task(self, task: str) -> str:
        """Classify the task type."""
        task_lower = task.lower()

        if "dag" in task_lower and ("create" in task_lower or "new" in task_lower):
            return "dag_creation"
        elif "fix" in task_lower or "debug" in task_lower or "error" in task_lower:
            return "troubleshooting"
        elif "modify" in task_lower or "update" in task_lower or "change" in task_lower:
            return "code_modification"
        else:
            return "general"

    async def _create_dag(
        self, task: str, rag_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """Create a new DAG based on task and RAG context."""
        logger.info("Creating new DAG...")

        # Extract relevant examples from RAG
        dag_examples = self._extract_dag_examples(rag_context)
        adr_guidance = self._extract_adr_guidance(rag_context)

        # Generate DAG code using LLM
        router = self._get_llm_router()
        if not router:
            return {"success": False, "output": "", "error": "LLM router not available"}

        prompt = self._build_dag_generation_prompt(task, dag_examples, adr_guidance)

        try:
            response = await router.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_dag_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # Lower for more consistent code
                max_tokens=4000,
            )

            code = response.get("content", "")

            # Extract Python code if wrapped in markdown
            code = self._extract_code_from_response(code)

            # Validate the generated code
            validation = self._validate_dag_code(code)

            if validation["valid"]:
                await self._log_troubleshooting(
                    session_id=session_id,
                    task=task,
                    solution=f"Generated DAG code ({len(code)} chars)",
                    result="success",
                )
                return {
                    "success": True,
                    "output": code,
                    "type": "dag",
                    "validation": validation,
                }
            else:
                return {
                    "success": False,
                    "output": code,
                    "error": validation["error"],
                    "validation": validation,
                }

        except Exception as e:
            logger.error(f"DAG generation failed: {e}")
            return {"success": False, "output": "", "error": str(e)}

    def _get_dag_system_prompt(self) -> str:
        """Get system prompt for DAG generation."""
        return """You are an expert Airflow DAG developer for the Qubinode Navigator project.

Guidelines:
1. Use the DAG Factory pattern established in ADR-0046
2. Prefer BashOperator with SSH for remote commands
3. Include proper error handling with retries
4. Add helpful docstrings and comments
5. Follow Provider-First rule - use official providers when available
6. Include XCom for passing data between tasks
7. Use proper task dependencies

Output only the Python code, no explanations.
"""

    def _build_dag_generation_prompt(
        self,
        task: str,
        dag_examples: List[Dict[str, Any]],
        adr_guidance: List[Dict[str, Any]],
    ) -> str:
        """Build the prompt for DAG generation."""
        prompt = f"Task: {task}\n\n"

        if dag_examples:
            prompt += "## Relevant DAG Examples:\n"
            for example in dag_examples[:2]:
                content = example.get("content", "")[:1500]
                prompt += f"\n```python\n{content}\n```\n"

        if adr_guidance:
            prompt += "\n## ADR Guidance:\n"
            for adr in adr_guidance[:2]:
                content = adr.get("content", "")[:500]
                prompt += f"\n{content}\n"

        prompt += "\nGenerate a complete, production-ready DAG that follows the project patterns."
        return prompt

    def _extract_dag_examples(
        self, rag_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract DAG examples from RAG context."""
        return [
            doc
            for doc in rag_context.get("documents", [])
            if doc.get("doc_type") == "dag"
        ]

    def _extract_adr_guidance(
        self, rag_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract ADR guidance from RAG context."""
        return [
            doc
            for doc in rag_context.get("documents", [])
            if doc.get("doc_type") == "adr"
        ]

    def _extract_code_from_response(self, response: str) -> str:
        """Extract Python code from LLM response."""
        # Check if code is wrapped in markdown
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                return response[start:end].strip()
        return response.strip()

    def _validate_dag_code(self, code: str) -> Dict[str, Any]:
        """Validate generated DAG code."""
        try:
            # Check for syntax errors
            compile(code, "<string>", "exec")

            # Basic checks
            checks = {
                "has_dag_import": "from airflow" in code,
                "has_dag_definition": "DAG(" in code or "dag=" in code.lower(),
                "has_tasks": "task" in code.lower() or "operator" in code.lower(),
                "has_dependencies": ">>" in code
                or "<<" in code
                or "set_downstream" in code,
            }

            all_passed = all(checks.values())
            return {
                "valid": all_passed,
                "checks": checks,
                "error": None if all_passed else "Missing required DAG components",
            }
        except SyntaxError as e:
            return {"valid": False, "checks": {}, "error": f"Syntax error: {e}"}

    async def _modify_code(
        self, task: str, rag_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """Modify existing code using Aider or direct LLM."""
        logger.info("Modifying existing code...")

        # Try Aider first if available
        if self._check_aider_available():
            return await self._modify_with_aider(task, rag_context, session_id)

        # Fall back to LLM-based modification
        return await self._modify_with_llm(task, rag_context, session_id)

    async def _modify_with_aider(
        self, task: str, rag_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """Use Aider for code modifications."""
        logger.info("Using Aider for code modification...")

        # Build Aider prompt with RAG context
        context_str = self._build_context_for_aider(rag_context)

        try:
            # Run Aider in non-interactive mode
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(f"{context_str}\n\nTask: {task}")
                prompt_file = f.name

            result = subprocess.run(
                ["aider", "--yes", "--no-auto-commits", "--message-file", prompt_file],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=DAGS_PATH,
            )

            os.unlink(prompt_file)

            success = result.returncode == 0
            output = result.stdout if success else result.stderr

            await self._log_troubleshooting(
                session_id=session_id,
                task=task,
                solution=f"Aider modification: {output[:500]}",
                result="success" if success else "failed",
            )

            return {"success": success, "output": output, "method": "aider"}

        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "Aider timed out"}
        except Exception as e:
            logger.error(f"Aider modification failed: {e}")
            return {"success": False, "output": "", "error": str(e)}

    async def _modify_with_llm(
        self, task: str, rag_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """Use LLM for code modifications."""
        router = self._get_llm_router()
        if not router:
            return {"success": False, "output": "", "error": "LLM router not available"}

        prompt = f"""Task: {task}

Context from project:
{self._build_context_for_aider(rag_context)}

Provide the modified code with clear comments explaining changes.
"""

        try:
            response = await router.complete(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a code modification assistant. Output only the modified code.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=4000,
            )

            code = self._extract_code_from_response(response.get("content", ""))

            return {"success": True, "output": code, "method": "llm"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    def _build_context_for_aider(self, rag_context: Dict[str, Any]) -> str:
        """Build context string for Aider from RAG context."""
        context_parts = []

        # Add relevant documents
        for doc in rag_context.get("documents", [])[:3]:
            doc_type = doc.get("doc_type", "document")
            content = doc.get("content", "")[:800]
            context_parts.append(f"[{doc_type}]\n{content}")

        # Add successful troubleshooting solutions
        for ts in rag_context.get("troubleshooting", [])[:2]:
            if ts.get("result") == "success":
                context_parts.append(
                    f"[Previous Solution]\n"
                    f"Problem: {ts.get('error_message', 'N/A')}\n"
                    f"Solution: {ts.get('attempted_solution', 'N/A')}"
                )

        return "\n\n---\n\n".join(context_parts)

    async def _troubleshoot(
        self, task: str, rag_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """Handle troubleshooting tasks."""
        logger.info("Troubleshooting...")

        # Check for similar past issues
        similar_solutions = rag_context.get("troubleshooting", [])

        if similar_solutions:
            # Found similar past solutions
            best_match = similar_solutions[0]
            return {
                "success": True,
                "output": self._format_troubleshooting_suggestion(
                    best_match, similar_solutions
                ),
                "type": "troubleshooting",
                "from_history": True,
                "confidence": best_match.get("similarity", 0),
            }

        # No history, use LLM to troubleshoot
        return await self._troubleshoot_with_llm(task, rag_context, session_id)

    def _format_troubleshooting_suggestion(
        self, best_match: Dict[str, Any], all_matches: List[Dict[str, Any]]
    ) -> str:
        """Format troubleshooting suggestion from history."""
        output = "## Found Similar Issue in History\n\n"

        output += f"**Similarity:** {best_match.get('similarity', 0):.2f}\n"
        output += f"**Previous Error:** {best_match.get('error_message', 'N/A')}\n"
        output += f"**Successful Solution:**\n```\n{best_match.get('attempted_solution', 'N/A')}\n```\n"

        if len(all_matches) > 1:
            output += "\n### Other Similar Issues:\n"
            for match in all_matches[1:3]:
                output += f"- {match.get('error_message', 'N/A')[:100]}... (similarity: {match.get('similarity', 0):.2f})\n"

        return output

    async def _troubleshoot_with_llm(
        self, task: str, rag_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """Use LLM to troubleshoot when no history is available."""
        router = self._get_llm_router()
        if not router:
            return {"success": False, "output": "", "error": "LLM router not available"}

        context_str = self._build_context_for_aider(rag_context)

        prompt = f"""Troubleshoot the following issue:

{task}

Context:
{context_str}

Provide:
1. Possible causes
2. Diagnostic steps
3. Recommended solution
4. Prevention measures
"""

        try:
            response = await router.complete(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert troubleshooter for Airflow and infrastructure automation.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=2000,
            )

            return {
                "success": True,
                "output": response.get("content", ""),
                "type": "troubleshooting",
                "from_history": False,
            }
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    async def _generate_code(
        self, task: str, rag_context: Dict[str, Any], session_id: str
    ) -> Dict[str, Any]:
        """Generate general code based on task."""
        router = self._get_llm_router()
        if not router:
            return {"success": False, "output": "", "error": "LLM router not available"}

        context_str = self._build_context_for_aider(rag_context)

        prompt = f"""Generate code for the following task:

{task}

Context:
{context_str}

Requirements:
- Follow Python best practices
- Include error handling
- Add docstrings and comments
- Make it production-ready
"""

        try:
            response = await router.complete(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Python developer.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=4000,
            )

            code = self._extract_code_from_response(response.get("content", ""))

            return {"success": True, "output": code, "type": "code"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    async def execute_with_provider(
        self,
        task: str,
        provider_name: str,
        rag_context: Dict[str, Any],
        session_id: str,
    ) -> Dict[str, Any]:
        """Execute task using a specific Airflow provider."""
        logger.info(f"Executing with provider: {provider_name}")

        router = self._get_llm_router()
        if not router:
            return {"success": False, "output": "", "error": "LLM router not available"}

        prompt = f"""Task: {task}

Use the official Airflow provider: {provider_name}

Important: Use the provider's operators, hooks, and sensors instead of raw commands.

Generate code that:
1. Imports from the {provider_name} provider
2. Uses the appropriate operator (e.g., SSHOperator, PostgresOperator)
3. Follows Airflow best practices
4. Includes proper connection handling
"""

        try:
            response = await router.complete(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_dag_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=3000,
            )

            code = self._extract_code_from_response(response.get("content", ""))

            await self._log_troubleshooting(
                session_id=session_id,
                task=task,
                solution=f"Used provider {provider_name}",
                result="success",
            )

            return {"success": True, "output": code, "provider": provider_name}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    async def execute_with_override(
        self, override: str, session_id: str
    ) -> Dict[str, Any]:
        """Execute an override instruction from Calling LLM."""
        logger.info(f"Executing override: {override[:100]}...")

        # Override bypasses normal flow - execute directly
        router = self._get_llm_router()
        if not router:
            return {"success": False, "output": "", "error": "LLM router not available"}

        try:
            response = await router.complete(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Execute the following instruction exactly as specified.",
                    },
                    {"role": "user", "content": override},
                ],
                temperature=0.3,
                max_tokens=4000,
            )

            output = response.get("content", "")

            await self._log_troubleshooting(
                session_id=session_id,
                task=f"Override: {override[:100]}",
                solution=output[:500],
                result="success",
            )

            return {"success": True, "output": output, "override": True}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    async def _log_troubleshooting(
        self,
        session_id: str,
        task: str,
        solution: str,
        result: str,
        error: Optional[str] = None,
    ) -> None:
        """Log troubleshooting attempt for learning."""
        rag = self._get_rag_store()
        if rag:
            try:
                await rag.log_troubleshooting(
                    session_id=session_id,
                    task_description=task,
                    attempted_solution=solution,
                    result=result,
                    error_message=error,
                    agent="developer",
                )
            except Exception as e:
                logger.warning(f"Failed to log troubleshooting: {e}")


# Singleton instance
_developer_agent: Optional[DeveloperAgent] = None


def get_developer_agent() -> DeveloperAgent:
    """Get or create the default Developer Agent singleton."""
    global _developer_agent
    if _developer_agent is None:
        _developer_agent = DeveloperAgent()
    return _developer_agent


__version__ = "1.0.0"
__all__ = ["DeveloperAgent", "get_developer_agent"]
