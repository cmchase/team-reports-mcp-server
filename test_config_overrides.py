#!/usr/bin/env python3
"""
Test script for config_overrides functionality
Tests the temp config file generation and merging logic
"""

import os
import sys
import tempfile
import yaml
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the helper functions from server.py
from server import create_temp_config_file, merge_config_with_defaults


def test_create_temp_config():
    """Test temporary config file creation"""
    print("Testing create_temp_config_file()...")
    
    config = {
        "base_jql": "project = TEST",
        "team_emails": ["test@example.com"],
        "nested": {
            "key1": "value1",
            "key2": "value2"
        }
    }
    
    try:
        # Create temp config file
        temp_path = create_temp_config_file(config, prefix='test_')
        print(f"✓ Created temp file: {temp_path}")
        
        # Verify file exists
        assert os.path.exists(temp_path), "Temp file should exist"
        print("✓ Temp file exists")
        
        # Verify content
        with open(temp_path, 'r') as f:
            loaded_config = yaml.safe_load(f)
        
        assert loaded_config == config, "Loaded config should match original"
        print("✓ Config content matches original")
        
        # Clean up
        os.unlink(temp_path)
        print("✓ Temp file cleaned up\n")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False


def test_merge_with_no_defaults():
    """Test merging when no default file exists"""
    print("Testing merge_config_with_defaults() with no defaults...")
    
    config_overrides = {
        "jira": {
            "base_jql": "project = TEST",
            "team_emails": ["test@example.com"]
        }
    }
    
    try:
        result = merge_config_with_defaults(
            config_overrides,
            "non_existent_file.yaml",
            "jira"
        )
        
        assert result == config_overrides["jira"], "Should return override values"
        print("✓ Returns override values when no defaults exist\n")
        return True
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False


def test_merge_with_defaults():
    """Test merging overrides with existing defaults"""
    print("Testing merge_config_with_defaults() with defaults...")
    
    # Create a temp default config file
    default_config = {
        "base_jql": "project = DEFAULT",
        "team_emails": ["default@example.com"],
        "custom_fields": {
            "story_points": "customfield_10016"
        }
    }
    
    fd, default_path = tempfile.mkstemp(suffix='.yaml')
    try:
        with os.fdopen(fd, 'w') as f:
            yaml.dump(default_config, f)
        
        # Override specific values
        config_overrides = {
            "jira": {
                "base_jql": "project = OVERRIDE",
                "team_emails": ["override@example.com"]
                # Note: custom_fields not overridden, should be preserved
            }
        }
        
        result = merge_config_with_defaults(
            config_overrides,
            default_path,
            "jira"
        )
        
        # Verify merged result
        assert result["base_jql"] == "project = OVERRIDE", "base_jql should be overridden"
        assert result["team_emails"] == ["override@example.com"], "team_emails should be overridden"
        assert result["custom_fields"] == {"story_points": "customfield_10016"}, "custom_fields should be preserved"
        
        print("✓ Override values correctly merged with defaults")
        print("✓ Non-overridden values preserved from defaults\n")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False
    finally:
        if os.path.exists(default_path):
            os.unlink(default_path)


def test_deep_merge():
    """Test deep merging of nested dictionaries"""
    print("Testing deep merge of nested dictionaries...")
    
    # Create a temp default config file
    default_config = {
        "nested": {
            "level1": {
                "key1": "default1",
                "key2": "default2"
            },
            "level2": "value2"
        }
    }
    
    fd, default_path = tempfile.mkstemp(suffix='.yaml')
    try:
        with os.fdopen(fd, 'w') as f:
            yaml.dump(default_config, f)
        
        # Override only one nested key
        config_overrides = {
            "test": {
                "nested": {
                    "level1": {
                        "key1": "override1"
                        # key2 should be preserved
                    }
                    # level2 should be preserved
                }
            }
        }
        
        result = merge_config_with_defaults(
            config_overrides,
            default_path,
            "test"
        )
        
        # Verify deep merge
        assert result["nested"]["level1"]["key1"] == "override1", "key1 should be overridden"
        assert result["nested"]["level1"]["key2"] == "default2", "key2 should be preserved"
        assert result["nested"]["level2"] == "value2", "level2 should be preserved"
        
        print("✓ Deep merge correctly preserves nested structures")
        print("✓ Only overridden values are replaced\n")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}\n")
        return False
    finally:
        if os.path.exists(default_path):
            os.unlink(default_path)


def main():
    print("=" * 60)
    print("Config Overrides Functionality Tests")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Create temp config", test_create_temp_config()))
    results.append(("Merge with no defaults", test_merge_with_no_defaults()))
    results.append(("Merge with defaults", test_merge_with_defaults()))
    results.append(("Deep merge", test_deep_merge()))
    
    # Print summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()

