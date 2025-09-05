import os
import sys
import time
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from src.config import save_config, log_action, save_list_config, load_list_config
from src.config import (
    DEFAULT_FILE_TYPES,
    DEFAULT_FILE_TYPES_HELP,
)  # <-- Add this import
from src.scanner import (
    find_duplicates,
    HashAlgorithm,
    get_image_metadata,
    ProgressStats,
)
from src.report import export_report
from src.actions import (
    ActionExecutor,
    FileAction,
    ActionBatch,
    ActionType,
    create_delete_actions,
    create_move_actions,
)
from src.lister import run_comprehensive_listing

console = Console()


def show_help():
    console.print("[bold cyan]Photochomper Help[/bold cyan]")
    console.print("Commands:")
    console.print("  --setup        Run setup TUI")
    console.print("  --search       Run duplicate search")
    console.print("  --review       Interactive duplicate review with actions")
    console.print("  --summary      Generate markdown summary from existing reports")
    console.print(
        "  --list         List all files with metadata and export to CSV/SQLite"
    )
    console.print("  --schedule N   Schedule search every N hours")
    console.print("  --help         Show this help message")
    console.print("\nExamples:")
    console.print(
        "  python main.py --summary                    # Auto-find report files"
    )
    console.print("  python main.py --summary report1.csv        # Use specific file")
    console.print("  python main.py --summary *.csv *.json       # Use multiple files")
    console.print(
        "\nNote: Auto-discovery looks for files containing 'report' in the name"
    )
    console.print(
        "      Setup automatically ensures compatibility by adding 'report' to filenames"
    )


