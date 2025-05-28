#!/usr/bin/env python3
"""
OCode CLI - Terminal-native AI coding assistant powered by Ollama models.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Callable

import click
from rich.console import Console
from rich.text import Text

from .engine import OCodeEngine
from ..utils.auth import AuthenticationManager
from ..utils.config import ConfigManager

console = Console()

async def cli_confirmation_callback(command: str, reason: str) -> bool:
    """Interactive confirmation callback for CLI."""
    try:
        console.print(f"\n[yellow]⚠️  Command requires confirmation:[/yellow]")
        console.print(f"[white]{command}[/white]")
        console.print(f"[dim]Reason: {reason}[/dim]")
        
        # Use blocking input since we're in CLI context
        response = input("⚠️ Run this command? (yes/no): ").strip().lower()
        return response in ['yes', 'y']
        
    except (KeyboardInterrupt, EOFError):
        return False

@click.group(invoke_without_command=True)
@click.option('-m', '--model', default=lambda: os.getenv("OCODE_MODEL", "MFDoom/deepseek-coder-v2-tool-calling:latest"),
              help='Ollama model tag (e.g. llama3:70b)')
@click.option('-c', '--continue', 'continue_session', is_flag=True,
              help='Resume last session')
@click.option('-p', '--print', 'print_prompt', metavar='PROMPT',
              help='Non-interactive single prompt')
@click.option('--out', type=click.Choice(['text', 'json', 'stream-json']),
              default='text', help='Output format')
@click.option('--config', 'config_file', type=click.Path(exists=True),
              help='Configuration file path')
@click.option('-v', '--verbose', is_flag=True, help='Verbose output')
@click.option('-h', '--help', is_flag=True, help='Show help message')
@click.option('--continue-response', is_flag=True, help='Continue from previous response')
@click.pass_context
def cli(ctx, model: str, continue_session: bool, print_prompt: Optional[str],
        out: str, config_file: Optional[str], verbose: bool, help: bool, continue_response: bool):
    """OCode - Terminal-native AI coding assistant powered by Ollama models."""

    if help:
        click.echo(ctx.get_help())
        return

    # Store options in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj.update({
        'model': model,
        'continue_session': continue_session,
        'output_format': out,
        'config_file': config_file,
        'verbose': verbose,
        'continue_response': continue_response
    })

    if print_prompt:
        # Non-interactive mode
        asyncio.run(handle_single_prompt(print_prompt, ctx.obj))
    elif ctx.invoked_subcommand is None:
        # Interactive mode
        asyncio.run(interactive_mode(ctx.obj))

@cli.command()
@click.argument('path', type=click.Path(), default='.')
def init(path: str):
    """Initialize OCode project configuration."""
    project_path = Path(path).resolve()
    ocode_dir = project_path / '.ocode'

    if ocode_dir.exists():
        console.print(f"[yellow]OCode already initialized in {project_path}[/yellow]")
        return

    # Create .ocode directory structure
    ocode_dir.mkdir()
    (ocode_dir / 'memory').mkdir()
    (ocode_dir / 'commands').mkdir()

    # Create default configuration
    config = {
        "model": "MFDoom/deepseek-coder-v2-tool-calling:latest",
        "max_tokens": 200000,
        "context_window": 4096,
        "permissions": {
            "allow_file_read": True,
            "allow_file_write": True,
            "allow_shell_exec": False,
            "allowed_paths": [str(project_path)]
        }
    }

    config_path = ocode_dir / 'settings.json'
    import json
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]✓[/green] Initialized OCode in {project_path}")
    console.print(f"[dim]Configuration: {config_path}[/dim]")

@cli.command()
@click.option('--list', is_flag=True, help='List MCP servers')
@click.option('--start', metavar='NAME', help='Start MCP server')
@click.option('--stop', metavar='NAME', help='Stop MCP server')
@click.option('--restart', metavar='NAME', help='Restart MCP server')
@click.option('--add', nargs=2, metavar='NAME COMMAND', help='Add new MCP server')
@click.option('--remove', metavar='NAME', help='Remove MCP server')
def mcp(list: bool, start: Optional[str], stop: Optional[str], 
        restart: Optional[str], add: Optional[tuple], remove: Optional[str]):
    """Manage Model Context Protocol servers."""
    from ..mcp.manager import MCPServerManager
    from rich.table import Table
    
    manager = MCPServerManager()
    
    if list:
        servers = manager.list_servers()
        
        if not servers:
            console.print("[dim]No MCP servers configured[/dim]")
            console.print("\n[dim]Add a server with:[/dim] ocode mcp --add <name> <command>")
            return
        
        # Create table
        table = Table(title="MCP Servers")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("PID", style="yellow")
        table.add_column("Command")
        table.add_column("Error", style="red")
        
        for server in servers:
            status_style = {
                "running": "green",
                "stopped": "dim",
                "error": "red"
            }.get(server.status, "white")
            
            table.add_row(
                server.name,
                f"[{status_style}]{server.status}[/{status_style}]",
                str(server.pid) if server.pid else "-",
                f"{server.command} {' '.join(server.args)}"[:50] + "...",
                server.error[:30] + "..." if server.error else ""
            )
        
        console.print(table)
        
    elif start:
        console.print(f"Starting MCP server: {start}")
        try:
            info = asyncio.run(manager.start_server(start))
            if info.status == "running":
                console.print(f"[green]✓[/green] Server '{start}' started (PID: {info.pid})")
            else:
                console.print(f"[red]✗[/red] Failed to start server '{start}': {info.error}")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            
    elif stop:
        console.print(f"Stopping MCP server: {stop}")
        try:
            info = asyncio.run(manager.stop_server(stop))
            if info.status == "stopped":
                console.print(f"[green]✓[/green] Server '{stop}' stopped")
            else:
                console.print(f"[red]✗[/red] Failed to stop server '{stop}': {info.error}")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            
    elif restart:
        console.print(f"Restarting MCP server: {restart}")
        try:
            info = asyncio.run(manager.restart_server(restart))
            if info.status == "running":
                console.print(f"[green]✓[/green] Server '{restart}' restarted (PID: {info.pid})")
            else:
                console.print(f"[red]✗[/red] Failed to restart server '{restart}': {info.error}")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            
    elif add:
        name, command = add
        # Parse command and args
        import shlex
        cmd_parts = shlex.split(command)
        
        if manager.add_server(name, cmd_parts[0], cmd_parts[1:] if len(cmd_parts) > 1 else []):
            console.print(f"[green]✓[/green] Added MCP server '{name}'")
            console.print(f"[dim]Start it with:[/dim] ocode mcp --start {name}")
        else:
            console.print(f"[red]✗[/red] Failed to add server '{name}'")
            
    elif remove:
        if manager.remove_server(remove):
            console.print(f"[green]✓[/green] Removed MCP server '{remove}'")
        else:
            console.print(f"[red]✗[/red] Failed to remove server '{remove}'")
            
    else:
        console.print("Use --help for available options")

@cli.command()
@click.option('--login', is_flag=True, help='Login to OCode service')
@click.option('--logout', is_flag=True, help='Logout from OCode service')
@click.option('--status', is_flag=True, help='Show authentication status')
@click.option('--api-key', metavar='KEY', help='Set API key for authentication')
@click.option('--token', metavar='TOKEN', help='Set authentication token directly')
def auth(login: bool, logout: bool, status: bool, api_key: Optional[str], token: Optional[str]):
    """Authentication helpers."""
    auth_manager = AuthenticationManager()
    from rich.table import Table
    import getpass

    if login:
        # Interactive login flow
        console.print("\n[bold]OCode Authentication[/bold]")
        console.print("Choose authentication method:\n")
        console.print("1. API Key")
        console.print("2. Username/Password")
        console.print("3. OAuth Device Flow")
        console.print("4. Cancel\n")
        
        choice = input("Select option (1-4): ").strip()
        
        if choice == "1":
            # API Key authentication
            api_key = getpass.getpass("Enter API key: ").strip()
            if api_key:
                if auth_manager.save_api_key(api_key):
                    console.print("[green]✓ API key saved successfully[/green]")
                else:
                    console.print("[red]✗ Failed to save API key[/red]")
            else:
                console.print("[yellow]Cancelled[/yellow]")
                
        elif choice == "2":
            # Username/Password authentication
            username = input("Username/Email: ").strip()
            password = getpass.getpass("Password: ").strip()
            
            if username and password:
                console.print("[dim]Authenticating...[/dim]")
                
                # For now, simulate OAuth password flow
                # In production, this would make an actual OAuth request
                import time
                import hashlib
                
                # Generate a mock token based on username
                mock_token = hashlib.sha256(f"{username}:{password}:{time.time()}".encode()).hexdigest()
                
                if auth_manager.save_token(
                    token=mock_token,
                    expires_at=time.time() + 3600,  # 1 hour
                    token_type="Bearer",
                    scope="read write"
                ):
                    console.print("[green]✓ Login successful[/green]")
                else:
                    console.print("[red]✗ Login failed[/red]")
            else:
                console.print("[yellow]Cancelled[/yellow]")
                
        elif choice == "3":
            # OAuth Device Flow
            console.print("\n[bold]Device Authorization[/bold]")
            console.print("1. Visit: https://ocode.dev/device")
            console.print("2. Enter code: [bold cyan]ABCD-1234[/bold cyan]")
            console.print("\n[dim]Waiting for authorization...[/dim]")
            
            # In production, this would poll the authorization endpoint
            console.print("[yellow]Device flow not yet implemented[/yellow]")
            
        else:
            console.print("[yellow]Cancelled[/yellow]")
            
    elif logout:
        if auth_manager.logout():
            console.print("[green]✓ Logged out successfully[/green]")
        else:
            console.print("[red]✗ Logout failed[/red]")
            
    elif status:
        status_info = auth_manager.get_auth_status()
        
        # Create status table
        table = Table(title="Authentication Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row(
            "Authenticated",
            "[green]Yes[/green]" if status_info["authenticated"] else "[red]No[/red]"
        )
        
        if status_info["has_token"]:
            table.add_row("Token", "[green]Present[/green]")
            if status_info["token_expires_at"]:
                import datetime
                expires = datetime.datetime.fromtimestamp(status_info["token_expires_at"])
                table.add_row("Token Expires", expires.strftime("%Y-%m-%d %H:%M:%S"))
                
        if status_info["has_api_key"]:
            table.add_row("API Key", "[green]Present[/green]")
            
        table.add_row(
            "Auth File",
            "[green]Exists[/green]" if status_info["auth_file_exists"] else "[dim]Not found[/dim]"
        )
        
        console.print(table)
        
    elif api_key:
        # Direct API key setting
        if auth_manager.save_api_key(api_key):
            console.print("[green]✓ API key saved successfully[/green]")
        else:
            console.print("[red]✗ Failed to save API key[/red]")
            
    elif token:
        # Direct token setting
        import time
        if auth_manager.save_token(
            token=token,
            expires_at=time.time() + 3600,  # Default 1 hour expiry
            token_type="Bearer"
        ):
            console.print("[green]✓ Token saved successfully[/green]")
        else:
            console.print("[red]✗ Failed to save token[/red]")
            
    else:
        console.print("Use --help for available options")

@cli.command()
@click.option('--get', metavar='KEY', help='Get configuration value')
@click.option('--set', metavar='KEY=VALUE', help='Set configuration value')
@click.option('--list', is_flag=True, help='List all configuration')
def config(get: Optional[str], set: Optional[str], list: bool):
    """View and edit configuration."""
    config_manager = ConfigManager()

    if get:
        value = config_manager.get(get)
        console.print(f"{get}: {value}")
    elif set:
        if '=' not in set:
            console.print("[red]Invalid format. Use KEY=VALUE[/red]")
            return
        key, value = set.split('=', 1)
        config_manager.set(key, value)
        console.print(f"[green]Set {key} = {value}[/green]")
    elif list:
        console.print("[bold]Configuration:[/bold]")
        for key, value in config_manager.get_all().items():
            console.print(f"  {key}: {value}")
    else:
        console.print("Use --help for available options")

async def handle_single_prompt(prompt: str, options: dict):
    """Handle single prompt in non-interactive mode."""
    try:
        auth = AuthenticationManager()
        engine = OCodeEngine(
            model=options['model'],
            api_key=auth.token(),
            output_format=options['output_format'],
            verbose=options['verbose'],
            confirmation_callback=cli_confirmation_callback
        )

        try:
            async for chunk in engine.process(prompt, continue_previous=options.get('continue_response', False)):
                if options['output_format'] == 'json':
                    import json
                    console.print(json.dumps(chunk))
                elif options['output_format'] == 'stream-json':
                    import json
                    print(json.dumps(chunk), flush=True)
                else:
                    print(chunk, end='', flush=True)

            if options['output_format'] == 'text':
                print()  # Final newline
        finally:
            # Ensure API client session is closed
            if hasattr(engine.api_client, 'session') and engine.api_client.session:
                await engine.api_client.session.close()

    except Exception as e:
        console.print(f"[red]❌ Error: Processing error: {e}[/red]")
        sys.exit(1)

async def interactive_mode(options: dict):
    """Start interactive OCode session."""
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

    console.print("[bold blue]OCode[/bold blue] - AI Coding Assistant")
    console.print(f"Model: [cyan]{options['model']}[/cyan]")
    console.print("Type [bold]/help[/bold] for commands or [bold]/exit[/bold] to quit")
    console.print("Type [bold]/continue[/bold] to continue from previous response\n")

    # Create prompt session with history
    history_file = Path.home() / '.ocode' / 'history'
    history_file.parent.mkdir(exist_ok=True)

    session = PromptSession(
        history=FileHistory(str(history_file)),
        auto_suggest=AutoSuggestFromHistory(),
    )

    try:
        auth = AuthenticationManager()
        engine = OCodeEngine(
            model=options['model'],
            api_key=auth.token(),
            output_format=options['output_format'],
            verbose=options['verbose'],
            confirmation_callback=cli_confirmation_callback
        )

        while True:
            try:
                # Get user input
                prompt = await session.prompt_async('ocode> ')

                if not prompt.strip():
                    continue

                if prompt.strip() in ['/exit', '/quit', '/q']:
                    break
                elif prompt.strip() == '/continue':
                    if not engine.current_response:
                        console.print("[yellow]No previous response to continue from[/yellow]")
                        continue
                    if engine.is_response_complete():
                        console.print("[yellow]Previous response is already complete[/yellow]")
                        continue
                    prompt = "Continue the previous response"
                    console.print("[dim]Continuing previous response...[/dim]")

                async for chunk in engine.process(prompt, continue_previous=prompt.strip() == '/continue'):
                    if options['output_format'] == 'json':
                        import json
                        console.print(json.dumps(chunk))
                    elif options['output_format'] == 'stream-json':
                        import json
                        print(json.dumps(chunk), flush=True)
                    else:
                        print(chunk, end='', flush=True)

                if options['output_format'] == 'text':
                    print()  # Final newline

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/yellow]")
                continue
            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")

    finally:
        if hasattr(engine.api_client, 'session') and engine.api_client.session:
            await engine.api_client.session.close()

def show_help():
    """Show help message."""
    console.print("""
[bold]Available Commands:[/bold]
  /help     - Show this help message
  /exit     - Exit OCode
  /quit     - Exit OCode
  /q        - Exit OCode
  /continue - Continue from previous response

[bold]Tips:[/bold]
  - Use /continue to continue from a truncated response
  - Press Ctrl+C to interrupt the current response
  - Use --verbose for detailed logging
  - Use --out json for JSON output format
""")

def main():
    """Entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        if os.getenv('OCODE_DEBUG'):
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()
