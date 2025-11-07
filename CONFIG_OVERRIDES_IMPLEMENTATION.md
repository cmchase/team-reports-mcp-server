# Configuration Overrides Implementation

## Overview

Implemented the **medium-term solution** for flexible configuration management, enabling the MCP server to support both configuration files and runtime parameter overrides.

## What Was Implemented

### 1. Core Functionality

#### Temporary Config File Generation
- Added `create_temp_config_file()` helper function
- Creates temporary YAML files from dictionaries
- Automatically cleans up temp files after use

#### Config Merging with Deep Update
- Added `merge_config_with_defaults()` helper function
- Loads default configs from YAML files (if they exist)
- Performs deep merge of `config_overrides` parameter
- Nested values are properly merged (not replaced)

#### Integration in `generate_weekly_status`
- Modified `_generate_weekly_status()` method to:
  - Check for `config_overrides` parameter
  - Merge with default config files (if present)
  - Create temporary config files for team-reports library
  - Pass temp config paths to WeeklyJiraSummary and WeeklyGitHubSummary
  - Clean up temp files in `finally` block

### 2. Example Configuration Files

Created example config templates in `config/` directory:

#### `config/jira_config.yaml.example`
```yaml
base_jql: "project = MYPROJECT"  # REQUIRED
team_emails:
  - member1@company.com
  - member2@company.com
# ... additional optional fields
```

#### `config/github_config.yaml.example`
```yaml
repositories:  # REQUIRED
  - owner: your-org
    repo: your-repo-1
team_members:
  - github-username-1
# ... additional optional fields
```

### 3. Documentation Updates

#### README.md
- Updated "Prerequisites for Weekly Reports" section
- Clarified three configuration approaches:
  - **Option A:** Config files (recommended for permanent setups)
  - **Option B:** Parameter overrides (recommended for one-off reports)
  - **Hybrid:** Config files as defaults + overrides for specific values
- Updated "Configuration Setup" with detailed examples
- Enhanced "With Configuration Overrides" usage examples

#### WEEKLY_REPORTS_QUICKSTART.md
- Updated setup steps to show both configuration approaches
- Added minimal config file examples
- Added parameter override examples
- Clarified that config files are now truly optional

## Technical Implementation

### File: `server.py`

#### New Imports
```python
import tempfile
```

#### New Helper Functions

```python
def create_temp_config_file(config_dict: Dict[str, Any], prefix: str = 'mcp_config_') -> str:
    """
    Create a temporary YAML config file from a dictionary.
    Returns path to temp file.
    """

def merge_config_with_defaults(
    config_overrides: Optional[Dict[str, Any]],
    default_config_path: str,
    config_key: str
) -> Dict[str, Any]:
    """
    Merge config overrides with defaults from a config file.
    Performs deep merge for nested dictionaries.
    """
```

#### Updated Method Logic

```python
async def _generate_weekly_status(...):
    # Prepare config files (temp or default)
    jira_config_file = 'config/jira_config.yaml'
    github_config_file = 'config/github_config.yaml'
    temp_files_to_cleanup = []
    
    try:
        # Create temp config files if overrides provided
        if config_overrides:
            # Merge Jira config with overrides
            jira_config = merge_config_with_defaults(...)
            if jira_config:
                jira_config_file = create_temp_config_file(...)
                temp_files_to_cleanup.append(jira_config_file)
            
            # Similar for GitHub config
        
        # Generate reports using config files (temp or default)
        jira_summary = WeeklyJiraSummary(config_file=jira_config_file, ...)
        github_summary = WeeklyGitHubSummary(config_file=github_config_file, ...)
    
    finally:
        # Clean up temporary config files
        for temp_file in temp_files_to_cleanup:
            os.unlink(temp_file)
```

## Usage Examples

### Basic Usage (Config Files)
```python
# Requires config/jira_config.yaml and config/github_config.yaml
generate_weekly_status()
```

### Full Override (No Config Files)
```python
generate_weekly_status(
    config_overrides={
        "jira": {
            "base_jql": "project = MYPROJ",
            "team_emails": ["user@company.com"]
        },
        "github": {
            "repositories": [{"owner": "org", "repo": "repo"}],
            "team_members": ["username"]
        }
    }
)
```

### Hybrid Approach (Override Specific Values)
```python
# Uses config files as base, overrides specific values
generate_weekly_status(
    config_overrides={
        "jira": {
            "base_jql": "project = MYPROJ AND sprint = 'Sprint 42'"
        }
    }
)
```

### Deep Merge Example
```python
# Config file has:
# jira:
#   base_jql: "project = MYPROJ"
#   team_emails: ["alice@co.com", "bob@co.com"]
#   custom_fields:
#     story_points: "customfield_10016"

# Override just one team member
generate_weekly_status(
    config_overrides={
        "jira": {
            "team_emails": ["charlie@co.com"]  # Replaces team_emails only
            # base_jql and custom_fields remain from config file
        }
    }
)
```

## Benefits

### Flexibility
- ✅ Support both file-based and parameter-based configs
- ✅ Mix and match approaches as needed
- ✅ No breaking changes to existing setups

### User Experience
- ✅ Quick testing without creating config files
- ✅ Config files for permanent team setups
- ✅ Override specific values on-the-fly

### Implementation Quality
- ✅ Proper cleanup of temporary files
- ✅ Deep merge preserves nested structures
- ✅ Graceful fallback if config files don't exist
- ✅ No linting errors

## Testing

To test the implementation:

1. **With config files:**
   ```bash
   cd config
   cp jira_config.yaml.example jira_config.yaml
   cp github_config.yaml.example github_config.yaml
   # Edit files with your settings
   ```
   Then: `generate_weekly_status()`

2. **Without config files (parameter overrides):**
   ```python
   generate_weekly_status(
       config_overrides={
           "jira": {"base_jql": "...", "team_emails": [...]},
           "github": {"repositories": [...], "team_members": [...]}
       }
   )
   ```

3. **Hybrid (config + overrides):**
   Set up config files, then override specific values with `config_overrides`

## Files Modified

1. **server.py**
   - Added `tempfile` import
   - Added `create_temp_config_file()` function
   - Added `merge_config_with_defaults()` function
   - Updated `_generate_weekly_status()` method

2. **config/jira_config.yaml.example**
   - Created comprehensive example config with comments

3. **config/github_config.yaml.example**
   - Created comprehensive example config with comments

4. **README.md**
   - Updated prerequisites section
   - Enhanced configuration setup section
   - Improved usage examples

5. **WEEKLY_REPORTS_QUICKSTART.md**
   - Updated configuration steps
   - Added parameter override examples
   - Clarified optional nature of config files

## Next Steps (Future Enhancements)

1. **Validation:** Add schema validation for config_overrides
2. **Error Messages:** Provide helpful errors for missing required fields
3. **Config Templates:** Generate initial config files programmatically
4. **Team Reports Library:** Consider upstreaming config dict support to the library itself

## Summary

The implementation successfully delivers the **medium-term solution**, providing users with maximum flexibility:
- Config files work as before (no breaking changes)
- Parameter overrides enable dynamic configuration
- Hybrid approach allows both together
- Clean implementation with proper resource cleanup
- Comprehensive documentation and examples

