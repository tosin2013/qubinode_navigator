#!/usr/bin/env python3
"""
FastMCP Implementation for Qubinode AI Assistant
Simple, reliable MCP server using FastMCP framework
"""

import os
import sys
import logging
from typing import Optional
import httpx
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fastmcp-ai-assistant")

# Configuration from environment
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8080")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8081"))
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
MCP_ENABLED = os.getenv("MCP_SERVER_ENABLED", "false").lower() == "true"

# Create FastMCP server
mcp = FastMCP(name="qubinode-ai-assistant")

logger.info("=" * 60)
logger.info("Initializing FastMCP AI Assistant Server")
logger.info(f"AI Service URL: {AI_SERVICE_URL}")
logger.info(f"MCP Server Port: {MCP_SERVER_PORT}")
logger.info(f"MCP Enabled: {MCP_ENABLED}")
logger.info("=" * 60)


@mcp.tool()
async def query_documents(query: str, max_results: int = 5) -> str:
    """
    Search the RAG document store for relevant information about Qubinode,
    Airflow, kcli, or VM management.
    
    Args:
        query: Search query for the document store
        max_results: Maximum number of results to return (1-20)
    
    Returns:
        Formatted search results with content, scores, and sources
    """
    logger.info(f"Tool called: query_documents(query='{query}', max_results={max_results})")
    
    # Validate input
    if not query or not query.strip():
        return "Error: Query cannot be empty"
    
    if max_results < 1 or max_results > 20:
        return "Error: max_results must be between 1 and 20"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/query",
                json={"query": query, "max_results": max_results}
            )
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            
            if not results:
                return f"No results found for query: '{query}'"
            
            # Format results
            output = f"# Document Search Results\n\n"
            output += f"Query: {query}\n"
            output += f"Found {len(results)} results:\n\n"
            
            for i, result in enumerate(results, 1):
                content = result.get('content', '').strip()
                score = result.get('score', 0)
                source = result.get('source', 'Unknown')
                
                output += f"## Result {i} (Score: {score:.2f})\n"
                output += f"**Source:** {source}\n\n"
                output += f"{content}\n\n"
                output += "---\n\n"
            
            logger.info(f"Successfully returned {len(results)} results")
            return output
            
        except httpx.HTTPError as e:
            error_msg = f"Error querying documents: {str(e)}\n\nThe AI Assistant service may not be running at {AI_SERVICE_URL}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg


@mcp.tool()
async def chat_with_context(
    message: str,
    task: Optional[str] = None,
    environment: Optional[str] = None,
    user_role: Optional[str] = None
) -> str:
    """
    Send a message to the Qubinode AI assistant with optional context for
    intelligent responses about infrastructure, VMs, and workflows.
    
    Args:
        message: Message or question to send to the AI assistant
        task: Optional context about current task (e.g., "deploying VM")
        environment: Optional environment context (e.g., "production", "dev")
        user_role: Optional user role (e.g., "admin", "operator")
    
    Returns:
        AI assistant's response
    """
    logger.info(f"Tool called: chat_with_context(message='{message[:50]}...')")
    
    if not message or not message.strip():
        return "Error: Message cannot be empty"
    
    # Build context
    context = {
        "mcp_integration": True,
        "interface": "fastmcp",
        "framework": "fastmcp"
    }
    
    if task:
        context["task"] = task
    if environment:
        context["environment"] = environment
    if user_role:
        context["user_role"] = user_role
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(
                f"{AI_SERVICE_URL}/chat",
                json={"message": message, "context": context}
            )
            response.raise_for_status()
            data = response.json()
            
            ai_response = data.get("response", "No response received")
            logger.info("Chat response received successfully")
            return ai_response
            
        except httpx.HTTPError as e:
            error_msg = f"Error communicating with AI assistant: {str(e)}\n\nThe AI Assistant service may not be running at {AI_SERVICE_URL}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg


@mcp.tool()
async def get_project_status() -> str:
    """
    Get current Qubinode project deployment status, including service health,
    VM count, and system metrics.
    
    Returns:
        Formatted status report
    """
    logger.info("Tool called: get_project_status()")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{AI_SERVICE_URL}/api/status")
            response.raise_for_status()
            data = response.json()
            
            output = "# Qubinode Navigator Project Status\n\n"
            
            # AI Assistant Status
            ai_status = data.get('ai_status', 'unknown')
            output += f"## AI Assistant\n"
            output += f"Status: **{ai_status}**\n\n"
            
            # Airflow Status
            airflow_status = data.get('airflow_status', 'unknown')
            output += f"## Airflow\n"
            output += f"Status: **{airflow_status}**\n\n"
            
            # VM Information
            vm_count = data.get('vm_count', 0)
            output += f"## Virtual Machines\n"
            output += f"Active VMs: **{vm_count}**\n\n"
            
            # Additional metrics
            if 'metrics' in data:
                output += f"## Metrics\n"
                for key, value in data['metrics'].items():
                    output += f"- {key}: {value}\n"
                output += "\n"
            
            logger.info("Project status retrieved successfully")
            return output
            
        except httpx.HTTPError as e:
            error_msg = f"Error retrieving project status: {str(e)}\n\nThe AI Assistant service may not be running at {AI_SERVICE_URL}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg


