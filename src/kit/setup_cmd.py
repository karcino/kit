"""Interactive setup wizard for kit."""

from __future__ import annotations

import typer
from rich.console import Console

from kit.config import KitConfig, load_config, save_config, get_config_dir

VALID_MODES = ("transit", "driving", "bicycling", "walking")

_console = Console()


def setup(
    check: bool = typer.Option(False, "--check", help="Validate current config."),
) -> None:
    """Interactive setup for kit: home address, API key, transport mode.

    Run without flags to launch the interactive wizard.
    """
    if check:
        _run_check()
        return
    _run_wizard()


# ---------------------------------------------------------------------------
# Wizard
# ---------------------------------------------------------------------------


def _run_wizard() -> None:
    config = load_config()

    _console.print("\n[bold]Welcome to kit![/bold] Let's get you set up.\n")

    # Step 1: Home address
    _console.print("[bold]1/3 — Home Address[/bold]")
    _console.print("  Your default starting point for route calculations.\n")
    home = typer.prompt(
        "  Address",
        default=config.home or "",
    )
    if home:
        config.home = home

    # Step 2: Google Maps API key
    _console.print("\n[bold]2/3 — Google Maps API Key[/bold]")
    _console.print("  kit needs a Google Maps API key for route planning.")
    _console.print("  Follow these steps to get one:\n")
    _console.print("  1. Go to [link]https://console.cloud.google.com[/link]")
    _console.print("  2. Create a project (or select an existing one)")
    _console.print("  3. Enable the [bold]Directions API[/bold] + [bold]Geocoding API[/bold]")
    _console.print("     APIs & Services > Library > search each name > Enable")
    _console.print("  4. Create an API key")
    _console.print("     APIs & Services > Credentials > Create Credentials > API key")
    _console.print("  5. Paste it below\n")
    api_key = typer.prompt(
        "  API key",
        default=config.google_maps_api_key or "",
    )
    if api_key:
        config.google_maps_api_key = api_key

    # Step 3: Default transport mode
    _console.print("\n[bold]3/3 — Default Transport Mode[/bold]")
    _console.print(f"  Options: {', '.join(VALID_MODES)}")
    while True:
        mode = typer.prompt(
            "  Mode",
            default=config.default_mode or "transit",
        )
        if mode in VALID_MODES:
            config.default_mode = mode
            break
        _console.print(f"  [red]Invalid mode.[/red] Choose from: {', '.join(VALID_MODES)}")

    save_config(config)
    config_path = get_config_dir() / "config.toml"
    _console.print(f"\n[green]Setup complete![/green] Config saved to {config_path}")


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------


def _run_check() -> None:
    config = load_config()
    issues: list[str] = []

    # Check home address
    if not config.home:
        issues.append("Home address is not set.")
    else:
        _console.print(f"  [green]OK[/green]  Home address: {config.home}")

    # Check API key
    if not config.google_maps_api_key:
        issues.append("Google Maps API key is not set.")
    else:
        _console.print(f"  [green]OK[/green]  API key: {config.google_maps_api_key[:8]}...")

    # Check transport mode
    if config.default_mode not in VALID_MODES:
        issues.append(f"Invalid transport mode: {config.default_mode}")
    else:
        _console.print(f"  [green]OK[/green]  Transport mode: {config.default_mode}")

    if issues:
        _console.print("")
        for issue in issues:
            _console.print(f"  [red]FAIL[/red]  {issue}")
        _console.print("\nRun [bold]kit setup[/bold] to fix.")
        raise typer.Exit(code=1)
    else:
        _console.print("\n  [green]All checks passed![/green]")
