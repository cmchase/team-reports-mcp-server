# Team Reports & Jira MCP Server

A clean and focused Model Context Protocol (MCP) server that provides seamless integration between AI assistants and Jira, enabling natural language interaction with your Jira projects, issues, and workflows.

## 🎯 Features

- **17 Comprehensive Tools** for full Jira interaction, manager workflows, and flow metrics
- **Weekly Team Reports** - Automated Jira + GitHub status reports with auto-generated AI executive summaries
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
| `get_manager_attention_items` | Items needing your guidance (unassigned, stuck in Refinement/Review, high priority) | `get_manager_attention_items(days_in_review=5)` |
| `get_lingering_items` | Tickets lingering in progress/review | `get_lingering_items(days_lingering=7)` |
| `get_bottlenecks_and_priorities` | WIP by status + high-priority in progress | `get_bottlenecks_and_priorities()` |
| `get_manager_coach_brief` | Operator Coach: what to watch for team health and execution | `get_manager_coach_brief()` |
| `get_flow_metrics` | Cycle time, lead time, throughput, predictability over a date range (Kanban-friendly) | `get_flow_metrics(period="last_month")` or `get_flow_metrics(start_date="2026-01-01", end_date="2026-01-31")` |
| `get_sizing_analysis` | Time-to-completion by size (story points) over a date range; repeatable (e.g. 9 months); optionally save baseline; works for any team (kanban, scrum) | `get_sizing_analysis(period_days=270)` or `get_sizing_analysis(start_date="2025-06-01", end_date="2026-03-01", save_report=True)` |
| `test_connections` | Test Jira, GitHub, and GitLab connectivity and credentials | `test_connections()` or `test_connections(connections=["jira", "github"])` |

### Manager workflow (busy engineering managers)

Use these tools to focus on items that need your guidance, spot bottlenecks, and align with coach feedback:

1. **get_manager_attention_items** — Unassigned tickets, items stuck in Refinement or Review, and high-priority in-progress work. Tune with `days_in_refinement`, `days_in_review`, and `include_unassigned`.
2. **get_lingering_items** — Tickets in progress or review for longer than `days_lingering` (default 7). Surfaces stalled work and review bottlenecks.
3. **get_bottlenecks_and_priorities** — WIP counts by status and a list of Critical/Blocker items in progress. Use to prioritize where to unblock.
4. **get_manager_coach_brief** — Operator Coach perspective: what to watch for team health and execution cadence, weekly cadence checklist, and tactical prompts. Optional: add `config/manager_coach_brief.txt` to customize the brief.
5. **get_flow_metrics** — Cycle time, lead time, throughput, and predictability (std dev, percentiles) over a date range. Text-driven for weekly, monthly, quarterly, or ad hoc review. Kanban-friendly; uses the same `status_filters` (execution = active work, completed = done).
6. **get_sizing_analysis** — Time-to-completion by size (story points) over a window (e.g. 9 months). Run periodically to establish a baseline; flow metrics then flag *possibly mis-sized* items when cycle time far exceeds the median for that size. Usable by kanban, scrum, or any team using story points.

All manager and flow-metrics tools use your existing `config/jira_config.yaml` (e.g. `base_jql`, `status_filters`). For t-shirt sizing and “possibly mis-sized” callouts, set `flow_metrics.story_points_field` and keep `team_sizing` (e.g. xsmall: 1, small: 3, medium: 9, large: 27, xlarge: 81). For open PRs that may be lingering, run **generate_weekly_status** and review the PR section. Use **test_connections** to verify Jira, GitHub, and GitLab credentials and connectivity before running reports.

## 👁️ Team health and manager tools

These tools help you keep eyes on team health, spot bottlenecks, and focus on items that need your guidance. They use your Jira config (`config/jira_config.yaml`: `base_jql`, `status_filters`). **get_flow_metrics** delegates to the team-reports library (single source of truth); other manager tools query Jira directly. Optional `config_overrides` apply to the latter; flow metrics use config from file only.

### get_manager_attention_items

Surfaces items that likely need your guidance or feedback.

