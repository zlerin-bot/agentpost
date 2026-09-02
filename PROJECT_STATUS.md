# AgentPost Project Status

Last updated: 2026-09-02

Current handoff stage: `v0.1.42-task-only-collaboration-local-verified`

## Current local candidate

- Version: `0.1.42`
- Schema: `0032_task_only_collaboration`
- Collaboration model: Task is the only multi-Human collaboration scope.
- Human navigation: 任务、好友、AI、设置。
- Task identity: one stable `task_id`, one main `thread_id`, with a Human-facing copy action.
- Membership authority: `TaskMembership` only.
- Agent participation: Human-selected Agents, or the Human default Agent when none is selected.
- Execution reliability: durable Agent Run claim, lease, heartbeat, idempotent completion, and Human acceptance as a separate state.
- Private messaging: retained only as one-to-one transport and old-Connector compatibility.
- Canonical design: `docs/TASK_CORE_MODEL.md` and `AGENTS.md`.

Removed from runtime and future rules: the former parallel multi-user container, group-channel transport, invitation and
role system, domain verification, enterprise SSO, and all corresponding server, UI, SDK, MCP, OpenClaw, Manus adapter,
configuration, and test paths.

## Verification

- Ruff check: passed.
- Ruff format check: passed.
- Orbit JavaScript: 32 passed.
- Non-PostgreSQL Pytest: 450 passed, one expected loopback sandbox skip, five PostgreSQL tests deselected.
- Fresh SQLite Alembic chain: blocked at the pre-existing 0019 constraint-alter limitation before reaching 0032.
- PostgreSQL migration acceptance: `待确认`.
- Authenticated desktop and 390px browser acceptance: passed; four primary entries, Task list/detail layering,
  copyable Task ID, zero horizontal overflow, and no console warnings/errors were verified.

## Production

- Current production commit: `422c5cc3f10231e324797695e5f45b1e2161a22a`
- Current production version/schema: `0.1.40 / 0030_task_messages`
- State: `deployed_https_verified`, not `production_accepted`.
- This 0.1.42 candidate has not been uploaded or deployed.

## Next release gates

1. Complete PostgreSQL upgrade/rollback acceptance for 0032 and verify Task, Friendship, Connector, message, and attachment counts.
2. Commit only the task-core slice and leave the two unrelated untracked management-report files untouched.
3. Deploy only after explicit authorization, using the protected Alibaba Cloud release scripts and postflight gates.
