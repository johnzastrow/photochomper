#!/usr/bin/env python3
"""
PhotoChomper Version Test Runner
Created: 2025-09-05
Purpose: Run all version-specific tests and regression tests

This script executes all version test scripts and provides comprehensive
reporting on the status of fixes across all PhotoChomper versions.
"""

import sys
import subprocess
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_test_script(script_path, verbose=False):
    """Run a single test script and return results."""
    print(f"\n{'='*60}")
    print(f"Running: {script_path}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, cwd=str(project_root))
        
        execution_time = time.time() - start_time
        
        if verbose or result.returncode != 0:
            print("STDOUT:")
            print(result.stdout)
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
        
        success = result.returncode == 0
        print(f"Result: {'✓ PASS' if success else '✗ FAIL'} ({execution_time:.2f}s)")
        
        return {
            'script': script_path,
            'success': success,
            'execution_time': execution_time,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
        
    except Exception as e:
        print(f"✗ ERROR: Failed to run {script_path}: {e}")
        return {
            'script': script_path,
            'success': False,
            'execution_time': 0,
            'stdout': '',
            'stderr': str(e)
        }

def find_version_tests():
    """Find all version test scripts."""
    version_tests_dir = project_root / "tests" / "version_tests"
    if not version_tests_dir.exists():
        return []
    
    test_scripts = []
    for script in version_tests_dir.glob("test_v*.py"):
        test_scripts.append(script)
    
    return sorted(test_scripts)

def find_regression_tests():
    """Find all regression test scripts."""
    regression_tests_dir = project_root / "tests" / "regression"
    if not regression_tests_dir.exists():
        return []
    
    test_scripts = []
    for script in regression_tests_dir.glob("regression_suite_v*.py"):
        test_scripts.append(script)
    
    return sorted(test_scripts)

def find_integration_tests():
    """Find all integration test scripts."""
    integration_tests_dir = project_root / "tests" / "integration"
    if not integration_tests_dir.exists():
        return []
    
    test_scripts = []
    for script in integration_tests_dir.glob("integration_v*.py"):
        test_scripts.append(script)
    
    return sorted(test_scripts)

def save_test_log(results, log_file):
    """Save test results to log file."""
    with open(log_file, 'w') as f:
        f.write("PhotoChomper Test Execution Log\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['success'])
        failed_tests = total_tests - passed_tests
        
        f.write("Summary:\n")
        f.write(f"  Total Tests: {total_tests}\n")
        f.write(f"  Passed: {passed_tests}\n")
        f.write(f"  Failed: {failed_tests}\n")
        f.write(f"  Success Rate: {(passed_tests/total_tests*100):.1f}%\n\n")
        
        f.write("Detailed Results:\n")
        f.write(f"{'='*60}\n")
        
        for result in results:
            status = "PASS" if result['success'] else "FAIL"
            f.write(f"\n{result['script'].name}: {status} ({result['execution_time']:.2f}s)\n")
            
            if not result['success']:
                f.write("STDOUT:\n")
                f.write(result['stdout'])
                f.write("\nSTDERR:\n")
                f.write(result['stderr'])
                f.write("\n" + "-"*40 + "\n")

def main():
    """Main test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run PhotoChomper version tests")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Verbose output")
    parser.add_argument("--version-tests", action="store_true",
                       help="Run only version-specific tests")
    parser.add_argument("--regression-tests", action="store_true", 
                       help="Run only regression tests")
    parser.add_argument("--integration-tests", action="store_true",
                       help="Run only integration tests")
    
    args = parser.parse_args()
    
    print("PhotoChomper Version Test Suite")
    print(f"Project Root: {project_root}")
    print(f"{'='*60}")
    
    all_results = []
    
    # Find all test scripts
    version_tests = find_version_tests()
    regression_tests = find_regression_tests()
    integration_tests = find_integration_tests()
    
    print(f"Found {len(version_tests)} version tests")
    print(f"Found {len(regression_tests)} regression tests")
    print(f"Found {len(integration_tests)} integration tests")
    
    # Run tests based on arguments
    if args.version_tests or not any([args.regression_tests, args.integration_tests]):
        print("\nRunning Version-Specific Tests...")
        for test_script in version_tests:
            result = run_test_script(test_script, args.verbose)
            all_results.append(result)
    
    if args.regression_tests or not any([args.version_tests, args.integration_tests]):
        print("\nRunning Regression Tests...")
        for test_script in regression_tests:
            result = run_test_script(test_script, args.verbose)
            all_results.append(result)
    
    if args.integration_tests or not any([args.version_tests, args.regression_tests]):
        print("\nRunning Integration Tests...")
        for test_script in integration_tests:
            result = run_test_script(test_script, args.verbose)
            all_results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST EXECUTION SUMMARY")
    print(f"{'='*60}")
    
    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if r['success'])
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests Run: {total_tests}")
    print(f"Passed: {passed_tests} ✓")
    print(f"Failed: {failed_tests} ✗")
    
    if total_tests > 0:
        success_rate = (passed_tests / total_tests) * 100
        print(f"Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print("\nFailed Tests:")
            for result in all_results:
                if not result['success']:
                    print(f"  ✗ {result['script'].name}")
    
    # Save log
    logs_dir = project_root / "tests" / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"test_run_{timestamp}.log"
    save_test_log(all_results, log_file)
    
    print(f"\nDetailed log saved to: {log_file}")
    
    # Exit with appropriate code
    sys.exit(0 if failed_tests == 0 else 1)

if __name__ == "__main__":
    main()