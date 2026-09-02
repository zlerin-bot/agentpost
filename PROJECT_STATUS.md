# AgentPost Project Status

Last updated: 2026-09-02

Current handoff stage: `v0.1.43-task-state-and-runtime-truth-local-verified`

## Current local candidate

- Version: `0.1.43`
- Schema: `0033_connector_runtime_truth`
- Collaboration model: Task is the only multi-Human collaboration scope.
- Human navigation: 任务、好友、AI、设置。
- Task identity: one stable `task_id`, one main `thread_id`, with a Human-facing copy action.
- Membership authority: `TaskMembership` only.
- Agent participation: Human-selected Agents, or the Human default Agent when none is selected.
- Execution reliability: durable Agent Run claim, lease, heartbeat, idempotent completion, and Human acceptance as a separate state.
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
- Orbit and TypeScript JavaScript: 39 passed.
- Non-PostgreSQL Pytest: 451 passed, one expected loopback sandbox skip, five PostgreSQL tests deselected.
- Fresh SQLite Alembic chain: blocked at the pre-existing 0019 constraint-alter limitation before reaching 0033.
- PostgreSQL migration acceptance: `待确认`.
- Public desktop and 390px browser shell: passed with zero horizontal overflow and no console errors. Authenticated visual acceptance of the new Task state strip and Connector details is `待确认`; API and DOM contract tests passed.

## Production

- Current production commit: `422c5cc3f10231e324797695e5f45b1e2161a22a`
- Current production version/schema: `0.1.40 / 0030_task_messages`
- State: `deployed_https_verified`, not `production_accepted`.
- This 0.1.43 candidate has not been uploaded or deployed.

## Next release gates

1. Complete PostgreSQL upgrade/rollback acceptance through 0033 and verify Task, Friendship, Connector, message, and attachment counts.
2. Complete authenticated desktop and 390px visual acceptance for the new Task state strip and Connector runtime details.
3. Commit only the P0 slice and leave the two unrelated untracked management-report files untouched.
4. Deploy only after explicit authorization, using the protected Alibaba Cloud release scripts and postflight gates.