def tui_setup():
    console.print("[bold green]📸 PhotoChomper Setup[/bold green]")
    console.print("Configure duplicate detection and file management settings\n")

    # Define all defaults
    default_dirs = [str(Path.home() / "Pictures")]
    default_types = DEFAULT_FILE_TYPES  # <-- Use the full default types from config
    default_exclude_dirs = []
    default_similarity = 0.1
    default_path_pref = "shorter"
    default_filename_pref = None
    default_algorithm = "dhash"
    default_quality_ranking = False
    default_max_workers = 4
    default_move_dir = str(Path.home() / "Pictures" / "duplicates_to_review")

    # Scan directories
    console.print("[bold cyan]📁 Scan Directories[/bold cyan]")
    dirs_default_display = ", ".join(default_dirs)
    dirs = console.input(
        f"Directories to scan (comma separated)\n[dim]Default: {dirs_default_display}[/dim]\n> "
    ).strip()
    dirs = [d.strip() for d in dirs.split(",")] if dirs else default_dirs

    # File types
    console.print(f"\n[bold cyan]📄 File Types[/bold cyan]")
    # Show the full list in the prompt
    types = console.input(
        f"File types to include (comma separated)\n[dim]{DEFAULT_FILE_TYPES_HELP}[/dim]\n> "
    ).strip()
    types = [t.strip() for t in types.split(",")] if types else default_types

    # Exclude directories
    console.print(f"\n[bold cyan]🚫 Exclude Directories[/bold cyan]")
    exclude_dirs = console.input(
        f"Directories to exclude (comma separated)\n[dim]Default: none[/dim]\n> "
    ).strip()
    exclude_dirs = (
        [e.strip() for e in exclude_dirs.split(",")]
        if exclude_dirs
        else default_exclude_dirs
    )

    # Similarity threshold
    console.print(f"\n[bold cyan]🎯 Detection Sensitivity[/bold cyan]")
    similarity = console.input(
        f"Similarity threshold (0.0 = identical, 1.0 = completely different)\n[dim]Default: {default_similarity} (recommended for most images)[/dim]\n> "
    ).strip()
    similarity = float(similarity) if similarity else default_similarity

    # Hash algorithm selection (SHA256 is always calculated)
    console.print(f"\n[bold cyan]🔍 Similarity Detection Algorithm[/bold cyan]")
    console.print(
        "Choose how to identify similar files (SHA256 is always calculated for exact duplicates):"
    )
    console.print(
        "  [dim]dhash[/dim]  - Difference hash (good for similar images, recommended)"
    )
    console.print(
        "  [dim]phash[/dim]  - Perceptual hash (good for rotated/scaled images)"
    )
    console.print(
        "  [dim]ahash[/dim]  - Average hash (fastest perceptual, less accurate)"
    )
    console.print("  [dim]whash[/dim]  - Wavelet hash (best for edited images, slower)")

    algorithm = (
        console.input(
            f"Similarity algorithm\n[dim]Default: {default_algorithm} (recommended)[/dim]\n> "
        )
        .strip()
        .lower()
    )
    algorithm = (
        algorithm
        if algorithm in ["dhash", "phash", "ahash", "whash"]
        else default_algorithm
    )

    # SHA256 skip option
    console.print(f"\n[bold cyan]⚡ Performance Optimization[/bold cyan]")
    console.print("PhotoChomper uses a two-stage process:")
    console.print(
        "  1. Fast SHA256 hashing for exact duplicates (30-70% of duplicates)"
    )
    console.print("  2. Slower perceptual hashing for similar images")
    console.print(
        "\nSkipping stage 1 processes only similar images (not exact duplicates)."
    )

    skip_sha256_input = (
        console.input(
            "Skip SHA256 exact duplicate detection?\n[dim]Default: no (recommended for complete duplicate detection)[/dim]\n> "
        )
        .strip()
        .lower()
    )
    skip_sha256 = skip_sha256_input in ("y", "yes")

    if skip_sha256:
        console.print(
            "[yellow]⚠️  Note: This will only find similar images, not exact duplicates[/yellow]"
        )

    # Quality ranking option
    console.print(f"\n[bold cyan]📊 Quality Analysis[/bold cyan]")
    quality_default_display = "yes" if default_quality_ranking else "no"
    quality_input = (
        console.input(
            f"Enable image quality ranking?\n[dim]Default: {quality_default_display} (analyzes resolution and file size)[/dim]\n> "
        )
        .strip()
        .lower()
    )
    quality_ranking = (
        quality_input in ("y", "yes") if quality_input else default_quality_ranking
    )

    # Threading options
    console.print(f"\n[bold cyan]⚡ Performance Settings[/bold cyan]")
    workers = console.input(
        f"Number of worker threads\n[dim]Default: {default_max_workers} (adjust based on CPU cores)[/dim]\n> "
    ).strip()
    max_workers = int(workers) if workers.isdigit() else default_max_workers

    # Memory optimization options with enhanced recommendations
    console.print(f"\n[bold cyan]💾 Memory Optimization[/bold cyan]")
    console.print(
        "PhotoChomper automatically optimizes memory usage based on your system"
    )

    # Get memory info for recommendations
    try:
        from src.scanner import MemoryStats, get_chunk_size_recommendations

        memory_stats = MemoryStats.current()
        console.print(
            f"System Memory: {memory_stats.available_mb:.0f}MB available ({memory_stats.percent_used:.1f}% in use)"
        )

        # Show recommendations for a sample file count
        sample_files = 50000  # Use representative number for recommendations
        recommendations = get_chunk_size_recommendations(
            sample_files, memory_stats.available_mb
        )

        console.print("\n[dim]Memory optimization strategies:[/dim]")
        for strategy, rec in recommendations.items():
            console.print(f"  [dim]{strategy.title()}: {rec['description']}[/dim]")

    except Exception:
        console.print("Unable to analyze system memory - using conservative defaults")

    console.print("\nChunking configuration:")
    chunk_mode = (
        console.input(
            "Memory optimization mode:\n"
            + "  [dim]auto[/dim]     - Automatic optimization (recommended)\n"
            + "  [dim]custom[/dim]   - Specify custom chunk size\n"
            + "  [dim]disable[/dim]  - Process all files at once (high memory)\n"
            + "[dim]Default: auto[/dim]\n> "
        )
        .strip()
        .lower()
    )

    chunk_size = None
    if chunk_mode == "custom":
        chunk_size_input = console.input(
            "Chunk size (files per batch)\n[dim]Example: 1000 for conservative, 2000 for performance[/dim]\n> "
        ).strip()
        if chunk_size_input.isdigit():
            chunk_size = int(chunk_size_input)
    elif chunk_mode == "disable":
        chunk_size = 0  # Disable chunking
        console.print(
            "[yellow]⚠️  Warning: Disabling chunking may cause high memory usage with large collections[/yellow]"
        )

    # File preferences
    console.print(f"\n[bold cyan]📋 Master File Selection[/bold cyan]")
    console.print("When duplicates are found, which original should be kept?")

    path_pref = (
        console.input(
            f"Prefer file with (shorter/longer) path?\n[dim]Default: {default_path_pref} (shorter paths are usually main directories)[/dim]\n> "
        )
        .strip()
        .lower()
    )
    if path_pref not in ("shorter", "longer"):
        path_pref = default_path_pref

    filename_pref_default_display = (
        default_filename_pref if default_filename_pref else "none"
    )
    filename_pref = (
        console.input(
            f"Prefer file with (shorter/longer) filename?\n[dim]Default: {filename_pref_default_display} (no filename preference)[/dim]\n> "
        )
        .strip()
        .lower()
    )
    if filename_pref not in ("shorter", "longer"):
        filename_pref = default_filename_pref

    # Move directory for duplicates
    console.print(f"\n[bold cyan]📂 Duplicate Management[/bold cyan]")
    console.print("Directory to move duplicates when using --review 'move' option")
    move_dir = console.input(
        f"Move duplicates to directory\n[dim]Default: {default_move_dir}[/dim]\n> "
    ).strip()
    move_dir = move_dir if move_dir else default_move_dir

    # Configuration file
    console.print(f"\n[bold cyan]💾 Configuration File[/bold cyan]")
    default_config_dir = os.getcwd()
    config_dir = console.input(
        f"Directory to save config file\n[dim]Default: {default_config_dir}[/dim]\n> "
    ).strip()
    if not config_dir:
        config_dir = default_config_dir

    config_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_config_base = "photochomper_config"
    config_base = console.input(
        f"Config file base name\n[dim]Default: {default_config_base} (timestamp will be added)[/dim]\n> "
    ).strip()
    if not config_base:
        config_base = default_config_base
    # Always append date/time to config file name and use .conf extension
    config_name = f"{config_base}_{config_timestamp}.conf"
    config_path = os.path.join(config_dir, config_name)

    # Output files
    console.print(f"\n[bold cyan]📄 Report Files[/bold cyan]")
    default_output_dir = os.getcwd()
    output_dir = console.input(
        f"Directory to save report files\n[dim]Default: {default_output_dir}[/dim]\n> "
    ).strip()
    if not output_dir:
        output_dir = default_output_dir

    default_output_base = "duplicates_report"
    console.print("Note: The word 'report' will be automatically included in filenames")
    console.print(
        "This ensures compatibility with the --summary auto-discovery feature"
    )

    output_base = console.input(
        f"Report file base name\n[dim]Default: {default_output_base}[/dim]\n> "
    ).strip()
    if not output_base:
        output_base = default_output_base

    # Ensure "report" is always in the filename for auto-discovery compatibility
    if "report" not in output_base.lower():
        if output_base.endswith("_"):
            output_base += "report"
        else:
            output_base += "_report"
        console.print(
            f"[yellow]→ Filename updated to '{output_base}' (added 'report' for --summary compatibility)[/yellow]"
        )

    include_dt_default = "yes"
    include_dt = (
        console.input(
            f"Include date and time in report filenames?\n[dim]Default: {include_dt_default} (recommended for multiple scans)[/dim]\n> "
        )
        .strip()
        .lower()
    )
    if include_dt in ("", "y", "yes"):
        output_base += f"_{config_timestamp}"
    output_base = os.path.join(output_dir, output_base)

    config = {
        "dirs": [d.strip() for d in dirs if d.strip()],
        "types": [t.strip() for t in types if t.strip()],
        "exclude_dirs": [e.strip() for e in exclude_dirs if e.strip()],
        "similarity_threshold": similarity,
        "hash_algorithm": algorithm,
        "skip_sha256": skip_sha256,
        "quality_ranking": quality_ranking,
        "max_workers": max_workers,
        "chunk_size": chunk_size,
        "path_preference": path_pref,
        "filename_preference": filename_pref,
        "duplicate_move_dir": move_dir,
        "config_file": config_path,
        "output_base": output_base,
    }
    save_config(config, config_path)
    console.print(f"[bold green]Configuration saved to {config_path}.[/bold green]")

    # Summary file
    console.print(f"\n[bold cyan]📋 Summary File[/bold cyan]")
    default_summary_file = os.path.join(output_dir, "duplicates_summary.md")
    summary_file = console.input(
        f"Summary markdown file name\n[dim]Default: {default_summary_file}[/dim]\n> "
    ).strip()
    if not summary_file:
        summary_file = default_summary_file
    # Always append date/time if requested, even for custom summary file names
    if include_dt in ("", "y", "yes"):
        base, ext = os.path.splitext(summary_file)
        summary_file = f"{base}_{config_timestamp}{ext}"

    config.update({"summary_format": "markdown", "summary_file": summary_file})
    save_config(config, config_path)

    # Final confirmation
    console.print(f"\n[bold green]✅ Configuration Complete![/bold green]")
    console.print(f"📁 Config saved to: [cyan]{config_path}[/cyan]")
    console.print(f"📂 Duplicate move directory: [cyan]{move_dir}[/cyan]")
    console.print(f"📄 Reports will be saved to: [cyan]{output_dir}[/cyan]")
    console.print(f"\n[dim]Next steps:[/dim]")
    console.print(f"[dim]• Run 'python main.py --search' to find duplicates[/dim]")
    console.print(
        f"[dim]• Run 'python main.py --review' for interactive management[/dim]"
    )
    console.print(
        f"[dim]• Run 'python main.py --summary' to generate markdown reports[/dim]"
    )


