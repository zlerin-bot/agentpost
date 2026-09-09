from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status

from agentpost.api.dependencies import SessionDep, SettingsDep
from agentpost.control.auth import CurrentHumanDep
from agentpost.control.human_security import (
    HumanCsrfDep,
    add_human_action_audit,
    human_session_id_from_request,
)
from agentpost.wakeup.schemas import (
    FeishuAilyWakeChannelCreate,
    WakeChannelStatus,
    WakeChannelTestResult,
)
from agentpost.wakeup.service import (
    WakeChannelAccessDeniedError,
    WakeChannelInvalidEndpointError,
    WakeChannelNotFoundError,
    WakeDeliveryError,
    configure_wake_channel,
    disable_wake_channel,
    get_wake_channel,
    test_wake_channel,
)

router = APIRouter(tags=["agent-wake-channels"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "wake_channel_not_found", "message": "Wake channel was not found"},
    )


def _audit(
    request: Request,
    session: SessionDep,
    current_human: CurrentHumanDep,
    *,
    action: str,
    agent_id: UUID,
    outcome: str,
) -> None:
    add_human_action_audit(
        session,
        human_user_id=current_human.id,
        human_session_id=human_session_id_from_request(request),
        action=action,
        target_type="agent",
        target_id=str(agent_id),
        outcome=outcome,
        request_id=request.state.request_id,
    )
    session.commit()


@router.get(
    "/api/v1/orbit/agents/{agent_id}/wake-channel",
    response_model=WakeChannelStatus,
)
def read_agent_wake_channel(
    agent_id: UUID,
    response: Response,
    current_human: CurrentHumanDep,
    session: SessionDep,
    settings: SettingsDep,
) -> WakeChannelStatus:
    response.headers["Cache-Control"] = "no-store"
    try:
        return get_wake_channel(session, settings, user=current_human, agent_id=agent_id)
    except (WakeChannelNotFoundError, WakeChannelAccessDeniedError) as exc:
        raise _not_found() from exc


@router.put(
    "/api/v1/orbit/agents/{agent_id}/wake-channel/feishu-aily",
    response_model=WakeChannelStatus,
)
def put_feishu_aily_wake_channel(
    agent_id: UUID,
    payload: FeishuAilyWakeChannelCreate,
    request: Request,
    response: Response,
    current_human: CurrentHumanDep,
    session: SessionDep,
    settings: SettingsDep,
    csrf: HumanCsrfDep,
) -> WakeChannelStatus:
    _ = csrf
    response.headers["Cache-Control"] = "no-store"
    try:
        result = configure_wake_channel(
            session, settings, user=current_human, agent_id=agent_id, payload=payload
        )
    except WakeChannelAccessDeniedError as exc:
        raise _not_found() from exc
    except WakeChannelInvalidEndpointError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "wake_endpoint_invalid",
                "message": "Use one public HTTPS Aily webhook URL and its Bearer token",
            },
        ) from exc
    _audit(
        request,
        session,
        current_human,
        action="control.feishu_aily_wake_configured",
        agent_id=agent_id,
        outcome="success",
    )
    return result


@router.post(
    "/api/v1/orbit/agents/{agent_id}/wake-channel/test",
    response_model=WakeChannelTestResult,
)
def verify_agent_wake_channel(
    agent_id: UUID,
    request: Request,
    response: Response,
    current_human: CurrentHumanDep,
    session: SessionDep,
    settings: SettingsDep,
    csrf: HumanCsrfDep,
) -> WakeChannelTestResult:
    _ = csrf
    response.headers["Cache-Control"] = "no-store"
    try:
        test_wake_channel(session, settings, user=current_human, agent_id=agent_id)
    except (WakeChannelNotFoundError, WakeChannelAccessDeniedError) as exc:
        raise _not_found() from exc
    except WakeDeliveryError as exc:
        _audit(
            request,
            session,
            current_human,
            action="control.feishu_aily_wake_tested",
            agent_id=agent_id,
            outcome="failed",
        )
        return WakeChannelTestResult(status="error", delivered=False, error_code=exc.code)
    _audit(
        request,
        session,
        current_human,
        action="control.feishu_aily_wake_tested",
        agent_id=agent_id,
        outcome="success",
    )
    return WakeChannelTestResult(status="active", delivered=True)


@router.delete(
    "/api/v1/orbit/agents/{agent_id}/wake-channel",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_agent_wake_channel(
    agent_id: UUID,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    settings: SettingsDep,
    csrf: HumanCsrfDep,
) -> None:
    _ = csrf
    try:
        disable_wake_channel(session, settings, user=current_human, agent_id=agent_id)
    except (WakeChannelNotFoundError, WakeChannelAccessDeniedError) as exc:
        raise _not_found() from exc
    _audit(
        request,
        session,
        current_human,
        action="control.feishu_aily_wake_disabled",
        agent_id=agent_id,
        outcome="success",
    )
