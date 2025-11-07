# Jira MCP Server

A clean and focused Model Context Protocol (MCP) server that provides seamless integration between AI assistants and Jira, enabling natural language interaction with your Jira projects, issues, and workflows.

## 🎯 Features

- **12 Comprehensive Tools** for full Jira interaction
- **Weekly Team Reports** - Automated Jira + GitHub status reports with AI summaries
- **Natural Language Interface** - Ask AI to manage your Jira work
- **Real-time Updates** - Get current project status and issue information
- **Secure Authentication** - API token-based authentication
- **Cross-platform** - Works with any MCP-compatible client
- **Easy Setup** - Simple configuration and testing
- **Intelligent Caching** - Avoids duplicate API calls for existing reports

## 🛠️ Available Tools

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `get_issue` | Get detailed issue info | `get_issue(issue_key="PROJ-12345")` |
| `search_issues` | Search with JQL | `search_issues(jql="project = PROJ")` |
| `create_issue` | Create new issue | `create_issue(project_key="PROJ", issue_type="Bug", summary="...")` |
| `update_issue` | Update existing issue | `update_issue(issue_key="PROJ-12345", summary="New title")` |
| `add_comment` | Add comment to issue | `add_comment(issue_key="PROJ-12345", comment="...")` |
| `get_comments` | Get all comments | `get_comments(issue_key="PROJ-12345")` |
| `transition_issue` | Move through workflow | `transition_issue(issue_key="PROJ-12345", transition_name="In Progress")` |
| `get_project` | Get project info | `get_project(project_key="PROJ")` |
| `get_issue_types` | Get available types | `get_issue_types(project_key="PROJ")` |
| `get_my_issues` | Get assigned issues | `get_my_issues(max_results=20)` |
| `get_project_issues` | Get project issues | `get_project_issues(project_key="PROJ")` |
| `generate_weekly_status` | Generate weekly report | `generate_weekly_status(github_token="ghp_...")` |

## 🚀 Quick Start (5 minutes)

### Prerequisites

- Python 3.8 or higher
- Jira account with API access
- MCP-compatible client (Cursor, VS Code, etc.)

### 1. Clone and Setup

#### Create Virtual Environment (Recommended)

Using a virtual environment isolates dependencies and prevents conflicts:

```bash
cd team-reports-mcp-server

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

#### Without Virtual Environment (Not Recommended)

```bash
cd team-reports-mcp-server
pip install -r requirements.txt
```

> **Note:** If you use a virtual environment, remember to use the venv Python path in your MCP configuration (see step 4).

### 2. Configure Credentials

Create a `.env` file with your Jira details:

```bash
JIRA_SERVER=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token
```

**Getting Your API Token:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token to your `.env` file

### 3. Test Connection

```bash
python3 test_connection.py
```



### 4. Configure MCP Client

#### For Cursor:
Add to `~/.cursor/mcp.json`:

**With Virtual Environment (Recommended):**
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

#### For VS Code:
Add to your VS Code MCP configuration:

**With Virtual Environment (Recommended):**
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
- Use the full absolute path to `server.py` and Python interpreter
- The `"type": "stdio"` field is **required** for proper MCP communication
- With virtual environment: point `command` to `venv/bin/python3`
- Without virtual environment: use system `python3`

### 5. Start the Server

```bash
# If using virtual environment, activate it first
source venv/bin/activate  # On macOS/Linux

# Start the server
python3 server.py
```

### 6. Restart and Test

Restart your MCP client and try these commands:

- "Show me all open issues in project XYZ"
- "Create a new task for fixing the login bug"
- "Search for high priority bugs assigned to me"

## 📁 Project Structure

```
jira-mcp-server/
├── server.py              # Main MCP server implementation
├── test_connection.py     # Connection test script
├── test_weekly_report.py  # Weekly report functionality tests
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create this)
├── README.md              # This file
├── config/                # Configuration files (optional)
│   ├── jira_config.yaml   # Jira configuration
│   ├── github_config.yaml # GitHub configuration
│   └── team_config.yaml   # Team configuration
└── Reports/               # Generated weekly reports
    └── Weekly_Report_*.md