def run_search(config: dict, config_path: str = None):
    console.print("[bold blue]🔍 Starting PhotoChomper Duplicate Search[/bold blue]")
    console.print(
        "[dim]Using advanced two-stage optimization for maximum performance[/dim]\n"
    )

    start_time = time.time()
    current_progress = {"stats": None, "task_id": None}

    def progress_callback(stats: ProgressStats):
        """Enhanced progress callback with detailed status and time estimation."""
        current_progress["stats"] = stats

        # Format time displays
        elapsed_str = format_time(stats.elapsed_time)
        phase_elapsed_str = format_time(stats.phase_elapsed_time)

        # Status line with emoji indicators
        status_emoji = {
            "File Discovery": "📁",
            "Stage 1/2: SHA256 Exact Duplicates": "🔗",
            "Stage 1/1: SHA256 Exact Duplicates": "🔗",
            "Stage 2/2: DHASH Similarity": "🎯",
            "Stage 2/2: PHASH Similarity": "🎯",
            "Stage 2/2: AHASH Similarity": "🎯",
            "Stage 2/2: WHASH Similarity": "🎯",
            "Completed": "✅",
        }

        emoji = status_emoji.get(stats.phase, "⚙️")

        # Memory usage display
        try:
            from src.scanner import MemoryStats

            memory = MemoryStats.current()
            memory_str = f" | Memory: {memory.percent_used:.1f}%"
            if memory.percent_used > 85:
                memory_str = f"[red]{memory_str}[/red]"
            elif memory.percent_used > 70:
                memory_str = f"[yellow]{memory_str}[/yellow]"
            else:
                memory_str = f"[green]{memory_str}[/green]"
        except:
            memory_str = ""

        # Build progress display
        if stats.total_files > 0:
            file_progress = f"{stats.files_processed:,}/{stats.total_files:,} files ({stats.files_percent:.1f}%)"

            # Time estimation
            if stats.estimated_completion_time > 0 and stats.phase != "Completed":
                eta_str = format_time(stats.estimated_completion_time)
                time_info = f" | ETA: {eta_str}"
            else:
                time_info = ""

            console.print(f"{emoji} [bold]{stats.phase}[/bold]")
            console.print(
                f"   Progress: {file_progress} | Elapsed: {elapsed_str} ({phase_elapsed_str} this phase){time_info}{memory_str}"
            )
        else:
            console.print(
                f"{emoji} [bold]{stats.phase}[/bold] | Elapsed: {elapsed_str}"
            )

        # Add a separator line for readability
        if stats.phase == "Completed":
            console.print()

    # Convert algorithm string to enum
    algorithm_str = config.get("hash_algorithm", "dhash")
    try:
        algorithm = HashAlgorithm(algorithm_str)
    except ValueError:
        algorithm = HashAlgorithm.DHASH
        log_action(f"Unknown algorithm '{algorithm_str}', using dhash")

    # Get skip_sha256 setting
    skip_sha256 = config.get("skip_sha256", False)
    if skip_sha256:
        console.print(
            "[yellow]⚠️  Skipping SHA256 exact duplicate detection (as configured)[/yellow]\n"
        )

    try:
        dupes, hash_results = find_duplicates(
            config.get("dirs", []),
            config.get("types", []),
            config.get("exclude_dirs", []),
            config.get("similarity_threshold", 0.1),
            algorithm,
            config.get("max_workers", 4),
            config.get("chunk_size"),
            skip_sha256,
            progress_callback,
        )

        exec_time = time.time() - start_time

        # Final summary
        console.print(f"[bold green]🎉 Search Completed![/bold green]")
        console.print(
            f"[bold yellow]📊 Results: {len(dupes)} duplicate groups found[/bold yellow]"
        )
        total_files = sum(len(g) for g in dupes)
        console.print(
            f"[bold magenta]📁 Total duplicate files: {total_files:,}[/bold magenta]"
        )
        console.print(
            f"[bold cyan]⏱️  Total execution time: {format_time(exec_time)}[/bold cyan]\n"
        )

        # Export reports
        console.print("[bold blue]📄 Exporting reports...[/bold blue]")
        export_report(
            dupes,
            formats=["csv", "json", "sqlite"],
            config_path=config.get("config_file", config_path),
            exec_time=exec_time,
        )
        console.print("[bold green]✅ Reports exported:[/bold green]")
        console.print("   • duplicates_report.csv (spreadsheet format)")
        console.print("   • duplicates_report.json (structured data)")
        console.print("   • duplicates_report.db (SQLite database with analytics)")

        log_action(
            f"Search completed: {len(dupes)} groups ({total_files} files) found | "
            f"Config: {config.get('config_file', config_path) or 'default'} | "
            f"Execution time: {exec_time:.2f}s"
        )

    except Exception as e:
        console.print(f"[red]❌ Search failed: {e}[/red]")
        import traceback

        log_action(f"Search error: {e}\n{traceback.format_exc()}")
        raise


