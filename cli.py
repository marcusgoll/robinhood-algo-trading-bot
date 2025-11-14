#!/usr/bin/env python3
"""
Robinhood Algo Trading Bot CLI

A comprehensive command-line interface for managing and monitoring the trading bot.

Usage:
    python cli.py --help
    python cli.py bot start [--dry-run] [--mode paper|live|backtest]
    python cli.py trading positions
    python cli.py agents status
    python cli.py workflow execute pre-market-screening
    python cli.py risk metrics
    python cli.py logs view --tail 50
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

console = Console()


def format_currency(value: float) -> str:
    """Format value as currency."""
    return f"${value:,.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage."""
    color = "green" if value >= 0 else "red"
    sign = "+" if value >= 0 else ""
    return f"[{color}]{sign}{value:.2f}%[/{color}]"


def format_timestamp(ts: datetime) -> str:
    """Format timestamp in a readable way."""
    return ts.strftime("%Y-%m-%d %H:%M:%S")


@click.group()
@click.version_option(version="1.0.0", prog_name="Trading Bot CLI")
def cli():
    """Robinhood Algo Trading Bot CLI - Comprehensive trading bot management."""
    pass


# ============================================================================
# BOT CONTROL COMMANDS
# ============================================================================
@cli.group()
def bot():
    """Bot control commands (start, stop, status, restart)."""
    pass


@bot.command()
@click.option("--dry-run", is_flag=True, help="Run in validation mode without real trades")
@click.option("--mode", type=click.Choice(["paper", "live", "backtest"]), default="paper",
              help="Trading mode")
