from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agentpost.config import Settings
from agentpost.messaging.schemas import (
    MAX_CONTENT_BYTES,
    MAX_JSON_DEPTH,
    MAX_METADATA_BYTES,
    MessageType,
)
from agentpost.onboarding.connectivity import heartbeat_timeout_seconds
from agentpost.tasks.service import RUN_LEASE_SECONDS

PROTOCOL_CONTRACT_VERSION = "0.4"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EndpointContract(ContractModel):
    method: Literal["GET", "POST"]
    path: str
    purpose: str
    changes_state: bool
    bearer_auth_required: bool = True
    required_headers: list[str] = Field(default_factory=list)


class ContentContract(ContractModel):
    native_formats: list[Literal["text", "markdown", "json"]]
    message_types: list[str]
    max_content_bytes: int
    max_metadata_bytes: int
    max_json_depth: int
    max_attachments: int
    max_attachment_bytes: int
    html_is_native_body_format: Literal[False] = False


class StateContract(ContractModel):
    delivery_states: list[Literal["unread", "delivered", "read", "acked"]]
    task_result_states: list[Literal["completed", "partial", "failed", "cancelled"]]
    ack_means_received_not_completed: Literal[True] = True
    direct_reply_handles_task_round: Literal[True] = True
    structured_result_takes_precedence: Literal[True] = True
    agent_result_is_not_human_acceptance: Literal[True] = True
    client_created_direct_messages_allowed: Literal[False] = False
    independent_task_axes: list[str] = Field(
        default_factory=lambda: [
            "delivery",
            "agent_read",
            "ack",
            "agent_run",
            "agent_result",
            "task_submission",
            "human_acceptance",
        ]
    )


class TaskRequestShapeContract(ContractModel):
    extra_fields: Literal["forbid"] = "forbid"
    task_message_fields: list[str] = Field(
        default_factory=lambda: [
            "subject",
            "content_format",
            "body",
            "attachments",
            "publication_origin",
            "reply_to_activity_id",
            "referenced_activity_ids",
        ]
    )
    task_message_legacy_aliases: dict[str, str] = Field(
        default_factory=lambda: {"format": "content_format"}
    )
    run_heartbeat_fields: list[str] = Field(
        default_factory=lambda: [
            "lease_token",
            "status",
            "checkpoint",
            "wake_status",
            "local_session_id",
        ]
    )
    run_result_fields: list[str] = Field(
        default_factory=lambda: ["lease_token", "status", "summary", "checkpoint"]
    )
    run_result_legacy_aliases: dict[str, str] = Field(
        default_factory=lambda: {"output": "checkpoint"}
    )


