from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse

from agentpost.api.dependencies import CurrentAgentDep, SessionDep
from agentpost.attachments.service import AttachmentUnavailableError
from agentpost.control.auth import CurrentHumanDep
from agentpost.control.human_security import HumanCsrfDep, human_session_id_from_request
from agentpost.tasks.schemas import (
    AgentChoice,
    AgentRunClaim,
    AgentRunClaimRequest,
    AgentRunPendingList,
    AgentRunResult,
    AgentRunUpdate,
    AgentTaskCreate,
    AgentTaskMessageCreate,
    AgentTaskMessageResponse,
    AgentTaskResolution,
    AgentTaskResolveRequest,
    FriendRequestCreate,
    FriendRequestDecision,
    FriendResponse,
    HumanTaskMessageCreate,
    TaskAcceptanceDecision,
    TaskActivityReplyRelationCreate,
    TaskAssignmentBatchCreate,
    TaskAssignmentCreate,
    TaskCreate,
    TaskDetail,
    TaskFinalSubmission,
    TaskInvitationDecision,
    TaskMembersInvite,
    TaskRunHumanResponse,
    TaskStatusUpdate,
    TaskSummary,
)
from agentpost.tasks.service import (
    AgentRunLeaseError,
    AgentRunNotFoundError,
    FriendshipConflictError,
    FriendshipNotFoundError,
    TaskAgentSelectionError,
    TaskHumanResponseForbiddenError,
    TaskMessageIdempotencyConflictError,
    TaskNotFoundError,
    TaskOwnerRequiredError,
    TaskStateConflictError,
    agent_handshake,
    cancel_queued_assignment,
    claim_agent_run,
    complete_agent_run,
    confirm_task_activity_reply,
    create_assignment,
    create_assignment_batch,
    create_task,
    create_task_by_agent,
    decide_friendship,
    decide_task_acceptance,
    decide_task_invitation,
    get_task,
    get_task_for_agent,
    invite_task_members,
    list_friend_suggestions,
    list_friends,
    list_pending_agent_runs,
    list_task_invitation_candidates,
    list_tasks,
    read_agent_activity_page,
    remove_friendship,
    request_friendship,
    resolve_task_for_agent,
    respond_to_waiting_agent_run,
    select_task_agents,
    send_task_message_by_agent,
    send_task_message_by_human,
    submit_task,
    update_agent_run,
    update_task_status,
)

router = APIRouter(prefix="/api/v1", tags=["tasks"])
Limit = Annotated[int, Query(ge=1, le=200)]


def _not_found(code: str = "task_not_found") -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": "Resource not found"})


def _conflict(code: str = "task_state_conflict") -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": "State has changed"})


def _forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"code": "task_owner_required", "message": "Task owner access is required"},
    )


def _human_response_forbidden() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={
            "code": "task_human_response_forbidden",
            "message": "Only the task owner or responsible Human can answer this AI",
        },
    )


@router.get("/friends", response_model=dict[str, list[FriendResponse]])
def get_friends(
    current_human: CurrentHumanDep,
    session: SessionDep,
    query: Annotated[str | None, Query(max_length=100)] = None,
    limit: Limit = 100,
) -> dict[str, list[FriendResponse]]:
    return {"items": list_friends(session, user=current_human, query=query, limit=limit)}


@router.get("/friends/suggestions", response_model=dict[str, list[FriendResponse]])
def get_friend_suggestions(
    current_human: CurrentHumanDep,
    session: SessionDep,
    query: Annotated[str | None, Query(max_length=100)] = None,
    limit: Limit = 20,
) -> dict[str, list[FriendResponse]]:
    return {"items": list_friend_suggestions(session, user=current_human, query=query, limit=limit)}


