# AgentPost Project Status

Last updated: 2026-09-03

Current handoff stage: `v0.1.45-backlog-cleanup-and-multi-agent-local-candidate`

## Current local candidate

- Version: `0.1.45`
- Schema: `0035_cancel_legacy_task_backlog`
- Collaboration model: Task is the only multi-Human collaboration scope.
- Human navigation: 任务、好友、AI、设置。
- Task identity: one stable `task_id`, one main `thread_id`, with a Human-facing copy action.
- Membership authority: `TaskMembership` only.
- Agent participation: a Human can select one or more owned active Agents and designate one primary Agent; the Human default Agent remains the fallback when none was explicitly selected.
- Legacy backlog: pre-0.1.44 automatic participant-start, task-message, and result-sync work that never reached a terminal state is cancelled with an explicit reason, retained for audit, and excluded from current progress/state totals.
- Human progress: every AI progress card shows its update time and uses a stable per-Human color tone; long structured output remains in Task records/attachment cards instead of expanding the progress column.
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
- Orbit and TypeScript JavaScript: 45 passed.
- TypeScript compile: passed.
- Non-PostgreSQL Pytest: 454 passed, one expected loopback sandbox skip, five PostgreSQL tests deselected.
- Alembic graph: one head at `0035_cancel_legacy_task_backlog`.
- Fresh SQLite Alembic chain: blocked at the pre-existing 0019 constraint-alter limitation before reaching 0035.
- PostgreSQL 0030 → 0034 → 0030 → 0034 rehearsal and production upgrade: passed in the protected release switch.
- Authenticated desktop and 390px Task list/detail: passed with zero horizontal overflow and no console errors; Run routing/wake labels and copyable Task ID were visible. A real task attachment card has API/DOM coverage but authenticated visual acceptance remains `待确认` because the isolated seed has no physical attachment.
- Authenticated desktop 0.1.45 candidate: passed for two-Agent selection, primary-Agent switching, save/reload, add-Agent navigation, Human colors, timestamps, and zero horizontal overflow. The changed 390px layout and PostgreSQL 0035 data migration remain `待确认` before release.

## Production

- Current production commit: `6609837`
- Current production version/schema: `0.1.44 / 0034_task_run_routing`
- State: `deployed_https_verified`, not `production_accepted`.
- Protected switch reported `deploy_status=ok`; corrected full postflight reported `postflight_status=ok`.
- Public health/ready report 0.1.44, protocol contract reports 0.3, the public wheel SHA-256 matches the release manifest, and an unknown wheel URL returns 404.
- The authenticated production Task page loaded the four primary entries and existing Task data successfully.
- The original postflight package expected the obsolete protocol contract 0.1. The assertion is corrected to 0.3 with a regression test; rerunning the otherwise unchanged postflight pipeline passed all gates.

## Next release gates

1. Complete authenticated visual acceptance of a real Task attachment card and Connector runtime details.
2. Rehearse the 0035 cleanup migration against a protected PostgreSQL copy and verify cancelled-row counts before release.
3. Complete 390px acceptance for the multi-Agent selector and progress colors.
4. Complete real-user cross-device acceptance before changing the state to `production_accepted`.
5. Keep the two unrelated untracked management-report files untouched.
