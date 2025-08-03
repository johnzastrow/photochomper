from datetime import datetime
from pathlib import Path
from rich.console import Console
import os

console = Console()

def tui_setup():
    console.print("[bold green]Photochomper Setup[/bold green]")
    default_dirs = [str(Path.home() / "Pictures")]
    default_types = ["jpg", "jpeg", "png", "gif", "bmp", "tiff"]
    default_exclude_dirs = []
    default_similarity = 1.0
    default_path_pref = "shorter"
    default_filename_pref = None

    dirs = console.input(f"Enter directories to scan (comma separated) [{','.join(default_dirs)}]: ").strip()
    dirs = dirs.split(",") if dirs else default_dirs

    types = console.input(f"Enter file types to include (comma separated, e.g. jpg,png) [{','.join(default_types)}]: ").strip()
    types = types.split(",") if types else default_types

    exclude_dirs = console.input("Enter directories to exclude (comma separated) [none]: ").strip()
    exclude_dirs = exclude_dirs.split(",") if exclude_dirs else default_exclude_dirs

    similarity_input = console.input(f"Similarity threshold (1.0 = exact) [{default_similarity}]: ").strip()
    similarity = float(similarity_input) if similarity_input else default_similarity

    path_pref = console.input(f"Prefer master file with (shorter/longer) path? [{default_path_pref}]: ").strip().lower()
    if path_pref not in ("shorter", "longer"):
        path_pref = default_path_pref

    filename_pref = console.input("Prefer master file with (shorter/longer) filename? [none]: ").strip().lower()
    if filename_pref not in ("shorter", "longer"):
        filename_pref = default_filename_pref

    # Always create a new config file with a unique timestamp
    default_config_dir = os.getcwd()
    config_dir = console.input(f"Directory to save config file? [{default_config_dir}]: ").strip()
    if not config_dir:
        config_dir = default_config_dir

    config_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    default_config_base = "photochomper_config"
    config_base = console.input(f"Config file base name? [{default_config_base}]: ").strip()
    if not config_base:
        config_base = default_config_base
    # Always append date/time to config file name and use .conf extension
    config_name = f"{config_base}_{config_timestamp}.conf"
    config_path = os.path.join(config_dir, config_name)

    # Ask for output file location
    default_output_dir = os.getcwd()
    output_dir = console.input(f"Directory to save output files? [{default_output_dir}]: ").strip()
    if not output_dir:
        output_dir = default_output_dir

    default_output_base = "duplicates_report"
    output_base = console.input(f"Output file base name? [{default_output_base}]: ").strip()
    if not output_base:
        output_base = default_output_base
    include_dt = console.input("Include date and time in output file name? (y/n) [y]: ").strip().lower()
    if include_dt in ("", "y", "yes"):
        output_base += f"_{config_timestamp}"
    output_base = os.path.join(output_dir, output_base)

    config = {
        "dirs": [d.strip() for d in dirs if d.strip()],
        "types": [t.strip() for t in types if t.strip()],
        "exclude_dirs": [e.strip() for e in exclude_dirs if e.strip()],
        "similarity_threshold": similarity,
        "path_preference": path_pref,
        "filename_preference": filename_pref,
        "config_file": config_path,
        "output_base": output_base
    }
    # Save config function should be imported from your config module
    from src.config import save_config
    save_config(config, config_path)
    console.print(f"[bold green]Configuration saved to {config_path}.[/bold green]")

    # Only ask for summary file name, not format
    default_summary_file = os.path.join(output_dir, "duplicates_summary.md")
    summary_file = console.input(f"Summary output file name? [{default_summary_file}]: ").strip()
    if not summary_file:
        summary_file = default_summary_file
    # Always append date/time if requested, even for custom summary file names
    if include_dt in ("", "y", "yes"):
        base, ext = os.path.splitext(summary_file)
        summary_file = f"{base}_{config_timestamp}{ext}"

    config.update({
        "summary_format": "markdown",
        "summary_file": summary_file
    })
    save_config(config, config_path)