@router.post("/friend-requests", response_model=FriendResponse, status_code=201)
def create_friend_request(
    payload: FriendRequestCreate,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> FriendResponse:
    del csrf
    try:
        return request_friendship(
            session,
            user=current_human,
            username=payload.username,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except FriendshipNotFoundError as exc:
        raise _not_found("human_not_found") from exc
    except FriendshipConflictError as exc:
        raise _conflict("friendship_conflict") from exc


@router.post("/friend-requests/{friendship_id}/decision", response_model=FriendResponse)
def decide_friend_request(
    friendship_id: UUID,
    payload: FriendRequestDecision,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> FriendResponse:
    del csrf
    try:
        return decide_friendship(
            session,
            user=current_human,
            friendship_id=friendship_id,
            accept=payload.decision == "accept",
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except FriendshipNotFoundError as exc:
        raise _not_found("friendship_not_found") from exc


@router.delete("/friends/{friendship_id}", status_code=204)
def delete_friend(
    friendship_id: UUID,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> Response:
    del csrf
    try:
        remove_friendship(
            session,
            user=current_human,
            friendship_id=friendship_id,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except FriendshipNotFoundError as exc:
        raise _not_found("friendship_not_found") from exc
    return Response(status_code=204)


@router.get("/tasks", response_model=dict[str, list[TaskSummary]])
def get_tasks(
    current_human: CurrentHumanDep, session: SessionDep, limit: Limit = 100
) -> dict[str, list[TaskSummary]]:
    return {"items": list_tasks(session, user=current_human, limit=limit)}


@router.post("/tasks", response_model=TaskDetail, status_code=201)
def create_human_task(
    payload: TaskCreate,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> TaskDetail:
    del csrf
    try:
        return create_task(
            session,
            user=current_human,
            payload=payload,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except TaskAgentSelectionError as exc:
        raise _not_found("agent_not_found") from exc


@router.post("/agent/tasks", response_model=TaskDetail, status_code=201)
def create_agent_task(
    payload: AgentTaskCreate,
    current_agent: CurrentAgentDep,
    session: SessionDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> TaskDetail:
    try:
        return create_task_by_agent(
            session,
            agent=current_agent,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    except TaskAgentSelectionError as exc:
        raise _not_found("agent_owner_not_found") from exc


@router.post("/agent/tasks/resolve", response_model=AgentTaskResolution)
def resolve_agent_task(
    payload: AgentTaskResolveRequest,
    current_agent: CurrentAgentDep,
    session: SessionDep,
) -> AgentTaskResolution:
    return resolve_task_for_agent(session, agent=current_agent, query=payload.query)


@router.get("/agent/handshake")
def get_agent_handshake(current_agent: CurrentAgentDep, session: SessionDep) -> dict:
    return agent_handshake(session, agent=current_agent)


@router.get("/agent/tasks/{task_id}", response_model=TaskDetail)
def get_agent_task(
    task_id: UUID,
    current_agent: CurrentAgentDep,
    session: SessionDep,
    include_history: bool = True,
) -> TaskDetail:
    try:
        return get_task_for_agent(
            session, agent=current_agent, task_id=task_id, include_history=include_history
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc


@router.get("/agent/tasks/{task_id}/activities")
def get_agent_activities(
    task_id: UUID,
    current_agent: CurrentAgentDep,
    session: SessionDep,
    cursor: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    try:
        return read_agent_activity_page(
            session, agent=current_agent, task_id=task_id, cursor=cursor, limit=limit
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc


@router.get("/agent/tasks/{task_id}/activities/{activity_id}")
def get_agent_activity(
    task_id: UUID,
    activity_id: UUID,
    current_agent: CurrentAgentDep,
    session: SessionDep,
) -> dict:
    try:
        return read_agent_activity_page(
            session, agent=current_agent, task_id=task_id, activity_id=activity_id, limit=1
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc


@router.post(
    "/agent/tasks/{task_id}/messages",
    response_model=AgentTaskMessageResponse,
    status_code=201,
)
def send_agent_task_message(
    task_id: UUID,
    payload: AgentTaskMessageCreate,
    current_agent: CurrentAgentDep,
    session: SessionDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> AgentTaskMessageResponse:
    try:
        return send_task_message_by_agent(
            session,
            agent=current_agent,
            task_id=task_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskMessageIdempotencyConflictError as exc:
        raise _conflict("idempotency_conflict") from exc
    except AttachmentUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "attachment_unavailable", "message": str(exc)},
        ) from exc


@router.post("/tasks/{task_id}/messages", response_model=AgentTaskMessageResponse, status_code=201)
def send_human_task_message(
    task_id: UUID,
    payload: HumanTaskMessageCreate,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> AgentTaskMessageResponse:
    del csrf
    try:
        return send_task_message_by_human(
            session,
            user=current_human,
            task_id=task_id,
            body=payload.body,
            parent_id=payload.reply_to_activity_id,
            references=payload.referenced_activity_ids,
            idempotency_key=idempotency_key,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskMessageIdempotencyConflictError as exc:
        raise _conflict("idempotency_conflict") from exc


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_human_task(
    task_id: UUID,
    current_human: CurrentHumanDep,
    session: SessionDep,
    activity_limit: Annotated[int, Query(ge=50, le=2000)] = 200,
) -> TaskDetail:
    try:
        return get_task(
            session,
            user=current_human,
            task_id=task_id,
            activity_limit=activity_limit,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc


@router.post("/tasks/{task_id}/activity-relations/reply", response_model=TaskDetail)
def confirm_human_task_activity_reply(
    task_id: UUID,
    payload: TaskActivityReplyRelationCreate,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> TaskDetail:
    del csrf
    try:
        return confirm_task_activity_reply(
            session,
            user=current_human,
            task_id=task_id,
            payload=payload,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskOwnerRequiredError as exc:
        raise _forbidden() from exc
    except TaskStateConflictError as exc:
        raise _conflict("task_activity_relation_conflict") from exc


@router.get("/tasks/{task_id}/invite-candidates", response_model=dict[str, list[FriendResponse]])
def get_task_invitation_candidates(
    task_id: UUID,
    current_human: CurrentHumanDep,
    session: SessionDep,
    limit: Limit = 100,
) -> dict[str, list[FriendResponse]]:
    try:
        return {
            "items": list_task_invitation_candidates(
                session, user=current_human, task_id=task_id, limit=limit
            )
        }
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskOwnerRequiredError as exc:
        raise _forbidden() from exc


@router.post("/tasks/{task_id}/members", response_model=TaskDetail)
def invite_human_task_members(
    task_id: UUID,
    payload: TaskMembersInvite,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> TaskDetail:
    del csrf
    try:
        return invite_task_members(
            session,
            user=current_human,
            task_id=task_id,
            human_user_ids=payload.human_user_ids,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
            settings=request.app.state.settings,
        )
    except (TaskNotFoundError, FriendshipNotFoundError) as exc:
        raise _not_found() from exc
    except TaskOwnerRequiredError as exc:
        raise _forbidden() from exc
    except TaskStateConflictError as exc:
        raise _conflict() from exc
    except TaskAgentSelectionError as exc:
        raise _conflict("friend_default_agent_required") from exc


@router.put("/tasks/{task_id}/my-agents", response_model=TaskDetail)
def select_human_task_agents(
    task_id: UUID,
    payload: AgentChoice,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> TaskDetail:
    del csrf
    try:
        return select_task_agents(
            session,
            user=current_human,
            task_id=task_id,
            choice=payload,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskAgentSelectionError as exc:
        raise _not_found("agent_not_found") from exc
    except TaskStateConflictError as exc:
        raise _conflict() from exc


@router.post("/tasks/{task_id}/accept", response_model=TaskDetail)
def accept_human_task_invitation(
    task_id: UUID,
    payload: TaskInvitationDecision,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> TaskDetail:
    del csrf
    try:
        result = decide_task_invitation(
            session,
            user=current_human,
            task_id=task_id,
            accept=True,
            choice=payload,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskAgentSelectionError as exc:
        raise _not_found("agent_not_found") from exc
    except TaskStateConflictError as exc:
        raise _conflict() from exc
    assert result is not None
    return result


@router.post("/tasks/{task_id}/decline", status_code=204)
def decline_human_task_invitation(
    task_id: UUID,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> Response:
    del csrf
    try:
        decide_task_invitation(
            session,
            user=current_human,
            task_id=task_id,
            accept=False,
            choice=None,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskStateConflictError as exc:
        raise _conflict() from exc
    return Response(status_code=204)


@router.post("/tasks/{task_id}/assignments", response_model=TaskDetail)
def create_task_assignment(
    task_id: UUID,
    payload: TaskAssignmentCreate,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> TaskDetail:
    del csrf
    try:
        return create_assignment(
            session,
            user=current_human,
            task_id=task_id,
            payload=payload,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskOwnerRequiredError as exc:
        raise _forbidden() from exc
    except TaskAgentSelectionError as exc:
        raise _not_found("agent_not_found") from exc
    except TaskStateConflictError as exc:
        raise _conflict() from exc


@router.post("/tasks/{task_id}/assignments/batch", response_model=TaskDetail)
def create_task_assignment_batch(
    task_id: UUID,
    payload: TaskAssignmentBatchCreate,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
) -> TaskDetail:
    del csrf
    try:
        return create_assignment_batch(
            session,
            user=current_human,
            task_id=task_id,
            payload=payload,
            idempotency_key=idempotency_key,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskOwnerRequiredError as exc:
        raise _forbidden() from exc
    except TaskAgentSelectionError as exc:
        raise _not_found("agent_not_found") from exc
    except TaskStateConflictError as exc:
        raise _conflict() from exc
    except TaskMessageIdempotencyConflictError as exc:
        raise _conflict("idempotency_conflict") from exc


@router.post("/tasks/{task_id}/assignments/{assignment_id}/cancel", response_model=TaskDetail)
def cancel_human_queued_assignment(
    task_id: UUID,
    assignment_id: UUID,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> TaskDetail:
    del csrf
    try:
        return cancel_queued_assignment(
            session, user=current_human, task_id=task_id, assignment_id=assignment_id
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskOwnerRequiredError as exc:
        raise _forbidden() from exc
    except TaskStateConflictError as exc:
        raise _conflict("assignment_no_longer_queued") from exc


@router.post(
    "/tasks/{task_id}/assignments/{assignment_id}/human-response",
    response_model=TaskDetail,
)
def answer_waiting_agent_run(
    task_id: UUID,
    assignment_id: UUID,
    payload: TaskRunHumanResponse,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> TaskDetail:
    del csrf
    try:
        return respond_to_waiting_agent_run(
            session,
            user=current_human,
            task_id=task_id,
            assignment_id=assignment_id,
            payload=payload,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskHumanResponseForbiddenError as exc:
        raise _human_response_forbidden() from exc
    except TaskStateConflictError as exc:
        raise _conflict("task_run_not_waiting_human") from exc


@router.post("/tasks/{task_id}/status", response_model=TaskDetail)
def change_task_status(
    task_id: UUID,
    payload: TaskStatusUpdate,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> TaskDetail:
    del csrf
    try:
        return update_task_status(
            session,
            user=current_human,
            task_id=task_id,
            action=payload.action,
            reason=payload.reason,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskOwnerRequiredError as exc:
        raise _forbidden() from exc
    except TaskStateConflictError as exc:
        raise _conflict() from exc


@router.post("/tasks/{task_id}/submit", response_model=TaskDetail)
def submit_task_for_acceptance(
    task_id: UUID,
    payload: TaskFinalSubmission,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> TaskDetail:
    del csrf
    try:
        return submit_task(
            session,
            user=current_human,
            task_id=task_id,
            payload=payload,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskOwnerRequiredError as exc:
        raise _forbidden() from exc
    except TaskStateConflictError as exc:
        raise _conflict() from exc


@router.post("/tasks/{task_id}/acceptance", response_model=TaskDetail)
def decide_human_task_acceptance(
    task_id: UUID,
    payload: TaskAcceptanceDecision,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> TaskDetail:
    del csrf
    try:
        return decide_task_acceptance(
            session,
            user=current_human,
            task_id=task_id,
            payload=payload,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except TaskNotFoundError as exc:
        raise _not_found() from exc
    except TaskOwnerRequiredError as exc:
        raise _forbidden() from exc
    except TaskStateConflictError as exc:
        raise _conflict() from exc


@router.get("/task-runs/pending", response_model=AgentRunPendingList)
def pending_task_runs(
    current_agent: CurrentAgentDep,
    session: SessionDep,
    task_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AgentRunPendingList:
    return list_pending_agent_runs(
        session,
        agent=current_agent,
        task_id=task_id,
        limit=limit,
    )


@router.post("/task-runs/claim", response_model=AgentRunClaim | None)
def claim_task_run(
    current_agent: CurrentAgentDep,
    session: SessionDep,
    payload: AgentRunClaimRequest | None = None,
) -> AgentRunClaim | None:
    try:
        return claim_agent_run(
            session,
            agent=current_agent,
            task_id=payload.task_id if payload else None,
            assignment_id=payload.assignment_id if payload else None,
        )
    except AgentRunNotFoundError as exc:
        raise _not_found("run_not_found") from exc


@router.post("/task-runs/{run_id}/heartbeat", response_model=AgentRunClaim)
def heartbeat_task_run(
    run_id: UUID,
    payload: AgentRunUpdate,
    current_agent: CurrentAgentDep,
    session: SessionDep,
) -> AgentRunClaim:
    try:
        return update_agent_run(session, agent=current_agent, run_id=run_id, payload=payload)
    except (AgentRunNotFoundError, AgentRunLeaseError, TaskNotFoundError) as exc:
        raise _not_found("run_not_found") from exc


@router.post("/task-runs/{run_id}/result", status_code=204)
def complete_task_run(
    run_id: UUID,
    payload: AgentRunResult,
    current_agent: CurrentAgentDep,
    session: SessionDep,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=1, max_length=255)
    ] = None,
    prefer: Annotated[str | None, Header()] = None,
) -> Response:
    try:
        result = complete_agent_run(
            session,
            agent=current_agent,
            run_id=run_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    except (AgentRunNotFoundError, AgentRunLeaseError, TaskNotFoundError) as exc:
        raise _not_found("run_not_found") from exc
    except TaskStateConflictError as exc:
        raise _conflict("idempotency_conflict") from exc
    if prefer == "return=representation":
        return JSONResponse(result, headers={"Preference-Applied": prefer})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
