#!/usr/bin/env python3
"""
Test script to demonstrate the automatic 'report' addition in filenames.
"""


def test_filename_logic():
    """Test the logic for ensuring 'report' is in filenames."""
    print("🔧 Testing Report Filename Logic")
    print("=" * 40)

    test_cases = [
        ("duplicates", "duplicates_report"),
        ("my_files", "my_files_report"),
        ("photos_report", "photos_report"),
        ("report_data", "report_data"),
        ("my_duplicates_", "my_duplicates_report"),
        ("REPORT_Photos", "REPORT_Photos"),
        ("photos_REPORT_data", "photos_REPORT_data"),
        ("scan_results", "scan_results_report"),
    ]

    print("Input filename → Output filename (reason)")
    print("-" * 50)

    for input_name, expected in test_cases:
        # Apply the same logic as in tui.py
        if "report" not in input_name.lower():
            if input_name.endswith("_"):
                result = input_name + "report"
            else:
                result = input_name + "_report"
            reason = "added 'report'"
        else:
            result = input_name
            reason = "already contains 'report'"

        status = "✅" if result == expected else "❌"
        print(f"{input_name:20} → {result:25} ({reason}) {status}")


def show_auto_discovery_patterns():
    """Show what patterns the --summary auto-discovery looks for."""
    print("\n🔍 Auto-Discovery File Patterns")
    print("=" * 35)
    print("The --summary command automatically finds files matching:")
    print("• duplicates_report*.csv")
    print("• duplicates_report*.json")
    print("• *_report*.csv")
    print("• *_report*.json")
    print()
    print("Examples of files that WILL be found:")
    print("  ✅ duplicates_report.csv")
    print("  ✅ duplicates_report_20250803_123456.csv")
    print("  ✅ my_photos_report.json")
    print("  ✅ scan_report_final.csv")
    print()
    print("Examples of files that will NOT be found:")
    print("  ❌ duplicates.csv (missing 'report')")
    print("  ❌ my_files.json (missing 'report')")
    print("  ❌ scan_results.csv (missing 'report')")
    print()
    print(
        "💡 Solution: Use --setup to configure filenames, or specify files explicitly:"
    )
    print("   python main.py --summary my_files.csv")


def main():
    """Run filename logic tests and show auto-discovery patterns."""
    print("⚡ PhotoChomper Report Filename Tests")
    print("=" * 50)

    test_filename_logic()
    show_auto_discovery_patterns()

    print("\n📝 Summary:")
    print("• Setup now automatically adds 'report' to filenames if missing")
    print("• This ensures compatibility with --summary auto-discovery")
    print("• Users are informed when filenames are modified")
    print("• Explicit file specification still works for any filename")


if __name__ == "__main__":
    main()