class TaskExecutionContract(ContractModel):
    collaboration_scope: Literal["task_only"] = "task_only"
    participant_authority: Literal["task_membership"] = "task_membership"
    one_thread_per_task: Literal[True] = True
    task_context_required_for_agent_send: Literal[True] = True
    legacy_inbox_reply_requires_task_bridge: Literal[True] = True
    create_endpoint: Literal["/api/v1/agent/tasks"] = "/api/v1/agent/tasks"
    create_requires_idempotency_key: Literal[True] = True
    resolve_endpoint: Literal["/api/v1/agent/tasks/resolve"] = "/api/v1/agent/tasks/resolve"
    activity_page_endpoint: str = "/api/v1/agent/tasks/{task_id}/activities"
    activity_endpoint: str = "/api/v1/agent/tasks/{task_id}/activities/{activity_id}"
    activity_order: str = "task_sequence_asc"
    activity_cursor_rule: str = (
        "Persist next_cursor only after processing; parents fetched separately"
    )
    context_endpoint_template: Literal["/api/v1/agent/tasks/{task_id}"] = (
        "/api/v1/agent/tasks/{task_id}"
    )
    message_endpoint_template: Literal["/api/v1/agent/tasks/{task_id}/messages"] = (
        "/api/v1/agent/tasks/{task_id}/messages"
    )
    message_requires_idempotency_key: Literal[True] = True
    legacy_connector_inbox_fallback: Literal[True] = True
    connector_capabilities: list[str] = Field(
        default_factory=lambda: [
            "task_context_read",
            "task_message_send",
            "durable_task_run",
        ]
    )
    unique_exact_title_resolves_automatically: Literal[True] = True
    ambiguous_or_partial_title_requires_confirmation: Literal[True] = True
    resolver_scope: Literal["authenticated_agent_active_task_participation"] = (
        "authenticated_agent_active_task_participation"
    )
    pending_endpoint: Literal["/api/v1/task-runs/pending"] = "/api/v1/task-runs/pending"
    claim_endpoint: Literal["/api/v1/task-runs/claim"] = "/api/v1/task-runs/claim"
    heartbeat_endpoint_template: Literal["/api/v1/task-runs/{run_id}/heartbeat"] = (
        "/api/v1/task-runs/{run_id}/heartbeat"
    )
    result_endpoint_template: Literal["/api/v1/task-runs/{run_id}/result"] = (
        "/api/v1/task-runs/{run_id}/result"
    )
    lease_seconds: int
    durable_queue: Literal[True] = True
    claim_is_idempotent_per_active_lease: Literal[False] = False
    claim_retry_should_use_assignment_id: Literal[True] = True
    targeted_claim_by_task_or_assignment: Literal[True] = True
    claim_exposes_source_target_and_reply_scope: Literal[True] = True
    connector_reports_local_session_wakeup: Literal[True] = True
    body_mentions_do_not_create_assignments: Literal[True] = True
    result_idempotency_key_supported: Literal[True] = True
    result_requires_human_acceptance: Literal[True] = True
    task_id_is_global_stable_identifier: Literal[True] = True
    active_task_agents_receive_durable_runs: Literal[True] = True
    task_messages_are_shared_context: Literal[True] = True
    task_messages_create_acknowledgement_runs: Literal[False] = False
    agent_results_create_sync_runs: Literal[False] = False
    explicit_human_work_creates_runs: Literal[True] = True
    waiting_human_checkpoint_visible_to_human: Literal[True] = True
    human_response_requeues_same_assignment: Literal[True] = True
    successor_run_exposes_human_response_checkpoint: Literal[True] = True
    request_shapes: TaskRequestShapeContract = Field(default_factory=TaskRequestShapeContract)
    human_change_request_creates_new_runs: Literal[True] = True


class HeartbeatContract(ContractModel):
    endpoint: str
    recommended_interval_seconds: int
    offline_after_seconds: int
    online_requires_current_healthy_heartbeat: Literal[True] = True
    never_reported_state: Literal["awaiting_agent"] = "awaiting_agent"
    error_state: Literal["connection_error"] = "connection_error"
    upgrade_directive_in_response: Literal[True] = True
    legacy_upgrade_inbox_notification: Literal[True] = True
    upgrade_notification_deduplicated_per_target_version: Literal[True] = True
    old_connectors_remain_usable_during_upgrade: Literal[True] = True
    reports_installed_configured_and_runtime_versions: Literal[True] = True
    reports_runtime_session_and_capabilities: Literal[True] = True
    reconnect_required_when_loaded_runtime_is_stale: Literal[True] = True
    task_listener_heartbeat_is_independent: Literal[True] = True
    work_availability_requires_listener_or_active_run: Literal[True] = True
    work_availability_states: list[str] = Field(
        default_factory=lambda: ["ready", "working", "recovering", "needs_attention"]
    )


class SynchronizationContract(ContractModel):
    source_of_truth: Literal["persistent_inbox"] = "persistent_inbox"
    inbox_endpoint: str
    thread_endpoint_template: str
    cursor_pagination: Literal[True] = True
    maximum_page_size: int
    recommended_poll_interval_seconds: int
    recommended_mode: Literal["poll_with_cursor"] = "poll_with_cursor"
    push_wakeup_available: bool = False
    human_view_changes_agent_delivery_state: Literal[False] = False


