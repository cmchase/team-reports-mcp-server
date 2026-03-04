# Manager cadence (team-reports MCP)

Use **calendar reminders** to trigger each cadence. When the reminder fires, open Cursor (with this project / team-reports MCP enabled) and run the prompt for that day.

| When | Tools | Prompt to use in Cursor |
|------|--------|-------------------------|
| **Every Monday** | 1–4: attention items, lingering, bottlenecks, coach brief | *"Run my Monday manager check."* |
| **First work day of month** | 5: flow metrics | *"Run my monthly flow metrics."* |
| **Every Tuesday** | 6: weekly status | *"Run my Tuesday weekly status."* |

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