- **What it finds:** Unassigned tickets; tickets stuck in Refinement (or similar) for N days; tickets stuck in Review (or similar) for N days; Critical/Blocker items in progress or review.
- **Parameters:** `days_in_refinement` (default 3), `days_in_review` (default 5), `include_unassigned` (default true), `max_results` (default 30), `config_overrides` (optional).
- **Example:** `get_manager_attention_items(days_in_review=5, days_in_refinement=3)`
- **Output:** List of issues with key, summary, status, assignee, priority, last updated, and URL.

### get_lingering_items

Highlights work that has been in the same execution state (e.g. In Progress, Review) for too long—useful for spotting stalled work and review bottlenecks.

- **What it finds:** Tickets in your configured “execution” statuses (e.g. In Progress, Review) that haven’t been updated for at least `days_lingering` days, ordered by oldest first.
- **Parameters:** `days_lingering` (default 7), `max_results` (default 50), `config_overrides` (optional).
- **Example:** `get_lingering_items(days_lingering=7)`
- **Output:** List of lingering tickets; includes a note to run **generate_weekly_status** for open PRs/MRs that may be lingering.

### get_bottlenecks_and_priorities

Quick view of WIP distribution and high-priority execution work.

- **What it shows:** Counts of issues by status (planned + execution from your config), then a list of Critical/Blocker items in progress or review.
- **Parameters:** `max_results` (default 20, for the high-priority list), `config_overrides` (optional).
- **Example:** `get_bottlenecks_and_priorities()`
- **Output:** “WIP by status” counts, then high-priority in-progress/review items; ends with a short suggested-focus line.

### get_manager_coach_brief

Operator Coach–style brief for team health and execution cadence: what to watch, weekly cadence checklist, and tactical prompts.

- **Content:** What to watch (review latency, WIP depth, unassigned/refinement, priority alignment); weekly cadence (e.g. top 3 outcomes, 1 decision needed, 1 risk, 1 experiment); tactical prompts when things feel stuck; rules of engagement.
- **Parameters:** `include_data_context` (default true)—when true, adds a tip to run **get_lingering_items** and **get_bottlenecks_and_priorities** first.
- **Customization:** Create `config/manager_coach_brief.txt` to replace the built-in brief with your own.
- **Example:** `get_manager_coach_brief(include_data_context=True)`

### get_flow_metrics

Flow metrics for team health: cycle time, lead time, throughput, and predictability. Text-driven so you can review weekly, monthly, quarterly, or ad hoc without relying on Jira’s control chart UI. Kanban-friendly; the same metrics are useful for Scrum teams (e.g. for “done” flow).

**Implementation:** This tool delegates to the **team-reports** library (single source of truth). The MCP server does not duplicate flow logic; it calls `team_reports.reports.jira_flow_metrics`. `config_overrides` are not applied when delegating. For long periods or very large boards, run from the CLI: `team-reports jira flow-metrics --quarter N --year Y` or `--days N` (no timeout, same config).

#### What it measures

- **Cycle time** — Time from the first transition into an *execution* status (e.g. In Progress, In Review) to the first transition into a *completed* status (e.g. Closed, Done). This is “time in active work” and aligns with Kanban columns (e.g. To Do → In Progress → In Review → Done). Computed from each issue’s Jira changelog (status history).
- **Lead time** — Time from issue creation to the first transition into a completed status. If changelog is missing, resolution date is used as the “done” time. Lead time includes backlog wait, so it is typically longer than cycle time.
- **Throughput** — Number of issues that reached a completed status (and were resolved) within the chosen date range. The tool uses a **count-only Jira request** first, so the number is the true total matching your `base_jql` + completed status + resolution date—not capped by `max_issues`. If there are more completed issues than `max_issues`, cycle/lead stats are computed from the first `max_issues` (by resolution date); the report will say so (e.g. “cycle/lead stats from first 300 issues; increase max_issues for full sample”). **Scope:** Throughput is whatever your `base_jql` matches; if that includes multiple teams or projects, the count will reflect all of them. Tighten `base_jql` in `config/jira_config.yaml` to scope to one team or board (e.g. by board name, project, or label).
- **Predictability** — Standard deviation and 85th/95th percentiles for both cycle and lead time. A **lower standard deviation** means more consistent delivery; **narrowing percentiles** over time can indicate process improvement. High max or wide percentiles often point to outliers worth investigating.

