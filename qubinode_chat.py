#!/usr/bin/env python3
"""
Qubinode Navigator Interactive Chat

A modern terminal chat interface for the AI Assistant with:
- Streaming responses
- Markdown rendering
- Conversation history
- Command shortcuts

Usage:
    ./qubinode_chat.py              # Interactive mode
    ./qubinode_chat.py "question"   # Single question mode
"""

import sys
import os
import json
import argparse
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional, Generator

# Check for required dependencies
try:
    import requests
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.text import Text
    from rich.theme import Theme
    from rich.style import Style
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    from prompt_toolkit.styles import Style as PTStyle
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("\nInstall required packages:")
    print("  pip install rich prompt_toolkit requests")
    sys.exit(1)

# Custom theme for Qubinode
QUBINODE_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "user": "bold blue",
    "assistant": "bold magenta",
    "dim": "dim white",
    "highlight": "bold cyan",
})

console = Console(theme=QUBINODE_THEME)

# Configuration
DEFAULT_AI_URL = os.getenv("AI_ASSISTANT_URL", "http://localhost:8080")
HISTORY_FILE = Path.home() / ".qubinode_chat_history"
CONVERSATION_FILE = Path.home() / ".qubinode_conversation.json"


class ConversationHistory:
    """Manage conversation history for context."""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.messages: list[dict] = []

    def add(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # Keep only recent messages
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-self.max_turns * 2:]

    def get_context(self) -> str:
        """Format recent conversation for context."""
        if not self.messages:
            return ""

        context_parts = []
        for msg in self.messages[-6:]:  # Last 3 exchanges
            prefix = "User" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{prefix}: {msg['content'][:200]}")

        return "\n".join(context_parts)

    def clear(self):
        self.messages = []

    def save(self):
        try:
            with open(CONVERSATION_FILE, 'w') as f:
                json.dump(self.messages, f, indent=2)
        except Exception:
            pass

    def load(self):
        try:
            if CONVERSATION_FILE.exists():
                with open(CONVERSATION_FILE, 'r') as f:
                    self.messages = json.load(f)
        except Exception:
            self.messages = []


class QuibinodeChatClient:
    """Client for Qubinode AI Assistant."""

    def __init__(self, base_url: str = DEFAULT_AI_URL):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def check_health(self) -> tuple[bool, str]:
        """Check if AI Assistant is available."""
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            if response.status_code == 200:
                return True, "AI Assistant is online"
            return False, f"Health check failed (HTTP {response.status_code})"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to AI Assistant"
        except requests.exceptions.Timeout:
            return False, "Connection timed out"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def chat(self, message: str, context: str = "", stream: bool = True) -> Generator[str, None, None]:
        """
        Send a chat message and yield response chunks.

        Falls back to non-streaming if streaming isn't supported.
        """
        payload = {
            "message": message,
            "max_tokens": 1000,
            "temperature": 0.7
        }

        if context:
            payload["context"] = {"conversation_history": context}

        try:
            # Try streaming first
            if stream:
                response = self.session.post(
                    f"{self.base_url}/chat",
                    json=payload,
                    stream=True,
                    timeout=90
                )

                if response.status_code == 200:
                    # Check if response is actually streaming
                    content_type = response.headers.get('content-type', '')

                    if 'text/event-stream' in content_type:
                        # True streaming response
                        for line in response.iter_lines(decode_unicode=True):
                            if line:
                                if line.startswith('data: '):
                                    data = line[6:]
                                    if data != '[DONE]':
                                        try:
                                            chunk = json.loads(data)
                                            if 'text' in chunk:
                                                yield chunk['text']
                                            elif 'content' in chunk:
                                                yield chunk['content']
                                        except json.JSONDecodeError:
                                            yield data
                    else:
                        # Non-streaming JSON response
                        try:
                            result = response.json()
                            text = result.get('text') or result.get('response') or result.get('message', '')
                            yield text
                        except json.JSONDecodeError:
                            yield response.text
                else:
                    yield f"Error: HTTP {response.status_code}"
            else:
                # Non-streaming request
                response = self.session.post(
                    f"{self.base_url}/chat",
                    json=payload,
                    timeout=90
                )

                if response.status_code == 200:
                    try:
                        result = response.json()
                        yield result.get('text') or result.get('response') or result.get('message', '')
                    except json.JSONDecodeError:
                        yield response.text
                else:
                    yield f"Error: HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            yield "Error: Request timed out. The AI Assistant may be processing a complex query."
        except requests.exceptions.ConnectionError:
            yield "Error: Cannot connect to AI Assistant. Is it running?"
        except Exception as e:
            yield f"Error: {str(e)}"

    def chat_sync(self, message: str, context: str = "") -> str:
        """Synchronous chat for simple queries."""
        chunks = list(self.chat(message, context, stream=False))
        return "".join(chunks)


