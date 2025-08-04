import os
import json
import sys
from datetime import datetime
from rich.console import Console

console = Console()

def log_action(message: str):
    """Append a log message with timestamp to photochomper.log."""
    with open("photochomper.log", "a") as f:
        f.write(f"{datetime.now().isoformat()} {message}\n")

def load_config(config_path="photochomper_config.conf"):
    """Load configuration from a .conf file (JSON format)."""
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        log_action(f"Error loading config: {e}")
        return {}

def save_config(config, config_path="photochomper_config.conf"):
    """Save configuration to a .conf file (JSON format)."""
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        log_action(f"Error saving config: {e}")

def select_config_file(config_dir: str) -> str:
    """Allow the user to select a config file if more than one exists in the directory."""
    configs = [f for f in os.listdir(config_dir) if f.endswith(".conf")]
    if not configs:
        console.print(f"[bold red]No config files found in {config_dir}. Running setup.[/bold red]")
        from src.tui import tui_setup
        tui_setup()
        sys.exit(0)
    if len(configs) == 1:
        return os.path.join(config_dir, configs[0])
    # Warn and offer selection
    console.print(f"[bold yellow]Multiple config files found in {config_dir}:[/bold yellow]")
    for idx, fname in enumerate(configs, 1):
        console.print(f"  {idx}. {fname}")
    console.print(f"  {len(configs)+1}. [Create a new config file]")
    while True:
        choice = console.input(f"Select config file by number (1-{len(configs)+1}): ").strip()
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(configs):
                return os.path.join(config_dir, configs[choice_num - 1])
            elif choice_num == len(configs) + 1:
                from src.tui import tui_setup
                tui_setup()
                sys.exit(0)
        console.print("[bold red]Invalid selection. Try again.[/bold red]")

def save_list_config(config: dict, config_path: str = None):
    """Save list configuration to a .listconf file (JSON format)."""
    try:
        if not config_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            config_path = f"photochomper_list_config_{timestamp}.listconf"
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        log_action(f"List config saved to {config_path}")
        return config_path
    except Exception as e:
        log_action(f"Error saving list config: {e}")
        return None

def load_list_config(config_path: str):
    """Load list configuration from a .listconf file (JSON format)."""
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        log_action(f"Error loading list config: {e}")
        return {}

def select_list_config_file(config_dir: str = None) -> tuple:
    """Allow the user to select a list config file or create new one.
    
    Returns:
        tuple: (config_path, is_new_config)
            config_path: path to config file or None for new config
            is_new_config: True if user wants to create new config
    """
    if not config_dir:
        config_dir = os.getcwd()
    
    # Look for existing list config files
    list_configs = [f for f in os.listdir(config_dir) if f.endswith(".listconf")]
    
    if not list_configs:
        console.print(f"[bold blue]No saved --list configurations found in {config_dir}.[/bold blue]")
        console.print("Creating new configuration...")
        return None, True
    
    # Show available configs
    console.print(f"[bold cyan]📋 Found {len(list_configs)} saved --list configuration(s):[/bold cyan]")
    for idx, fname in enumerate(list_configs, 1):
        # Extract timestamp from filename for display
        try:
            timestamp_part = fname.replace("photochomper_list_config_", "").replace(".listconf", "")
            if len(timestamp_part) == 15:  # YYYYMMDD_HHMMSS format
                formatted_time = f"{timestamp_part[:4]}-{timestamp_part[4:6]}-{timestamp_part[6:8]} {timestamp_part[9:11]}:{timestamp_part[11:13]}:{timestamp_part[13:15]}"
                console.print(f"  {idx}. {fname} [dim](created {formatted_time})[/dim]")
            else:
                console.print(f"  {idx}. {fname}")
        except:
            console.print(f"  {idx}. {fname}")
    
    console.print(f"  {len(list_configs)+1}. [bold]Create new configuration[/bold]")
    
    while True:
        choice = console.input(f"\n[bold]Select option (1-{len(list_configs)+1}): [/bold]").strip()
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(list_configs):
                config_path = os.path.join(config_dir, list_configs[choice_num - 1])
                console.print(f"[green]Using saved configuration: {list_configs[choice_num - 1]}[/green]")
                return config_path, False
            elif choice_num == len(list_configs) + 1:
                console.print("[blue]Creating new configuration...[/blue]")
                return None, True
        console.print("[bold red]Invalid selection. Please try again.[/bold red]")