# Weekly Team Reports - Quick Start Guide

Get started with automated weekly team status reports in 5 minutes!

## Prerequisites

- ✅ Python 3.8+
- ✅ Jira account with API access
- ✅ GitHub account with repository access
- ✅ MCP-compatible client (Cursor, VS Code, etc.)

## Setup Steps

### 1. Install Dependencies

#### With Virtual Environment (Recommended)

```bash
cd team-reports-mcp-server

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

#### Without Virtual Environment

```bash
cd team-reports-mcp-server
pip install -r requirements.txt
```

This installs:
- MCP server framework
- Jira Python client
- team-reports library
- YAML configuration support

> **Why virtual environment?** Isolates dependencies and prevents conflicts with other Python projects.

### 2. Configure Jira Credentials

Create `.env` file in the project root:

```bash
JIRA_SERVER=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token
```

**Get your Jira API token:**
1. Visit: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy token to `.env` file

### 3. Configure GitHub Token

**Create a Personal Access Token:**
1. Visit: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - ✅ `repo` (for private repos)
   - or just `public_repo` (for public repos only)
4. Click "Generate token"
5. **Add to `.env` file:**

```bash
GITHUB_TOKEN=ghp_your_github_token_here
```

> **Note:** You can also pass the token as a parameter instead of storing in `.env`

### 4. Configure Team Settings (Flexible Options)

You have **two ways** to configure your team reports:

#### Option A: Configuration Files (Recommended for Regular Use)

Copy and customize the example config files:

```bash
cd config
cp jira_config.yaml.example jira_config.yaml
cp github_config.yaml.example github_config.yaml
```

**Minimal `config/jira_config.yaml`:**
```yaml
# REQUIRED: Base JQL query for filtering issues
base_jql: "project = MYPROJECT"

# Team member email addresses
team_emails:
  - john@company.com
  - jane@company.com
```

**Minimal `config/github_config.yaml`:**
```yaml
# REQUIRED: Repositories to monitor
repositories:
  - owner: myorg
    repo: backend
  - owner: myorg
    repo: frontend

# Team member GitHub usernames
team_members:
  - johndoe
  - janesmith
```

#### Option B: Parameter Overrides (Great for Testing)

Skip config files entirely and pass settings as parameters:

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

> **Note:** Configuration files are optional! You can use `config_overrides` parameter instead.

### 5. Test the Setup

```bash
# Test Jira connection
python3 test_connection.py

# Test weekly report functionality
python3 test_weekly_report.py
```

Expected output:
```
✓ All tests passed!
```

### 6. Configure Your MCP Client

**For Cursor** (`~/.cursor/mcp.json`):

**With Virtual Environment:**
```json
{
  "mcpServers": {
    "team-reports": {
      "type": "stdio",
      "command": "/full/path/to/team-reports-mcp-server/venv/bin/python3",
      "args": ["/full/path/to/team-reports-mcp-server/server.py"],
      "env": {
        "JIRA_SERVER": "https://your-company.atlassian.net",
        "JIRA_EMAIL": "your-email@company.com",
        "JIRA_API_TOKEN": "your-api-token",
        "GITHUB_TOKEN": "your-github-token"
      }
    }
  }
}
```

**Without Virtual Environment:**
```json
{
  "mcpServers": {
    "team-reports": {
      "type": "stdio",
      "command": "python3",
      "args": ["/full/path/to/team-reports-mcp-server/server.py"],
      "env": {
        "JIRA_SERVER": "https://your-company.atlassian.net",
        "JIRA_EMAIL": "your-email@company.com",
        "JIRA_API_TOKEN": "your-api-token",
        "GITHUB_TOKEN": "your-github-token"
      }
    }
  }
}
```

**Important:** 
- Replace `/full/path/to/` with your actual absolute path
- With venv: point `command` to `venv/bin/python3`
- Without venv: use system `python3`

### 7. Restart Your MCP Client

Restart Cursor or VS Code to load the new server configuration.

## Usage

### First Report - Basic

In your MCP client, use natural language:

```
"Generate a weekly status report"
```

Or call the tool directly:
```python
# If GITHUB_TOKEN is in .env (recommended):
generate_weekly_status()