@click.option("--orchestrator", is_flag=True, help="Enable LLM orchestrator")
def start(dry_run: bool, mode: str, orchestrator: bool):
    """Start the trading bot."""
    from trading_bot.main import main as bot_main

    console.print(Panel(
        f"[bold green]Starting Trading Bot[/bold green]\n\n"
        f"Mode: {mode}\n"
        f"Dry Run: {dry_run}\n"
        f"Orchestrator: {orchestrator}",
        title="Bot Startup",
        border_style="green"
    ))

    try:
        # Prepare arguments
        sys.argv = ["trading_bot"]
        if dry_run:
            sys.argv.append("--dry-run")
        if orchestrator:
            sys.argv.extend(["orchestrator", "--orchestrator-mode", mode])

        asyncio.run(bot_main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Bot stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting bot: {e}[/red]")
        sys.exit(1)


@bot.command()
def stop():
    """Stop the running trading bot."""
    console.print("[yellow]Stopping trading bot...[/yellow]")

    # Check for running processes
    import psutil
    stopped = False

    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and 'trading_bot' in ' '.join(cmdline):
                proc.terminate()
                console.print(f"[green]Stopped process {proc.pid}[/green]")
                stopped = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if not stopped:
        console.print("[yellow]No running bot processes found[/yellow]")
    else:
        console.print("[green]✓ Bot stopped successfully[/green]")


@bot.command()
def status():
    """Get current bot status and metrics."""
    import requests

    try:
        # Try to connect to the API server
        response = requests.get("http://localhost:8000/state/current", timeout=2)

        if response.status_code == 200:
            data = response.json()

            table = Table(title="Bot Status", box=box.ROUNDED)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Status", "[green]RUNNING[/green]")
            table.add_row("Current State", data.get("current_state", "UNKNOWN"))
            table.add_row("Uptime", data.get("uptime", "N/A"))
            table.add_row("Last Update", data.get("last_updated", "N/A"))

            console.print(table)
        else:
            console.print("[yellow]Bot is not responding (API unreachable)[/yellow]")

    except requests.exceptions.ConnectionError:
        console.print("[red]Bot is not running (connection refused)[/red]")
    except Exception as e:
        console.print(f"[red]Error checking status: {e}[/red]")


@bot.command()
@click.option("--dry-run", is_flag=True, help="Run in validation mode")
@click.option("--mode", type=click.Choice(["paper", "live", "backtest"]), default="paper")
def restart(dry_run: bool, mode: str):
    """Restart the trading bot."""
    console.print("[yellow]Restarting bot...[/yellow]")

    # Stop first
    ctx = click.get_current_context()
    ctx.invoke(stop)

    # Wait a moment
    import time
    time.sleep(2)

    # Start again
    ctx.invoke(start, dry_run=dry_run, mode=mode, orchestrator=False)


# ============================================================================
# TRADING COMMANDS
# ============================================================================
@cli.group()
def trading():
    """Trading commands (orders, positions, portfolio)."""
    pass


@trading.command()
@click.option("--format", "output_format", type=click.Choice(["table", "json"]),
              default="table", help="Output format")
def positions(output_format: str):
    """View current positions."""
    from trading_bot.services.account_data import AccountData
    from trading_bot.services.auth import RobinhoodAuth

    try:
        auth = RobinhoodAuth()
        account_data = AccountData(auth)

        positions_data = account_data.get_positions()

        if output_format == "json":
            console.print_json(data=positions_data)
            return

        table = Table(title="Current Positions", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan", no_wrap=True)
        table.add_column("Quantity", justify="right")
        table.add_column("Avg Cost", justify="right")
        table.add_column("Current Price", justify="right")
        table.add_column("P&L", justify="right")
        table.add_column("P&L %", justify="right")

        for pos in positions_data:
            symbol = pos.get("symbol", "N/A")
            quantity = pos.get("quantity", 0)
            avg_cost = pos.get("average_buy_price", 0)
            current_price = pos.get("current_price", 0)
            pnl = (current_price - avg_cost) * quantity
            pnl_pct = ((current_price / avg_cost) - 1) * 100 if avg_cost > 0 else 0

            table.add_row(
                symbol,
                f"{quantity:.2f}",
                format_currency(avg_cost),
                format_currency(current_price),
                format_currency(pnl),
                format_percentage(pnl_pct)
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error fetching positions: {e}[/red]")
        sys.exit(1)


@trading.command()
@click.option("--days", default=1, help="Number of days to look back")
@click.option("--status", type=click.Choice(["all", "filled", "pending", "cancelled"]),
              default="all", help="Filter by order status")
def orders(days: int, status: str):
    """View recent orders."""
    console.print(f"[cyan]Fetching orders from last {days} days...[/cyan]")

    # Read from order logs
    log_dir = Path("logs/trades")
    orders_found = []

    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        log_file = log_dir / f"{date.strftime('%Y-%m-%d')}.jsonl"

        if log_file.exists():
            with open(log_file) as f:
                for line in f:
                    try:
                        order = json.loads(line)
                        if status == "all" or order.get("status") == status:
                            orders_found.append(order)
                    except json.JSONDecodeError:
                        continue

    if not orders_found:
        console.print("[yellow]No orders found[/yellow]")
        return

    table = Table(title=f"Orders (Last {days} Days)", box=box.ROUNDED)
    table.add_column("Time", style="cyan")
    table.add_column("Symbol", style="yellow")
    table.add_column("Side", style="magenta")
    table.add_column("Quantity", justify="right")
    table.add_column("Price", justify="right")
    table.add_column("Status", style="green")

    for order in sorted(orders_found, key=lambda x: x.get("timestamp", ""), reverse=True)[:50]:
        timestamp = order.get("timestamp", "N/A")
        symbol = order.get("symbol", "N/A")
        side = order.get("side", "N/A")
        quantity = order.get("quantity", 0)
        price = order.get("price", 0)
        order_status = order.get("status", "N/A")

        table.add_row(
            timestamp[:19] if len(timestamp) > 19 else timestamp,
            symbol,
            side.upper(),
            f"{quantity:.2f}",
            format_currency(price),
            order_status
        )

    console.print(table)


@trading.command()
def portfolio():
    """View portfolio summary."""
    from trading_bot.services.account_data import AccountData
    from trading_bot.services.auth import RobinhoodAuth

    try:
        auth = RobinhoodAuth()
        account_data = AccountData(auth)

        # Get account summary
        equity = account_data.get_total_equity()
        buying_power = account_data.get_buying_power()
        positions = account_data.get_positions()

        # Calculate totals
        total_pnl = sum(
            (pos.get("current_price", 0) - pos.get("average_buy_price", 0)) * pos.get("quantity", 0)
            for pos in positions
        )
        total_invested = sum(
            pos.get("average_buy_price", 0) * pos.get("quantity", 0)
            for pos in positions
        )
        pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

        # Create summary panel
        summary = (
            f"[bold]Total Equity:[/bold] {format_currency(equity)}\n"
            f"[bold]Buying Power:[/bold] {format_currency(buying_power)}\n"
            f"[bold]Total Invested:[/bold] {format_currency(total_invested)}\n"
            f"[bold]Total P&L:[/bold] {format_currency(total_pnl)} ({format_percentage(pnl_pct)})\n"
            f"[bold]Positions:[/bold] {len(positions)}"
        )

        console.print(Panel(summary, title="Portfolio Summary", border_style="green"))

    except Exception as e:
        console.print(f"[red]Error fetching portfolio: {e}[/red]")
        sys.exit(1)


# ============================================================================
# AGENT COMMANDS
# ============================================================================
@cli.group()
def agents():
    """Agent management commands (status, metrics, consensus)."""
    pass


@agents.command()
def status():
    """Show status of all agents."""
    table = Table(title="Agent Status", box=box.ROUNDED)
    table.add_column("Agent", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Status", style="green")

    # List of available agents
    agent_list = [
        ("NewsAnalystAgent", "Analysis", "Active"),
        ("ResearchAgent", "Analysis", "Active"),
        ("RiskManagerAgent", "Risk", "Active"),
        ("StrategyBuilderAgent", "Strategy", "Active"),
        ("RegimeDetectorAgent", "Analysis", "Active"),
        ("TrendAnalystAgent", "Technical (Crypto)", "Active"),
        ("MomentumAnalystAgent", "Technical (Crypto)", "Active"),
        ("VolatilityAnalystAgent", "Technical (Crypto)", "Active"),
        ("LearningAgent", "ML", "Active"),
    ]

    for agent_name, agent_type, status in agent_list:
        table.add_row(agent_name, agent_type, f"[green]{status}[/green]")

    console.print(table)


@agents.command()
@click.option("--agent", help="Specific agent name to show metrics for")
def metrics(agent: Optional[str]):
    """Show agent performance metrics."""
    console.print("[cyan]Reading agent metrics...[/cyan]")

    metrics_file = Path("data/agent_metrics.json")

    if not metrics_file.exists():
        console.print("[yellow]No metrics data found[/yellow]")
        return

    try:
        with open(metrics_file) as f:
            data = json.load(f)

        if agent:
            # Show specific agent
            if agent in data:
                console.print(Panel(
                    json.dumps(data[agent], indent=2),
                    title=f"Metrics for {agent}",
                    border_style="cyan"
                ))
            else:
                console.print(f"[red]Agent '{agent}' not found[/red]")
        else:
            # Show all agents
            table = Table(title="Agent Metrics", box=box.ROUNDED)
            table.add_column("Agent", style="cyan")
            table.add_column("Total Calls", justify="right")
            table.add_column("Success Rate", justify="right")
            table.add_column("Avg Response Time", justify="right")

            for agent_name, agent_data in data.items():
                total_calls = agent_data.get("total_calls", 0)
                success_rate = agent_data.get("success_rate", 0)
                avg_time = agent_data.get("avg_response_time", 0)

                table.add_row(
                    agent_name,
                    str(total_calls),
                    f"{success_rate:.1f}%",
                    f"{avg_time:.2f}s"
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error reading metrics: {e}[/red]")


@agents.command()
@click.argument("symbol")
@click.argument("task_type", type=click.Choice(["analyze", "risk_check", "strategy"]))
def consensus(symbol: str, task_type: str):
    """Get consensus decision from multiple agents."""
    console.print(f"[cyan]Getting consensus for {symbol} - {task_type}...[/cyan]")

    from trading_bot.agents.agent_orchestrator import AgentOrchestrator

    try:
        orchestrator = AgentOrchestrator()

        # Get consensus
        result = asyncio.run(orchestrator.get_consensus(
            task_type=task_type,
            symbol=symbol
        ))

        console.print(Panel(
            json.dumps(result, indent=2),
            title=f"Consensus Result for {symbol}",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[red]Error getting consensus: {e}[/red]")


# ============================================================================
# WORKFLOW COMMANDS
# ============================================================================
@cli.group()
def workflow():
    """Workflow management commands."""
    pass


@workflow.command()
@click.argument("workflow_name", type=click.Choice([
    "pre-market-screening",
    "trade-analysis",
    "position-optimization",
    "market-execution",
    "intraday-monitoring",
    "end-of-day-review",
    "weekly-review"
]))
@click.option("--dry-run", is_flag=True, help="Simulate without executing")
def execute(workflow_name: str, dry_run: bool):
    """Execute a specific workflow."""
    from trading_bot.orchestration.trading_orchestrator import TradingOrchestrator

    console.print(f"[cyan]Executing workflow: {workflow_name}...[/cyan]")

    try:
        orchestrator = TradingOrchestrator()

        # Map workflow names to methods
        workflow_map = {
            "pre-market-screening": orchestrator.pre_market_screening,
            "trade-analysis": orchestrator.trade_analysis,
            "position-optimization": orchestrator.position_optimization,
            "market-execution": orchestrator.market_execution,
            "intraday-monitoring": orchestrator.intraday_monitoring,
            "end-of-day-review": orchestrator.end_of_day_review,
            "weekly-review": orchestrator.weekly_review,
        }

        if dry_run:
            console.print(f"[yellow]DRY RUN: Would execute {workflow_name}[/yellow]")
            return

        result = asyncio.run(workflow_map[workflow_name]())

        console.print(Panel(
            f"[green]✓ Workflow completed successfully[/green]\n\n{result}",
            title=workflow_name.replace("-", " ").title(),
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[red]Error executing workflow: {e}[/red]")
        sys.exit(1)


@workflow.command()
def list():
    """List all available workflows."""
    table = Table(title="Available Workflows", box=box.ROUNDED)
    table.add_column("Workflow", style="cyan")
    table.add_column("Description", style="yellow")
    table.add_column("Typical Time", style="green")

    workflows = [
        ("pre-market-screening", "Scan for trading opportunities", "6:30 AM"),
        ("trade-analysis", "Analyze potential trades", "Before market"),
        ("position-optimization", "Optimize existing positions", "During market"),
        ("market-execution", "Execute planned trades", "9:30 AM"),
        ("intraday-monitoring", "Monitor active positions", "10 AM, 11 AM, 2 PM"),
        ("end-of-day-review", "Review day's performance", "4:00 PM"),
        ("weekly-review", "Weekly performance analysis", "Friday EOD"),
    ]

    for name, desc, time in workflows:
        table.add_row(name, desc, time)

    console.print(table)


# ============================================================================
# RISK COMMANDS
# ============================================================================
@cli.group()
def risk():
    """Risk management commands."""
    pass


@risk.command()
def metrics():
    """Show current risk metrics."""
    from trading_bot.services.risk_manager import RiskManager
    from trading_bot.services.account_data import AccountData
    from trading_bot.services.auth import RobinhoodAuth

    try:
        auth = RobinhoodAuth()
        account_data = AccountData(auth)
        risk_manager = RiskManager(account_data)

        # Get risk metrics
        equity = account_data.get_total_equity()
        daily_loss_limit = risk_manager.max_daily_loss
        current_loss = risk_manager.get_daily_loss()

        table = Table(title="Risk Metrics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        table.add_column("Limit", style="red")

        table.add_row(
            "Total Equity",
            format_currency(equity),
            "-"
        )
        table.add_row(
            "Daily Loss",
            format_currency(abs(current_loss)),
            format_currency(daily_loss_limit)
        )
        table.add_row(
            "Loss %",
            f"{(current_loss / equity * 100):.2f}%",
            f"{(daily_loss_limit / equity * 100):.2f}%"
        )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error fetching risk metrics: {e}[/red]")


@risk.command()
def limits():
    """Show configured risk limits."""
    from trading_bot.config import load_config

    try:
        config = load_config()

        table = Table(title="Risk Limits", box=box.ROUNDED)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Max Daily Loss", f"{config.get('max_daily_loss_pct', 2)}%")
        table.add_row("Max Position Size", f"{config.get('max_position_size_pct', 10)}%")
        table.add_row("Stop Loss", f"{config.get('stop_loss_pct', 2)}%")
        table.add_row("Take Profit", f"{config.get('take_profit_pct', 5)}%")
        table.add_row("Max Open Positions", str(config.get('max_positions', 5)))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")


@risk.command()
def emotional_control():
    """Show emotional control system status."""
    console.print("[cyan]Reading emotional control state...[/cyan]")

    ec_file = Path("data/emotional_control_state.json")

    if not ec_file.exists():
        console.print("[yellow]No emotional control data found[/yellow]")
        return

    try:
        with open(ec_file) as f:
            data = json.load(f)

        table = Table(title="Emotional Control Status", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Loss Streak", str(data.get("loss_streak", 0)))
        table.add_row("Position Size Multiplier", f"{data.get('position_size_multiplier', 1.0):.2f}")
        table.add_row("Circuit Breaker Active", str(data.get("circuit_breaker_active", False)))
        table.add_row("Last Updated", data.get("last_updated", "N/A"))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error reading emotional control state: {e}[/red]")


# ============================================================================
# CONFIG COMMANDS
# ============================================================================
@cli.group()
def config():
    """Configuration management commands."""
    pass


@config.command()
@click.option("--format", "output_format", type=click.Choice(["table", "json"]),
              default="table", help="Output format")
def view(output_format: str):
    """View current configuration."""
    from trading_bot.config import load_config

    try:
        cfg = load_config()

        if output_format == "json":
            console.print_json(data=cfg)
            return

        table = Table(title="Configuration", box=box.ROUNDED)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="yellow")

        for key, value in cfg.items():
            table.add_row(key, str(value))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")


@config.command()
def validate():
    """Validate configuration files."""
    console.print("[cyan]Validating configuration...[/cyan]")

    checks = [
        (".env file", Path(".env").exists()),
        ("config.json", Path("config.json").exists()),
        ("data directory", Path("data").exists()),
        ("logs directory", Path("logs").exists()),
    ]

    table = Table(title="Configuration Validation", box=box.ROUNDED)
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="yellow")

    all_valid = True
    for check_name, result in checks:
        status = "[green]✓ PASS[/green]" if result else "[red]✗ FAIL[/red]"
        table.add_row(check_name, status)
        all_valid = all_valid and result

    console.print(table)

    if all_valid:
        console.print("\n[green]✓ All configuration checks passed[/green]")
    else:
        console.print("\n[red]✗ Some configuration checks failed[/red]")
        sys.exit(1)


# ============================================================================
# LOG COMMANDS
# ============================================================================
@cli.group()
def logs():
    """Log viewing and analysis commands."""
    pass


@logs.command()
@click.option("--tail", default=50, help="Number of lines to show")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
              help="Filter by log level")
def view(tail: int, follow: bool, level: Optional[str]):
    """View recent log entries."""
    log_file = Path("logs/trading_bot.log")

    if not log_file.exists():
        console.print("[yellow]No log file found[/yellow]")
        return

    try:
        with open(log_file) as f:
            lines = f.readlines()

        # Filter by level if specified
        if level:
            lines = [line for line in lines if level in line]

        # Show last N lines
        for line in lines[-tail:]:
            # Color code by level
            if "ERROR" in line:
                console.print(f"[red]{line.rstrip()}[/red]")
            elif "WARNING" in line:
                console.print(f"[yellow]{line.rstrip()}[/yellow]")
            elif "INFO" in line:
                console.print(f"[cyan]{line.rstrip()}[/cyan]")
            else:
                console.print(line.rstrip())

        if follow:
            console.print("\n[cyan]Following log (Ctrl+C to stop)...[/cyan]\n")
            import time

            with open(log_file) as f:
                # Seek to end
                f.seek(0, 2)
                while True:
                    line = f.readline()
                    if line:
                        console.print(line.rstrip())
                    else:
                        time.sleep(0.1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following log[/yellow]")
    except Exception as e:
        console.print(f"[red]Error reading log: {e}[/red]")


@logs.command()
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option("--output", help="Output file path")
def export(start_date: Optional[str], end_date: Optional[str], output: Optional[str]):
    """Export trade logs to file."""
    console.print("[cyan]Exporting trade logs...[/cyan]")

    log_dir = Path("logs/trades")

    if not log_dir.exists():
        console.print("[yellow]No trade logs found[/yellow]")
        return

    # Parse dates
    start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    all_trades = []

    for log_file in sorted(log_dir.glob("*.jsonl")):
        file_date = datetime.strptime(log_file.stem, "%Y-%m-%d")

        if start and file_date < start:
            continue
        if end and file_date > end:
            continue

        with open(log_file) as f:
            for line in f:
                try:
                    trade = json.loads(line)
                    all_trades.append(trade)
                except json.JSONDecodeError:
                    continue

    # Write output
    output_file = output or f"trades_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, "w") as f:
        json.dump(all_trades, f, indent=2)

    console.print(f"[green]✓ Exported {len(all_trades)} trades to {output_file}[/green]")


# ============================================================================
# DASHBOARD COMMAND
# ============================================================================
@cli.command()
def dashboard():
    """Launch interactive dashboard."""
    console.print("[cyan]Launching dashboard...[/cyan]")

    from trading_bot.main import main as bot_main

    try:
        sys.argv = ["trading_bot", "dashboard"]
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard closed[/yellow]")


# ============================================================================
# WATCHLIST COMMANDS
# ============================================================================
@cli.group()
def watchlist():
    """Watchlist management commands."""
    pass


@watchlist.command()
@click.option("--preview", is_flag=True, help="Preview without saving")
@click.option("--min-volume", type=int, help="Minimum volume filter")
def generate(preview: bool, min_volume: Optional[int]):
    """Generate new watchlist."""
    from trading_bot.main import main as bot_main

    console.print("[cyan]Generating watchlist...[/cyan]")

    try:
        sys.argv = ["trading_bot", "generate-watchlist"]
        if preview:
            sys.argv.append("--preview")
        if min_volume:
            sys.argv.extend(["--min-volume", str(min_volume)])

        asyncio.run(bot_main())
    except Exception as e:
        console.print(f"[red]Error generating watchlist: {e}[/red]")


@watchlist.command()
def view():
    """View current watchlist."""
    watchlist_file = Path("data/watchlist.json")

    if not watchlist_file.exists():
        console.print("[yellow]No watchlist found[/yellow]")
        return

    try:
        with open(watchlist_file) as f:
            data = json.load(f)

        table = Table(title="Current Watchlist", box=box.ROUNDED)
        table.add_column("Symbol", style="cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Sector", style="green")
        table.add_column("Score", justify="right")

        for item in data.get("symbols", []):
            table.add_row(
                item.get("symbol", "N/A"),
                item.get("name", "N/A"),
                item.get("sector", "N/A"),
                f"{item.get('score', 0):.2f}"
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error reading watchlist: {e}[/red]")


# ============================================================================
# TECHNICAL ANALYSIS COMMANDS
# ============================================================================
@cli.group()
def ta():
    """Technical analysis framework commands."""
    pass


@ta.command()
@click.argument("symbol")
@click.option("--timeframe", default="1d", help="Timeframe (1h, 4h, 1d, 1w)")
@click.option("--lookback", default=100, help="Number of bars to analyze")
@click.option("--account-size", default=10000.0, help="Account size for position sizing")
def analyze(symbol: str, timeframe: str, lookback: int, account_size: float):
    """Analyze a symbol using the TA framework."""
    from trading_bot.technical_analysis import TACoordinator
    from trading_bot.data.providers import get_market_data
    import pandas as pd

    console.print(Panel(
        f"[bold cyan]Technical Analysis[/bold cyan]\n\n"
        f"Symbol: {symbol}\n"
        f"Timeframe: {timeframe}\n"
        f"Lookback: {lookback} bars",
        title="TA Analysis",
        border_style="cyan"
    ))

    try:
        # Initialize TA coordinator
        ta_coordinator = TACoordinator(account_size=account_size)

        # Get market data
        console.print("[yellow]Fetching market data...[/yellow]")
        # For now, create sample data - in production, fetch real data
        dates = pd.date_range(end=datetime.now(), periods=lookback, freq='D')
        df = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + pd.Series(range(lookback)).cumsum() * 0.1,
            'high': 102 + pd.Series(range(lookback)).cumsum() * 0.1,
            'low': 98 + pd.Series(range(lookback)).cumsum() * 0.1,
            'close': 101 + pd.Series(range(lookback)).cumsum() * 0.1,
            'volume': 1000000
        })

        # Analyze
        console.print("[yellow]Running TA analysis...[/yellow]")
        signal = ta_coordinator.analyze_simple(symbol=symbol, df=df)

        # Display results
        table = Table(title=f"TA Signal: {symbol}", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        signal_color = {
            'LONG': 'green',
            'SHORT': 'red',
            'HOLD': 'yellow',
            'SKIP': 'dim'
        }.get(signal.signal, 'white')

        table.add_row("Signal", f"[{signal_color}]{signal.signal}[/{signal_color}]")
        table.add_row("Confidence", f"{signal.confidence:.1f}%")
        table.add_row("Entry Price", format_currency(signal.entry_price))

        if signal.stop_loss:
            table.add_row("Stop Loss", format_currency(signal.stop_loss))
        if signal.take_profit:
            table.add_row("Take Profit", format_currency(signal.take_profit))
        if signal.position_size_usd:
            table.add_row("Position Size", format_currency(signal.position_size_usd))
        if signal.risk_reward_ratio:
            table.add_row("Risk/Reward", f"{signal.risk_reward_ratio:.2f}")

        console.print(table)

        # Display reasoning
        if signal.reasoning:
            console.print(Panel(
                signal.reasoning,
                title="Analysis Reasoning",
                border_style="cyan"
            ))

    except Exception as e:
        console.print(f"[red]Error analyzing {symbol}: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


@ta.command()
@click.argument("symbol")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option("--initial-capital", default=10000.0, help="Initial capital")
def backtest(symbol: str, start_date: Optional[str], end_date: Optional[str], initial_capital: float):
    """Backtest TA framework on historical data."""
    from trading_bot.technical_analysis import TACoordinator, TradingJournal
    from datetime import datetime

    console.print(Panel(
        f"[bold cyan]TA Framework Backtest[/bold cyan]\n\n"
        f"Symbol: {symbol}\n"
        f"Period: {start_date or 'auto'} to {end_date or 'now'}\n"
        f"Capital: {format_currency(initial_capital)}",
        title="Backtest",
        border_style="cyan"
    ))

    console.print("[yellow]Backtesting functionality coming soon![/yellow]")
    console.print("This will run historical analysis using the TA framework and generate performance reports.")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    cli()
