# GitHub Token Refactoring Summary

## Overview

Refactored the team-reports MCP server to treat GitHub tokens the same way as Jira credentials - stored in the `.env` file with optional parameter override.

## Date

November 7, 2025

## Motivation

The user requested that GitHub tokens be stored in the `.env` file rather than only passed as parameters, providing:
- **Consistency** with Jira credential handling
- **Convenience** for users with single GitHub accounts
- **Flexibility** to still override via parameter when needed

## Changes Made

### 1. Environment Template (`env.template`)

**Added:**
```bash
# ============================================================================
# GITHUB CONFIGURATION
# ============================================================================

# Your GitHub Personal Access Token
# Generate at: https://github.com/settings/tokens
GITHUB_TOKEN=your-github-token-here
```

**Benefits:**
- Clear instructions for obtaining GitHub token
- Consistent with Jira credential format
- Documents required token scopes

### 2. Server Implementation (`server.py`)

#### Tool Definition Changes

**Before:**
```python
"github_token": {
    "type": "string",
    "description": "GitHub API token for accessing repository data"
},
"required": ["github_token"]
```

**After:**
```python
"github_token": {
    "type": "string",
    "description": "GitHub API token for accessing repository data. If not provided, reads from GITHUB_TOKEN environment variable."
},
"required": []
```

#### Method Signature Changes

**Before:**
```python
async def _generate_weekly_status(
    self,
    github_token: str,  # Required parameter
    ...
```

**After:**
```python
async def _generate_weekly_status(
    self,
    github_token: Optional[str] = None,  # Now optional
    ...
```

#### Credential Validation Logic

**Before:**
```python
# Validate required credentials
jira_server = os.getenv("JIRA_SERVER")
jira_email = os.getenv("JIRA_EMAIL")
jira_api_token = os.getenv("JIRA_API_TOKEN")

if not all([jira_server, jira_email, jira_api_token]):
    return [TextContent(
        type="text",
        text="Error: Missing Jira credentials. Ensure JIRA_SERVER, JIRA_EMAIL, and JIRA_API_TOKEN are set."
    )]
```

**After:**
```python
# Validate required credentials
jira_server = os.getenv("JIRA_SERVER")
jira_email = os.getenv("JIRA_EMAIL")
jira_api_token = os.getenv("JIRA_API_TOKEN")

# Get GitHub token from parameter or environment variable
if not github_token:
    github_token = os.getenv("GITHUB_TOKEN")

# Validate all required credentials
missing_creds = []
if not jira_server:
    missing_creds.append("JIRA_SERVER")
if not jira_email:
    missing_creds.append("JIRA_EMAIL")
if not jira_api_token:
    missing_creds.append("JIRA_API_TOKEN")
if not github_token:
    missing_creds.append("GITHUB_TOKEN")

if missing_creds:
    return [TextContent(
        type="text",
        text=f"Error: Missing required credentials: {', '.join(missing_creds)}\n\n"
             f"Please set these environment variables in your .env file or pass github_token as a parameter."
    )]
```

### 3. Test Suite (`test_weekly_report.py`)

**Updated credential test:**
```python
required_vars = ["JIRA_SERVER", "JIRA_EMAIL", "JIRA_API_TOKEN", "GITHUB_TOKEN"]
```

Added note that GitHub token can also be passed as parameter.

### 4. Documentation Updates

#### README.md

**Prerequisites section:**
```markdown
2. **GitHub token** (from `.env` file or passed as parameter):
   - `GITHUB_TOKEN` environment variable (recommended)
   - Or pass `github_token` parameter when calling the tool
   - Personal Access Token with `repo` scope
   - Generate at: https://github.com/settings/tokens
```

**Basic usage example:**
```python
# If GITHUB_TOKEN is set in .env, no parameters needed!
generate_weekly_status()

# Or pass GitHub token explicitly
generate_weekly_status(
    github_token="ghp_your_github_token_here"
)
```

#### WEEKLY_REPORTS_QUICKSTART.md