# Or pass token explicitly:
generate_weekly_status(
    github_token="ghp_your_github_token_here"
)
```

**What happens:**
1. ✅ Calculates current week (goes back 7 days from today)
2. ✅ Fetches Jira tickets for your team
3. ✅ Fetches GitHub activity for configured repos
4. ✅ Combines into comprehensive markdown report
5. ✅ Saves to `Reports/Weekly_Report_YYYY-MM-DD_to_YYYY-MM-DD.md`
6. ✅ Returns report content to you

### Subsequent Runs - Cached

Running the same command again:

```
"Generate this week's status report"
```

**What happens:**
1. ✅ Checks for existing report
2. ✅ Returns cached content instantly (no API calls!)
3. ✅ Message: "Found existing report (use regenerate=true to recreate)"

### Force Refresh

To get fresh data:

```
"Regenerate this week's status report with fresh data"
```

Or:
```python
generate_weekly_status(regenerate=True)
```

### Specific Week

For last week's report:

```python
generate_weekly_status(
    start_date="2024-11-06",  # Last Wednesday
    end_date="2024-10-30"     # Previous Tuesday
)
```

### Without Config Files

If you don't have config files, use overrides:

```python
generate_weekly_status(
    config_overrides={
        "jira": {
            "projects": ["PROJ1", "PROJ2"],
            "team_members": ["user1@company.com", "user2@company.com"]
        },
        "github": {
            "repositories": ["org/repo1", "org/repo2"],
            "team_members": {
                "githubuser1": "User One",
                "githubuser2": "User Two"
            }
        }
    }
)
```

## Report Output

Your report will include:

### Jira Section
- ✅ Completed tickets by team member
- ✅ Story points and velocity
- ✅ Status distribution
- ✅ Ticket categories and priorities

### GitHub Section
- ✅ Pull requests (opened, merged, reviewed) with descriptions
- ✅ Commit activity by contributor
- ✅ Lines of code changed
- ✅ Repository breakdown

### Getting Executive Summaries
After generating a report, simply ask Cursor:
- ✅ "Summarize this report"
- ✅ "What are the key takeaways?"
- ✅ "Give me an executive overview"

Cursor will analyze the full report and provide a tailored summary!

## Common Issues

### "Missing required credentials"
**Solution:** Ensure `.env` file exists with all required credentials:
- `JIRA_SERVER`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `GITHUB_TOKEN`

Or pass `github_token` as a parameter if you prefer not to store it in `.env`

### "Failed to import team-reports library"
**Solution:** Run `pip install -r requirements.txt` again

### "start_date must be a Wednesday"
**Solution:** Use dates that fall on Wednesday for start_date and Tuesday for end_date

### "No issues found" or "No repositories found"
**Solution:** Check your config files or pass `config_overrides` with your projects/repos

### MCP client doesn't see the tool
**Solution:** 
1. Check the full path in MCP configuration
2. If using venv: ensure `command` points to `venv/bin/python3`
3. Restart MCP client completely
4. Verify server starts without errors: `python3 server.py`

### Virtual environment issues
**Solution:**
- Activate before running: `source venv/bin/activate`
- Check it's active: `which python3` (should show venv path)
- Recreate if broken: `rm -rf venv && python3 -m venv venv`
- Windows users: use `venv\Scripts\activate`

## Tips & Best Practices

### 1. Keep Tokens Secure
- ✅ Store both Jira and GitHub tokens in `.env` file
- ✅ Never commit `.env` to git (already in `.gitignore`)
- ✅ Rotate tokens regularly for security
- ✅ Use minimum required permissions

### 2. Use Caching Efficiently
- ✅ Let the tool cache reports by default
- ✅ Only use `regenerate=True` when data changes
- ✅ Saves API rate limits and speeds up queries

### 3. Customize for Your Team
- ✅ Create config files matching your team structure
- ✅ Adjust status filters to match your workflow
- ✅ Map all team members for accurate reporting

### 4. Automate with Scheduling
- ✅ Consider running reports on a schedule (e.g., Friday afternoons)
- ✅ Use cached reports for quick reference during the week
- ✅ Regenerate when preparing for team meetings

### 5. Share Reports
- ✅ Reports are in Markdown format (easy to share)
- ✅ Can be committed to git for historical tracking
- ✅ Convert to PDF or HTML for distribution

## Example Workflow

**Monday morning:**
```
generate_weekly_status()
→ Creates comprehensive report of previous week
→ Use in team standup or weekly review
```

**During the week:**
```
generate_weekly_status()
→ Returns cached report instantly
→ Quick reference without API calls
```

**Friday afternoon:**
```
generate_weekly_status(regenerate=True)
→ Fresh data for week-end summary
→ Ready for team review meeting
```

## Next Steps

1. ✅ Generate your first report
2. ✅ Review the output in `Reports/` directory
3. ✅ Customize config files for your team
4. ✅ Ask Cursor for executive summaries
5. ✅ Integrate into your weekly team process

## Getting Help

- 📖 Full documentation: See `README.md`
- 🔧 Team-reports config: https://github.com/cmchase/team-reports/blob/main/CONFIGURATION_GUIDE.md
- 🐛 Found a bug? Check logs or run tests: `python3 test_weekly_report.py`
- 💡 Feature ideas? The code is modular and extensible!

## Success!

You're now ready to generate automated weekly team status reports! 🎉

The MCP tool will:
- ✅ Save you hours of manual report compilation
- ✅ Provide consistent, data-driven insights
- ✅ Cache results to minimize API usage
- ✅ Generate AI-ready summaries for leadership

Happy reporting! 📊