#### How it works

- The tool runs **two Jira requests**: (1) a **count-only** search (`maxResults=0`) to get the true throughput for the period; (2) a search for up to `max_issues` results **with changelog** (`expand='changelog'`) to compute cycle and lead times. So throughput is never understated by the cap; only the cycle/lead sample may be capped.
- It fetches each issue with changelog so it can detect the first transition into an execution status and the first into a completed status. Cycle and lead times are derived from those transitions (or from `created` and `resolutiondate` when changelog is insufficient).
- Status names must match your config: **execution** = active-work columns (e.g. `["In Progress", "Review"]`), **completed** = done columns (e.g. `["Closed"]`). If your board uses different names (e.g. “In Review” vs “Review”), set them in `config/jira_config.yaml` under `status_filters` so cycle time aligns with your board.

#### Choosing a date range

- **`period` presets** — Use `period="last_week"` (7 days), `period="last_month"` (30 days), or `period="last_quarter"` (90 days) for quick, relative ranges from today. Good for weekly standup prep, monthly reviews, or quarterly retrospectives.
- **Custom range** — Use `start_date` and `end_date` (YYYY-MM-DD) for a specific window (e.g. a calendar month, a quarter, or a sprint boundary). If both are provided, they override `period`.
- **Default** — If you omit both `period` and dates, the tool uses the last 30 days.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | string | Start date YYYY-MM-DD. Omit if using `period`. |
| `end_date` | string | End date YYYY-MM-DD. Omit if using `period`. |
| `period` | string | One of `last_week`, `last_month`, `last_quarter`. Ignored when `start_date` and `end_date` are set. |
| `max_issues` | integer | Maximum number of issues to fetch with changelog for cycle/lead stats (default 300). Throughput is always the full count; this only caps the sample used for cycle/lead. |
| `config_overrides` | object | Not applied when delegating to team-reports; config is read from `config/jira_config.yaml` only. |
| `save_report` | boolean | If true, save the report to `Reports/Flow_Metrics_{start}_to_{end}.md`. Default: false (output only in chat). |

#### Examples

```text
# Last 30 days (default)
get_flow_metrics()

# Preset ranges
get_flow_metrics(period="last_week")
get_flow_metrics(period="last_month")
get_flow_metrics(period="last_quarter")

# Custom date range (e.g. January 2026)
get_flow_metrics(start_date="2026-01-01", end_date="2026-01-31")

# Longer period with more issues
get_flow_metrics(period="last_quarter", max_issues=500)

# Save report to disk (Reports/Flow_Metrics_*.md)
get_flow_metrics(period="last_month", save_report=True)
```

#### Output

By default the report is **returned in chat only** (not written to disk). Use `save_report=True` to write it to `Reports/Flow_Metrics_{start}_to_{end}.md`.

Report contents:

- **Period** — The start and end date used.
- **Throughput** — True total issues completed in that period (from a count-only query). If the total exceeds `max_issues`, a note indicates that cycle/lead stats are from the first N issues.
- **Cycle time** — Average, median, min, max, standard deviation, 85th and 95th percentiles (and count of issues with computable cycle time).
- **Lead time** — Same statistics for lead time.
- Notes on scope (`base_jql`) and config (`status_filters`).

#### Config requirement

Ensure `config/jira_config.yaml` has:

- **`base_jql`** — Restricts to the board/project/team you care about (e.g. `project = DISCO AND board = "Discovery Main Board"`).
- **`status_filters.execution`** — Statuses that count as “active work” for cycle time (e.g. `["In Progress", "In Review"]`). Must match your board’s column names exactly.
- **`status_filters.completed`** — Statuses that count as “done” (e.g. `["Closed"]` or `["Done", "Closed"]`).

If cycle time shows “No cycle time data,” check that your board’s status names match these lists and that issues have transition history (changelog) in Jira.

When **flow_metrics.story_points_field** is set, the flow report includes **Cycle by size (story points)** and **Possibly mis-sized**. Optional **team_sizing** maps points to labels (e.g. t-shirt names); without it, raw point values are used. Use **get_sizing_analysis** (e.g. `period_days=270`) for a repeatable view by size; optionally `save_report` and `save_baseline`.

### Suggested workflow