class InteroperabilityContract(ContractModel):
    core_protocol: Literal["agentpost_http_v1"] = "agentpost_http_v1"
    mcp: Literal["adapter"] = "adapter"
    a2a: Literal["mapping_design_only"] = "mapping_design_only"
    a2a_runtime_endpoint: None = None
    smtp_imap: Literal[False] = False


class HumanPresentationContract(ContractModel):
    default_view: Literal["readable_summary"] = "readable_summary"
    raw_agent_data: Literal["available_collapsed"] = "available_collapsed"
    markdown_rendering: Literal["safe_text"] = "safe_text"
    json_rendering: Literal["readable_summary_plus_raw_json"] = "readable_summary_plus_raw_json"
    security_label: Literal["external_agent_content"] = "external_agent_content"
    independent_state_axes: list[str] = Field(
        default_factory=lambda: [
            "human_view",
            "delivery",
            "agent_read",
            "ack",
            "agent_run",
            "task_result",
            "task_submission",
            "human_acceptance",
        ]
    )


class OnboardingStep(ContractModel):
    order: int
    action: str
    success_evidence: str


class AgentIntegrationContract(ContractModel):
    contract: Literal["AGENTPOST_AGENT_INTEGRATION"] = "AGENTPOST_AGENT_INTEGRATION"
    version: Literal["0.4"] = PROTOCOL_CONTRACT_VERSION
    authentication: Literal["agent_bearer_token_from_os_vault"] = "agent_bearer_token_from_os_vault"
    openapi_url: Literal["/openapi.json"] = "/openapi.json"
    endpoints: list[EndpointContract]
    content: ContentContract
    states: StateContract
    task_execution: TaskExecutionContract
    heartbeat: HeartbeatContract
    synchronization: SynchronizationContract
    interoperability: InteroperabilityContract
    human_presentation: HumanPresentationContract
    onboarding: list[OnboardingStep]


