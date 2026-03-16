#!/usr/bin/env python3
"""
One-off: fetch 5 stories from Jira and print customfield_10016 (Story Points) for each.
Run from repo root with .env set: JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN.
"""
import os
import sys
from pathlib import Path

# Add parent so we can load config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def main():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    from jira import JIRA
    import yaml

    server = os.getenv("JIRA_SERVER")
    token = os.getenv("JIRA_API_TOKEN")
    if not server or not token:
        print("Set JIRA_SERVER and JIRA_API_TOKEN in .env")
        sys.exit(1)

    config_path = Path(__file__).resolve().parent.parent / "config" / "jira_config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    base_jql = " ".join((config.get("base_jql") or "project is not empty").strip().split())

    # Tickets in To Do (refined backlog) — more likely to have story points set
    jql = f'({base_jql}) AND status = "To Do" ORDER BY updated DESC'
    client = JIRA(server=server, token_auth=token, timeout=30)
    issues = client.search_issues(jql, maxResults=5)

    field_id = (config.get("flow_metrics") or {}).get("story_points_field") or "customfield_12310243"
    print(f"{field_id} check — 5 issues in To Do ({len(issues)} found)\n")
    for issue in issues:
        val = getattr(issue.fields, field_id, None)
        print(f"  {issue.key}  {field_id} = {val!r}  — {getattr(issue.fields, 'summary', '')[:50]}")
    if not issues:
        print("  No stories found.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