```

## 🔗 Related Projects

- **[Team Reports](https://github.com/cmchase/team-reports)** - Comprehensive team reporting library for Jira and GitHub (integrated in this MCP server)
- **[Jira Weekly Reports](https://github.com/sthirugn/jira-weekly-reports)** - Original project for automated weekly team summaries from Jira tickets

## 🎯 Usage Examples

### Get Your Issues
```python
# Get issues assigned to you
get_my_issues(max_results=10)
```

### Search for Specific Issues
```python
# Find high priority bugs
search_issues(jql="project = PROJ AND priority = High AND type = Bug")

# Find recent updates
search_issues(jql="project = PROJ AND updated >= -7d")
```

### Create New Issue
```python
create_issue(
    project_key="PROJ",
    issue_type="Task",
    summary="Implement new feature",
    description="Add support for advanced filtering",
    priority="Medium"
)
```

### Update Issue Status
```python
transition_issue(
    issue_key="PROJ-12345",
    transition_name="In Progress"
)
```

### Get Issue Details
```python
# Get details for issue PROJ-12345
get_issue(issue_key="PROJ-12345")
```

### Search Issues
```python
# Search for open issues in PROJ project
search_issues(jql="project = PROJ AND status = Open", max_results=10)
```

## 📊 Weekly Team Status Reports

The `generate_weekly_status` tool combines data from Jira and GitHub to create comprehensive weekly team reports with optional AI-powered executive summaries.

### Features

- **Intelligent Caching** - Checks for existing reports to avoid duplicate API calls
- **Wednesday-Tuesday Weeks** - Follows standard sprint week boundaries
- **Combined Data** - Merges Jira issue tracking with GitHub code activity
- **AI Summaries** - Optional executive summaries with configurable prompts
- **Hybrid Configuration** - Load from config files or pass parameters directly
- **Auto-Save** - Reports saved to `Reports/` directory in Markdown format

### Prerequisites for Weekly Reports

1. **Jira credentials** (from `.env` file):
   - `JIRA_SERVER`
   - `JIRA_EMAIL`
   - `JIRA_API_TOKEN`

2. **GitHub token** (from `.env` file or passed as parameter):
   - `GITHUB_TOKEN` environment variable (recommended)
   - Or pass `github_token` parameter when calling the tool
   - Personal Access Token with `repo` scope
   - Generate at: https://github.com/settings/tokens

3. **Configuration** (flexible, choose one approach):
   
   **Option A: Configuration Files** (recommended for permanent setups)
   - Create `config/jira_config.yaml` - Jira projects, team members, filters
   - Create `config/github_config.yaml` - GitHub repositories, team mapping
   - Copy from `.example` files in `config/` directory
   - See [team-reports documentation](https://github.com/cmchase/team-reports) for full config details
   
   **Option B: Parameter Overrides** (recommended for one-off reports)
   - Pass `config_overrides` parameter directly
   - No config files needed
   - Great for testing or dynamic configurations

### Basic Usage

```python
# Generate report for current week (uses current date, goes back 7 days)
# If GITHUB_TOKEN is set in .env, no parameters needed!
generate_weekly_status()

# Or pass GitHub token explicitly
generate_weekly_status(
    github_token="ghp_your_github_token_here"
)
```

### Advanced Usage

```python
# Generate report for specific week (dates must be Wednesday-Tuesday)
generate_weekly_status(
    github_token="ghp_your_github_token_here",
    start_date="2024-11-13",  # Wednesday
    end_date="2024-11-06",    # Previous Tuesday
    regenerate=False,         # Use cached report if exists
    generate_summary=True     # Include AI summary prompt
)
```

### With Configuration Overrides

```python
# Option 1: Override config files with custom settings
generate_weekly_status(
    config_overrides={
        "jira": {
            "base_jql": "project IN (PROJ1, PROJ2) AND sprint = 'Sprint 42'",
            "team_emails": ["alice@company.com", "bob@company.com"]
        },
        "github": {
            "repositories": [
                {"owner": "myorg", "repo": "backend"},
                {"owner": "myorg", "repo": "frontend"}
            ],
            "team_members": ["alice-gh", "bob-gh"]
        }
    }
)

# Option 2: No config files, everything in parameters
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

### With Custom AI Summary Prompt

