#!/usr/bin/env python3
"""
Qubinode Navigator CLI

Command-line interface for the plugin framework as defined in ADR-0028.
This serves as the main entry point for the new modular architecture.
"""

import sys
import argparse
import logging
import requests
import json
from pathlib import Path

# Add core module to path
sys.path.insert(0, str(Path(__file__).parent))

from core import PluginManager, EventSystem, ConfigManager, ExecutionContext


def setup_logging(level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def list_plugins(plugin_manager: PluginManager):
    """List all available plugins"""
    plugins = plugin_manager.list_plugins()

    print("Available Plugins:")
    print("-" * 50)

    for plugin_name in plugins:
        plugin_info = plugin_manager.get_plugin_info(plugin_name)
        if plugin_info:
            print(f"  {plugin_name}")
            print(f"    Version: {plugin_info.version}")
            print(f"    Dependencies: {plugin_info.dependencies or 'None'}")
            print(f"    Description: {plugin_info.description or 'No description'}")
            print()


def execute_plugins(
    plugin_manager: PluginManager,
    config_manager: ConfigManager,
    plugin_names: list = None,
    inventory: str = "localhost",
):
    """Execute plugins"""

    # Load plugin configurations
    if plugin_names:
        plugins_to_run = plugin_names
    else:
        plugins_to_run = config_manager.get_enabled_plugins()

    if not plugins_to_run:
        print("No plugins to execute. Use --list to see available plugins.")
        return

    print(f"Executing plugins: {', '.join(plugins_to_run)}")
    print("-" * 50)

    # Load plugins
    for plugin_name in plugins_to_run:
        plugin_config = config_manager.get_plugin_config(plugin_name)
        plugin = plugin_manager.load_plugin(plugin_name, plugin_config)

        if not plugin:
            print(f"❌ Failed to load plugin: {plugin_name}")
            continue

    # Execute plugins
    context = ExecutionContext(
        inventory=inventory,
        environment="development",
        config=config_manager.get_global_config(),
    )

    results = plugin_manager.execute_plugins(plugins_to_run, context)

    # Display results
    for plugin_name, result in results.items():
        status_icon = "✅" if result.status.value == "completed" else "❌"
        change_icon = "🔄" if result.changed else "⏭️"

        print(f"{status_icon} {change_icon} {plugin_name}: {result.message}")

        if result.data:
            for key, value in result.data.items():
                print(f"    {key}: {value}")


def start_interactive_chat(ai_port: int = 8080) -> int:
    """Start interactive chat mode with Rich UI."""
    try:
        from qubinode_chat import QuibinodeChat

        ai_url = f"http://localhost:{ai_port}"
        chat = QuibinodeChat(ai_url=ai_url)
        chat.run_interactive()
        return 0
    except ImportError:
        print("❌ Interactive chat requires additional dependencies.")
        print("   Install with: pip install rich prompt_toolkit")
        print("\n   Or use the standalone: ./qubinode_chat.py")
        return 1
    except KeyboardInterrupt:
        print("\n👋 Chat ended.")
        return 0
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return 1


def ask_ai(question: str, ai_port: int = 8080):
    """Ask the AI Assistant a question"""
    try:
        # Check if AI Assistant is available
        health_url = f"http://localhost:{ai_port}/health"
        health_response = requests.get(health_url, timeout=5)

        if health_response.status_code != 200:
            print("❌ AI Assistant is not available. Make sure it's running:")
            print(f"   curl -s http://localhost:{ai_port}/health")
            return

        # Ask the question
        chat_url = f"http://localhost:{ai_port}/chat"
        payload = {"message": question, "max_tokens": 500}

        print("🤖 AI Assistant is thinking...")
        response = requests.post(chat_url, json=payload, timeout=30)

        if response.status_code == 200:
            try:
                result = response.json()
                ai_response = result.get("text") or result.get("message") or str(result)

                print("\n" + "=" * 60)
                print("🤖 AI Assistant Response:")
                print("=" * 60)
                print(ai_response)
                print("=" * 60)

            except json.JSONDecodeError:
                print("\n" + "=" * 60)
                print("🤖 AI Assistant Response:")
                print("=" * 60)
                print(response.text)
                print("=" * 60)
        else:
            print(
                f"❌ Failed to get response from AI Assistant (HTTP {response.status_code})"
            )

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to AI Assistant. Is it running?")
        print("   Try: podman ps | grep qubinode-ai-assistant")
        print("   Or start it with: ./deploy-qubinode.sh")
    except requests.exceptions.Timeout:
        print("⏱️  AI Assistant is taking too long to respond. Please try again.")
    except Exception as e:
        print(f"❌ Error communicating with AI Assistant: {e}")


def show_status(plugin_manager: PluginManager):
    """Show plugin manager status"""
    status = plugin_manager.get_status()

    print("Plugin Manager Status:")
    print("-" * 50)
    print(f"Initialized: {status['initialized']}")
    print(f"Discovered Plugins: {status['discovered_plugins']}")
    print(f"Loaded Plugins: {status['loaded_plugins']}")
    print(f"Execution Order: {', '.join(status['execution_order'])}")

    if status["plugin_status"]:
        print("\nPlugin Health:")
        for name, health in status["plugin_status"].items():
            health_icon = "🟢" if health["status"] == "healthy" else "🔴"
            print(f"  {health_icon} {name} v{health['version']} - {health['status']}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Plugin Framework CLI"
    )

    parser.add_argument(
        "--config", default="config/plugins.yml", help="Configuration file path"
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    subparsers.add_parser("list", help="List available plugins")

    # Execute command
    exec_parser = subparsers.add_parser("execute", help="Execute plugins")
    exec_parser.add_argument(
        "--plugins",
        nargs="+",
        help="Specific plugins to execute (default: all enabled)",
    )
    exec_parser.add_argument(
        "--inventory", default="localhost", help="Ansible inventory to use"
    )

    # Status command
    subparsers.add_parser("status", help="Show plugin manager status")

    # Ask AI command (single question)
    ask_parser = subparsers.add_parser("ask", help="Ask the AI Assistant a question")
    ask_parser.add_argument(
        "question", nargs="+", help="Question to ask the AI Assistant"
    )
    ask_parser.add_argument(
        "--port", type=int, default=8080, help="AI Assistant port (default: 8080)"
    )

    # Chat command (interactive mode)
    chat_parser = subparsers.add_parser(
        "chat", help="Start interactive chat with AI Assistant"
    )
    chat_parser.add_argument(
        "--port", type=int, default=8080, help="AI Assistant port (default: 8080)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Setup logging
    setup_logging(args.log_level)

    try:
        # Handle ask command separately (doesn't need plugin manager)
        if args.command == "ask":
            question = " ".join(args.question)
            ask_ai(question, args.port)
            return 0

        # Handle chat command (interactive mode)
        if args.command == "chat":
            return start_interactive_chat(args.port)

        # Initialize components for other commands
        config_manager = ConfigManager(args.config)
        config_manager.load_config()

        event_system = EventSystem()
        plugin_manager = PluginManager(
            plugin_directories=config_manager.get(
                "global.plugin_directories", ["plugins"]
            ),
            event_system=event_system,
        )

        if not plugin_manager.initialize():
            print("❌ Failed to initialize plugin manager")
            return 1

        # Execute command
        if args.command == "list":
            list_plugins(plugin_manager)
        elif args.command == "execute":
            execute_plugins(
                plugin_manager, config_manager, args.plugins, args.inventory
            )
        elif args.command == "status":
            show_status(plugin_manager)

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        # Cleanup
        if "plugin_manager" in locals():
            plugin_manager.cleanup()


if __name__ == "__main__":
    sys.exit(main())
