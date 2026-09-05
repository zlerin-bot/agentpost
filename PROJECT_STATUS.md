# AgentPost Project Status

Last updated: 2026-09-05

Current handoff stage: `v0.1.52-task-progress-local-verified`

## Current local candidate

- Version: `0.1.52`
- Schema: `0037_task_activity_relations`
- Collaboration model: Task is the only multi-Human collaboration scope.
- Human navigation: 任务、好友、AI、设置。
- Task identity: one stable `task_id`, one main `thread_id`, with a Human-facing copy action.
- Membership authority: `TaskMembership` only.
- Agent participation: a Human can select one or more owned active Agents and designate one primary Agent; the Human default Agent remains the fallback when none was explicitly selected.
- Legacy backlog: pre-0.1.44 automatic participant-start, task-message, and result-sync work that never reached a terminal state is cancelled with an explicit reason, retained for audit, and excluded from current progress/state totals.
- Human progress: every AI progress card shows its update time and uses a stable per-Human color tone; long structured output remains in Task records/attachment cards instead of expanding the progress column.
- Publication provenance: Human-direct, Human-delegated Agent, Agent-autonomous, and platform actions remain distinct; directed work renders initiator → responsible Human → execution Agent.
- Shared context: a Task message is recorded once and does not create mandatory acknowledgement Runs; explicit assignments and revisions remain the reliable execution boundary.
- Automatic acknowledgement cleanup: nonterminal `task_message` and `result_sync` work from the former rule is cancelled without deleting history or reviving on rollback.
- Execution reliability: pending Run preview, task/assignment-targeted claim, lease, heartbeat, local-session wake evidence, idempotent result, and separate Human acceptance.
- Waiting-Human loop: the Human UI exposes the Agent checkpoint; the task owner or responsible Human can answer, invalidate the old lease, and requeue the same Assignment with the response in the successor checkpoint.
- Progress navigation: status-change time and current-attempt heartbeat are distinct; long progress links to the matching Task record, execution lifecycle rows are grouped, and obsolete automatic activity is collapsed as history.
- Execution pointers: each Run exposes its source activity/message, target Human/Agent, reply Thread, priority, and wake stage; body mentions never create implicit targeted assignments.
- Task files: Agent task messages accept attachment IDs; active Task Agents can read those attachments while outsiders retain the existing not-found boundary.
- Progress de-duplication: participant-start and task-message results no longer create recursive result-sync work; Human change requests create explicit revision Runs.
- State truth: delivery/read/ACK, Agent Run, Agent Result, Task submission, and Human acceptance are exposed as independent axes.
- Change requests: every active participant Agent receives a new durable Run; previous results remain immutable history.
- Connector truth: installed, configured, and actually loaded runtime versions, session start, and capabilities are reported separately; stale loaded sessions require reconnect.
- Protocol compatibility: canonical Task message and Run result fields are `content_format` and `checkpoint`; legacy `format` and `output` remain accepted.
- Client-created taskless Agent messaging: rejected with `task_context_required`; old-Connector compatibility is limited to server-generated Task bridge delivery, read, ACK, and Task-linked reply.
- Canonical design: `docs/TASK_CORE_MODEL.md` and `AGENTS.md`.
- Discussion relations: explicit replies remain immutable activity metadata; legacy Connector replies are reconstructed from the verified Task bridge; uncertain historical relations require a Human-owner confirmation stored separately from the original activity.
- Human progress projection: explicit work/results and recent discussion updates are presented separately from collapsible Agent lease/wake/heartbeat state. Automatic `participant_start` work is de-duplicated and excluded from business-progress cards.
- Task records: discussion, work/results, system, and all-record filters replace one mixed stream. The Human UI can request older records up to 2,000 items, while referenced roots outside the current window are fetched automatically.

Removed from runtime and future rules: the former parallel multi-user container, group-channel transport, invitation and
role system, domain verification, enterprise SSO, and all corresponding server, UI, SDK, MCP, OpenClaw, Manus adapter,
configuration, and test paths.

## Verification

- Ruff check: passed.
- Ruff format check: passed.
- Browser JavaScript: 36 passed; TypeScript Connector: 8 passed; OpenClaw adapter: 4 passed.
- TypeScript compile: passed.
- Non-PostgreSQL Pytest: 463 passed, one expected loopback sandbox skip, five PostgreSQL tests deselected.
- Alembic graph: one head at `0037_task_activity_relations`.
- Fresh SQLite Alembic chain: blocked at the pre-existing 0019 constraint-alter limitation before reaching 0036.
- PostgreSQL 0030 → 0034 → 0030 → 0034 rehearsal and production upgrade: passed in the protected release switch.
- Authenticated isolated desktop and 390px Task list/detail: passed with zero horizontal overflow and no console errors; waiting-Human question, Human response, same-Assignment requeue, status/heartbeat labels, unified task Agent names, grouped execution history, Run routing/wake labels and copyable Task ID were visible. A real production task attachment card remains `待确认`.
- Authenticated desktop and 390px production 0.1.45: passed for multi-Agent selection, primary-Agent controls, add-Agent navigation, Human colors, timestamps, mobile list/detail navigation, zero horizontal overflow, and zero console errors.
- PostgreSQL 0034 → 0035 → 0034 → 0035 rehearsal and production upgrade: passed. The migration cancelled 43 obsolete Assignments and 49 associated historical Runs; zero targeted pre-0.1.44 nonterminal Assignments remain.
- PostgreSQL 0036 production cleanup cancelled 5 nonterminal automatic acknowledgement Assignments and 5 associated Runs; zero nonterminal `task_message` / `result_sync` Assignments remain.

## Production

- Current production commit: `2a6b464`
- Current production version/schema: `0.1.51 / 0036_cancel_auto_ack_runs`
- State: `deployed_https_verified`, not `production_accepted`.
- Protected switch reported `deploy_status=ok`; independent full postflight reported `postflight_status=ok`.
- Public health/ready and Connector release config report 0.1.51; the protocol contract requires task context for Agent sends while preserving legacy Task bridge compatibility. Production remains `deployed_https_verified`, not `production_accepted`.
- The authenticated production “测试任务” page exposes the waiting-Human question and response control. Its long-progress link expands the matching lifecycle group, updates the activity anchor, and reveals the complete Task record; the console had no warnings/errors.

## Next release gates

1. Rehearse PostgreSQL schema 0036 → 0037 → 0036 → 0037 before release.
2. Verify the deterministic legacy-reply reconstruction against the real “小孔成像” task without rewriting production activity.
3. Complete the real-Agent waiting-Human response → reclaim → result cross-device loop.
4. Complete authenticated visual acceptance of a real Task attachment card and Connector runtime details.
5. Complete real-user cross-device acceptance before changing the state to `production_accepted`.
6. Keep the two unrelated untracked management-report files untouched.