```python
# Use custom prompt for AI summary generation
generate_weekly_status(
    github_token="ghp_your_github_token_here",
    generate_summary=True,
    summary_prompt="""
    Analyze this weekly report and provide:
    1. Top 3 achievements
    2. Critical blockers
    3. Recommendations for next week
    
    {report_content}
    """
)
```

### Force Regeneration

```python
# Force regeneration even if report exists
generate_weekly_status(
    github_token="ghp_your_github_token_here",
    regenerate=True  # Bypass cache and regenerate
)
```

### Report Output

Reports are saved to `Reports/Weekly_Report_YYYY-MM-DD_to_YYYY-MM-DD.md` and include:

1. **Jira Weekly Summary**
   - Completed tickets by team member
   - Story points and velocity metrics
   - Status distribution and trends

2. **GitHub Weekly Summary**
   - Pull requests opened/merged/reviewed
   - Commit activity by contributor
   - Lines of code added/removed
   - Repository activity breakdown

3. **AI Summary Prompt** (if enabled)
   - Ready-to-use prompt for executive summary
   - Customizable focus areas
   - Action-oriented insights

### Example Workflow

1. **First run** - Generates fresh report from Jira and GitHub APIs:
```
generate_weekly_status(github_token="ghp_...")
→ Creates Reports/Weekly_Report_2024-11-06_to_2024-11-13.md
```

2. **Subsequent runs** - Returns cached report instantly:
```
generate_weekly_status(github_token="ghp_...")
→ Found existing report (use regenerate=true to recreate)
→ Returns cached content without API calls
```

3. **Force update** - Regenerates with fresh data:
```
generate_weekly_status(github_token="ghp_...", regenerate=True)
→ Fetches latest data from APIs
→ Overwrites existing report
```

### Configuration Setup

The MCP server now supports **two flexible ways** to configure reports:

#### Option 1: Config Files (Recommended for Regular Use)

Example config files are provided in the `config/` directory. Copy and customize them:

```bash
# Copy example files and customize
cd config
cp jira_config.yaml.example jira_config.yaml
cp github_config.yaml.example github_config.yaml

# Edit the files with your team's settings
```

**`config/jira_config.yaml` (required fields):**
```yaml
# Base JQL query for filtering issues (REQUIRED)
base_jql: "project = MYPROJECT"

# Team member email addresses
team_emails:
  - member1@company.com
  - member2@company.com

# Optional: Additional filters, custom fields, etc.
# See jira_config.yaml.example for full options
```

**`config/github_config.yaml` (required fields):**
```yaml
# Repositories to monitor (REQUIRED)
repositories:
  - owner: your-org
    repo: your-repo-1
  - owner: your-org
    repo: your-repo-2

# Team member GitHub usernames
team_members:
  - github-username-1
  - github-username-2

# Optional: Activity filters, report options, etc.
# See github_config.yaml.example for full options
```

#### Option 2: Parameter Overrides (Great for Testing)

Skip config files entirely and pass settings directly:

```python
generate_weekly_status(
    config_overrides={
        "jira": {
            "base_jql": "project = MYPROJ",
            "team_emails": ["user@company.com"]
        },
        "github": {
            "repositories": [
                {"owner": "org", "repo": "repo1"}
            ],
            "team_members": ["username"]
        }
    }
)
```

#### Hybrid Approach (Best of Both Worlds)

Config files serve as defaults, `config_overrides` modifies specific values:

```python
# Config file has full team setup
# Override just the date range or specific filters
generate_weekly_status(
    config_overrides={
        "jira": {
            "base_jql": "project = MYPROJ AND sprint = 'Sprint 42'"
        }
    }
)
```