@mcp.tool()
async def ask_qubinode(
    question: str,
    topic: Optional[str] = None,
    skill_level: Optional[str] = None
) -> str:
    """
    Ask Qubinode Navigator for help understanding features, usage patterns,
    and best practices. Perfect for LLMs to learn how to work with Qubinode.
    
    This tool combines documentation search with AI-powered guidance to provide
    comprehensive, context-aware answers about:
    - Plugin system and architecture
    - Deployment workflows
    - Configuration management
    - Troubleshooting and debugging
    - AI/MCP integration patterns
    - Airflow and kcli integration
    
    Args:
        question: Your question about Qubinode (e.g., "How do I create a plugin?")
        topic: Optional topic for better focus (e.g., "plugins", "deployment", "mcp", "airflow", "configuration")
        skill_level: Optional skill level (e.g., "beginner", "intermediate", "advanced") to tailor response depth
    
    Returns:
        Comprehensive guide with documentation snippets and AI recommendations
    """
    logger.info(f"Tool called: ask_qubinode(question='{question[:60]}...')")
    
    if not question or not question.strip():
        return "Error: Question cannot be empty. Please ask something about Qubinode!"
    
    # Enhance question with topic and skill level for better search
    search_query = question
    if topic:
        search_query = f"{question} {topic}"
    
    # Build context for AI assistant
    context = {
        "mcp_integration": True,
        "interface": "fastmcp",
        "mode": "learning",
        "user_intent": "understanding_qubinode"
    }
    
    if topic:
        context["topic"] = topic
    if skill_level:
        context["skill_level"] = skill_level
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            # First, search documentation for relevant info
            logger.info(f"Searching documentation for: {search_query}")
            search_response = await client.post(
                f"{AI_SERVICE_URL}/api/query",
                json={"query": search_query, "max_results": 5},
                timeout=30.0
            )
            
            docs_context = ""
            if search_response.status_code == 200:
                search_data = search_response.json()
                results = search_data.get("results", [])
                
                if results:
                    docs_context = "\n\n## Relevant Documentation:\n\n"
                    for i, result in enumerate(results, 1):
                        content = result.get('content', '').strip()
                        source = result.get('source', 'Unknown')
                        docs_context += f"**[{i}] From {source}:**\n{content}\n\n"
            
            # Now get AI-powered answer with documentation context
            logger.info("Getting AI-powered guidance")
            ai_prompt = f"""You are a Qubinode Navigator expert helping an LLM understand the platform.

Question: {question}

Provide a clear, comprehensive answer that:
1. Directly answers the question
2. Includes practical examples when relevant
3. Links to key concepts and best practices
4. Suggests next steps for learning more

If skill level is '{skill_level or 'any'}', adjust depth accordingly.{docs_context}

Provide your answer in clear, actionable markdown format."""
            
            chat_response = await client.post(
                f"{AI_SERVICE_URL}/chat",
                json={"message": ai_prompt, "context": context},
                timeout=90.0
            )
            
            if chat_response.status_code == 200:
                data = chat_response.json()
                ai_answer = data.get("response", "No response received")
                logger.info("Successfully generated Qubinode guidance")
                return ai_answer
            else:
                logger.warning(f"Chat endpoint returned status {chat_response.status_code}")
                # Fallback: return documentation if AI service fails
                if docs_context:
                    return f"# Documentation Results for: {question}\n{docs_context}\n\n**Note:** AI-powered guidance unavailable, showing documentation instead."
                else:
                    return f"Could not find documentation or AI guidance for: {question}"
                    
        except httpx.HTTPError as e:
            error_msg = f"Error getting Qubinode guidance: {str(e)}\n\nThe AI Assistant service may not be running at {AI_SERVICE_URL}\n\nTry running: podman run -d --name qubinode-ai -p 8080:8080 localhost/qubinode-ai-assistant:latest"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg


def main():
    """Main entry point"""
    if not MCP_ENABLED:
        logger.warning("=" * 60)
        logger.warning("MCP Server is DISABLED")
        logger.warning("To enable: export MCP_SERVER_ENABLED=true")
        logger.warning("=" * 60)
        sys.exit(0)
    
    logger.info("=" * 60)
    logger.info("Starting FastMCP AI Assistant Server")
    logger.info(f"Host: {MCP_SERVER_HOST}")
    logger.info(f"Port: {MCP_SERVER_PORT}")
    logger.info("Tools: query_documents, chat_with_context, get_project_status, ask_qubinode")
    logger.info("=" * 60)
    
    # FastMCP handles everything: SSE, HTTP, stdio, auth, errors!
    # No manual transport code needed!
    mcp.run(transport="sse", host=MCP_SERVER_HOST, port=MCP_SERVER_PORT)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