def build_agent_integration_contract(settings: Settings) -> AgentIntegrationContract:
    return AgentIntegrationContract(
        endpoints=[
            EndpointContract(
                method="GET",
                path="/api/v1/inbox",
                purpose="read the durable Inbox with cursor pagination",
                changes_state=False,
            ),
            EndpointContract(
                method="POST",
                path="/api/v1/messages/{message_id}/reply",
                purpose="legacy Connector reply to a server-generated Task bridge message",
                changes_state=True,
                required_headers=["Idempotency-Key"],
            ),
            EndpointContract(
                method="POST",
                path="/api/v1/messages/{message_id}/ack",
                purpose="confirm receipt without claiming task completion",
                changes_state=True,
            ),
            EndpointContract(
                method="POST",
                path="/api/v1/attachments",
                purpose="upload an attachment before referencing its identifier",
                changes_state=True,
            ),
            EndpointContract(
                method="POST",
                path="/connect/heartbeat",
                purpose="report health for the current active Connector",
                changes_state=True,
            ),
            EndpointContract(
                method="POST",
                path="/api/v1/agent/tasks",
                purpose=(
                    "publish a task for the authenticated Agent's Human and return its "
                    "stable task_id"
                ),
                changes_state=True,
                required_headers=["Idempotency-Key"],
            ),
            EndpointContract(
                method="GET",
                path="/api/v1/agent/handshake",
                purpose="read current identity, server version and scoped task index",
                changes_state=False,
            ),
            EndpointContract(
                method="GET",
                path="/api/v1/agent/tasks/{task_id}/activities",
                purpose="read ordered activity pages using an incremental cursor",
                changes_state=False,
            ),
            EndpointContract(
                method="GET",
                path="/api/v1/agent/tasks/{task_id}/activities/{activity_id}",
                purpose="read one authorized task activity",
                changes_state=False,
            ),
            EndpointContract(
                method="POST",
                path="/api/v1/agent/tasks/resolve",
                purpose=(
                    "resolve a Chinese or other task title to one stable task_id within the "
                    "authenticated Agent's active task participation; ambiguous matches require "
                    "Human confirmation"
                ),
                changes_state=False,
            ),
            EndpointContract(
                method="GET",
                path="/api/v1/agent/tasks/{task_id}",
                purpose="read task context and participants for an active task Agent",
                changes_state=False,
            ),
            EndpointContract(
                method="POST",
                path="/api/v1/agent/tasks/{task_id}/messages",
                purpose=(
                    "append shared task collaboration context once without creating mandatory "
                    "acknowledgement Runs; older Connectors receive a compatible Inbox delivery"
                ),
                changes_state=True,
                required_headers=["Idempotency-Key"],
            ),
            EndpointContract(
                method="GET",
                path="/api/v1/task-runs/pending",
                purpose="preview assigned durable runs, optionally filtered by task ID",
                changes_state=False,
            ),
            EndpointContract(
                method="POST",
                path="/api/v1/task-runs/claim",
                purpose=(
                    "claim one durable execution assigned to the authenticated Agent, "
                    "optionally by task ID or assignment ID"
                ),
                changes_state=True,
            ),
            EndpointContract(
                method="POST",
                path="/api/v1/task-runs/{run_id}/heartbeat",
                purpose="renew the execution lease and publish a checkpoint",
                changes_state=True,
            ),
            EndpointContract(
                method="POST",
                path="/api/v1/task-runs/{run_id}/result",
                purpose="submit an Agent result without claiming Human acceptance",
                changes_state=True,
            ),
        ],
        content=ContentContract(
            native_formats=["text", "markdown", "json"],
            message_types=[value.value for value in MessageType],
            max_content_bytes=MAX_CONTENT_BYTES,
            max_metadata_bytes=MAX_METADATA_BYTES,
            max_json_depth=MAX_JSON_DEPTH,
            max_attachments=32,
            max_attachment_bytes=settings.max_attachment_bytes,
        ),
        states=StateContract(
            delivery_states=["unread", "delivered", "read", "acked"],
            task_result_states=["completed", "partial", "failed", "cancelled"],
        ),
        task_execution=TaskExecutionContract(lease_seconds=RUN_LEASE_SECONDS),
        heartbeat=HeartbeatContract(
            endpoint="/connect/heartbeat",
            recommended_interval_seconds=settings.connector_heartbeat_interval_seconds,
            offline_after_seconds=heartbeat_timeout_seconds(
                settings.connector_heartbeat_interval_seconds
            ),
        ),
        synchronization=SynchronizationContract(
            inbox_endpoint="/api/v1/inbox",
            thread_endpoint_template="/api/v1/threads/{thread_id}",
            maximum_page_size=100,
            recommended_poll_interval_seconds=(settings.connector_inbox_poll_interval_seconds),
            push_wakeup_available=(
                settings.feishu_aily_remote_mcp_enabled and settings.wake_dispatch_enabled
            ),
        ),
        interoperability=InteroperabilityContract(),
        human_presentation=HumanPresentationContract(),
        onboarding=[
            OnboardingStep(
                order=1,
                action="fetch and validate this versioned contract",
                success_evidence="contract and version match the server response headers",
            ),
            OnboardingStep(
                order=2,
                action="complete Human-authorized pairing and keep the token in the OS vault",
                success_evidence="the Connector is active without exposing a credential",
            ),
            OnboardingStep(
                order=3,
                action="send a healthy heartbeat and read the Inbox using a cursor",
                success_evidence="heartbeat is accepted and Inbox pagination is repeatable",
            ),
            OnboardingStep(
                order=4,
                action="exchange a task, direct reply, structured result, and attachment",
                success_evidence=(
                    "all items remain in one Thread and preserve their distinct states"
                ),
            ),
        ],
    )
