import os
import json
from datetime import datetime
from rich.console import Console

console = Console()

def log_action(message: str):
    with open("photochomper.log", "a") as f:
        f.write(f"{datetime.now().isoformat()} {message}\n")

def load_config(config_path="photochomper_config.conf"):
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        log_action(f"Error loading config: {e}")
        return {}

def save_config(config, config_path="photochomper_config.conf"):
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        log_action(f"Error saving config: {e}")

def select_config_file(config_dir: str) -> str:
    configs = [f for f in os.listdir(config_dir) if f.endswith(".conf")]
    if not configs:
        console.print(f"[bold red]No config files found in {config_dir}. Running setup.[/bold red]")
        from tui import tui_setup
        tui_setup()
        sys.exit(0)
    console.print(f"[bold yellow]Config files found in {config_dir}:[/bold yellow]")
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
                from tui import tui_setup
                tui_setup()
                sys.exit(0)
        console.print("[bold red]Invalid selection. Try again.[/bold red]")