from __future__ import annotations

from fastapi.testclient import TestClient


def test_public_agent_integration_contract_preserves_machine_and_human_semantics(
    client: TestClient,
) -> None:
    response = client.get("/api/v1/protocol/contract")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=300"
    assert response.headers["X-AgentPost-Contract-Version"] == "0.3"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    payload = response.json()
    assert payload["contract"] == "AGENTPOST_AGENT_INTEGRATION"
    assert payload["version"] == "0.3"
    assert payload["openapi_url"] == "/openapi.json"
    send_endpoint = next(
        endpoint for endpoint in payload["endpoints"] if endpoint["path"] == "/api/v1/messages"
    )
    assert send_endpoint["bearer_auth_required"] is True
    assert send_endpoint["required_headers"] == ["Idempotency-Key"]
    assert payload["content"]["native_formats"] == ["text", "markdown", "json"]
    assert payload["content"]["html_is_native_body_format"] is False
    assert payload["content"]["max_attachments"] == 32
    assert payload["states"]["ack_means_received_not_completed"] is True
    assert payload["states"]["direct_reply_handles_task_round"] is True
    assert payload["states"]["structured_result_takes_precedence"] is True
    assert payload["states"]["agent_result_is_not_human_acceptance"] is True
    assert payload["task_execution"] == {
        "claim_endpoint": "/api/v1/task-runs/claim",
        "create_endpoint": "/api/v1/agent/tasks",
        "create_requires_idempotency_key": True,
        "resolve_endpoint": "/api/v1/agent/tasks/resolve",
        "context_endpoint_template": "/api/v1/agent/tasks/{task_id}",
        "message_endpoint_template": "/api/v1/agent/tasks/{task_id}/messages",
        "message_requires_idempotency_key": True,
        "legacy_connector_inbox_fallback": True,
        "connector_capabilities": [
            "task_context_read",
            "task_message_send",
            "durable_task_run",
        ],
        "unique_exact_title_resolves_automatically": True,
        "ambiguous_or_partial_title_requires_confirmation": True,
        "resolver_scope": "authenticated_agent_active_task_participation",
        "pending_endpoint": "/api/v1/task-runs/pending",
        "heartbeat_endpoint_template": "/api/v1/task-runs/{run_id}/heartbeat",
        "result_endpoint_template": "/api/v1/task-runs/{run_id}/result",
        "lease_seconds": 90,
        "durable_queue": True,
        "claim_is_idempotent_per_active_lease": False,
        "claim_retry_should_use_assignment_id": True,
        "targeted_claim_by_task_or_assignment": True,
        "claim_exposes_source_target_and_reply_scope": True,
        "connector_reports_local_session_wakeup": True,
        "body_mentions_do_not_create_assignments": True,
        "result_idempotency_key_supported": True,
        "result_requires_human_acceptance": True,
        "task_id_is_global_stable_identifier": True,
        "active_task_agents_receive_durable_runs": True,
        "task_messages_are_shared_context": True,
        "task_messages_create_acknowledgement_runs": False,
        "agent_results_create_sync_runs": False,
        "explicit_human_work_creates_runs": True,
        "waiting_human_checkpoint_visible_to_human": True,
        "human_response_requeues_same_assignment": True,
        "successor_run_exposes_human_response_checkpoint": True,
        "request_shapes": {
            "extra_fields": "forbid",
            "task_message_fields": [
                "subject",
                "content_format",
                "body",
                "attachments",
                "publication_origin",
            ],
            "task_message_legacy_aliases": {"format": "content_format"},
            "run_heartbeat_fields": [
                "lease_token",
                "status",
                "checkpoint",
                "wake_status",
                "local_session_id",
            ],
            "run_result_fields": ["lease_token", "status", "summary", "checkpoint"],
            "run_result_legacy_aliases": {"output": "checkpoint"},
        },
        "human_change_request_creates_new_runs": True,
        "collaboration_scope": "task_only",
        "participant_authority": "task_membership",
        "one_thread_per_task": True,
    }
    assert payload["heartbeat"]["recommended_interval_seconds"] == 30
    assert payload["heartbeat"]["offline_after_seconds"] == 90
    assert payload["heartbeat"]["online_requires_current_healthy_heartbeat"] is True
    assert payload["heartbeat"]["upgrade_directive_in_response"] is True
    assert payload["heartbeat"]["legacy_upgrade_inbox_notification"] is True
    assert payload["heartbeat"]["upgrade_notification_deduplicated_per_target_version"] is True
    assert payload["heartbeat"]["old_connectors_remain_usable_during_upgrade"] is True
    assert payload["heartbeat"]["reports_installed_configured_and_runtime_versions"] is True
    assert payload["heartbeat"]["reports_runtime_session_and_capabilities"] is True
    assert payload["heartbeat"]["reconnect_required_when_loaded_runtime_is_stale"] is True
    assert payload["synchronization"]["source_of_truth"] == "persistent_inbox"
    assert payload["synchronization"]["recommended_mode"] == "poll_with_cursor"
    assert payload["synchronization"]["recommended_poll_interval_seconds"] == 30
    assert payload["synchronization"]["push_wakeup_available"] is False
    assert payload["synchronization"]["human_view_changes_agent_delivery_state"] is False
    assert payload["interoperability"] == {
        "core_protocol": "agentpost_http_v1",
        "mcp": "adapter",
        "a2a": "mapping_design_only",
        "a2a_runtime_endpoint": None,
        "smtp_imap": False,
    }
    assert payload["human_presentation"]["default_view"] == "readable_summary"
    assert payload["human_presentation"]["raw_agent_data"] == "available_collapsed"
    assert payload["human_presentation"]["security_label"] == "external_agent_content"
    assert payload["human_presentation"]["independent_state_axes"] == [
        "human_view",
        "delivery",
        "agent_read",
        "ack",
        "agent_run",
        "task_result",
        "task_submission",
        "human_acceptance",
    ]
    task = payload["task_execution"]
    assert task["collaboration_scope"] == "task_only"
    assert task["participant_authority"] == "task_membership"
    assert task["one_thread_per_task"] is True


def test_agent_integration_contract_is_in_openapi(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/protocol/contract" in response.json()["paths"]
    assert all(
        "organizations" not in path and "organization-channel" not in path
        for path in response.json()["paths"]
    )