def format_time(seconds: float) -> str:
    """Format time duration in a human-readable way."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def schedule_search(interval_hours: int, config: dict):
    console.print(
        f"[bold blue]Scheduled search every {interval_hours} hours.[/bold blue]"
    )
    while True:
        run_search(config)
        time.sleep(interval_hours * 3600)


def get_file_selection(group: list, action_name: str) -> list:
    """Get user selection of specific files from a group by row numbers."""
    while True:
        console.print(f"\n[yellow]📋 {action_name} - Select Files:[/yellow]")
        console.print(
            "Enter row numbers to select (comma-separated, e.g., '1,3,4') or 'all' for all files:"
        )

        # Display numbered list of files
        for i, file_path in enumerate(group, 1):
            filename = Path(file_path).name
            status_text = "👑 Master" if i == 1 else f"#{i-1} Duplicate"
            console.print(f"  [bold]{i}.[/bold] [{status_text}] {filename}")

        selection = (
            console.input(
                f"\n[bold]Select files for {action_name.lower()} (or 'cancel'): [/bold]"
            )
            .strip()
            .lower()
        )

        if selection == "cancel":
            return []
        elif selection == "all":
            return group.copy()
        else:
            try:
                # Parse comma-separated row numbers
                row_numbers = [
                    int(x.strip()) for x in selection.split(",") if x.strip()
                ]
                selected_files = []

                for row_num in row_numbers:
                    if 1 <= row_num <= len(group):
                        selected_files.append(
                            group[row_num - 1]
                        )  # Convert to 0-based index
                    else:
                        console.print(
                            f"[red]Row {row_num} is out of range (1-{len(group)})[/red]"
                        )
                        break
                else:
                    # All row numbers were valid
                    if selected_files:
                        return selected_files
                    else:
                        console.print("[red]No files selected.[/red]")
                        continue

                # If we broke out of the loop, there was an error
                continue

            except ValueError:
                console.print(
                    "[red]Invalid input. Please enter numbers separated by commas (e.g., '1,3,4') or 'all'.[/red]"
                )
                continue


def display_duplicate_group(
    group: list, group_id: int, hash_results: dict = None
) -> None:
    """Display a single group of duplicate files with metadata."""
    console.print(f"\n[bold cyan]📁 Duplicate Group {group_id + 1}[/bold cyan]")
    console.print(f"[dim]Found {len(group)} identical/similar files[/dim]")

    table = Table(show_header=True, header_style="bold magenta", box=None, expand=True)
    table.add_column("Row", style="bold", width=4, no_wrap=False)
    table.add_column("Status", style="bold", width=12, no_wrap=False)
    table.add_column("File", style="cyan", min_width=30, no_wrap=False)
    table.add_column("Size", justify="right", width=10, no_wrap=False)
    table.add_column("Created", justify="center", width=18, no_wrap=False)
    table.add_column("Resolution", justify="center", width=12, no_wrap=False)
    table.add_column("SHA256", justify="left", width=70, no_wrap=False)
    table.add_column("Similarity", justify="right", width=12, no_wrap=False)

    for i, file_path in enumerate(group):
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                filename = Path(file_path).name
                table.add_row(
                    f"[red]{i + 1}[/red]",
                    "[red]❌ MISSING[/red]",
                    f"[red]{filename}[/red]",
                    "[red]Missing[/red]",
                    "[red]N/A[/red]",
                    "[red]N/A[/red]",
                    "[red]N/A[/red]",
                    "[red]N/A[/red]",
                )
                continue

            # Get file stats
            stat = file_path_obj.stat()
            size_kb = stat.st_size / 1024
            created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")

            # Get image metadata if possible
            metadata = get_image_metadata(file_path)
            resolution = "N/A"
            quality_score = "N/A"

            if metadata and "width" in metadata and "height" in metadata:
                resolution = f"{metadata['width']}x{metadata['height']}"
                # Simple quality score based on resolution and file size
                if metadata["width"] and metadata["height"]:
                    pixels = metadata["width"] * metadata["height"]
                    quality_score = f"{(pixels * stat.st_size) / 1000000:.1f}"

            # Get hash information if available
            sha256_hash = "N/A"
            similarity_score = "N/A"
            if hash_results and file_path in hash_results:
                hash_result = hash_results[file_path]
                if hash_result.sha256_hash:
                    sha256_hash = hash_result.sha256_hash  # Show full SHA256 hash
                if (
                    i > 0 and hash_result.similarity_score > 0
                ):  # Don't show similarity for master file
                    similarity_score = f"{hash_result.similarity_score:.3f}"

            # Get just the filename from the full path
            filename = Path(file_path).name

            # Determine status and coloring
            if i == 0:
                row_display = f"[bold green]{i + 1}[/bold green]"
                status = "[bold green]👑 MASTER[/bold green]"
                file_display = f"[bold green]{filename}[/bold green]"
                size_display = f"[green]{size_kb:.0f} KB[/green]"
                created_display = f"[green]{created}[/green]"
                resolution_display = f"[green]{resolution}[/green]"
                sha256_display = f"[green]{sha256_hash}[/green]"
                similarity_display = f"[green]MASTER[/green]"
            else:
                row_display = f"{i + 1}"
                status = f"[dim]#{i} DUPLICATE[/dim]"
                file_display = filename
                size_display = f"{size_kb:.0f} KB"
                created_display = created
                resolution_display = resolution
                sha256_display = sha256_hash
                similarity_display = similarity_score

            table.add_row(
                row_display,
                status,
                file_display,
                size_display,
                created_display,
                resolution_display,
                sha256_display,
                similarity_display,
            )

        except Exception as e:
            filename = Path(file_path).name
            table.add_row(
                f"[red]{i + 1}[/red]",
                "[red]❌ ERROR[/red]",
                f"[red]{filename}[/red]",
                "[red]Error[/red]",
                "[red]N/A[/red]",
                "[red]N/A[/red]",
                "[red]N/A[/red]",
                "[red]N/A[/red]",
            )

    console.print(table)

    # Add explanatory footer for the group
    console.print(f"\n[dim]📋 Group Summary:[/dim]")
    console.print(f"[dim]• Master file (👑) will be kept by default[/dim]")
    console.print(f"[dim]• {len(group) - 1} duplicate(s) available for action[/dim]")
    console.print(
        f"[dim]• Choose 'd' to delete duplicates, 'm' to move them, or 'k' to select different master[/dim]"
    )


def interactive_duplicate_review(
    duplicate_groups: list, config: dict = None, hash_results: dict = None
) -> tuple:
    """Interactive review of duplicate groups with action selection."""
    console.print("\n[bold yellow]📋 Interactive Duplicate Review[/bold yellow]")
    console.print("Review each group of duplicates and choose actions.\n")

    # Show color coding and action explanations
    console.print("[bold cyan]🎨 Display Guide:[/bold cyan]")
    console.print(
        "  • [bold green]Green text[/bold green] = Master file (recommended to keep)"
    )
    console.print(
        "  • [white]White text[/white] = Duplicate files (candidates for action)"
    )
    console.print("  • [red]Red text[/red] = Missing or error files")
    console.print(
        "  • SHA256 = Full file content hash for exact duplicate identification"
    )
    console.print(
        "  • Similarity = How similar files are (0.000 = identical, higher = more different)"
    )

    console.print("\n[bold cyan]⚡ Available Actions:[/bold cyan]")
    console.print(
        "  • [bold](k)eep[/bold] - Choose specific file to keep, delete others"
    )
    console.print("  • [bold](d)elete[/bold] - Select specific files to delete")
    console.print("  • [bold](m)ove[/bold] - Select specific files to move to folder")
    console.print("  • [bold](s)kip[/bold] - Skip this group, make no changes")
    console.print(
        "  • [bold](a)uto[/bold] - Enable automatic processing with chosen strategy"
    )
    console.print("  • [bold](q)uit[/bold] - Exit review (no changes made)")

    console.print(
        "\n[dim]💡 Tip: Master files (green) are usually the best choice to keep based on path length, file size, and quality analysis from your configuration.[/dim]\n"
    )

    selected_actions = []
    current_group = 0
    auto_mode = False
    auto_strategy = "first"
    remembered_move_dir = None  # Remember move directory choice across groups

    while current_group < len(duplicate_groups):
        group = duplicate_groups[current_group]

        if auto_mode:
            # Auto process with selected strategy
            delete_actions = create_delete_actions([group], auto_strategy)
            selected_actions.extend(delete_actions)
            current_group += 1
            continue

        # Display current group
        display_duplicate_group(group, current_group, hash_results)

        # Show navigation info and action prompt
        console.print(
            f"\n[bold]📊 Progress: Group {current_group + 1} of {len(duplicate_groups)}[/bold]"
        )
        console.print("[cyan]What would you like to do with this group?[/cyan]")
        console.print(
            "[dim]💡 Tip: You can select specific files by entering row numbers (e.g., '2,3' for rows 2 and 3)[/dim]"
        )

        while True:
            action = (
                console.input("\n[bold]Choose action [k/d/m/s/q/a]: [/bold]")
                .strip()
                .lower()
            )

            if action == "q":
                console.print("[yellow]Review cancelled by user.[/yellow]")
                return [], False

            elif action == "s":
                # Skip this group
                console.print(
                    f"[dim]⏭️  Skipping group {current_group + 1} - no changes will be made[/dim]"
                )
                break

            elif action == "a":
                # Enable auto mode
                console.print(f"[yellow]🤖 AUTO Mode - Automatic Processing:[/yellow]")
                console.print(
                    "Choose a strategy to automatically process all remaining groups:"
                )
                console.print(
                    "  [bold]first[/bold]    - Keep first file (current master 👑), delete others"
                )
                console.print("  [bold]last[/bold]     - Keep last file, delete others")
                console.print(
                    "  [bold]largest[/bold]  - Keep largest file by size, delete others"
                )
                console.print(
                    "  [bold]smallest[/bold] - Keep smallest file by size, delete others"
                )

                remaining_groups = len(duplicate_groups) - current_group
                console.print(
                    f"\n[dim]This will automatically process {remaining_groups} remaining group(s)[/dim]"
                )

                strategy = (
                    console.input(
                        f"\n[bold]Auto strategy [first/last/largest/smallest]: [/bold]"
                    )
                    .strip()
                    .lower()
                )
                if strategy in ["first", "last", "largest", "smallest"]:
                    confirm = (
                        console.input(
                            f"[bold]Enable auto mode with '{strategy}' strategy? (y/n): [/bold]"
                        )
                        .strip()
                        .lower()
                    )
                    if confirm in ("y", "yes"):
                        auto_mode = True
                        auto_strategy = strategy
                        console.print(
                            f"[green]🤖 Auto mode enabled: '{strategy}' strategy for {remaining_groups} groups[/green]"
                        )
                        break
                    else:
                        console.print("[dim]Auto mode cancelled[/dim]")
                        continue
                else:
                    console.print(
                        "[red]Invalid strategy. Choose from: first, last, largest, smallest[/red]"
                    )
                    continue

            elif action == "k":
                # Keep specific file - show selection
                console.print(f"[yellow]📋 KEEP Action - Choose Master File:[/yellow]")
                console.print("Select which file to keep (others will be deleted):")

                for i, file_path in enumerate(group):
                    file_path_obj = Path(file_path)
                    if file_path_obj.exists():
                        stat = file_path_obj.stat()
                        size_mb = stat.st_size / (1024 * 1024)
                        status_text = "👑 Current Master" if i == 0 else "Duplicate"
                        console.print(
                            f"  [bold]{i + 1}.[/bold] [{status_text}] {Path(file_path).name} ({size_mb:.1f} MB)"
                        )
                    else:
                        console.print(
                            f"  [bold]{i + 1}.[/bold] [red]❌ Missing[/red] {Path(file_path).name}"
                        )

                try:
                    keep_idx = (
                        int(
                            console.input(
                                f"\n[bold]Keep file (1-{len(group)}): [/bold]"
                            ).strip()
                        )
                        - 1
                    )
                    if 0 <= keep_idx < len(group):
                        # Show what will happen
                        keep_file = group[keep_idx]
                        files_to_delete = [
                            f for i, f in enumerate(group) if i != keep_idx
                        ]

                        console.print(f"[green]✅ KEEP: {Path(keep_file).name}[/green]")
                        console.print(
                            f"[red]🗑️  DELETE: {len(files_to_delete)} other file(s)[/red]"
                        )
                        for i, file_path in enumerate(files_to_delete, 1):
                            console.print(f"[red]   #{i}: {Path(file_path).name}[/red]")

                        confirm = (
                            console.input(
                                f"\n[bold]Confirm this selection? (y/n): [/bold]"
                            )
                            .strip()
                            .lower()
                        )
                        if confirm in ("y", "yes"):
                            # Create delete actions for all files except the selected one
                            for file_path in files_to_delete:
                                action_obj = FileAction(
                                    action_id=f"manual_delete_{current_group}_{len(selected_actions)}",
                                    action_type=ActionType.DELETE,
                                    source_path=file_path,
                                    metadata={
                                        "group_id": current_group,
                                        "manual_review": True,
                                        "kept_file": keep_file,
                                    },
                                )
                                selected_actions.append(action_obj)
                            console.print(
                                f"[green]✅ {len(files_to_delete)} files queued for deletion[/green]"
                            )
                            break
                        else:
                            console.print("[dim]Keep action cancelled[/dim]")
                            continue
                    else:
                        console.print(
                            "[red]Invalid selection. Please choose a number from the list.[/red]"
                        )
                        continue
                except ValueError:
                    console.print("[red]Please enter a valid number.[/red]")
                    continue

            elif action == "d":
                # Delete selected files
                selected_files = get_file_selection(group, "DELETE")
                if not selected_files:
                    console.print("[dim]Delete action cancelled[/dim]")
                    continue

                console.print(f"[yellow]📋 DELETE Action Preview:[/yellow]")
                console.print(
                    f"[red]🗑️  DELETE: {len(selected_files)} selected file(s)[/red]"
                )
                for i, file_path in enumerate(selected_files, 1):
                    console.print(f"[red]   #{i}: {Path(file_path).name}[/red]")

                confirm = (
                    console.input(
                        f"\n[bold]Delete {len(selected_files)} selected file(s)? (y/n): [/bold]"
                    )
                    .strip()
                    .lower()
                )
                if confirm in ("y", "yes"):
                    # Create delete actions for selected files only
                    for file_path in selected_files:
                        action_obj = FileAction(
                            action_id=f"manual_delete_{current_group}_{len(selected_actions)}",
                            action_type=ActionType.DELETE,
                            source_path=file_path,
                            metadata={
                                "group_id": current_group,
                                "manual_review": True,
                                "selected_files": len(selected_files),
                            },
                        )
                        selected_actions.append(action_obj)
                    console.print(
                        f"[green]✅ {len(selected_files)} files queued for deletion[/green]"
                    )
                    break
                else:
                    console.print("[dim]Delete action cancelled[/dim]")
                    continue

            elif action == "m":
                # Move selected files to a directory
                selected_files = get_file_selection(group, "MOVE")
                if not selected_files:
                    console.print("[dim]Move action cancelled[/dim]")
                    continue

                console.print(f"[yellow]📋 MOVE Action Preview:[/yellow]")
                console.print(
                    f"[blue]📦 MOVE: {len(selected_files)} selected file(s) to review folder[/blue]"
                )

                # Determine move directory: use remembered > config > ask user
                move_dir = None
                config_move_dir = config.get("duplicate_move_dir", "") if config else ""

                if remembered_move_dir:
                    # Use previously chosen directory
                    move_dir = remembered_move_dir
                    console.print(
                        f"[dim]Using previously chosen directory: {move_dir}[/dim]"
                    )
                elif config_move_dir:
                    # Use configured directory
                    move_dir = config_move_dir
                    console.print(f"[dim]Using configured directory: {move_dir}[/dim]")
                else:
                    # Ask user for directory
                    move_dir = console.input(
                        f"Directory to move selected files to: "
                    ).strip()
                    if move_dir:
                        remembered_move_dir = move_dir  # Remember this choice

                if move_dir:
                    try:
                        # Show what will be moved
                        console.print(f"[blue]📂 Destination: {move_dir}[/blue]")
                        for i, file_path in enumerate(selected_files, 1):
                            console.print(
                                f"[blue]   #{i}: {Path(file_path).name}[/blue]"
                            )

                        confirm = (
                            console.input(
                                f"\n[bold]Move {len(selected_files)} selected file(s) to {Path(move_dir).name}? (y/n): [/bold]"
                            )
                            .strip()
                            .lower()
                        )
                        if confirm in ("y", "yes"):
                            # Create move actions for selected files only
                            for file_path in selected_files:
                                action_obj = FileAction(
                                    action_id=f"manual_move_{current_group}_{len(selected_actions)}",
                                    action_type=ActionType.MOVE,
                                    source_path=file_path,
                                    target_path=str(
                                        Path(move_dir) / Path(file_path).name
                                    ),
                                    metadata={
                                        "group_id": current_group,
                                        "manual_review": True,
                                        "selected_files": len(selected_files),
                                    },
                                )
                                selected_actions.append(action_obj)
                            console.print(
                                f"[green]✅ {len(selected_files)} files queued for moving[/green]"
                            )
                            break
                        else:
                            console.print("[dim]Move action cancelled[/dim]")
                            continue
                    except Exception as e:
                        console.print(f"[red]Error creating move actions: {e}[/red]")
                        continue
                else:
                    console.print("[red]Please specify a directory.[/red]")
                    continue

            else:
                console.print(
                    f"[red]❌ Invalid command '{action}'. Available options:[/red]"
                )
                console.print(
                    "[dim]k=keep specific, d=delete duplicates, m=move duplicates, s=skip, a=auto mode, q=quit[/dim]"
                )
                continue

        current_group += 1

    console.print(f"\n[bold green]Review completed![/bold green]")
    console.print(f"Total actions selected: {len(selected_actions)}")

    return selected_actions, True


def execute_selected_actions(actions: list) -> bool:
    """Execute the selected actions with user confirmation."""
    if not actions:
        console.print("[yellow]No actions to execute.[/yellow]")
        return True

    # Show summary of actions
    console.print("\n[bold cyan]Action Summary:[/bold cyan]")
    action_counts = {}
    for action in actions:
        action_type = action.action_type.value
        action_counts[action_type] = action_counts.get(action_type, 0) + 1

    for action_type, count in action_counts.items():
        console.print(f"  {action_type.capitalize()}: {count} files")

    # Confirm execution
    confirm_prompt = f"\nExecute {len(actions)} actions? (y/n): "
    confirm = console.input(confirm_prompt).strip().lower()

    if confirm not in ("y", "yes"):
        console.print("[yellow]Action execution cancelled.[/yellow]")
        return False

    # Execute actions
    console.print("\n[bold blue]Executing actions...[/bold blue]")

    executor = ActionExecutor()
    batch = ActionBatch(
        batch_id=f"interactive_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        actions=actions,
        backup_dir="",
        created_at=datetime.now().isoformat(),
    )

    def progress_callback(current, total, percent, action):
        console.print(
            f"  Progress: {current}/{total} ({percent:.1f}%) - {action.action_type.value} {Path(action.source_path).name}"
        )

    try:
        result_batch = executor.execute_batch(batch, progress_callback)

        console.print(f"\n[bold green]Execution completed![/bold green]")
        console.print(f"✅ Successful: {result_batch.completed_actions}")
        console.print(f"❌ Failed: {result_batch.failed_actions}")

        if result_batch.failed_actions > 0:
            console.print(
                f"\n[yellow]Some actions failed. Check the backup directory:[/yellow]"
            )
            console.print(f"  {result_batch.backup_dir}")

            rollback_prompt = "Rollback all actions? (y/n): "
            rollback = console.input(rollback_prompt).strip().lower()
            if rollback in ("y", "yes"):
                console.print("[blue]Rolling back actions...[/blue]")
                executor.rollback_batch(result_batch)
                console.print("[green]Rollback completed.[/green]")

        return result_batch.failed_actions == 0

    except Exception as e:
        console.print(f"[red]Error executing actions: {e}[/red]")
        return False


def run_interactive_review(config: dict):
    """Run the complete interactive duplicate review process."""
    console.print("[bold blue]Starting interactive duplicate review...[/bold blue]")

    # First, find duplicates
    start_time = time.time()
    with Progress() as progress:
        task = progress.add_task("Scanning for duplicates...", total=100)

        algorithm_str = config.get("hash_algorithm", "dhash")
        try:
            algorithm = HashAlgorithm(algorithm_str)
        except ValueError:
            algorithm = HashAlgorithm.DHASH
            log_action(f"Unknown algorithm '{algorithm_str}', using dhash")

        duplicate_groups, hash_results = find_duplicates(
            config.get("dirs", []),
            config.get("types", []),
            config.get("exclude_dirs", []),
            config.get("similarity_threshold", 0.1),
            algorithm,
            config.get("max_workers", 4),
            config.get("chunk_size"),
        )
        progress.update(task, completed=100)

    exec_time = time.time() - start_time

    if not duplicate_groups:
        console.print("[green]No duplicates found![/green]")
        return

    console.print(
        f"[bold yellow]Found {len(duplicate_groups)} duplicate groups[/bold yellow]"
    )
    total_duplicates = sum(len(group) for group in duplicate_groups)
    console.print(
        f"[bold magenta]Total duplicate files: {total_duplicates}[/bold magenta]"
    )

    # Interactive review
    actions, completed = interactive_duplicate_review(
        duplicate_groups, config, hash_results
    )

    if not completed:
        return

    # Execute selected actions
    if actions:
        success = execute_selected_actions(actions)
        if success:
            console.print(
                "[bold green]Interactive review completed successfully![/bold green]"
            )
        else:
            console.print("[bold red]Some errors occurred during execution.[/bold red]")
    else:
        console.print("[yellow]No actions were selected.[/yellow]")


def tui_list_setup():
    """Main setup for --list command with config selection."""
    from src.config import select_list_config_file

    console.print("[bold green]📋 PhotoChomper File Listing[/bold green]")
    console.print(
        "Generate comprehensive file listings with metadata export to CSV and SQLite"
    )

    # Check for existing configs and let user choose
    config_path, is_new_config = select_list_config_file()

    if is_new_config or config_path is None:
        # Create new configuration
        tui_list_setup_new()
    else:
        # Load and use existing configuration
        list_config = load_list_config(config_path)
        if not list_config:
            console.print("[red]Error loading configuration. Creating new one...[/red]")
            tui_list_setup_new()
            return

        # Display loaded configuration
        console.print(f"\n[bold cyan]📂 Loaded Configuration:[/bold cyan]")
        console.print(
            f"• Search directory: [cyan]{list_config.get('search_dir', 'Not set')}[/cyan]"
        )
        console.print(
            f"• Output directory: [cyan]{list_config.get('output_dir', 'Not set')}[/cyan]"
        )
        excluded = list_config.get("excluded_extensions", [])
        console.print(
            f"• Excluded extensions: [cyan]{', '.join(excluded) if excluded else 'none'}[/cyan]"
        )
        console.print(f"• Created: [dim]{list_config.get('created', 'Unknown')}[/dim]")

        # Confirm use of loaded config
        use_config = (
            console.input(f"\n[bold]Use this configuration? (y/n): [/bold]")
            .strip()
            .lower()
        )
        if use_config not in ("y", "yes"):
            console.print("[blue]Creating new configuration instead...[/blue]")
            tui_list_setup_new()
            return

        # Run with loaded configuration
        console.print(
            f"\n[bold blue]Starting file listing with saved configuration...[/bold blue]"
        )
        run_comprehensive_listing(
            list_config["search_dir"],
            list_config["output_dir"],
            list_config.get("excluded_extensions", []),
        )


def tui_list_setup_new():
    """Interactive setup for comprehensive file listing command."""
    console.print("[bold green]📋 PhotoChomper File Listing Setup[/bold green]")
    console.print(
        "Generate comprehensive file listings with metadata export to CSV and SQLite\n"
    )

    # Starting search directory
    console.print("[bold cyan]📁 Search Directory[/bold cyan]")
    default_search_dir = str(Path.home() / "Pictures")
    search_dir = console.input(
        f"Starting search directory\n[dim]Default: {default_search_dir}[/dim]\n> "
    ).strip()
    search_dir = search_dir if search_dir else default_search_dir

    # Output directory
    console.print(f"\n[bold cyan]💾 Output Directory[/bold cyan]")
    default_output_dir = search_dir
    output_dir = console.input(
        f"Output directory for CSV and SQLite files\n[dim]Default: {default_output_dir} (same as search)[/dim]\n> "
    ).strip()
    output_dir = output_dir if output_dir else default_output_dir

    # Excluded file extensions
    console.print(f"\n[bold cyan]🚫 Excluded File Extensions[/bold cyan]")
    console.print("Enter file extensions to exclude (without dots, comma-separated)")
    excluded_extensions = console.input(
        f"Excluded extensions (e.g., tmp,log,cache)\n[dim]Default: none (include all files)[/dim]\n> "
    ).strip()
    excluded_extensions = (
        [ext.strip() for ext in excluded_extensions.split(",")]
        if excluded_extensions
        else []
    )

    # Confirmation and field explanation
    console.print(f"\n[bold cyan]📊 Output Fields[/bold cyan]")
    console.print("The listing will include these fields:")
    console.print("• [dim]DateTimeRun[/dim] - When this list was created")
    console.print("• [dim]FileName[/dim] - Name of file")
    console.print("• [dim]FilePath[/dim] - Full path to the file")
    console.print("• [dim]SHA256[/dim] - SHA256 hash of file contents")
    console.print(
        "• [dim]DupeSHA256[/dim] - 'Yes' if SHA256 appears elsewhere in the list"
    )
    console.print("• [dim]CharLengthName[/dim] - Character length of filename")
    console.print("• [dim]CharLengthPath[/dim] - Character length of full path")
    console.print("• [dim]FileSizeBytes[/dim] - File size in bytes")
    console.print("• [dim]FileCreatedDateTime[/dim] - File system creation time")
    console.print("• [dim]FileModifiedDateTime[/dim] - File system modification time")
    console.print("• [dim]ImageWidthPx[/dim] - Image width in pixels (for images)")
    console.print("• [dim]ImageHeightPx[/dim] - Image height in pixels (for images)")
    console.print("• [dim]FileType[/dim] - Detected file type")
    console.print("• [dim]ImageCameraMake[/dim] - Camera manufacturer (from EXIF)")
    console.print("• [dim]ImageCameraModel[/dim] - Camera model (from EXIF)")
    console.print(
        "• [dim]ImageDateTimeTaken[/dim] - Date/time photo was taken (from EXIF)"
    )
    console.print("• [dim]ImageQualityScore[/dim] - Calculated image quality score")
    console.print("• [dim]ImageIPTCKeywords[/dim] - IPTC keywords metadata")
    console.print("• [dim]ImageIPTCCaption[/dim] - IPTC caption metadata")
    console.print("• [dim]ImageXMPKeywords[/dim] - XMP keywords metadata")
    console.print("• [dim]ImageXMPTitle[/dim] - XMP title metadata")
    console.print("• [dim]ImageLatitude[/dim] - GPS latitude (from EXIF)")
    console.print("• [dim]ImageLongitude[/dim] - GPS longitude (from EXIF)")

    # Configuration saving option
    console.print(f"\n[bold cyan]💾 Save Configuration[/bold cyan]")
    save_config_choice = (
        console.input(
            "Save this configuration for future use? (y/n)\n[dim]Saved configs can be reused with --list command[/dim]\n> "
        )
        .strip()
        .lower()
    )

    list_config = {
        "search_dir": search_dir,
        "output_dir": output_dir,
        "excluded_extensions": excluded_extensions,
        "created": datetime.now().isoformat(),
        "description": f"List config: {search_dir} -> {output_dir}",
    }

    config_saved = False
    if save_config_choice in ("y", "yes"):
        console.print("Choose how to save the configuration:")
        console.print("  1. Auto-generate filename with timestamp")
        console.print("  2. Specify custom filename")

        save_choice = console.input("Choice (1 or 2): ").strip()

        if save_choice == "2":
            custom_name = console.input("Config name (without extension): ").strip()
            if custom_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                config_path = (
                    f"photochomper_list_config_{custom_name}_{timestamp}.listconf"
                )
            else:
                config_path = None
        else:
            config_path = None

        saved_path = save_list_config(list_config, config_path)
        if saved_path:
            console.print(f"[green]✅ Configuration saved: {saved_path}[/green]")
            config_saved = True
        else:
            console.print("[red]❌ Failed to save configuration[/red]")

    # Final confirmation
    console.print(f"\n[bold yellow]📋 Configuration Summary:[/bold yellow]")
    console.print(f"• Search directory: [cyan]{search_dir}[/cyan]")
    console.print(f"• Output directory: [cyan]{output_dir}[/cyan]")
    console.print(
        f"• Excluded extensions: [cyan]{', '.join(excluded_extensions) if excluded_extensions else 'none'}[/cyan]"
    )
    console.print(f"• Include hidden files: [cyan]yes[/cyan]")
    console.print(f"• Include all file types: [cyan]yes[/cyan]")
    if config_saved:
        console.print(f"• Configuration saved: [green]yes[/green]")

    confirm = (
        console.input(f"\n[bold]Start file listing? (y/n): [/bold]").strip().lower()
    )
    if confirm not in ("y", "yes"):
        console.print("[yellow]File listing cancelled.[/yellow]")
        return

    # Run the comprehensive listing
    console.print(f"\n[bold blue]Starting comprehensive file listing...[/bold blue]")
    run_comprehensive_listing(search_dir, output_dir, excluded_extensions)


def run_list(config: dict):
    """Run file listing using configuration (for compatibility if needed)."""
    search_dir = config.get("search_dir", str(Path.home() / "Pictures"))
    output_dir = config.get("output_dir", search_dir)
    excluded_extensions = config.get("excluded_extensions", [])

    run_comprehensive_listing(search_dir, output_dir, excluded_extensions)
