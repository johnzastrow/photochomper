import argparse
import os
import time
from glob import glob
from src.config import load_config, select_config_file
from src.tui import tui_setup, run_search, schedule_search, show_help, run_interactive_review, tui_list_setup
from src.report import summarize_reports
from src.version import get_version, print_version_info
from rich.console import Console

console = Console()

def run_summary_command(report_files, config_dir):
    """Handle the --summary command to generate markdown from existing reports."""
    
    # If no files specified, auto-discover report files in current directory
    if not report_files:
        console.print("[bold blue]No report files specified. Searching for existing reports...[/bold blue]")
        
        # Look for common report file patterns
        patterns = [
            "duplicates_report*.csv",
            "duplicates_report*.json", 
            "*_report*.csv",
            "*_report*.json"
        ]
        
        found_files = []
        for pattern in patterns:
            found_files.extend(glob(pattern))
        
        # Remove duplicates and sort
        report_files = sorted(list(set(found_files)))
        
        if not report_files:
            console.print("[red]No report files found. Expected files like 'duplicates_report.csv' or 'duplicates_report.json'[/red]")
            console.print("[yellow]Run --search first to generate reports, or specify report files explicitly:[/yellow]")
            console.print("  python main.py --summary report1.csv report2.json")
            console.print("\n[dim]Auto-discovery looks for files containing 'report' in the name:")
            console.print("  • duplicates_report*.csv, duplicates_report*.json")
            console.print("  • *_report*.csv, *_report*.json")
            console.print("  Setup automatically ensures filenames contain 'report' for compatibility[/dim]")
            return
            
        console.print(f"[green]Found {len(report_files)} report files:[/green]")
        for f in report_files:
            console.print(f"  • {f}")
    
    # Validate that files exist and are readable
    valid_files = []
    for file_path in report_files:
        if not os.path.exists(file_path):
            console.print(f"[red]File not found: {file_path}[/red]")
            continue
        
        if not file_path.lower().endswith(('.csv', '.json')):
            console.print(f"[yellow]Skipping unsupported file type: {file_path}[/yellow]")
            continue
            
        valid_files.append(file_path)
    
    if not valid_files:
        console.print("[red]No valid report files found.[/red]")
        return
    
    # Generate output filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = f"duplicates_summary_{timestamp}.md"
    
    console.print(f"[bold blue]Generating markdown summary from {len(valid_files)} files...[/bold blue]")
    
    try:
        # Generate the summary
        markdown_content = summarize_reports(valid_files, output_file)
        
        console.print(f"[bold green]✅ Markdown summary generated: {output_file}[/bold green]")
        
        # Show a preview of the summary
        lines = markdown_content.split('\n')
        if len(lines) > 10:
            console.print("\n[dim]Preview (first 10 lines):[/dim]")
            for line in lines[:10]:
                console.print(f"[dim]{line}[/dim]")
            console.print(f"[dim]... and {len(lines) - 10} more lines[/dim]")
        else:
            console.print("\n[dim]Generated summary:[/dim]")
            console.print(f"[dim]{markdown_content}[/dim]")
            
    except Exception as e:
        console.print(f"[red]Error generating summary: {e}[/red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")

def main():
    parser = argparse.ArgumentParser(description=f"PhotoChomper v{get_version()} - High-Performance Duplicate Photo Detection")
    parser.add_argument("--setup", action="store_true", help="Run setup TUI")
    parser.add_argument("--search", action="store_true", help="Run duplicate search")
    parser.add_argument("--review", action="store_true", help="Interactive duplicate review with actions")
    parser.add_argument("--summary", nargs="*", help="Generate markdown summary from existing reports (CSV/JSON files)")
    parser.add_argument("--schedule", type=int, help="Schedule search every N hours")
    parser.add_argument("--list", action="store_true", help="List all files with comprehensive metadata and export to CSV/SQLite")
    parser.add_argument("--configdir", type=str, help="Specify config directory to use")
    parser.add_argument("--config", type=str, help="Specify config file to use")
    parser.add_argument("--version", action="store_true", help="Show version information")
    args = parser.parse_args()

    # Handle version command first
    if args.version:
        print_version_info()
        return

    if not (args.setup or args.search or args.review or args.summary is not None or args.schedule or args.list):
        console.print(f"[bold blue]PhotoChomper v{get_version()}[/bold blue]")
        console.print("[bold yellow]No command specified. Use --help for options.[/bold yellow]")
        show_help()
        return

    # Show version on startup for all commands
    console.print(f"[bold blue]PhotoChomper v{get_version()}[/bold blue] - High-Performance Duplicate Photo Detection\n")

    # Handle commands that don't need config first
    if args.setup:
        tui_setup()
        return

    if args.list:
        tui_list_setup()
        return

    config_dir = args.configdir if args.configdir else os.getcwd()
    
    if args.summary is not None:
        run_summary_command(args.summary, config_dir)
        return

    # Determine config file for commands that need it
    config_path = None
    if args.config:
        config_path = os.path.join(config_dir, args.config)
    else:
        config_path = select_config_file(config_dir)

    # Load config for commands that need it
    config = load_config(config_path)
    if args.search:
        run_search(config, config_path)
    if args.review:
        run_interactive_review(config)
    if args.schedule:
        schedule_search(args.schedule, config)

if __name__ == "__main__":
    main()
