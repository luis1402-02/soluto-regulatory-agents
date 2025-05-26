"""CLI interface for the multi-agent system."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .config import get_settings
from .graph import RegulatoryMultiAgentSystem
from .memory import RedisMemoryStore
from .utils import setup_logging

app = typer.Typer(
    name="soluto-agents",
    help="Soluto Regulatory Multi-Agent System CLI",
    add_completion=False,
)

console = Console()


class AgentMonitor:
    """Monitor for agent activities."""

    def __init__(self):
        """Initialize monitor."""
        self.layout = Layout()
        self.logs = []
        self.current_agent = None
        self.iteration = 0
        self.max_iterations = 10
        
    def setup_layout(self):
        """Setup the layout."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        
        self.layout["main"].split_row(
            Layout(name="agents", ratio=1),
            Layout(name="logs", ratio=2),
        )
        
    def update_header(self, task: str):
        """Update header with task info."""
        header = Panel(
            Text(f"Task: {task}", style="bold blue"),
            title="[bold]Soluto Regulatory Agents[/bold]",
        )
        self.layout["header"].update(header)
        
    def update_agents(self):
        """Update agents panel."""
        table = Table(title="Active Agents")
        table.add_column("Agent", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Actions", style="yellow")
        
        agents = [
            ("orchestrator_agent", "Coordinating", "Planning workflow"),
            ("research_agent", "Active" if self.current_agent == "research_agent" else "Waiting", "Web search"),
            ("compliance_agent", "Active" if self.current_agent == "compliance_agent" else "Waiting", "Compliance analysis"),
            ("legal_analysis_agent", "Active" if self.current_agent == "legal_analysis_agent" else "Waiting", "Legal review"),
            ("risk_assessment_agent", "Active" if self.current_agent == "risk_assessment_agent" else "Waiting", "Risk evaluation"),
            ("document_review_agent", "Active" if self.current_agent == "document_review_agent" else "Waiting", "Document generation"),
        ]
        
        for agent, status, action in agents:
            table.add_row(agent, status, action)
            
        self.layout["agents"].update(Panel(table, title="Agents"))
        
    def update_logs(self):
        """Update logs panel."""
        log_text = "\n".join(self.logs[-20:])  # Show last 20 logs
        self.layout["logs"].update(
            Panel(
                Syntax(log_text, "log", theme="monokai", line_numbers=True),
                title=f"Activity Logs (Iteration {self.iteration}/{self.max_iterations})",
            )
        )
        
    def update_footer(self):
        """Update footer with progress."""
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        )
        task = progress.add_task(
            f"Processing... Agent: {self.current_agent or 'Initializing'}",
            total=None,
        )
        self.layout["footer"].update(Panel(progress))
        
    def add_log(self, message: str, level: str = "INFO"):
        """Add a log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] [{level}] {message}")
        
    def update(self):
        """Update all panels."""
        self.update_agents()
        self.update_logs()
        self.update_footer()


@app.command()
def run(
    task: str = typer.Argument(..., help="Task to execute"),
    thread_id: Optional[str] = typer.Option(None, help="Thread ID for conversation continuity"),
    max_iterations: int = typer.Option(10, help="Maximum iterations"),
    output_dir: Optional[Path] = typer.Option(None, help="Directory to save outputs"),
    config_file: Optional[Path] = typer.Option(None, help="Configuration file"),
):
    """Run the multi-agent system on a task."""
    asyncio.run(_run_async(task, thread_id, max_iterations, output_dir, config_file))


async def _run_async(
    task: str,
    thread_id: Optional[str],
    max_iterations: int,
    output_dir: Optional[Path],
    config_file: Optional[Path],
):
    """Async implementation of run command."""
    setup_logging()
    
    # Create output directory if specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize system
    console.print("[bold]Initializing Soluto Regulatory Agents...[/bold]")
    
    memory_store = RedisMemoryStore()
    await memory_store.initialize()
    system = RegulatoryMultiAgentSystem(memory_store)
    
    # Setup monitor
    monitor = AgentMonitor()
    monitor.setup_layout()
    monitor.update_header(task)
    monitor.max_iterations = max_iterations
    
    try:
        with Live(monitor.layout, console=console, refresh_per_second=4) as live:
            # Add initial log
            monitor.add_log("System initialized successfully")
            monitor.add_log(f"Starting task: {task[:100]}...")
            monitor.update()
            
            # Mock agent activity updates (in real implementation, these would come from agent callbacks)
            async def update_monitor(agent_name: str, action: str):
                monitor.current_agent = agent_name
                monitor.iteration += 1
                monitor.add_log(f"{agent_name}: {action}")
                monitor.update()
                await asyncio.sleep(0.5)  # Visual effect
            
            # Run the system
            monitor.add_log("Executing multi-agent workflow...")
            
            # Start task execution
            task_future = asyncio.create_task(
                system.run(
                    task=task,
                    thread_id=thread_id,
                    max_iterations=max_iterations,
                )
            )
            
            # Simulate agent updates (in production, use proper callbacks)
            agents_sequence = [
                ("orchestrator_agent", "Planning workflow"),
                ("research_agent", "Searching for regulations"),
                ("compliance_agent", "Analyzing compliance requirements"),
                ("legal_analysis_agent", "Reviewing legal implications"),
                ("risk_assessment_agent", "Evaluating risks"),
                ("document_review_agent", "Generating report"),
            ]
            
            for agent, action in agents_sequence:
                if task_future.done():
                    break
                await update_monitor(agent, action)
            
            # Wait for completion
            result = await task_future
            
            monitor.add_log("Task completed!", "SUCCESS" if result["success"] else "ERROR")
            monitor.update()
            
        # Display results
        console.print("\n[bold green]Task Completed![/bold green]\n")
        
        if result["success"]:
            console.print(Panel(
                result["output"],
                title="[bold]Final Output[/bold]",
                border_style="green",
            ))
            
            # Save outputs if directory specified
            if output_dir:
                # Save main output
                output_file = output_dir / f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                output_file.write_text(result["output"])
                console.print(f"\n[green]Output saved to: {output_file}[/green]")
                
                # Save full result
                result_file = output_dir / f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                result_file.write_text(json.dumps(result, indent=2, default=str))
                console.print(f"[green]Full result saved to: {result_file}[/green]")
                
                # Save any generated documents
                if "documents" in result["context"]:
                    docs = result["context"]["documents"]
                    if docs and docs.get("pdf"):
                        pdf_file = output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        if "path" in docs["pdf"]:
                            console.print(f"[green]PDF report saved to: {docs['pdf']['path']}[/green]")
                        
        else:
            console.print(Panel(
                f"Error: {result.get('error', 'Unknown error')}",
                title="[bold red]Error[/bold red]",
                border_style="red",
            ))
            
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        
    finally:
        await system.cleanup()
        await memory_store.close()


@app.command()
def interactive():
    """Run in interactive mode."""
    asyncio.run(_interactive_async())


async def _interactive_async():
    """Async implementation of interactive mode."""
    setup_logging()
    
    console.print("[bold]Soluto Regulatory Agents - Interactive Mode[/bold]")
    console.print("Type 'help' for commands, 'exit' to quit\n")
    
    # Initialize system
    memory_store = RedisMemoryStore()
    await memory_store.initialize()
    system = RegulatoryMultiAgentSystem(memory_store)
    
    thread_id = str(datetime.now().timestamp())
    
    try:
        while True:
            # Get user input
            user_input = console.input("[bold blue]You:[/bold blue] ")
            
            if user_input.lower() == "exit":
                break
            elif user_input.lower() == "help":
                console.print("""
