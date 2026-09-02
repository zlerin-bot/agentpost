from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status

from agentpost.api.dependencies import CurrentAgentDep, SessionDep
from agentpost.control.auth import CurrentHumanDep
from agentpost.control.human_security import HumanCsrfDep, human_session_id_from_request
from agentpost.tasks.schemas import (
    AgentChoice,
    AgentRunClaim,
    AgentRunResult,
    AgentRunUpdate,
    AgentTaskCreate,
    FriendRequestCreate,
    FriendRequestDecision,
    FriendResponse,
    TaskAcceptanceDecision,
    TaskAssignmentCreate,
    TaskCreate,
    TaskDetail,
    TaskFinalSubmission,
    TaskInvitationDecision,
    TaskMembersInvite,
    TaskStatusUpdate,
    TaskSummary,
)
from agentpost.tasks.service import (
    AgentRunLeaseError,
    AgentRunNotFoundError,
    FriendshipConflictError,
    FriendshipNotFoundError,
    TaskAgentSelectionError,
    TaskNotFoundError,
    TaskOwnerRequiredError,
    TaskStateConflictError,
    claim_agent_run,
    complete_agent_run,
    create_assignment,
    create_task,
    create_task_by_agent,
    decide_friendship,
    decide_task_acceptance,
    decide_task_invitation,
    get_task,
    invite_task_members,
    list_friend_suggestions,
    list_friends,
    list_task_invitation_candidates,
    list_tasks,
    remove_friendship,
    request_friendship,
    select_task_agents,
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


@router.get("/tasks/{task_id}", response_model=TaskDetail)
def get_human_task(
    task_id: UUID, current_human: CurrentHumanDep, session: SessionDep
) -> TaskDetail:
    try:
        return get_task(session, user=current_human, task_id=task_id)
    except TaskNotFoundError as exc:
        raise _not_found() from exc


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


@router.post("/task-runs/claim", response_model=AgentRunClaim | None)
def claim_task_run(current_agent: CurrentAgentDep, session: SessionDep) -> AgentRunClaim | None:
    try:
        return claim_agent_run(session, agent=current_agent)
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
    except (AgentRunNotFoundError, AgentRunLeaseError) as exc:
        raise _not_found("run_not_found") from exc


@router.post("/task-runs/{run_id}/result", status_code=204)
def complete_task_run(
    run_id: UUID,
    payload: AgentRunResult,
    current_agent: CurrentAgentDep,
    session: SessionDep,
) -> Response:
    try:
        complete_agent_run(session, agent=current_agent, run_id=run_id, payload=payload)
    except (AgentRunNotFoundError, AgentRunLeaseError) as exc:
        raise _not_found("run_not_found") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