**Updated setup instructions:**
- Added step 3 to configure GitHub token in `.env`
- Updated all usage examples to show parameter-free calls
- Updated Common Issues section
- Updated Tips & Best Practices for token security

## Usage Patterns

### Pattern 1: Token in .env (Recommended)

```bash
# .env file
JIRA_SERVER=https://company.atlassian.net
JIRA_EMAIL=user@company.com
JIRA_API_TOKEN=jira_token_here
GITHUB_TOKEN=ghp_github_token_here
```

```python
# Simple usage - no parameters needed!
generate_weekly_status()
```

### Pattern 2: Parameter Override

```bash
# .env file (GitHub token optional)
JIRA_SERVER=https://company.atlassian.net
JIRA_EMAIL=user@company.com
JIRA_API_TOKEN=jira_token_here
```

```python
# Pass token explicitly (useful for multi-account scenarios)
generate_weekly_status(
    github_token="ghp_different_token"
)
```

### Pattern 3: Mixed Approach

```bash
# .env file with default token
GITHUB_TOKEN=ghp_default_token
```

```python
# Use default from .env
generate_weekly_status()

# Override for specific repositories
generate_weekly_status(
    github_token="ghp_org_specific_token",
    config_overrides={
        "github": {
            "repositories": ["special-org/private-repo"]
        }
    }
)
```

## Benefits

### 1. Consistency
- ✅ Both Jira and GitHub credentials handled identically
- ✅ Single `.env` file for all credentials
- ✅ Predictable credential management pattern

### 2. Convenience
- ✅ No need to pass token on every call
- ✅ Simpler tool invocation for common use cases
- ✅ Cleaner natural language commands

### 3. Flexibility
- ✅ Still supports parameter override when needed
- ✅ Useful for multi-account scenarios
- ✅ Backwards compatible approach

### 4. Security
- ✅ Centralized credential storage
- ✅ All tokens in `.gitignore`d file
- ✅ Clear documentation about security practices

## Migration Guide

### For Existing Users

If you were previously passing `github_token` as a parameter:

**Option A: Move to .env (Recommended)**
```bash
# Add to .env file
echo "GITHUB_TOKEN=your_token_here" >> .env

# Update usage (remove parameter)
# Before:
generate_weekly_status(github_token="ghp_...")

# After:
generate_weekly_status()
```

**Option B: Keep Parameter Approach**
```python
# No changes needed - parameter still works!
generate_weekly_status(github_token="ghp_...")
```

### For New Users

1. Copy `env.template` to `.env`
2. Fill in all credentials including `GITHUB_TOKEN`
3. Call `generate_weekly_status()` without parameters

## Testing

All tests pass with the new implementation:

```bash
python3 test_weekly_report.py
```

Expected output:
```
✓ Date Calculation - PASS
✓ Configuration Loading - PASS  
✓ Report Caching - PASS
⚠ Credentials - WARN (expected without .env)
```

## Backwards Compatibility

✅ **Fully backwards compatible**

- Existing code passing `github_token` parameter continues to work
- Parameter overrides environment variable when provided
- No breaking changes to API

## Files Modified

1. ✅ `env.template` - Added GITHUB_TOKEN section
2. ✅ `server.py` - Made github_token optional, reads from env
3. ✅ `test_weekly_report.py` - Updated credential checks
4. ✅ `README.md` - Updated documentation and examples
5. ✅ `WEEKLY_REPORTS_QUICKSTART.md` - Updated setup guide and examples

## Validation

- ✅ No linter errors
- ✅ Python syntax valid
- ✅ All imports work correctly
- ✅ Tool definition schema valid
- ✅ Documentation consistent
- ✅ Examples updated throughout

## Summary

The refactoring successfully treats GitHub tokens the same way as Jira credentials while maintaining full backwards compatibility. Users can now store their GitHub token in the `.env` file for convenience, or continue passing it as a parameter when needed. The implementation is clean, well-documented, and follows the existing patterns in the codebase.