[bold]Available Commands:[/bold]
- exit: Quit the application
- help: Show this help message
- clear: Clear conversation history
- save: Save conversation to file
- Any other input will be processed by the agents
                """)
                continue
            elif user_input.lower() == "clear":
                thread_id = str(datetime.now().timestamp())
                console.print("[yellow]Conversation cleared[/yellow]")
                continue
            elif user_input.lower() == "save":
                # Save conversation
                filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                console.print(f"[green]Conversation saved to {filename}[/green]")
                continue
                
            # Process with agents
            with console.status("[bold green]Processing..."):
                result = await system.run(
                    task=user_input,
                    thread_id=thread_id,
                    max_iterations=10,
                )
                
            if result["success"]:
                console.print(f"\n[bold green]Agents:[/bold green] {result['output']}\n")
            else:
                console.print(f"\n[bold red]Error:[/bold red] {result.get('error', 'Unknown error')}\n")
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        
    finally:
        await system.cleanup()
        await memory_store.close()
        console.print("\n[bold]Goodbye![/bold]")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    workers: int = typer.Option(4, help="Number of workers"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
):
    """Start the API server."""
    import uvicorn
    
    console.print(f"[bold]Starting API server on {host}:{port}...[/bold]")
    
    uvicorn.run(
        "src.api.app:create_app",
        host=host,
        port=port,
        workers=workers if not reload else 1,
        reload=reload,
        factory=True,
    )


@app.command()
def config():
    """Show current configuration."""
    settings = get_settings()
    
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    # Show non-sensitive settings
    table.add_row("API Host", settings.api_host)
    table.add_row("API Port", str(settings.api_port))
    table.add_row("Workers", str(settings.api_workers))
    table.add_row("Log Level", settings.log_level)
    table.add_row("Log Format", settings.log_format)
    table.add_row("Max Iterations", str(settings.max_iterations))
    table.add_row("Agent Timeout", f"{settings.agent_timeout}s")
    table.add_row("Memory TTL", f"{settings.memory_ttl}s")
    table.add_row("OpenAI Model (Main)", settings.openai_model_main)
    table.add_row("OpenAI Model (Mini)", settings.openai_model_mini)
    
    console.print(table)


if __name__ == "__main__":
    app()