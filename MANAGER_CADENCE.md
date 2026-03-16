# Manager cadence (team-reports MCP)

Use **calendar reminders** to trigger each cadence.

**One-time config check:** In `config/jira_config.yaml`, confirm `flow_metrics.story_points_field` is your Jira Story Points field ID (e.g. customfield_10016). If it’s wrong, “Cycle by size” and “Possibly mis-sized” in flow metrics will be empty. Saved reports go to `Reports/` next to this repo. When the reminder fires, open Cursor (with this project / team-reports MCP enabled) and run the prompt for that day.

| When | Tools | Prompt to use in Cursor |
|------|--------|-------------------------|
| **Every Monday** | 1–4: attention items, lingering, bottlenecks, coach brief | *"Run my Monday manager check."* |
| **First work day of month** | 5: flow metrics | *"Run my monthly flow metrics."* |
| **Every Tuesday** | 6: weekly status | *"Run my Tuesday weekly status."* |

---

## Rolling history and report changes

### Capturing data in rolling history

Flow metrics **trend comparison** (vs last period, rolling 3-period) and **traffic-light** lines use a history file. To capture data:

1. **Config:** `flow_metrics.history_file` is set in `config/jira_config.yaml` (e.g. `Reports/flow_metrics_history.json`). The path is resolved relative to the **config directory**, so the file is always written under this repo (e.g. `Reports/flow_metrics_history.json` next to `config/`).

2. **Run flow metrics regularly:** Each time you run **get_flow_metrics** (e.g. "Run my monthly flow metrics"), the run **appends one record** to the history file (period dates, throughput, cycle/lead medians, etc.). No separate step is needed.

3. **Cadence:** Use a consistent period (e.g. run monthly for `period="last_month"`). After the first run you have one record; after the second, you get "vs last period"; after a few runs, "Rolling trend (3-period)" and traffic-light lines populate.

4. **Where the file lives:** When you run via Cursor/MCP, the history file is written to **`Reports/flow_metrics_history.json`** in this repo. The directory is created automatically.

### Supporting changes to flow metrics reports

- **Config-driven:** Everything under `flow_metrics` in `config/jira_config.yaml` (e.g. `story_points_field`, `targets`, `possibly_missized`, `exclude_issue_types`, `size_display_order`) is read **on every run**. Change the config and the next flow metrics run uses the new values.

- **Report content:** Sections like "Cycle by size (story points)", "Possibly mis-sized", "Rolling trend", and "vs last period" come from the **team-reports** library. Code or dependency updates there change or add report sections; your config only controls which options are on.

---

## Copy-paste prompts (if the short phrase doesn’t trigger the rule)

### Monday — manager check (tools 1–4)

```
Run my Monday manager check: run get_lingering_items, get_bottlenecks_and_priorities, get_manager_attention_items, then get_manager_coach_brief. Use team Jira config; use defaults for parameters unless I say otherwise.
```

### First work day of month — flow metrics (tool 5)

```
Run my monthly flow metrics: get_flow_metrics for last_month, and save the report to Reports/ (save_report: true).
```

### Tuesday — weekly status (tool 6)

```
Run my Tuesday weekly status: generate_weekly_status for the week that just ended (default dates). After it’s done, give me the prompt for the executive summary.
```

---

## Why calendar reminders (and not automation)

Cursor doesn’t run prompts on a schedule. The MCP tools need an active Cursor chat and your Jira/GitHub (and optional GitLab) config. So:

1. **Set three recurring reminders** in your calendar:
   - **Every Monday** (e.g. 9:00): “Monday manager check in Cursor”
   - **First work day of each month** (e.g. 9:00): “Monthly flow metrics in Cursor”
   - **Every Tuesday** (e.g. 9:00): “Tuesday weekly status in Cursor”
2. When the reminder fires, open Cursor and say the short prompt (or paste the longer one from this doc).
3. If you added the Cursor rule (see below), the short phrase is enough and the AI will run the right tools in order.

The rule lives in `.cursor/rules/manager-cadence.mdc` in this repo so that when you’re in this project, phrases like “Monday manager check”, “monthly flow metrics”, and “Tuesday weekly status” trigger the correct tool runs.

---

## Release tracking and fixVersion

### Why the Kanban "Release" modal shows so many issues

The Release modal (e.g. "1090 issues will be released") uses a query that is **not** filtered by fixVersion. It's driven by the board's saved filter and the "released" status (e.g. status = Done). So it lists every issue in that status for the project, regardless of which version you intend to release.

- **To narrow what gets released:** The scope of "Release" is determined by **which issues have the fixVersion you're releasing**. So:
  1. **Option A — Board filter:** Change the board filter to include `fixVersion = "pre-2026-release-baseline"` (or the version you're releasing). Then the board and the Release action only see those issues.
  2. **Option B — Assign first, then release:** Ensure only the issues you want have that fixVersion set. When you create/release that version in Jira, only issues with that fixVersion are associated with the release. The modal count may still show all Done issues; confirm in Jira that the version you release only contains the intended issues.

### Cleaning up the backlog

1. **Audit by fixVersion:** Use **search_issues** with JQL to see what's in a version, e.g.  
   `project = DISCOVERY AND fixVersion = "pre-2026-release-baseline" AND status = "Closed"`  
   (Use your project key and status name; status `"6"` in the modal is often "Closed" or "Done".)
2. **Assign issues to a release:** Use **update_issue** with `fix_version` to set Fix Version/s on individual issues (e.g. `fix_version: "2.4.4"`). The version must already exist in the Jira project.
3. **Align with GitHub releases:** Use the same version names as your GitHub releases (e.g. `2.4.4` for quipucords, `2.4.5` for quipucords-ui, `2.4.3` for qpc) so Jira versions map 1:1 to repo releases. Create those versions in Jira (Project settings → Versions) if they don't exist, then assign tickets via MCP.

### Automating with the MCP client

| Goal | Tool / approach |
|------|------------------|
| List issues in a version | **search_issues** with JQL: `project = DISCOVERY AND fixVersion = "2.4.4"` |
| Assign a ticket to a release | **update_issue** with `issue_key` and `fix_version: "2.4.4"` |
| Bulk assign | Run **search_issues** for the desired JQL, then **update_issue** (with `fix_version`) for each issue key (or script/loop in your automation). |
| See what's in "pre-2026-release-baseline" | **search_issues** with `project = DISCOVERY AND fixVersion = "pre-2026-release-baseline"` (add `AND status = "Closed"` to limit to done items). |

After assigning fixVersion via MCP, use the Jira UI to perform "Release" for that version (name, date, description). The MCP does not create or release Jira versions; it only updates issue fields.
