#!/usr/bin/env python3
"""
Jira MCP Server

A Model Context Protocol server that provides integration with Jira.
Allows AI assistants to interact with Jira issues, projects, and workflows.
"""

import asyncio
import json
import logging
import os
import ssl
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import yaml

from dotenv import load_dotenv
from jira import JIRA
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
    ServerCapabilities,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_manager_coach_brief() -> Optional[str]:
    """
    Load manager coach brief from config file if present.
    Returns None if file does not exist (use embedded default in _get_manager_coach_brief).
    """
    server_dir = Path(__file__).parent.absolute()
    prompt_file = server_dir / "config" / "manager_coach_brief.txt"
    try:
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        logger.warning(f"Could not load manager coach brief: {e}")
    return None


def load_executive_summary_prompt() -> str:
    """
    Load executive summary prompt from config file.
    
    Returns:
        str: The executive summary prompt text
        
    The prompt is loaded from config/executive_summary_prompt.txt.
    If the file doesn't exist, returns a generic default prompt.
    """
    prompt_file = Path("config/executive_summary_prompt.txt")
    
    try:
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt = f.read()
                logger.info(f"Loaded executive summary prompt from {prompt_file}")
                return prompt
        else:
            logger.warning(f"Executive summary prompt file not found: {prompt_file}")
            logger.info("Using default generic prompt. Copy config/executive_summary_prompt.txt.example to config/executive_summary_prompt.txt to customize.")
            return """
💡 **Next Step:** Please create an executive summary of this report.

Include:
- Key accomplishments and completed work
- Team velocity and productivity metrics  
- Critical blockers or risks
- Notable trends or patterns
- Actionable recommendations for leadership

Format as a concise update suitable for leadership review.
"""
    except Exception as e:
        logger.error(f"Error loading executive summary prompt: {e}")
        return "\n💡 **Tip:** Please summarize this report for an executive overview.\n"

