# Configuration Directory

This directory contains configuration files for the team-reports MCP server.

## Files

### Executive Summary Prompt

**`executive_summary_prompt.txt`** (private, not in git)
- Contains your team-specific executive summary prompt
- This file is loaded when generating weekly status reports
- Keep this file private to avoid exposing team-specific reporting formats

**`executive_summary_prompt.txt.example`** (public, committed to git)
- Generic example prompt that can be shared
- Copy this file to `executive_summary_prompt.txt` and customize it for your team

### Setup

To customize the executive summary prompt for your team:

```bash
# Copy the example file
cp config/executive_summary_prompt.txt.example config/executive_summary_prompt.txt

# Edit the file with your team-specific instructions
nano config/executive_summary_prompt.txt
```

The server will automatically load your custom prompt when generating weekly status reports. If no custom prompt is found, it will use a generic default.

### Other Configuration Files

**`jira_config.yaml`** - Jira project and team configuration  
**`github_config.yaml`** - GitHub repositories and team mapping  
**`team_config.yaml`** - Team member information and mappings  
**`default_config.yaml`** - Default configuration values

See the main README.md for more information about these configuration files.

## Security Note

The `executive_summary_prompt.txt` file is automatically ignored by git to keep team-specific information private. Make sure this file is never committed to version control.

