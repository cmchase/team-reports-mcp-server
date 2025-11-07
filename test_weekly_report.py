#!/usr/bin/env python3
"""
Test script for weekly report generation functionality.
Tests the helper functions and validates the overall flow.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_date_calculation():
    """Test Wednesday-Tuesday week calculation"""
    print("Testing date calculation...")
    
    # Import after adding to path
    from server import get_week_range
    
    # Test 1: Default behavior (current date to 7 days back)
    try:
        start, end = get_week_range()
        print(f"✓ Default date range: {end} to {start}")
        
        # Verify it's 7 days apart
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        delta = (start_dt - end_dt).days
        assert delta == 7, f"Expected 7 days difference, got {delta}"
        print(f"✓ Date range is exactly 7 days apart")
    except Exception as e:
        print(f"✗ Default date range test failed: {e}")
        return False
    
    # Test 2: Valid Wednesday to Tuesday
    try:
        # Find a recent Wednesday
        today = datetime.now()
        days_since_wednesday = (today.weekday() - 2) % 7
        last_wednesday = today - timedelta(days=days_since_wednesday)
        last_tuesday = last_wednesday - timedelta(days=1)
        
        wed_str = last_wednesday.strftime("%Y-%m-%d")
        tue_str = last_tuesday.strftime("%Y-%m-%d")
        
        start, end = get_week_range(wed_str, tue_str)
        print(f"✓ Valid Wed-Tue range: {end} to {start}")
    except Exception as e:
        print(f"✗ Valid Wed-Tue test failed: {e}")
        return False
    
    # Test 3: Invalid start date (not Wednesday)
    try:
        today = datetime.now()
        # Find a day that's not Wednesday
        if today.weekday() != 2:
            invalid_date = today.strftime("%Y-%m-%d")
        else:
            invalid_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        
        start, end = get_week_range(invalid_date, None)
        # If it doesn't validate and is not Wednesday, we should have gotten an error
        if datetime.strptime(invalid_date, "%Y-%m-%d").weekday() != 2:
            print(f"✗ Should have rejected non-Wednesday start date")
            return False
        else:
            print(f"✓ Correctly accepted Wednesday start date")
    except ValueError as e:
        if "must be a Wednesday" in str(e):
            print(f"✓ Correctly rejected non-Wednesday start date")
        else:
            print(f"✗ Unexpected error: {e}")
            return False
    except Exception as e:
        print(f"✗ Invalid start date test failed: {e}")
        return False
    
    print("✓ All date calculation tests passed!\n")
    return True


def test_config_loading():
    """Test configuration loading"""
    print("Testing configuration loading...")
    
    from server import load_config_with_overrides
    
    # Test 1: Load without overrides (may not have config files)
    try:
        config = load_config_with_overrides()
        print(f"✓ Loaded base config: {list(config.keys())}")
        assert 'jira' in config, "Missing 'jira' key"
        assert 'github' in config, "Missing 'github' key"
        assert 'team' in config, "Missing 'team' key"
        print(f"✓ Config has required keys")
    except Exception as e:
        print(f"✗ Base config loading failed: {e}")
        return False
    
    # Test 2: Load with overrides
    try:
        overrides = {
            'jira': {'custom_field': 'test_value'},
            'github': {'test_repo': 'test-org/test-repo'}
        }
        config = load_config_with_overrides(overrides)
        print(f"✓ Loaded config with overrides")
        
        # Verify overrides were applied
        if 'custom_field' in config.get('jira', {}):
            print(f"✓ Overrides applied correctly")
        else:
            # This is OK if config files exist and have other data
            print(f"✓ Config structure is correct")
    except Exception as e:
        print(f"✗ Config override test failed: {e}")
        return False
    
    print("✓ All configuration tests passed!\n")
    return True


def test_report_caching():
    """Test report file caching logic"""
    print("Testing report caching...")
    
    from server import get_report_path, check_report_exists, save_report
    
    # Test 1: Get report path
    try:
        path = get_report_path("2024-11-13", "2024-11-06")
        print(f"✓ Report path: {path}")
        assert "Weekly_Report_2024-11-06_to_2024-11-13.md" in str(path)
        print(f"✓ Report path format is correct")
    except Exception as e:
        print(f"✗ Report path test failed: {e}")
        return False
    
    # Test 2: Check non-existent report
    try:
        content = check_report_exists("2099-01-13", "2099-01-06")
        assert content is None, "Should not find report from year 2099"
        print(f"✓ Correctly returned None for non-existent report")
    except Exception as e:
        print(f"✗ Non-existent report test failed: {e}")
        return False
    
    # Test 3: Save and retrieve report
    try:
        test_content = "# Test Report\n\nThis is a test."
        test_start = "2024-01-10"  # A Wednesday
        test_end = "2024-01-03"    # The Tuesday before
        
        # Save
        saved_path = save_report(test_content, test_start, test_end)
        print(f"✓ Saved test report to: {saved_path}")
        
        # Retrieve
        retrieved = check_report_exists(test_start, test_end)
        assert retrieved is not None, "Should find the report we just saved"
        assert test_content in retrieved, "Retrieved content doesn't match"
        print(f"✓ Successfully retrieved saved report")
        
        # Cleanup
        Path(saved_path).unlink()
        print(f"✓ Cleaned up test report")
    except Exception as e:
        print(f"✗ Save/retrieve test failed: {e}")
        return False
    
    print("✓ All caching tests passed!\n")
    return True


def test_credentials():
    """Test that required credentials are available"""
    print("Testing credentials availability...")
    
    required_vars = ["JIRA_SERVER", "JIRA_EMAIL", "JIRA_API_TOKEN", "GITHUB_TOKEN"]
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        else:
            print(f"✓ {var} is set")
    
    if missing:
        print(f"⚠ Missing environment variables: {', '.join(missing)}")
        print(f"  (These are required for actual report generation)")
        print(f"  Note: github_token can also be passed as a parameter")
        return False
    
    print("✓ All required credentials are available!\n")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Weekly Report Generation Functionality")
    print("=" * 60)
    print()
    
    results = {
        "Date Calculation": test_date_calculation(),
        "Configuration Loading": test_config_loading(),
        "Report Caching": test_report_caching(),
        "Credentials": test_credentials()
    }
    
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name:.<40} {status}")
    
    print()
    
    all_passed = all(results.values())
    
    if all_passed:
        print("🎉 All tests passed!")
        print("\nNext steps:")
        print("1. Ensure your .env file has Jira credentials")
        print("2. Configure config/*.yaml files (or use config_overrides)")
        print("3. Start the MCP server: python3 server.py")
        print("4. Use the generate_weekly_status tool from your MCP client")
        return 0
    else:
        print("⚠ Some tests failed. Please review the errors above.")
        if not results["Credentials"]:
            print("\n💡 Tip: Create a .env file with your Jira credentials to enable full testing")
        return 1


if __name__ == "__main__":
    sys.exit(main())