def get_week_range(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[str, str]:
    """
    Calculate Wednesday-Tuesday week boundaries.
    
    Args:
        start_date: Optional start date (YYYY-MM-DD), defaults to current date
        end_date: Optional end date (YYYY-MM-DD), goes back 7 days if not provided
    
    Returns:
        Tuple of (start_date, end_date) in ISO format (YYYY-MM-DD)
    
    Raises:
        ValueError: If start_date is not Wednesday or end_date is not Tuesday
    """
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
        # Validate it's a Tuesday (weekday() returns 1 for Tuesday)
        if end.weekday() != 1:
            raise ValueError(f"end_date must be a Tuesday. {end_date} is a {end.strftime('%A')}")
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            if start.weekday() != 2:
                raise ValueError(f"start_date must be a Wednesday. {start_date} is a {start.strftime('%A')}")
        else:
            # Derive Wednesday from Tuesday (6 days back)
            start = end - timedelta(days=6)
    else:
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            if start.weekday() != 2:
                raise ValueError(f"start_date must be a Wednesday. {start_date} is a {start.strftime('%A')}")
        else:
            start = datetime.now()
        # Calculate end date as 6 days forward from start (Wednesday + 6 days = Tuesday)
        end = start + timedelta(days=6)
    
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def load_config_with_overrides(config_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML files with optional overrides.
    
    Args:
        config_overrides: Optional dictionary to override config values
    
    Returns:
        Dictionary containing merged configuration
    """
    config = {
        'jira': {},
        'github': {},
        'gitlab': {},
        'team': {}
    }
    
    # Try to load config files
    config_dir = Path("config")
    
    # Load Jira config
    jira_config_path = config_dir / "jira_config.yaml"
    if jira_config_path.exists():
        try:
            with open(jira_config_path, 'r') as f:
                config['jira'] = yaml.safe_load(f) or {}
            logger.info(f"Loaded Jira config from {jira_config_path}")
        except Exception as e:
            logger.warning(f"Failed to load Jira config: {e}")
    
    # Load GitHub config
    github_config_path = config_dir / "github_config.yaml"
    if github_config_path.exists():
        try:
            with open(github_config_path, 'r') as f:
                config['github'] = yaml.safe_load(f) or {}
            logger.info(f"Loaded GitHub config from {github_config_path}")
        except Exception as e:
            logger.warning(f"Failed to load GitHub config: {e}")
    
    # Load GitLab config
    gitlab_config_path = config_dir / "gitlab_config.yaml"
    if gitlab_config_path.exists():
        try:
            with open(gitlab_config_path, 'r') as f:
                config['gitlab'] = yaml.safe_load(f) or {}
            logger.info(f"Loaded GitLab config from {gitlab_config_path}")
        except Exception as e:
            logger.warning(f"Failed to load GitLab config: {e}")
    
    # Load team config
    team_config_path = config_dir / "team_config.yaml"
    if team_config_path.exists():
        try:
            with open(team_config_path, 'r') as f:
                config['team'] = yaml.safe_load(f) or {}
            logger.info(f"Loaded team config from {team_config_path}")
        except Exception as e:
            logger.warning(f"Failed to load team config: {e}")
    
    # Apply overrides
    if config_overrides:
        for key, value in config_overrides.items():
            if key in config:
                config[key].update(value)
            else:
                config[key] = value
        logger.info(f"Applied config overrides: {list(config_overrides.keys())}")
    
    return config


def _test_github_sync(github_config: Dict[str, Any]) -> str:
    """Test GitHub: GET /user with token. Returns a status line."""
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        return "**GitHub:** No GITHUB_TOKEN set (required for API).\n"
    url = "https://api.github.com/user"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            login = data.get("login", "?")
            org = (github_config or {}).get("github_org") or (github_config or {}).get("org", "")
            if org:
                org_url = f"https://api.github.com/orgs/{org}"
                req_org = urllib.request.Request(org_url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"})
                try:
                    with urllib.request.urlopen(req_org, timeout=10) as _:
                        pass
                except urllib.error.HTTPError as e:
                    return f"**GitHub:** Authenticated as {login}; org '{org}' not accessible ({e.code}).\n"
            return f"**GitHub:** OK — authenticated as {login}" + (f", org '{org}' OK" if org else "") + "\n"
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return f"**GitHub:** Failed — HTTP {e.code}" + (f" {body[:200]}" if body else "") + "\n"
    except Exception as e:
        return f"**GitHub:** Failed — {str(e)}\n"


def _test_gitlab_sync(gitlab_config: Dict[str, Any]) -> str:
    """Test GitLab: GET /api/v4/user with token. Returns a status line."""
    token = os.getenv("GITLAB_TOKEN", "").strip()
    if not token:
        return "**GitLab:** No GITLAB_TOKEN set (required for API).\n"
    base = (gitlab_config or {}).get("base_url", "https://gitlab.com").rstrip("/")
    url = f"{base}/api/v4/user"
    req = urllib.request.Request(url, headers={"PRIVATE-TOKEN": token})
    ctx = ssl.create_default_context()
    api_settings = (gitlab_config or {}).get("api_settings") or {}
    if api_settings.get("verify_ssl") is False:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            username = data.get("username", data.get("name", "?"))
            return f"**GitLab:** OK — connected to {base}, user {username}\n"
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return f"**GitLab:** Failed — HTTP {e.code}" + (f" {body[:200]}" if body else "") + "\n"
    except Exception as e:
        return f"**GitLab:** Failed — {str(e)}\n"


def get_report_path(start_date: str, end_date: str) -> Path:
    """
    Construct the path for a weekly report file.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Path object for the report file
    """
    # Use absolute path relative to server.py location
    server_dir = Path(__file__).parent.absolute()
    reports_dir = server_dir / "Reports"
    reports_dir.mkdir(exist_ok=True)
    filename = f"Weekly_Report_{start_date}_to_{end_date}.md"
    return reports_dir / filename


def get_flow_metrics_report_path(start_date: str, end_date: str) -> Path:
    """Path for a saved flow metrics report (Reports/Flow_Metrics_{start}_to_{end}.md)."""
    server_dir = Path(__file__).parent.absolute()
    reports_dir = server_dir / "Reports"
    reports_dir.mkdir(exist_ok=True)
    return reports_dir / f"Flow_Metrics_{start_date}_to_{end_date}.md"


def check_report_exists(start_date: str, end_date: str) -> Optional[str]:
    """
    Check if a report already exists for the given date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Report content if exists, None otherwise
    """
    report_path = get_report_path(start_date, end_date)
    
    if report_path.exists():
        try:
            with open(report_path, 'r') as f:
                content = f.read()
            logger.info(f"Found existing report: {report_path}")
            return content
        except Exception as e:
            logger.warning(f"Failed to read existing report: {e}")
            return None
    
    return None


def save_report(content: str, start_date: str, end_date: str) -> str:
    """
    Save report content to disk.
    
    Args:
        content: Report content to save
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Path to saved report file
    """
    report_path = get_report_path(start_date, end_date)
    
    try:
        with open(report_path, 'w') as f:
            f.write(content)
        logger.info(f"Saved report to: {report_path}")
        return str(report_path)
    except Exception as e:
        logger.error(f"Failed to save report: {e}")
        raise


def create_temp_config_file(config_dict: Dict[str, Any], prefix: str = 'mcp_config_') -> str:
    """
    Create a temporary YAML config file from a dictionary.
    
    Args:
        config_dict: Configuration dictionary to write
        prefix: Prefix for the temp file name
    
    Returns:
        Path to the temporary config file
    """
    try:
        # Create a temporary file that won't be automatically deleted
        fd, temp_path = tempfile.mkstemp(suffix='.yaml', prefix=prefix, text=True)
        
        # Write the config to the file
        with os.fdopen(fd, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Created temporary config file: {temp_path}")
        return temp_path
    except Exception as e:
        logger.error(f"Failed to create temp config file: {e}")
        raise


def merge_config_with_defaults(
    config_overrides: Optional[Dict[str, Any]],
    default_config_path: str,
    config_key: str
) -> Dict[str, Any]:
    """
    Merge config overrides with defaults from a config file.
    
    Args:
        config_overrides: Dictionary with override values
        default_config_path: Path to default config file
        config_key: Key to extract from config_overrides (e.g., 'jira', 'github')
    
    Returns:
        Merged configuration dictionary
    """
    # Start with defaults if file exists
    config = {}
    if os.path.exists(default_config_path):
        try:
            with open(default_config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            logger.info(f"Loaded default config from: {default_config_path}")
        except Exception as e:
            logger.warning(f"Could not load default config from {default_config_path}: {e}")
    
    # Apply overrides if provided
    if config_overrides and config_key in config_overrides:
        override_values = config_overrides[config_key]
        if isinstance(override_values, dict):
            # Deep merge - update nested values
            def deep_update(base: dict, updates: dict) -> dict:
                for key, value in updates.items():
                    if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                        base[key] = deep_update(base[key], value)
                    else:
                        base[key] = value
                return base
            
            config = deep_update(config, override_values)
            logger.info(f"Applied config overrides for {config_key}")
    
    return config


class JiraMCPServer:
    def __init__(self):
        self.server = Server("jira-mcp-server")
        self.jira_client: Optional[JIRA] = None
        self._setup_tools()
        
    def _setup_tools(self):
        """Set up all available tools"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available Jira tools"""
            return [
                Tool(
                    name="get_issue",
                    description="Get detailed information about a specific Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "The Jira issue key (e.g., PROJ-123)"
                            }
                        },
                        "required": ["issue_key"]
                    }
                ),
                Tool(
                    name="search_issues",
                    description="Search for Jira issues using JQL (Jira Query Language)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "jql": {
                                "type": "string",
                                "description": "JQL query string (e.g., 'project = PROJ AND status = Open')"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 50
                            }
                        },
                        "required": ["jql"]
                    }
                ),
                Tool(
                    name="create_issue",
                    description="Create a new Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {
                                "type": "string",
                                "description": "Project key (e.g., PROJ)"
                            },
                            "issue_type": {
                                "type": "string",
                                "description": "Issue type (e.g., Task, Bug, Story)"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Issue title/summary"
                            },
                            "description": {
                                "type": "string",
                                "description": "Issue description"
                            },
                            "priority": {
                                "type": "string",
                                "description": "Priority level (e.g., Blocker, Critical, Major, Minor, Undefined)",
                                "default": "Undefined"
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Due date in YYYY-MM-DD format (optional)"
                            }
                        },
                        "required": ["project_key", "issue_type", "summary", "description"]
                    }
                ),
                Tool(
                    name="update_issue",
                    description="Update an existing Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "The Jira issue key"
                            },
                            "summary": {
                                "type": "string",
                                "description": "New summary (optional)"
                            },
                            "description": {
                                "type": "string",
                                "description": "New description (optional)"
                            }
                        },
                        "required": ["issue_key"]
                    }
                ),
                Tool(
                    name="add_comment",
                    description="Add a comment to a Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "The Jira issue key"
                            },
                            "comment": {
                                "type": "string",
                                "description": "Comment text"
                            }
                        },
                        "required": ["issue_key", "comment"]
                    }
                ),
                Tool(
                    name="link_to_epic",
                    description="Link a Jira issue to an epic as its parent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "The Jira issue key to link"
                            },
                            "epic_key": {
                                "type": "string",
                                "description": "The epic key to link to"
                            }
                        },
                        "required": ["issue_key", "epic_key"]
                    }
                ),
                Tool(
                    name="get_comments",
                    description="Get all comments for a Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "The Jira issue key"
                            }
                        },
                        "required": ["issue_key"]
                    }
                ),
                Tool(
                    name="transition_issue",
                    description="Move an issue through workflow states",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "The Jira issue key"
                            },
                            "transition_name": {
                                "type": "string",
                                "description": "Name of the transition (e.g., 'In Progress', 'Done')"
                            }
                        },
                        "required": ["issue_key", "transition_name"]
                    }
                ),
                Tool(
                    name="get_project",
                    description="Get information about a Jira project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {
                                "type": "string",
                                "description": "Project key"
                            }
                        },
                        "required": ["project_key"]
                    }
                ),
                Tool(
                    name="get_issue_types",
                    description="Get available issue types for a project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {
                                "type": "string",
                                "description": "Project key"
                            }
                        },
                        "required": ["project_key"]
                    }
                ),
                Tool(
                    name="get_my_issues",
                    description="Get issues assigned to the current user",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 20
                            }
                        }
                    }
                ),
                Tool(
                    name="get_project_issues",
                    description="Get all issues for a specific project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {
                                "type": "string",
                                "description": "Project key"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 50
                            }
                        },
                        "required": ["project_key"]
                    }
                ),
                Tool(
                    name="generate_weekly_status",
                    description="Generate weekly team status report combining Jira, GitHub, and optionally GitLab data. Checks for existing reports to avoid duplicate API calls. GitHub token from github_token or GITHUB_TOKEN; GitLab token from gitlab_token or GITLAB_TOKEN (for self-hosted/VPN GitLab). After generating, a customizable prompt will be provided for creating an executive summary (customize via config/executive_summary_prompt.txt).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "Week start date (YYYY-MM-DD format, must be Wednesday). Defaults to current date."
                            },
                            "end_date": {
                                "type": "string",
                                "description": "Week end date (YYYY-MM-DD format, must be Tuesday). Defaults to 7 days before start_date."
                            },
                            "github_token": {
                                "type": "string",
                                "description": "GitHub API token for accessing repository data. If not provided, reads from GITHUB_TOKEN environment variable."
                            },
                            "gitlab_token": {
                                "type": "string",
                                "description": "GitLab API token for GitLab data (e.g. self-hosted/VPN). If not provided, reads from GITLAB_TOKEN environment variable. Only used when config/gitlab_config.yaml exists."
                            },
                            "regenerate": {
                                "type": "boolean",
                                "description": "Force regeneration even if report exists. Default: false",
                                "default": False
                            },
                            "config_overrides": {
                                "type": "object",
                                "description": "Override configuration file settings (e.g., team filters, repositories, etc.)"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_manager_attention_items",
                    description="Items that likely need your guidance or feedback: unassigned tickets, tickets stuck in Refinement or Review, high-priority work in progress. Uses team Jira config (base_jql, status_filters).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days_in_refinement": {
                                "type": "integer",
                                "description": "Treat Refinement as needing attention after this many days. Default: 3",
                                "default": 3
                            },
                            "days_in_review": {
                                "type": "integer",
                                "description": "Treat Review as needing attention after this many days. Default: 5",
                                "default": 5
                            },
                            "include_unassigned": {
                                "type": "boolean",
                                "description": "Include unassigned issues. Default: true",
                                "default": True
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum items to return. Default: 30",
                                "default": 30
                            },
                            "config_overrides": {
                                "type": "object",
                                "description": "Optional config overrides (e.g. jira.base_jql)"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_lingering_items",
                    description="Tickets and context on work that has lingered in the same state (e.g. In Progress or Review) for too long. Helps spot stalled work and review bottlenecks. Uses team Jira config.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days_lingering": {
                                "type": "integer",
                                "description": "Consider an item lingering after this many days in same state. Default: 7",
                                "default": 7
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum tickets to return. Default: 50",
                                "default": 50
                            },
                            "config_overrides": {
                                "type": "object",
                                "description": "Optional config overrides"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_bottlenecks_and_priorities",
                    description="Summary of bottlenecks and priority items: WIP counts by status, high-priority in-progress tickets, and suggested focus areas. Uses team Jira config.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "max_results": {
                                "type": "integer",
                                "description": "Max high-priority in-progress items to list. Default: 20",
                                "default": 20
                            },
                            "config_overrides": {
                                "type": "object",
                                "description": "Optional config overrides"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_manager_coach_brief",
                    description="Operator Coach brief: what to watch for team health and execution cadence, weekly cadence checklist, and tactical prompts. Use after reviewing lingering items or bottlenecks to align actions with coach guidance.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_data_context": {
                                "type": "boolean",
                                "description": "If true, include a short note suggesting you run get_lingering_items and get_bottlenecks_and_priorities first. Default: true",
                                "default": True
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_flow_metrics",
                    description="Flow metrics for team health: cycle time, lead time, throughput, predictability (std dev, percentiles) over a date range. Delegates to team-reports library; uses config status_filters (execution, completed). For long periods, use CLI: team-reports jira flow-metrics.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "Start date YYYY-MM-DD. Omit if using period preset."
                            },
                            "end_date": {
                                "type": "string",
                                "description": "End date YYYY-MM-DD. Omit if using period preset."
                            },
                            "period": {
                                "type": "string",
                                "enum": ["last_week", "last_month", "last_quarter"],
                                "description": "Preset range from today: last_week (7 days), last_month (30 days), last_quarter (90 days). Ignored if start_date and end_date are provided."
                            },
                            "max_issues": {
                                "type": "integer",
                                "description": "Max issues to fetch with changelog for metrics. Default: 100 (use 300+ if you need a larger sample and can wait longer).",
                                "default": 100
                            },
                            "config_overrides": {
                                "type": "object",
                                "description": "Optional config overrides (e.g. jira.base_jql, jira.status_filters)."
                            },
                            "save_report": {
                                "type": "boolean",
                                "description": "If true, save the flow metrics report to Reports/Flow_Metrics_{start}_to_{end}.md. Default: false (output only in chat).",
                                "default": False
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="test_connections",
                    description="Test connectivity and credentials for Jira, GitHub, and/or GitLab. Runs a minimal API call per instance. Use to verify env vars and config before running reports or Jira tools.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "connections": {
                                "type": "array",
                                "items": {"type": "string", "enum": ["jira", "github", "gitlab"]},
                                "description": "Which instances to test. Default: all configured (jira, github, gitlab if config exists)."
                            }
                        },
                        "required": []
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            
            # Initialize Jira client only when needed (not for test_connections alone)
            if name != "test_connections" and not self.jira_client:
                await self._init_jira_client()
            
            try:
                if name == "test_connections":
                    return await self._test_connections(arguments.get("connections"))
                if name == "get_issue":
                    return await self._get_issue(arguments["issue_key"])
                elif name == "search_issues":
                    return await self._search_issues(
                        arguments["jql"],
                        arguments.get("max_results", 50)
                    )
                elif name == "create_issue":
                    return await self._create_issue(
                        arguments["project_key"],
                        arguments["issue_type"],
                        arguments["summary"],
                        arguments["description"],
                        arguments.get("priority", "Medium"),
                        arguments.get("due_date")
                    )
                elif name == "update_issue":
                    return await self._update_issue(
                        arguments["issue_key"],
                        arguments.get("summary"),
                        arguments.get("description")
                    )
                elif name == "add_comment":
                    return await self._add_comment(
                        arguments["issue_key"],
                        arguments["comment"]
                    )
                elif name == "link_to_epic":
                    return await self._link_to_epic(
                        arguments["issue_key"],
                        arguments["epic_key"]
                    )
                elif name == "get_comments":
                    return await self._get_comments(arguments["issue_key"])
                elif name == "transition_issue":
                    return await self._transition_issue(
                        arguments["issue_key"],
                        arguments["transition_name"]
                    )
                elif name == "get_project":
                    return await self._get_project(arguments["project_key"])
                elif name == "get_issue_types":
                    return await self._get_issue_types(arguments["project_key"])
                elif name == "get_my_issues":
                    return await self._get_my_issues(arguments.get("max_results", 20))
                elif name == "get_project_issues":
                    return await self._get_project_issues(
                        arguments["project_key"],
                        arguments.get("max_results", 50)
                    )
                elif name == "generate_weekly_status":
                    return await self._generate_weekly_status(
                        arguments.get("github_token"),
                        arguments.get("gitlab_token"),
                        arguments.get("start_date"),
                        arguments.get("end_date"),
                        arguments.get("regenerate", False),
                        arguments.get("config_overrides")
                    )
                elif name == "get_manager_attention_items":
                    return await self._get_manager_attention_items(
                        arguments.get("days_in_refinement", 3),
                        arguments.get("days_in_review", 5),
                        arguments.get("include_unassigned", True),
                        arguments.get("max_results", 30),
                        arguments.get("config_overrides")
                    )
                elif name == "get_lingering_items":
                    return await self._get_lingering_items(
                        arguments.get("days_lingering", 7),
                        arguments.get("max_results", 50),
                        arguments.get("config_overrides")
                    )
                elif name == "get_bottlenecks_and_priorities":
                    return await self._get_bottlenecks_and_priorities(
                        arguments.get("max_results", 20),
                        arguments.get("config_overrides")
                    )
                elif name == "get_manager_coach_brief":
                    return await self._get_manager_coach_brief(
                        arguments.get("include_data_context", True)
                    )
                elif name == "get_flow_metrics":
                    return await self._get_flow_metrics(
                        arguments.get("start_date"),
                        arguments.get("end_date"),
                        arguments.get("period"),
                        arguments.get("max_issues", 100),
                        arguments.get("config_overrides"),
                        arguments.get("save_report", False)
                    )
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
                    
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _init_jira_client(self):
        """Initialize the Jira client with credentials"""
        try:
            server = os.getenv("JIRA_SERVER")
            email = os.getenv("JIRA_EMAIL")
            api_token = os.getenv("JIRA_API_TOKEN")
            
            if not server or not email or not api_token:
                raise ValueError("Missing required environment variables: JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN")
            
            from jira.client import TokenAuth
            # Timeout (seconds) to avoid hanging on slow or large responses (e.g. flow metrics with changelog)
            jira_timeout = 120
            self.jira_client = JIRA(
                server=server,
                token_auth=api_token,
                timeout=jira_timeout,
            )
            logger.info("Successfully connected to Jira")
            
        except Exception as e:
            logger.error(f"Failed to initialize Jira client: {e}")
            raise

    async def _get_issue(self, issue_key: str) -> List[TextContent]:
        """Get detailed information about a Jira issue"""
        try:
            if not self.jira_client:
                return [TextContent(type="text", text="Jira client not initialized")]
            
            issue = self.jira_client.issue(issue_key)
            
            issue_data = {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description or "No description",
                "status": issue.fields.status.name,
                "priority": issue.fields.priority.name if issue.fields.priority else "None",
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                "reporter": issue.fields.reporter.displayName if issue.fields.reporter else "Unknown",
                "created": str(issue.fields.created),
                "updated": str(issue.fields.updated),
                "project": issue.fields.project.name,
                "issue_type": issue.fields.issuetype.name,
                "url": f"{self.jira_client.server_url}/browse/{issue.key}"
            }
            
            text = (f"**Issue: {issue_data['key']}**\n\n"
                   f"**Summary:** {issue_data['summary']}\n"
                   f"**Status:** {issue_data['status']}\n"
                   f"**Priority:** {issue_data['priority']}\n"
                   f"**Assignee:** {issue_data['assignee']}\n"
                   f"**Reporter:** {issue_data['reporter']}\n"
                   f"**Type:** {issue_data['issue_type']}\n"
                   f"**Project:** {issue_data['project']}\n"
                   f"**Created:** {issue_data['created']}\n"
                   f"**Updated:** {issue_data['updated']}\n"
                   f"**URL:** {issue_data['url']}\n\n"
                   f"**Description:**\n{issue_data['description']}")
            
            return [TextContent(type="text", text=text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error fetching issue {issue_key}: {str(e)}")]

    async def _search_issues(self, jql: str, max_results: int = 50) -> List[TextContent]:
        """Search for issues using JQL"""
        try:
            issues = self.jira_client.search_issues(jql, maxResults=max_results)
            
            if not issues:
                return [TextContent(type="text", text="No issues found matching the query.")]
            
            result_text = f"**Found {len(issues)} issue(s):**\n\n"
            
            for issue in issues:
                result_text += (
                    f"• **{issue.key}** - {issue.fields.summary}\n"
                    f"  Status: {issue.fields.status.name} | "
                    f"Assignee: {issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'}\n"
                    f"  URL: {self.jira_client.server_url}/browse/{issue.key}\n\n"
                )
            
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error searching issues: {str(e)}")]

    async def _create_issue(self, project_key: str, issue_type: str, summary: str, 
                          description: str, priority: str = "Medium", due_date: str = None) -> List[TextContent]:
        """Create a new Jira issue"""
        try:
            issue_dict = {
                'project': {'key': project_key},
                'summary': summary,
                'description': description,
                'issuetype': {'name': issue_type},
            }
            
            # Add priority if specified
            if priority:
                issue_dict['priority'] = {'name': priority}
            
            # Add due date if specified
            if due_date:
                issue_dict['duedate'] = due_date
            
            new_issue = self.jira_client.create_issue(fields=issue_dict)
            
            due_date_text = f"\n**Due Date:** {due_date}" if due_date else ""
            text = (f"**Issue created successfully!**\n\n"
                   f"**Key:** {new_issue.key}\n"
                   f"**Summary:** {summary}\n"
                   f"**Type:** {issue_type}\n"
                   f"**Priority:** {priority}{due_date_text}\n"
                   f"**URL:** {self.jira_client.server_url}/browse/{new_issue.key}")
            
            return [TextContent(type="text", text=text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error creating issue: {str(e)}")]

    async def _update_issue(self, issue_key: str, summary: Optional[str] = None, 
                          description: Optional[str] = None) -> List[TextContent]:
        """Update an existing issue"""
        try:
            issue = self.jira_client.issue(issue_key)
            update_dict = {}
            
            if summary:
                update_dict['summary'] = summary
            if description:
                update_dict['description'] = description
                
            if not update_dict:
                return [TextContent(type="text", text="No fields specified for update.")]
            
            issue.update(fields=update_dict)
            
            updates = []
            if summary:
                updates.append(f"Summary: {summary}")
            if description:
                updates.append("Description updated")
                
            text = (f"**Issue {issue_key} updated successfully!**\n\n"
                   f"**Updated fields:** {', '.join(updates)}\n"
                   f"**URL:** {self.jira_client.server_url}/browse/{issue_key}")
            
            return [TextContent(type="text", text=text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error updating issue {issue_key}: {str(e)}")]

    async def _link_to_epic(self, issue_key: str, epic_key: str) -> List[TextContent]:
        """Link an issue to an epic"""
        try:
            # Get the epic issue to find its ID
            epic = self.jira_client.issue(epic_key)
            
            # Use Jira's add_issues_to_epic method
            # This properly sets the Epic Link field (customfield_12311140 in Red Hat Jira)
            self.jira_client.add_issues_to_epic(epic.id, [issue_key])
            
            text = (f"**Issue {issue_key} linked to epic {epic_key} successfully!**\n\n"
                   f"**URL:** {self.jira_client.server_url}/browse/{issue_key}")
            
            return [TextContent(type="text", text=text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error linking issue {issue_key} to epic {epic_key}: {str(e)}")]

    async def _add_comment(self, issue_key: str, comment: str) -> List[TextContent]:
        """Add a comment to an issue"""
        try:
            issue = self.jira_client.issue(issue_key)
            self.jira_client.add_comment(issue, comment)
            
            text = (f"**Comment added to {issue_key} successfully!**\n\n"
                   f"**Comment:** {comment}\n"
                   f"**URL:** {self.jira_client.server_url}/browse/{issue_key}")
            
            return [TextContent(type="text", text=text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error adding comment to {issue_key}: {str(e)}")]

    async def _get_comments(self, issue_key: str) -> List[TextContent]:
        """Get all comments for an issue"""
        try:
            issue = self.jira_client.issue(issue_key)
            comments = self.jira_client.comments(issue)
            
            if not comments:
                return [TextContent(type="text", text=f"No comments found for issue {issue_key}.")]
            
            result_text = f"**Comments for {issue_key}:**\n\n"
            
            for comment in comments:
                result_text += (
                    f"**{comment.author.displayName}** - {comment.created}\n"
                    f"{comment.body}\n"
                    f"---\n\n"
                )
            
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error fetching comments for {issue_key}: {str(e)}")]

    async def _transition_issue(self, issue_key: str, transition_name: str) -> List[TextContent]:
        """Transition an issue to a new status"""
        try:
            issue = self.jira_client.issue(issue_key)
            transitions = self.jira_client.transitions(issue)
            
            # Find the transition by name
            transition_id = None
            available_transitions = []
            
            for transition in transitions:
                available_transitions.append(transition['name'])
                if transition['name'].lower() == transition_name.lower():
                    transition_id = transition['id']
                    break
            
            if not transition_id:
                text = (f"Transition '{transition_name}' not found for issue {issue_key}.\n\n"
                       f"Available transitions: {', '.join(available_transitions)}")
                return [TextContent(type="text", text=text)]
            
            self.jira_client.transition_issue(issue, transition_id)
            
            # Get updated issue to show new status
            updated_issue = self.jira_client.issue(issue_key)
            
            text = (f"**Issue {issue_key} transitioned successfully!**\n\n"
                   f"**New Status:** {updated_issue.fields.status.name}\n"
                   f"**URL:** {self.jira_client.server_url}/browse/{issue_key}")
            
            return [TextContent(type="text", text=text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error transitioning issue {issue_key}: {str(e)}")]

    async def _get_project(self, project_key: str) -> List[TextContent]:
        """Get information about a project"""
        try:
            project = self.jira_client.project(project_key)
            
            project_data = {
                "key": project.key,
                "name": project.name,
                "description": getattr(project, 'description', 'No description'),
                "lead": project.lead.displayName if hasattr(project, 'lead') and project.lead else "No lead",
                "project_type": getattr(project, 'projectTypeKey', 'Unknown'),
                "url": f"{self.jira_client.server_url}/projects/{project.key}"
            }
            
            text = (f"**Project: {project_data['key']}**\n\n"
                   f"**Name:** {project_data['name']}\n"
                   f"**Lead:** {project_data['lead']}\n"
                   f"**Type:** {project_data['project_type']}\n"
                   f"**URL:** {project_data['url']}\n\n"
                   f"**Description:**\n{project_data['description']}")
            
            return [TextContent(type="text", text=text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error fetching project {project_key}: {str(e)}")]

    async def _get_issue_types(self, project_key: str) -> List[TextContent]:
        """Get available issue types for a project"""
        try:
            project = self.jira_client.project(project_key)
            issue_types = project.issueTypes
            
            if not issue_types:
                return [TextContent(type="text", text=f"No issue types found for project {project_key}.")]
            
            result_text = f"**Issue types for project {project_key}:**\n\n"
            
            for issue_type in issue_types:
                result_text += f"• **{issue_type.name}**"
                if hasattr(issue_type, 'description') and issue_type.description:
                    result_text += f" - {issue_type.description}"
                result_text += "\n"
            
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error fetching issue types for {project_key}: {str(e)}")]

    async def _get_my_issues(self, max_results: int = 20) -> List[TextContent]:
        """Get issues assigned to the current user"""
        try:
            jql = "assignee = currentUser() ORDER BY updated DESC"
            issues = self.jira_client.search_issues(jql, maxResults=max_results)
            
            if not issues:
                return [TextContent(type="text", text="No issues assigned to you found.")]
            
            result_text = f"**Your assigned issues ({len(issues)}):**\n\n"
            
            for issue in issues:
                result_text += (
                    f"• **{issue.key}** - {issue.fields.summary}\n"
                    f"  Status: {issue.fields.status.name} | "
                    f"Priority: {issue.fields.priority.name if issue.fields.priority else 'None'}\n"
                    f"  URL: {self.jira_client.server_url}/browse/{issue.key}\n\n"
                )
            
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error fetching your issues: {str(e)}")]

    async def _get_project_issues(self, project_key: str, max_results: int = 50) -> List[TextContent]:
        """Get all issues for a specific project"""
        try:
            jql = f"project = {project_key} ORDER BY updated DESC"
            issues = self.jira_client.search_issues(jql, maxResults=max_results)
            
            if not issues:
                return [TextContent(type="text", text=f"No issues found for project {project_key}.")]
            
            result_text = f"**Issues in project {project_key} ({len(issues)}):**\n\n"
            
            for issue in issues:
                result_text += (
                    f"• **{issue.key}** - {issue.fields.summary}\n"
                    f"  Status: {issue.fields.status.name} | "
                    f"Assignee: {issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'}\n"
                    f"  URL: {self.jira_client.server_url}/browse/{issue.key}\n\n"
                )
            
            return [TextContent(type="text", text=result_text)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error fetching project issues: {str(e)}")]

    def _get_base_jql(self, config_overrides: Optional[Dict[str, Any]] = None) -> str:
        """Load Jira config and return base_jql as a single line for JQL."""
        config = load_config_with_overrides(config_overrides)
        jira = config.get("jira") or {}
        base = (jira.get("base_jql") or "project is not empty").strip()
        return " ".join(base.split())

    def _get_status_lists(self, config_overrides: Optional[Dict[str, Any]] = None) -> Dict[str, List[str]]:
        """Load Jira status_filters from config with defaults."""
        config = load_config_with_overrides(config_overrides)
        jira = config.get("jira") or {}
        status_filters = jira.get("status_filters") or {}
        return {
            "execution": status_filters.get("execution") or ["In Progress", "Review"],
            "planned": status_filters.get("planned") or ["New", "Refinement", "To Do"],
            "completed": status_filters.get("completed") or ["Closed"],
        }

    async def _get_manager_attention_items(
        self,
        days_in_refinement: int = 3,
        days_in_review: int = 5,
        include_unassigned: bool = True,
        max_results: int = 30,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> List[TextContent]:
        """Return Jira items that need manager guidance or feedback."""
        try:
            if not self.jira_client:
                return [TextContent(type="text", text="Jira client not initialized.")]
            base_jql = self._get_base_jql(config_overrides)
            status_lists = self._get_status_lists(config_overrides)
            refinement = status_lists["planned"]
            execution = status_lists["execution"]
            # Build OR conditions: (Refinement + old) OR (Review + old) OR unassigned OR (high priority + in progress/review)
            refinement_statuses = ", ".join(f'"{s}"' for s in refinement if "efinement" in s or s == "Refinement")
            execution_statuses = ", ".join(f'"{s}"' for s in execution)
            conditions = []
            if refinement_statuses and days_in_refinement > 0:
                conditions.append(f'(status IN ({refinement_statuses}) AND updated < -{days_in_refinement}d)')
            if execution_statuses and days_in_review > 0:
                conditions.append(f'(status IN ({execution_statuses}) AND updated < -{days_in_review}d)')
            if include_unassigned:
                conditions.append("assignee is EMPTY")
            if execution_statuses:
                conditions.append(f'(priority IN (Critical, Blocker) AND status IN ({execution_statuses}))')
            if not conditions:
                return [TextContent(type="text", text="**Manager attention:** No conditions configured (check status_filters in Jira config).")]
            jql = f"({base_jql}) AND ({' OR '.join(conditions)}) ORDER BY priority DESC, updated ASC"
            issues = self.jira_client.search_issues(jql, maxResults=max_results)
            if not issues:
                return [TextContent(type="text", text="**Manager attention:** No items need your guidance right now.")]
            lines = ["**Items that may need your guidance or feedback**\n"]
            for issue in issues:
                assignee = issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
                pri = issue.fields.priority.name if issue.fields.priority else "—"
                updated = str(issue.fields.updated)[:10] if issue.fields.updated else "—"
                url = f"{self.jira_client.server_url}/browse/{issue.key}"
                lines.append(f"- **{issue.key}** — {issue.fields.summary}\n  Status: {issue.fields.status.name} | Assignee: {assignee} | Priority: {pri} | Updated: {updated}\n  {url}\n")
            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            logger.error(f"Error in get_manager_attention_items: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_lingering_items(
        self,
        days_lingering: int = 7,
        max_results: int = 50,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> List[TextContent]:
        """Return tickets that have lingered in execution state (e.g. In Progress, Review)."""
        try:
            if not self.jira_client:
                return [TextContent(type="text", text="Jira client not initialized.")]
            base_jql = self._get_base_jql(config_overrides)
            status_lists = self._get_status_lists(config_overrides)
            execution_statuses = ", ".join(f'"{s}"' for s in status_lists["execution"])
            jql = f'({base_jql}) AND status IN ({execution_statuses}) AND updated < -{days_lingering}d ORDER BY updated ASC'
            issues = self.jira_client.search_issues(jql, maxResults=max_results)
            if not issues:
                return [TextContent(type="text", text=f"**Lingering items:** No tickets in progress/review older than {days_lingering} days.")]
            lines = [f"**Tickets in progress/review for more than {days_lingering} days**\n"]
            for issue in issues:
                assignee = issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
                updated = str(issue.fields.updated)[:10] if issue.fields.updated else "—"
                url = f"{self.jira_client.server_url}/browse/{issue.key}"
                lines.append(f"- **{issue.key}** — {issue.fields.summary}\n  Status: {issue.fields.status.name} | Assignee: {assignee} | Updated: {updated}\n  {url}\n")
            lines.append("\n*For open PRs that may be lingering, run generate_weekly_status and review the PR/merge request section.*")
            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            logger.error(f"Error in get_lingering_items: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_bottlenecks_and_priorities(
        self,
        max_results: int = 20,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> List[TextContent]:
        """Return WIP counts by status and high-priority in-progress items."""
        try:
            if not self.jira_client:
                return [TextContent(type="text", text="Jira client not initialized.")]
            base_jql = self._get_base_jql(config_overrides)
            status_lists = self._get_status_lists(config_overrides)
            planned = status_lists["planned"]
            execution = status_lists["execution"]
            all_active = list(planned) + list(execution)
            statuses_jql = ", ".join(f'"{s}"' for s in all_active)
            jql_all = f'({base_jql}) AND status IN ({statuses_jql})'
            issues = self.jira_client.search_issues(jql_all, maxResults=500)
            by_status: Dict[str, int] = {}
            for issue in issues:
                s = issue.fields.status.name
                by_status[s] = by_status.get(s, 0) + 1
            exec_jql = ", ".join(f'"{s}"' for s in execution)
            high_priority_jql = f'({base_jql}) AND status IN ({exec_jql}) AND priority IN (Critical, Blocker) ORDER BY updated DESC'
            high = self.jira_client.search_issues(high_priority_jql, maxResults=max_results)
            lines = ["**Bottlenecks and priorities**\n"]
            lines.append("**WIP by status:**")
            for s in sorted(by_status.keys(), key=lambda x: -by_status[x]):
                lines.append(f"  - {s}: {by_status[s]}")
            lines.append("\n**High-priority in progress/review:**")
            if not high:
                lines.append("  None.")
            else:
                for issue in high:
                    assignee = issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
                    url = f"{self.jira_client.server_url}/browse/{issue.key}"
                    lines.append(f"  - **{issue.key}** — {issue.fields.summary} ({assignee}) — {url}")
            lines.append("\n*Suggested focus: unblock high-priority items first; then reduce review/In Progress age (see get_lingering_items).*")
            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as e:
            logger.error(f"Error in get_bottlenecks_and_priorities: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _get_flow_metrics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        max_issues: int = 100,
        config_overrides: Optional[Dict[str, Any]] = None,
        save_report: bool = False,
    ) -> List[TextContent]:
        """
        Flow metrics (cycle time, lead time, throughput) via team-reports library.
        Delegates to team-reports; config_overrides are not applied.
        """
        try:
            from team_reports.reports.jira_flow_metrics import (
                JiraFlowMetricsReport,
                get_date_range_for_days,
            )

            # Resolve date range (same semantics as before)
            end_dt = datetime.now()
            if start_date and end_date:
                try:
                    datetime.strptime(start_date, "%Y-%m-%d")
                    datetime.strptime(end_date, "%Y-%m-%d")
                    calc_start, calc_end = start_date, end_date
                except ValueError as e:
                    return [TextContent(type="text", text=f"Invalid dates: {e}. Use YYYY-MM-DD.")]
            elif period:
                if period == "last_week":
                    calc_start, calc_end = get_date_range_for_days(7)
                elif period == "last_month":
                    calc_start, calc_end = get_date_range_for_days(30)
                elif period == "last_quarter":
                    calc_start, calc_end = get_date_range_for_days(90)
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown period: {period}. Use last_week, last_month, or last_quarter.",
                    )]
            else:
                calc_start, calc_end = get_date_range_for_days(30)

            server_dir = Path(__file__).resolve().parent
            config_file = str(server_dir / "config" / "jira_config.yaml")

            def _run_flow_metrics_sync() -> str:
                report = JiraFlowMetricsReport(
                    config_file=config_file,
                    jira_server=os.getenv("JIRA_SERVER"),
                    jira_email=os.getenv("JIRA_EMAIL"),
                    jira_token=os.getenv("JIRA_API_TOKEN"),
                )
                report.initialize()
                return report.generate_report(calc_start, calc_end, max_issues=max_issues)

            FLOW_METRICS_TIMEOUT = 600  # 10 min (no longer limited by MCP; team-reports is the source)
            logger.info("Flow metrics: delegating to team-reports (%s to %s)...", calc_start, calc_end)
            loop = asyncio.get_event_loop()
            report_text = await asyncio.wait_for(
                loop.run_in_executor(None, _run_flow_metrics_sync),
                timeout=FLOW_METRICS_TIMEOUT,
            )

            if save_report:
                def _write_sync() -> Tuple[Optional[Path], Optional[str]]:
                    try:
                        path = get_flow_metrics_report_path(calc_start, calc_end)
                        path.write_text(report_text, encoding="utf-8")
                        return (path, None)
                    except Exception as e:
                        return (None, str(e))

                try:
                    flow_path, save_err = await asyncio.wait_for(
                        loop.run_in_executor(None, _write_sync),
                        timeout=15.0,
                    )
                    if save_err:
                        logger.warning("Failed to save flow metrics report: %s", save_err)
                        report_text += f"\n\n*Could not save report to disk: {save_err}*"
                    else:
                        logger.info("Saved flow metrics report to %s", flow_path)
                        report_text += f"\n\n**Report saved to:** `{flow_path}`"
                except asyncio.TimeoutError:
                    report_text += "\n\n*Save to disk timed out (report is still shown above).*"

            return [TextContent(type="text", text=report_text)]
        except asyncio.TimeoutError:
            logger.warning("Flow metrics timed out")
            return [TextContent(
                type="text",
                text=(
                    "Flow metrics request timed out. For long periods or large boards, run from the CLI: "
                    "`team-reports jira flow-metrics --quarter N --year Y` or `--days N`."
                ),
            )]
        except ImportError as e:
            logger.error("team-reports not available for flow metrics: %s", e)
            return [TextContent(
                type="text",
                text="Flow metrics require the team-reports package. Install it (e.g. pip install team-reports) or run from CLI: team-reports jira flow-metrics.",
            )]
        except Exception as e:
            logger.error("Error in get_flow_metrics: %s", e)
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _test_connections(
        self,
        connections: Optional[List[str]] = None,
    ) -> List[TextContent]:
        """Test connectivity for Jira, GitHub, and/or GitLab. Returns a summary per instance."""
        config = load_config_with_overrides(None)
        to_test = connections or []
        if not to_test:
            to_test = ["jira", "github", "gitlab"]
        results: List[str] = ["## Connection test results\n"]
        for conn in to_test:
            if conn == "jira":
                results.append(await self._test_jira_connection())
            elif conn == "github":
                results.append(_test_github_sync(config.get("github") or {}))
            elif conn == "gitlab":
                results.append(_test_gitlab_sync(config.get("gitlab") or {}))
            else:
                results.append(f"**{conn}:** Unknown connection type (use jira, github, gitlab).\n")
        return [TextContent(type="text", text="\n".join(results))]

    async def _test_jira_connection(self) -> str:
        """Test Jira: init client and run one search. Returns a status line."""
        try:
            if not self.jira_client:
                await self._init_jira_client()
            if not self.jira_client:
                return "**Jira:** Not initialized (check JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN).\n"
            self.jira_client.search_issues("order by updated DESC", maxResults=1)
            url = getattr(self.jira_client, "server_url", "") or os.getenv("JIRA_SERVER", "?")
            return f"**Jira:** OK — connected to {url}\n"
        except Exception as e:
            return f"**Jira:** Failed — {str(e)}\n"

    async def _get_manager_coach_brief(
        self,
        include_data_context: bool = True,
    ) -> List[TextContent]:
        """Return Operator Coach brief for team health and execution cadence."""
        custom = load_manager_coach_brief()
        if custom:
            if include_data_context:
                custom += "\n---\n*Tip: Run **get_lingering_items** and **get_bottlenecks_and_priorities** first, then use this brief to decide what to act on.*\n"
            return [TextContent(type="text", text=custom)]
        brief = """## Manager Coach Brief (Operator perspective)

**What to watch for team health and execution**
- **Review latency** — Items stuck in Review > 5 days: unblock or re-prioritize.
- **WIP depth** — Too many In Progress per person: narrow focus or adjust commitments.
- **Unassigned / refinement backlog** — Tickets sitting without owner or in Refinement > 3 days: assign or clarify.
- **Priority alignment** — Critical/Blocker in progress should have a clear path to done; escalate if blocked.

**Weekly cadence (10 min, Friday)**
1. **Top 3 outcomes** you're driving (not tasks).
2. **1 decision needed from above** — write the recommendation. *(Leaders love this.)*
3. **1 risk** you're surfacing early.
4. **1 experiment or learning** you're capturing for visibility (e.g. AI usage, process change).

**Tactical prompts when things feel stuck**
- *Room is vague:* "What decision are we making today, and who's the decider?"
- *Work ballooning:* "What are we not doing so we can do this well?"
- *No measurable value:* "How will we know this worked, in a way the business cares about?"
- *One dominant voice:* "I want two other perspectives before we converge. Who sees it differently?"

**Rules of engagement**
- Default to action, but demand definition: *Define done and owner before starting.*
- Escalate early, not often: when decision stuck, risk rising, dependency blocking, or scope unclear.
"""
        if include_data_context:
            brief += "\n---\n*Tip: Run **get_lingering_items** and **get_bottlenecks_and_priorities** first, then use this brief to decide what to act on.*\n"
        return [TextContent(type="text", text=brief)]

    async def _generate_weekly_status(
        self,
        github_token: Optional[str] = None,
        gitlab_token: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        regenerate: bool = False,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
        """
        Generate weekly team status report combining Jira, GitHub, and optionally GitLab data.
        
        Args:
            github_token: Optional GitHub API token (reads from GITHUB_TOKEN env var if not provided)
            gitlab_token: Optional GitLab API token (reads from GITLAB_TOKEN env var if not provided)
            start_date: Optional start date (YYYY-MM-DD), defaults to current date
            end_date: Optional end date (YYYY-MM-DD), defaults to 7 days before start
            regenerate: Force regeneration even if report exists
            config_overrides: Override configuration values
        
        Returns:
            List of TextContent with report content and metadata
        """
        try:
            # Calculate date range
            try:
                calc_start_date, calc_end_date = get_week_range(start_date, end_date)
                logger.info(f"Generating report for {calc_end_date} to {calc_start_date}")
            except ValueError as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
            
            # Check for existing report
            if not regenerate:
                existing_report = check_report_exists(calc_start_date, calc_end_date)
                if existing_report:
                    report_path = get_report_path(calc_start_date, calc_end_date)
                    return [TextContent(
                        type="text",
                        text=f"**Found existing report (use regenerate=true to recreate):**\n\n"
                             f"**File:** {report_path}\n\n"
                             f"---\n\n{existing_report}"
                    )]
            
            # Load configuration
            config = load_config_with_overrides(config_overrides)
            
            # Validate required credentials
            jira_server = os.getenv("JIRA_SERVER")
            jira_email = os.getenv("JIRA_EMAIL")
            jira_api_token = os.getenv("JIRA_API_TOKEN")
            
            # Get GitHub token from parameter or environment variable
            if not github_token:
                github_token = os.getenv("GITHUB_TOKEN")
            # Get GitLab token (optional; only needed when gitlab_config.yaml and projects are configured)
            if not gitlab_token:
                gitlab_token = os.getenv("GITLAB_TOKEN")
            
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
            
            # Import team-reports library
            try:
                from team_reports import WeeklyJiraSummary, WeeklyGitHubSummary, WeeklyGitLabSummary
            except ImportError as e:
                return [TextContent(
                    type="text",
                    text=f"Error: Failed to import team-reports library. Please ensure it's installed: {str(e)}"
                )]
            
            # Prepare config files (temp or default)
            # Use absolute paths to ensure they're found regardless of working directory
            server_dir = Path(__file__).parent.absolute()
            jira_config_file = str(server_dir / 'config' / 'jira_config.yaml')
            github_config_file = str(server_dir / 'config' / 'github_config.yaml')
            gitlab_config_file = str(server_dir / 'config' / 'gitlab_config.yaml')
            temp_files_to_cleanup = []
            gitlab_report = ""
            
            try:
                # Create temp config files if overrides provided
                if config_overrides:
                    # Merge Jira config with overrides
                    jira_config = merge_config_with_defaults(
                        config_overrides,
                        jira_config_file,
                        'jira'
                    )
                    if jira_config:
                        jira_config_file = create_temp_config_file(jira_config, prefix='jira_mcp_')
                        temp_files_to_cleanup.append(jira_config_file)
                    
                    # Merge GitHub config with overrides
                    github_config = merge_config_with_defaults(
                        config_overrides,
                        github_config_file,
                        'github'
                    )
                    if github_config:
                        github_config_file = create_temp_config_file(github_config, prefix='github_mcp_')
                        temp_files_to_cleanup.append(github_config_file)
                    
                    # Merge GitLab config with overrides
                    gitlab_config = merge_config_with_defaults(
                        config_overrides,
                        gitlab_config_file,
                        'gitlab'
                    )
                    if gitlab_config:
                        gitlab_config_file = create_temp_config_file(gitlab_config, prefix='gitlab_mcp_')
                        temp_files_to_cleanup.append(gitlab_config_file)
                
                # Generate Jira weekly report
                logger.info(f"Generating Jira weekly report using config: {jira_config_file}")
                try:
                    jira_summary = WeeklyJiraSummary(
                        config_file=jira_config_file,
                        jira_server=jira_server,
                        jira_email=jira_email,
                        jira_token=jira_api_token
                    )
                    jira_report, _ = jira_summary.generate_weekly_summary(
                        start_date=calc_start_date,
                        end_date=calc_end_date
                    )
                    logger.info(f"Generated Jira report: {len(jira_report)} characters")
                except Exception as e:
                    logger.error(f"Failed to generate Jira report: {e}")
                    jira_report = f"**Error generating Jira report:** {str(e)}\n\n"
                
                # Generate GitHub weekly report
                logger.info(f"Generating GitHub weekly report using config: {github_config_file}")
                try:
                    github_summary = WeeklyGitHubSummary(
                        config_file=github_config_file,
                        github_token=github_token
                    )
                    github_report, _ = github_summary.generate_report(
                        start_date=calc_start_date,
                        end_date=calc_end_date,
                        config_file=github_config_file
                    )
                    logger.info(f"Generated GitHub report: {len(github_report)} characters")
                except Exception as e:
                    logger.error(f"Failed to generate GitHub report: {e}")
                    github_report = f"**Error generating GitHub report:** {str(e)}\n\n"
                
                # Generate GitLab weekly report when config and token are present
                if config.get("gitlab") and (gitlab_token or os.getenv("GITLAB_TOKEN")):
                    token = gitlab_token or os.getenv("GITLAB_TOKEN")
                    if os.path.exists(gitlab_config_file):
                        logger.info(f"Generating GitLab weekly report using config: {gitlab_config_file}")
                        try:
                            gitlab_summary = WeeklyGitLabSummary(
                                config_file=gitlab_config_file,
                                gitlab_token=token
                            )
                            gitlab_report, _ = gitlab_summary.generate_report(
                                start_date=calc_start_date,
                                end_date=calc_end_date,
                                config_file=gitlab_config_file
                            )
                            logger.info(f"Generated GitLab report: {len(gitlab_report)} characters")
                        except Exception as e:
                            logger.error(f"Failed to generate GitLab report: {e}")
                            gitlab_report = f"**Error generating GitLab report:** {str(e)}\n\n"
                    else:
                        logger.info("GitLab config file not found; skipping GitLab section")
                else:
                    if config.get("gitlab") and not (gitlab_token or os.getenv("GITLAB_TOKEN")):
                        logger.info("GitLab config present but no GITLAB_TOKEN; skipping GitLab section")
            
            finally:
                # Clean up temporary config files
                for temp_file in temp_files_to_cleanup:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                            logger.info(f"Cleaned up temp config file: {temp_file}")
                    except Exception as e:
                        logger.warning(f"Could not delete temp file {temp_file}: {e}")
            
            # Combine reports
            report_sections = [jira_report, github_report]
            if gitlab_report:
                report_sections.append(gitlab_report)
            combined_report = "# Weekly Team Status Report\n## Period: {} to {}\n\n---\n\n{}\n\n---\n\n*Report generated: {}*\n".format(
                calc_start_date,
                calc_end_date,
                "\n\n---\n\n".join(report_sections),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            
            # Save report to disk
            try:
                report_path = save_report(combined_report, calc_start_date, calc_end_date)
                logger.info(f"Report saved to: {report_path}")
            except Exception as e:
                logger.error(f"Failed to save report: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error: Failed to save report: {str(e)}\n\nReport content:\n\n{combined_report}"
                )]
            
            # Return success with report content
            success_msg = f"**Weekly status report generated successfully!**\n\n"
            success_msg += f"**Period:** {calc_start_date} to {calc_end_date}\n"
            success_msg += f"**File:** {report_path}\n"
            success_msg += f"**Size:** {len(combined_report)} characters\n\n"
            success_msg += load_executive_summary_prompt()
            success_msg += f"\n---\n\n{combined_report}"
            
            return [TextContent(type="text", text=success_msg)]
            
        except Exception as e:
            logger.error(f"Error generating weekly status: {e}")
            return [TextContent(type="text", text=f"Error generating weekly status: {str(e)}")]

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="jira-mcp-server",
                    server_version="1.0.0",
                    capabilities=ServerCapabilities(
                        tools={}
                    ),
                ),
            )


async def main():
    """Main entry point"""
    server = JiraMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main()) 