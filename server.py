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
import sys
import tempfile
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

# Default AI summary prompt
DEFAULT_SUMMARY_PROMPT = """Based on the following weekly team report, generate an executive summary highlighting:

1. Key Accomplishments: Major milestones and completed work
2. Team Velocity: Overall productivity and throughput metrics
3. Blockers & Risks: Issues requiring attention or escalation
4. Notable Trends: Patterns in team performance or workload

Keep the summary concise (3-5 paragraphs) and action-oriented.

---

{report_content}

---

Please provide the executive summary:"""

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
    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        # Validate it's a Wednesday (weekday() returns 2 for Wednesday)
        if start.weekday() != 2:
            raise ValueError(f"start_date must be a Wednesday. {start_date} is a {start.strftime('%A')}")
    else:
        # Default to current date
        start = datetime.now()
    
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
        # Validate it's a Tuesday (weekday() returns 1 for Tuesday)
        if end.weekday() != 1:
            raise ValueError(f"end_date must be a Tuesday. {end_date} is a {end.strftime('%A')}")
    else:
        # Go back 7 days from start date
        end = start - timedelta(days=7)
    
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
                    description="Generate weekly team status report combining Jira and GitHub data. Checks for existing reports to avoid duplicate API calls. Optionally generates AI-powered executive summary.",
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
                            "regenerate": {
                                "type": "boolean",
                                "description": "Force regeneration even if report exists. Default: false",
                                "default": False
                            },
                            "generate_summary": {
                                "type": "boolean",
                                "description": "Generate AI-powered executive summary. Default: true",
                                "default": True
                            },
                            "summary_prompt": {
                                "type": "string",
                                "description": "Custom prompt for AI summary generation. If not provided, uses default prompt."
                            },
                            "config_overrides": {
                                "type": "object",
                                "description": "Override configuration file settings (e.g., team filters, repositories, etc.)"
                            }
                        },
                        "required": []
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls"""
            
            # Initialize Jira client if not already done
            if not self.jira_client:
                await self._init_jira_client()
            
            try:
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
                        arguments.get("github_token"),  # Now optional
                        arguments.get("start_date"),
                        arguments.get("end_date"),
                        arguments.get("regenerate", False),
                        arguments.get("generate_summary", True),
                        arguments.get("summary_prompt"),
                        arguments.get("config_overrides")
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
            self.jira_client = JIRA(
                server=server,
                token_auth=api_token
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

    async def _generate_weekly_status(
        self,
        github_token: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        regenerate: bool = False,
        generate_summary: bool = True,
        summary_prompt: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
        """
        Generate weekly team status report combining Jira and GitHub data.
        
        Args:
            github_token: Optional GitHub API token (reads from GITHUB_TOKEN env var if not provided)
            start_date: Optional start date (YYYY-MM-DD), defaults to current date
            end_date: Optional end date (YYYY-MM-DD), defaults to 7 days before start
            regenerate: Force regeneration even if report exists
            generate_summary: Whether to generate AI summary
            summary_prompt: Custom prompt for AI summary
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
                from team_reports import WeeklyJiraSummary, WeeklyGitHubSummary
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
            temp_files_to_cleanup = []
            
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
            combined_report = f"""# Weekly Team Status Report
## Period: {calc_start_date} to {calc_end_date}

---

{jira_report}

---

{github_report}

---

*Report generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
            
            # Generate AI summary if requested
            summary_text = ""
            if generate_summary:
                logger.info("Generating AI summary...")
                try:
                    # Use custom prompt or default
                    prompt = summary_prompt if summary_prompt else DEFAULT_SUMMARY_PROMPT
                    prompt_with_report = prompt.format(report_content=combined_report)
                    
                    # Note: The AI summary will be generated by the MCP client
                    # We append a placeholder that the client can process
                    summary_text = f"""

---

## Executive Summary

> **Note:** To generate an AI-powered executive summary, process the above report with the following prompt:

{prompt}

"""
                    combined_report += summary_text
                    logger.info("AI summary prompt added to report")
                except Exception as e:
                    logger.warning(f"Failed to add AI summary prompt: {e}")
            
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
            return [TextContent(
                type="text",
                text=f"**Weekly status report generated successfully!**\n\n"
                     f"**Period:** {calc_start_date} to {calc_end_date}\n"
                     f"**File:** {report_path}\n"
                     f"**Size:** {len(combined_report)} characters\n\n"
                     f"---\n\n{combined_report}"
            )]
            
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
                    capabilities=ServerCapabilities(tools={}),
                ),
            )


async def main():
    """Main entry point"""
    server = JiraMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main()) 