See [team-reports CONFIGURATION_GUIDE.md](https://github.com/cmchase/team-reports/blob/main/CONFIGURATION_GUIDE.md) for complete configuration documentation.

## 🔍 JQL Query Examples

### Common Patterns
```jql
# Your assigned issues
assignee = currentUser()

# Issues in specific project
project = PROJ

# Open issues
status = Open

# Issues updated in last 7 days
updated >= -7d

# High priority issues
priority = High

# Issues with specific component
component = "Backend"

# Status filters
status IN ("In Progress", "Code Review")

# Date filters
created >= "2025-01-01"

# Priority filters
priority IN ("High", "Critical")

# Combined queries
project = PROJ AND status = Open AND priority = High
assignee = currentUser() AND updated >= -3d
```

## 🧪 Testing Your Setup

### 1. Connection Test
```bash
python3 test_connection.py
```
✅ Should show: "Successfully connected to Jira"

### 2. Weekly Report Functionality Test
```bash
python3 test_weekly_report.py
```
✅ Tests date calculation, configuration loading, and report caching
✅ Validates helper functions without requiring API credentials
✅ Shows detailed results for each test component

### 3. Start Server (Optional Test)
```bash
python3 server.py
```
✅ Should start the MCP server and wait for connections.

### 4. Individual Tool Test
```bash
# Test search functionality
python3 -c "
import asyncio
from server import JiraMCPServer

async def test():
    server = JiraMCPServer()
    await server._init_jira_client()
    result = await server._search_issues('project = PROJ', max_results=3)
    print(f'Found {len(result)} results')

asyncio.run(test())
"
```

## 🚀 Starting the Server

Simply run the server directly:

```bash
python3 server.py
```

**Note:** Make sure you've completed the setup steps above (installing dependencies, creating `.env` file, and testing connection) before starting the server.

## 🔒 Security Best Practices

1. **Never commit `.env` file** - Add to `.gitignore`
2. **Use API tokens** instead of passwords
3. **Rotate tokens regularly**
4. **Limit token permissions** to minimum required
5. **Use environment variables** for sensitive data

## 🐛 Troubleshooting

### Common Issues

1. **Authentication Error**
   - Check your API token is correct
   - Ensure your email matches your Jira account
   - Verify token hasn't expired

2. **Connection Error**
   - Check your internet connection
   - Verify JIRA_SERVER URL is correct
   - Ensure firewall allows HTTPS connections

3. **Permission Error**
   - Check your Jira permissions
   - Verify you have access to the project/issue
   - Contact your Jira administrator

4. **"Permission denied" errors**
   - Run: `chmod +x server.py test_connection.py`

5. **"Module not found" errors**
   - If using virtual environment: Make sure it's activated (`source venv/bin/activate`)
   - Run: `pip install -r requirements.txt`
   - Verify packages installed: `pip list | grep -E "mcp|jira|team-reports"`

6. **Virtual Environment Issues**
   - If MCP can't find modules: Ensure `command` in MCP config points to `venv/bin/python3`
   - If activation fails: Recreate venv (`rm -rf venv && python3 -m venv venv`)
   - On Windows: Use `venv\Scripts\activate` instead of `source venv/bin/activate`
   - Check venv is active: `which python3` should show path to venv

7. **Cursor/VS Code doesn't see the server**
   - Double-check the absolute path in your MCP config
   - Restart MCP client completely
   - Check that the `.env` file has the correct credentials
   - **"No tools or prompts" error**: Ensure `"type": "stdio"` is included in your MCP configuration
   - **Virtual environment**: Use the full path to your Python interpreter (e.g., `/full/path/to/team-reports-mcp-server/venv/bin/python3`)

### Debug Mode

Enable debug logging by modifying the logging level in `server.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## 🛠️ Development

### Adding New Tools

1. Add tool definition to `list_tools()` method
2. Add handler in `call_tool()` method
3. Implement the actual tool method
4. Update this README

### Error Handling

The server includes comprehensive error handling:
- Connection errors
- Authentication failures
- Invalid issue keys
- JQL syntax errors
- Permission errors

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🎉 Success!

Your Jira MCP server is now properly configured and ready to use! You can:

- ✅ Search and view Jira issues
- ✅ Create and update issues
- ✅ Manage comments and transitions
- ✅ Get project information
- ✅ Handle your assigned work

The server provides a powerful interface between AI assistants and your Jira workflow, making it easier to manage projects and track progress.

## 📈 What's Next?

Once it's working, you can:
- Ask about specific issues: "What's the status of PROJ-123?"
- Create issues: "Create a bug report for the navbar not working"
- Search with JQL: "Find all issues in project ABC that are in review"
- Add comments: "Add a comment to PROJ-456 saying testing is complete"
- Transition issues: "Move PROJ-789 to Done"

Enjoy your new Jira integration! 🎉 