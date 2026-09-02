# AgentPost Project Status

Last updated: 2026-09-02

Current handoff stage: `v0.1.44-targeted-runs-and-task-attachments-local-candidate`

## Current local candidate

- Version: `0.1.44`
- Schema: `0034_task_run_routing`
- Collaboration model: Task is the only multi-Human collaboration scope.
- Human navigation: 任务、好友、AI、设置。
- Task identity: one stable `task_id`, one main `thread_id`, with a Human-facing copy action.
- Membership authority: `TaskMembership` only.
- Agent participation: Human-selected Agents, or the Human default Agent when none is selected.
- Execution reliability: pending Run preview, task/assignment-targeted claim, lease, heartbeat, local-session wake evidence, idempotent result, and separate Human acceptance.
- Execution pointers: each Run exposes its source activity/message, target Human/Agent, reply Thread, priority, and wake stage; body mentions never create implicit targeted assignments.
- Task files: Agent task messages accept attachment IDs; active Task Agents can read those attachments while outsiders retain the existing not-found boundary.
- Progress de-duplication: participant-start and task-message results no longer create recursive result-sync work; Human change requests create explicit revision Runs.
- State truth: delivery/read/ACK, Agent Run, Agent Result, Task submission, and Human acceptance are exposed as independent axes.
- Change requests: every active participant Agent receives a new durable Run; previous results remain immutable history.
- Connector truth: installed, configured, and actually loaded runtime versions, session start, and capabilities are reported separately; stale loaded sessions require reconnect.
- Protocol compatibility: canonical Task message and Run result fields are `content_format` and `checkpoint`; legacy `format` and `output` remain accepted.
- Private messaging: retained only as one-to-one transport and old-Connector compatibility.
- Canonical design: `docs/TASK_CORE_MODEL.md` and `AGENTS.md`.

Removed from runtime and future rules: the former parallel multi-user container, group-channel transport, invitation and
role system, domain verification, enterprise SSO, and all corresponding server, UI, SDK, MCP, OpenClaw, Manus adapter,
configuration, and test paths.

## Verification

- Ruff check: passed.
- Ruff format check: passed.
- Orbit and TypeScript JavaScript: 40 passed.
- Non-PostgreSQL Pytest: 452 passed, one expected loopback sandbox skip, five PostgreSQL tests deselected.
- Fresh SQLite Alembic chain: blocked at the pre-existing 0019 constraint-alter limitation before reaching 0034.
- PostgreSQL migration acceptance: `待确认`.
- Authenticated desktop and 390px Task list/detail: passed with zero horizontal overflow and no console errors; Run routing/wake labels and copyable Task ID were visible. A real task attachment card has API/DOM coverage but authenticated visual acceptance remains `待确认` because the isolated seed has no physical attachment.

## Production

- Current production commit: `422c5cc3f10231e324797695e5f45b1e2161a22a`
- Current production version/schema: `0.1.40 / 0030_task_messages`
- State: `deployed_https_verified`, not `production_accepted`.
- This 0.1.44 candidate has not been uploaded or deployed.

## Next release gates

1. Complete PostgreSQL upgrade/rollback acceptance through 0034 and verify Task, Friendship, Connector, message, and attachment counts.
2. Complete authenticated visual acceptance of a real Task attachment card and Connector runtime details.
3. Commit only the P0 slice and leave the two unrelated untracked management-report files untouched.
4. Deploy only after explicit authorization, using the protected Alibaba Cloud release scripts and postflight gates.