class QuibinodeChat:
    """Interactive chat interface."""

    def __init__(self, ai_url: str = DEFAULT_AI_URL):
        self.client = QuibinodeChatClient(ai_url)
        self.history = ConversationHistory()
        self.history.load()

        # Prompt toolkit style
        self.prompt_style = PTStyle.from_dict({
            'prompt': '#00aa00 bold',
        })

        # Command shortcuts
        self.commands = {
            '/help': self.cmd_help,
            '/clear': self.cmd_clear,
            '/history': self.cmd_history,
            '/status': self.cmd_status,
            '/exit': self.cmd_exit,
            '/quit': self.cmd_exit,
            '/new': self.cmd_new_conversation,
            '/save': self.cmd_save,
        }

    def print_welcome(self):
        """Print welcome banner."""
        banner = """
[bold cyan]╔══════════════════════════════════════════════════════════════╗
║           Qubinode Navigator AI Assistant                    ║
║                Interactive Chat Interface                    ║
╚══════════════════════════════════════════════════════════════╝[/bold cyan]

[dim]Type your question or use commands:[/dim]
  [cyan]/help[/cyan]    - Show available commands
  [cyan]/status[/cyan]  - Check AI Assistant status
  [cyan]/clear[/cyan]   - Clear screen
  [cyan]/exit[/cyan]    - Exit chat

[dim]Press Ctrl+C to cancel a request, Ctrl+D to exit[/dim]
"""
        console.print(banner)

    def cmd_help(self, _=None):
        """Show help information."""
        help_text = """
[bold]Available Commands:[/bold]

  [cyan]/help[/cyan]     Show this help message
  [cyan]/status[/cyan]   Check AI Assistant connection status
  [cyan]/clear[/cyan]    Clear the terminal screen
  [cyan]/history[/cyan]  Show recent conversation history
  [cyan]/new[/cyan]      Start a new conversation (clear history)
  [cyan]/save[/cyan]     Save conversation to file
  [cyan]/exit[/cyan]     Exit the chat

[bold]Quick Questions:[/bold]

  Just type your question and press Enter!

[bold]Examples:[/bold]
  [dim]"How do I create a VM using kcli?"[/dim]
  [dim]"What DAGs are available for OpenShift deployment?"[/dim]
  [dim]"Explain the FreeIPA setup process"[/dim]
"""
        console.print(Panel(help_text, title="Help", border_style="cyan"))

    def cmd_clear(self, _=None):
        """Clear the screen."""
        console.clear()
        self.print_welcome()

    def cmd_history(self, _=None):
        """Show conversation history."""
        if not self.history.messages:
            console.print("[dim]No conversation history yet.[/dim]")
            return

        console.print("\n[bold]Recent Conversation:[/bold]\n")
        for msg in self.history.messages[-10:]:
            role = msg["role"]
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]

            if role == "user":
                console.print(f"[user]You:[/user] {content}")
            else:
                console.print(f"[assistant]AI:[/assistant] {content}")
        console.print()

    def cmd_status(self, _=None):
        """Check AI Assistant status."""
        with console.status("[bold cyan]Checking AI Assistant status...", spinner="dots"):
            healthy, message = self.client.check_health()

        if healthy:
            console.print(f"[success]✓[/success] {message}")
            console.print(f"[dim]  URL: {self.client.base_url}[/dim]")
        else:
            console.print(f"[error]✗[/error] {message}")
            console.print(f"[dim]  URL: {self.client.base_url}[/dim]")
            console.print("[dim]  Try: podman ps | grep qubinode-ai-assistant[/dim]")

    def cmd_exit(self, _=None):
        """Exit the chat."""
        self.history.save()
        console.print("\n[dim]Goodbye! Conversation saved.[/dim]")
        sys.exit(0)

    def cmd_new_conversation(self, _=None):
        """Start a new conversation."""
        self.history.clear()
        console.print("[success]Started new conversation. History cleared.[/success]")

    def cmd_save(self, _=None):
        """Save conversation to file."""
        self.history.save()
        console.print(f"[success]Conversation saved to {CONVERSATION_FILE}[/success]")

    def process_input(self, user_input: str) -> bool:
        """
        Process user input.

        Returns True to continue, False to exit.
        """
        user_input = user_input.strip()

        if not user_input:
            return True

        # Check for commands
        if user_input.startswith('/'):
            cmd = user_input.split()[0].lower()
            if cmd in self.commands:
                self.commands[cmd](user_input)
                return True
            else:
                console.print(f"[warning]Unknown command: {cmd}. Type /help for available commands.[/warning]")
                return True

        # Regular chat message
        self.send_message(user_input)
        return True

    def send_message(self, message: str):
        """Send a message and display the response."""
        # Add to history
        self.history.add("user", message)

        # Get context from recent conversation
        context = self.history.get_context()

        console.print()

        # Display response with streaming
        response_text = ""

        try:
            with Live(console=console, refresh_per_second=10) as live:
                spinner_text = Text()
                spinner_text.append("AI is thinking", style="bold magenta")
                spinner_text.append(" ", style="")

                # Show spinner while waiting for first chunk
                live.update(Panel(
                    Spinner("dots", text=spinner_text),
                    title="[assistant]Assistant[/assistant]",
                    border_style="magenta"
                ))

                first_chunk = True
                for chunk in self.client.chat(message, context, stream=True):
                    response_text += chunk

                    # Render markdown progressively
                    try:
                        md = Markdown(response_text)
                        live.update(Panel(
                            md,
                            title="[assistant]Assistant[/assistant]",
                            border_style="magenta"
                        ))
                    except Exception:
                        # Fall back to plain text if markdown fails
                        live.update(Panel(
                            response_text,
                            title="[assistant]Assistant[/assistant]",
                            border_style="magenta"
                        ))

                    first_chunk = False

        except KeyboardInterrupt:
            console.print("\n[warning]Response cancelled.[/warning]")
            return

        # Add response to history
        if response_text:
            self.history.add("assistant", response_text)

        console.print()

    def run_interactive(self):
        """Run the interactive chat loop."""
        self.print_welcome()

        # Check connection
        self.cmd_status()
        console.print()

        # Setup prompt with history
        session = PromptSession(
            history=FileHistory(str(HISTORY_FILE)),
            auto_suggest=AutoSuggestFromHistory(),
            style=self.prompt_style
        )

        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            console.print("\n[dim]Press Ctrl+D to exit, or type /exit[/dim]")

        signal.signal(signal.SIGINT, signal_handler)

        while True:
            try:
                user_input = session.prompt(
                    [('class:prompt', 'You: ')],
                    style=self.prompt_style
                )

                if not self.process_input(user_input):
                    break

            except KeyboardInterrupt:
                continue  # Handled by signal handler
            except EOFError:
                # Ctrl+D
                self.cmd_exit()
                break

    def run_single(self, question: str):
        """Run a single question and exit."""
        healthy, message = self.client.check_health()
        if not healthy:
            console.print(f"[error]✗[/error] {message}")
            sys.exit(1)

        console.print(f"\n[user]You:[/user] {question}\n")
        self.send_message(question)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Qubinode Navigator Interactive Chat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      Start interactive chat
  %(prog)s "How do I create a VM?"   Ask a single question
  %(prog)s --url http://server:8080  Connect to remote AI Assistant
        """
    )

    parser.add_argument(
        'question',
        nargs='?',
        help='Question to ask (starts interactive mode if not provided)'
    )

    parser.add_argument(
        '--url', '-u',
        default=DEFAULT_AI_URL,
        help=f'AI Assistant URL (default: {DEFAULT_AI_URL})'
    )

    parser.add_argument(
        '--no-stream',
        action='store_true',
        help='Disable streaming responses'
    )

    args = parser.parse_args()

    chat = QuibinodeChat(ai_url=args.url)

    if args.question:
        # Single question mode
        chat.run_single(args.question)
    else:
        # Interactive mode
        chat.run_interactive()


if __name__ == "__main__":
    main()
