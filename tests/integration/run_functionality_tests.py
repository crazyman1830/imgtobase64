"""
Comprehensive test runner for functionality verification.

This script runs all integration tests to verify that the refactored
code maintains all existing functionality.

Requirements: 1.1, 1.2
"""
import sys
import os
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import test modules
from test_functionality_verification import run_functionality_verification_tests
from test_cli_integration import run_cli_integration_tests
from test_web_integration import run_web_integration_tests


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"🎯 {title}")
    print("=" * 80)


def print_summary(results: dict):
    """Print test summary."""
    print("\n" + "=" * 80)
    print("📊 FUNCTIONALITY VERIFICATION TEST SUMMARY")
    print("=" * 80)
    
    total_suites = len(results)
    passed_suites = sum(1 for result in results.values() if result)
    failed_suites = total_suites - passed_suites
    
    print(f"\n📈 Test Suite Results:")
    for suite_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {suite_name}: {status}")
    
    print(f"\n📊 Overall Statistics:")
    print(f"   Total Test Suites: {total_suites}")
    print(f"   Passed: {passed_suites}")
    print(f"   Failed: {failed_suites}")
    print(f"   Success Rate: {passed_suites/total_suites*100:.1f}%")
    
    if failed_suites == 0:
        print("\n🎉 ALL FUNCTIONALITY VERIFICATION TESTS PASSED!")
        print("✅ The refactored code successfully maintains all existing functionality")
        print("🚀 The system is ready for production use")
    else:
        print(f"\n⚠️  {failed_suites} TEST SUITE(S) FAILED")
        print("🔍 Please review the detailed test output above")
        print("🛠️  Fix the issues before proceeding to production")
    
    return failed_suites == 0


def check_prerequisites():
    """Check if all prerequisites are met for running tests."""
    print("🔍 Checking Prerequisites...")
    
    # Check if main.py exists
    main_script = Path(__file__).parent.parent.parent / 'main.py'
    if not main_script.exists():
        print("❌ main.py not found")
        return False
    
    # Check if src directory exists
    src_dir = Path(__file__).parent.parent.parent / 'src'
    if not src_dir.exists():
        print("❌ src directory not found")
        return False
    
    # Check if core modules exist
    core_dir = src_dir / 'core'
    if not core_dir.exists():
        print("❌ src/core directory not found")
        return False
    
    # Check if web modules exist
    web_dir = src_dir / 'web'
    if not web_dir.exists():
        print("❌ src/web directory not found")
        return False
    
    print("✅ All prerequisites met")
    return True


def run_all_functionality_tests():
    """Run all functionality verification tests."""
    start_time = time.time()
    
    print_header("FUNCTIONALITY VERIFICATION TEST SUITE")
    print("This comprehensive test suite verifies that all existing functionality")
    print("continues to work correctly after the refactoring process.")
    print("\nTest Coverage:")
    print("• Dependency Injection Container")
    print("• CLI Interface (single file and batch processing)")
    print("• Web Interface (all API endpoints)")
    print("• Service Layer Integration")
    print("• Error Handling")
    print("• Backward Compatibility")
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Cannot run tests.")
        return False
    
    # Store test results
    results = {}
    
    try:
        # Test 1: Core Functionality Verification
        print_header("TEST SUITE 1: CORE FUNCTIONALITY VERIFICATION")
        results['Core Functionality'] = run_functionality_verification_tests()
        
        # Test 2: CLI Integration Tests
        print_header("TEST SUITE 2: CLI INTEGRATION TESTS")
        results['CLI Integration'] = run_cli_integration_tests()
        
        # Test 3: Web Interface Integration Tests
        print_header("TEST SUITE 3: WEB INTERFACE INTEGRATION TESTS")
        results['Web Integration'] = run_web_integration_tests()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n\n❌ Unexpected error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Calculate total time
    end_time = time.time()
    total_time = end_time - start_time
    
    # Print summary
    success = print_summary(results)
    
    print(f"\n⏱️  Total Test Time: {total_time:.2f} seconds")
    print("=" * 80)
    
    return success


def main():
    """Main entry point."""
    try:
        success = run_all_functionality_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Tests cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()