1. Run **get_flow_metrics** (e.g. `period="last_month"`) for a baseline on cycle time, lead time, throughput, and predictability.
2. Run **get_lingering_items** and **get_bottlenecks_and_priorities** to see where work is stuck and where WIP is concentrated.
3. Run **get_manager_attention_items** to see concrete tickets that need your guidance (unassigned, stuck in refinement/review, or high-priority in progress).
4. Run **get_manager_coach_brief** to align your actions with the Operator Coach perspective and weekly cadence.
5. For PR/MR context (e.g. open PRs that may be lingering), run **generate_weekly_status** and review the PR section.

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

Copy `env.template` to `.env` and set your Jira (and optional GitHub/GitLab) values:

```bash
cp env.template .env
# Edit .env: set JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN (and GITHUB_TOKEN, GITLAB_TOKEN if needed)
```

**Getting Your API Token:**  
Create a token at [Atlassian API tokens](https://id.atlassian.com/manage-profile/security/api-tokens) and paste it into `JIRA_API_TOKEN` in `.env`. After migrating to a new Jira instance, create a new token for that instance and update `.env`.

**Single source of truth:** Prefer storing credentials only in `.env`. You can omit the `env` block in your MCP config (see step 4) so the server loads from the repo’s `.env` when it starts—one place to update when URLs or tokens change.

### 3. Test Connection

```bash
python3 test_connection.py
```



### 4. Configure MCP Client

#### For Cursor:
Add to `~/.cursor/mcp.json` (or Cursor Settings → MCP). Use the full path to your `team-reports-mcp-server` repo.

**Recommended: use `.env` only (no credentials in MCP config).** The server loads from the repo’s `.env` when started with the repo as working directory:

**With Virtual Environment:**
```json
{
  "mcpServers": {
    "team-reports": {
      "type": "stdio",
      "command": "/full/path/to/team-reports-mcp-server/venv/bin/python3",
      "args": ["/full/path/to/team-reports-mcp-server/server.py"]
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
      "args": ["/full/path/to/team-reports-mcp-server/server.py"]
    }
  }
}
```

Optional: if you prefer to pass credentials in the MCP config instead of `.env`, add an `"env"` block with `JIRA_SERVER`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, and optionally `GITHUB_TOKEN`/`GITLAB_TOKEN`. Keeping credentials only in `.env` is easier to maintain (e.g. after a Jira instance migration).

#### For VS Code:
Add to your VS Code MCP configuration. Prefer no `env` block so the server uses the repo’s `.env`:

**With Virtual Environment:**
```json
{
  "mcpServers": {
    "team-reports": {
      "type": "stdio",
      "command": "/full/path/to/team-reports-mcp-server/venv/bin/python3",
      "args": ["/full/path/to/team-reports-mcp-server/server.py"]
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
      "args": ["/full/path/to/team-reports-mcp-server/server.py"]
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

The `generate_weekly_status` tool combines data from Jira and GitHub to create comprehensive weekly team reports with automatically generated AI-powered executive summaries.

### Features

- **Intelligent Caching** - Checks for existing reports to avoid duplicate API calls
- **Wednesday-Tuesday Weeks** - Follows standard sprint week boundaries
- **Combined Data** - Merges Jira issue tracking with GitHub code activity
- **AI Summaries** - Automatically generated executive summaries using Cursor's LLM (no additional API keys needed)
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
    regenerate=False          # Use cached report if exists
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

### Get an Executive Summary

After generating a report, ask Cursor to create a summary:

```
"Summarize the weekly report I just generated, focusing on:
1. Key accomplishments
2. Critical blockers
3. Team velocity and trends"
```

Or simply:

```
"Give me an executive summary of this report"
```

Cursor will analyze the full report content and provide a concise overview tailored to your needs.

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
   - Completed tickets by team member with descriptions (truncated to 500 chars)
   - Story points and velocity metrics
   - Status distribution and trends

2. **GitHub Weekly Summary**
   - Pull requests opened/merged/reviewed with descriptions (truncated to 500 chars)
   - Commit activity by contributor
   - Lines of code added/removed
   - Repository activity breakdown

**💡 Tip:** After generating a report, ask Cursor to create an executive summary tailored to your needs!

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