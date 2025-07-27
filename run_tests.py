#!/usr/bin/env python3
"""
Test runner for the image base64 converter project.

This script runs all unit tests and integration tests, providing
comprehensive test coverage verification.
"""
import sys
import os
import unittest
import subprocess
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def run_all_tests():
    """Run all tests and display results."""
    print("=" * 60)
    print("IMAGE BASE64 CONVERTER - TEST SUITE")
    print("=" * 60)
    
    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    # Return success status
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED!")
    
    return success


def run_specific_test_module(module_name):
    """Run tests from a specific module."""
    print(f"Running tests from: {module_name}")
    print("-" * 40)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(f'tests.{module_name}')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return len(result.failures) == 0 and len(result.errors) == 0


def check_test_coverage():
    """Check which components have test coverage."""
    print("\nTEST COVERAGE CHECK:")
    print("-" * 40)
    
    test_files = [
        ('tests/test_converter.py', 'ImageConverter class'),
        ('tests/test_file_handler.py', 'FileHandler class'),
        ('tests/test_cli.py', 'CLI class'),
        ('tests/test_integration.py', 'Integration tests'),
    ]
    
    for test_file, description in test_files:
        if os.path.exists(test_file):
            print(f"✅ {description}: {test_file}")
        else:
            print(f"❌ {description}: {test_file} (MISSING)")
    
    # Check test data
    test_data_dir = Path('tests/test_data')
    if test_data_dir.exists():
        test_files = list(test_data_dir.glob('*'))
        print(f"✅ Test data files: {len(test_files)} files in {test_data_dir}")
    else:
        print(f"❌ Test data directory: {test_data_dir} (MISSING)")


def main():
    """Main function to run tests based on command line arguments."""
    if len(sys.argv) > 1:
        # Run specific test module
        module_name = sys.argv[1]
        success = run_specific_test_module(module_name)
    else:
        # Run all tests
        check_test_coverage()
        print()
        success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()