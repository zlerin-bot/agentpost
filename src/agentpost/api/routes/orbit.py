from __future__ import annotations

import html
import io
import json
from collections.abc import Iterator
from typing import Annotated, BinaryIO
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse

from agentpost.accounts.usernames import HumanUsernameAlreadyRegisteredError
from agentpost.api.dependencies import SessionDep, SettingsDep
from agentpost.attachments.models import Attachment
from agentpost.attachments.preview import preview_content_type, zip_directory
from agentpost.control.auth import CurrentHumanDep, HumanAccessKeyDep
from agentpost.control.human_security import (
    HUMAN_CSRF_HEADER,
    HumanCsrfDep,
    add_human_action_audit,
    human_session_id_from_request,
)
from agentpost.control.models import AgentOwnership, HumanSession
from agentpost.control.schemas import (
    HumanProfile,
    HumanSessionResponse,
    HumanUsernameUpdate,
    OrbitAgent,
    OrbitAgentDelete,
    OrbitAgentHandleUpdate,
    OrbitDashboard,
    OrbitMessage,
    OrbitTask,
    OrbitThreadArchiveState,
    OrbitThreadDetail,
    OrbitThreadSummary,
    OrbitThreadViewState,
)
from agentpost.control.service import (
    AgentOwnerActionDeniedError,
    OrbitAttachmentNotFoundError,
    OrbitThreadNotFoundError,
    archive_orbit_thread,
    build_orbit_dashboard,
    disable_owned_agent,
    get_orbit_attachment,
    get_orbit_thread,
    human_profile,
    list_orbit_messages,
    list_orbit_tasks,
    list_orbit_threads,
    mark_orbit_thread_viewed,
    restore_orbit_thread,
    set_human_default_agent,
    update_human_username,
)
from agentpost.control.sessions import (
    HUMAN_SESSION_COOKIE,
    create_human_session,
    resolve_human_session,
    revoke_human_session,
    rotate_human_csrf_token,
    verify_human_csrf_token,
)
from agentpost.identity.models import Agent
from agentpost.identity.schemas import AgentProfile
from agentpost.identity.service import (
    HandleAlreadyRegisteredError,
    agent_profile,
    flush_agent_handle,
)
from agentpost.storage import LocalAttachmentStorage, StorageObjectNotFoundError

router = APIRouter(tags=["human-control-plane"])
Limit = Annotated[int, Query(ge=1, le=200)]
Search = Annotated[str | None, Query(max_length=200)]


def _stream_and_close(source: BinaryIO) -> Iterator[bytes]:
    try:
        while chunk := source.read(LocalAttachmentStorage.chunk_size):
            yield chunk
    finally:
        source.close()


def _attachment_disposition(filename: str, *, inline: bool) -> str:
    mode = "inline" if inline else "attachment"
    return f"{mode}; filename=attachment.bin; filename*=UTF-8''{quote(filename)}"


_TEXT_PREVIEW_TYPES = {
    "application/json",
    "application/markdown",
    "text/markdown",
    "text/plain",
    "text/x-markdown",
}


def _safe_markdown_fragment(content: str) -> str:
    """Render a small readable Markdown subset after escaping every source character."""

    lines = content.splitlines()
    output: list[str] = []
    index = 0
    in_code = False
    list_kind = ""

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            output.append(f"</{list_kind}>")
            list_kind = ""

    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if stripped.startswith("```"):
            close_list()
            output.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
            index += 1
            continue
        if in_code:
            output.append(html.escape(raw) + "\n")
            index += 1
            continue
        if not stripped:
            close_list()
            index += 1
            continue
        if (
            "|" in stripped
            and index + 1 < len(lines)
            and all(
                cell.strip().replace(":", "").replace("-", "") == "" and "-" in cell
                for cell in lines[index + 1].strip().strip("|").split("|")
            )
        ):
            close_list()
            headers = [html.escape(cell.strip()) for cell in stripped.strip("|").split("|")]
            output.append("<div class=table-wrap><table><thead><tr>")
            output.extend(f"<th>{cell}</th>" for cell in headers)
            output.append("</tr></thead><tbody>")
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                cells = [
                    html.escape(cell.strip()) for cell in lines[index].strip().strip("|").split("|")
                ]
                output.append("<tr>")
                output.extend(f"<td>{cell}</td>" for cell in cells)
                output.append("</tr>")
                index += 1
            output.append("</tbody></table></div>")
            continue
        heading_level = len(stripped) - len(stripped.lstrip("#"))
        if 1 <= heading_level <= 6 and stripped[heading_level : heading_level + 1] == " ":
            close_list()
            output.append(
                f"<h{heading_level}>{html.escape(stripped[heading_level + 1 :])}</h{heading_level}>"
            )
            index += 1
            continue
        unordered = stripped.startswith(("- ", "* ", "+ "))
        ordered_head, separator, ordered_body = stripped.partition(". ")
        ordered = bool(separator and ordered_head.isdigit())
        if unordered or ordered:
            kind = "ul" if unordered else "ol"
            if list_kind != kind:
                close_list()
                output.append(f"<{kind}>")
                list_kind = kind
            body = stripped[2:] if unordered else ordered_body
            output.append(f"<li>{html.escape(body)}</li>")
            index += 1
            continue
        close_list()
        output.append(f"<p>{html.escape(stripped)}</p>")
        index += 1
    close_list()
    if in_code:
        output.append("</code></pre>")
    return "".join(output)


def _text_attachment_preview(attachment: Attachment, source: BinaryIO) -> bytes:
    try:
        content = source.read().decode("utf-8", errors="replace")
    finally:
        source.close()
    if preview_content_type(attachment.content_type, attachment.filename) == "application/json":
        try:
            content = json.dumps(json.loads(content), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    filename = html.escape(attachment.filename)
    content_type = preview_content_type(attachment.content_type, attachment.filename)
    is_markdown = content_type in {"application/markdown", "text/markdown", "text/x-markdown"}
    safe_content = _safe_markdown_fragment(content) if is_markdown else html.escape(content)
    content_markup = (
        f'<article class="markdown-body">{safe_content}</article>'
        if is_markdown
        else f"<pre>{safe_content}</pre>"
    )
    preview_label = (
        "压缩包目录预览"
        if content_type == "application/zip"
        else "Markdown 安全阅读预览"
        if is_markdown
        else "只读文字预览"
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{filename}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    body {{ margin: 0; background: #f5f8fc; color: #172033; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 24px clamp(16px, 4vw, 42px) 48px; }}
    header {{ margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid #c8d7ec; }}
    h1 {{ margin: 0; font-size: clamp(18px, 3vw, 25px); overflow-wrap: anywhere; }}
    p {{ margin: 6px 0 0; color: #5f6b7d; font-size: 14px; }}
    pre {{
      margin: 0; border: 1px solid #c8d7ec; border-radius: 14px; background: #fff; padding: 18px;
      white-space: pre-wrap; overflow-wrap: anywhere;
      font: 15px/1.75 ui-monospace, SFMono-Regular, Menlo, monospace;
    }}
    .markdown-body {{
      border: 1px solid #c8d7ec; border-radius: 14px; background: #fff;
      padding: 20px; line-height: 1.75;
    }}
    .markdown-body :first-child {{ margin-top: 0; }}
    .markdown-body :last-child {{ margin-bottom: 0; }}
    .markdown-body h1, .markdown-body h2, .markdown-body h3 {{
      line-height: 1.35; overflow-wrap: anywhere;
    }}
    .markdown-body p, .markdown-body li {{
      color: #26354a; font-size: 15px; overflow-wrap: anywhere;
    }}
    .markdown-body pre {{ overflow: auto; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{
      border: 1px solid #c8d7ec; padding: 8px 10px;
      text-align: left; vertical-align: top;
    }}
    th {{ background: #eef4fc; }}
  </style>
</head>
<body><main><header><h1>{filename}</h1><p>{preview_label}</p></header>{content_markup}</main></body>
</html>""".encode()


def _visible_orbit_attachment_source(
    session: SessionDep,
    settings: SettingsDep,
    current_human: CurrentHumanDep,
    attachment_id: UUID,
) -> tuple[Attachment, BinaryIO]:
    try:
        attachment = get_orbit_attachment(
            session,
            current_human,
            attachment_id=attachment_id,
        )
        source = LocalAttachmentStorage(settings.storage_path).open(attachment.storage_key)
    except (OrbitAttachmentNotFoundError, StorageObjectNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "attachment_not_found", "message": "Attachment was not found"},
        ) from exc
    return attachment, source


def _orbit_asset(filename: str, media_type: str) -> FileResponse:
    from agentpost.orbit_ui import INDEX_PATH

    return FileResponse(
        INDEX_PATH.with_name(filename),
        media_type=media_type,
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/orbit", include_in_schema=False)
def orbit_console() -> FileResponse:
    from agentpost.orbit_ui import INDEX_PATH

    return FileResponse(
        INDEX_PATH,
        media_type="text/html",
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": (
                "default-src 'none'; style-src 'self'; script-src 'self'; "
                "img-src 'self'; connect-src 'self'; frame-src 'self'; base-uri 'none'; "
                "form-action 'self'; frame-ancestors 'none'"
            ),
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/", include_in_schema=False)
def platform_home() -> FileResponse:
    return orbit_console()


@router.get("/orbit/styles.css", include_in_schema=False)
def orbit_styles() -> FileResponse:
    return _orbit_asset("styles.css", "text/css")


@router.get("/orbit/app.js", include_in_schema=False)
def orbit_script() -> FileResponse:
    return _orbit_asset("app.js", "text/javascript")


@router.get("/orbit/xingyun-relay-logo.png", include_in_schema=False)
def orbit_logo() -> FileResponse:
    return _orbit_asset("xingyun-relay-logo.png", "image/png")


@router.get("/orbit/project-icon.svg", include_in_schema=False)
def orbit_project_icon() -> FileResponse:
    return _orbit_asset("project-icon.svg", "image/svg+xml")


@router.get("/orbit/friends-icon.svg", include_in_schema=False)
def orbit_friends_icon() -> FileResponse:
    return _orbit_asset("friends-icon.svg", "image/svg+xml")


@router.get("/api/v1/orbit/me", response_model=HumanProfile)
def orbit_me(current_human: CurrentHumanDep) -> HumanProfile:
    return human_profile(current_human)


@router.patch("/api/v1/orbit/me/username", response_model=HumanProfile)
def update_orbit_username(
    payload: HumanUsernameUpdate,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> HumanProfile:
    _ = csrf
    try:
        return update_human_username(
            session,
            user=current_human,
            payload=payload,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except HumanUsernameAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "username_already_registered",
                "message": "This username is already in use",
                "details": {"username": str(exc.args[0])},
            },
        ) from exc


@router.post(
    "/api/v1/orbit/session",
    response_model=HumanSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_orbit_session(
    response: Response,
    request: Request,
    access_key_user: HumanAccessKeyDep,
    session: SessionDep,
    settings: SettingsDep,
) -> HumanSessionResponse:
    created = create_human_session(
        session,
        settings,
        user=access_key_user,
        request_id=request.state.request_id,
    )
    response.set_cookie(
        key=HUMAN_SESSION_COOKIE,
        value=created.raw_token,
        max_age=settings.human_session_ttl_seconds,
        path="/api/v1",
        secure=settings.is_production,
        httponly=True,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"
    return HumanSessionResponse(
        user=human_profile(access_key_user),
        expires_at=created.expires_at,
        csrf_token=created.raw_csrf_token,
    )


@router.get(
    "/api/v1/orbit/session",
    response_model=HumanSessionResponse,
)
def refresh_orbit_session(
    response: Response,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    settings: SettingsDep,
) -> HumanSessionResponse:
    raw_session_id = getattr(request.state, "human_session_id", None)
    browser_session = session.get(HumanSession, UUID(raw_session_id)) if raw_session_id else None
    if browser_session is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "browser_session_required",
                "message": "A browser session is required to refresh CSRF state",
            },
        )
    csrf_token = rotate_human_csrf_token(
        session,
        settings,
        browser_session=browser_session,
    )
    response.headers["Cache-Control"] = "no-store"
    return HumanSessionResponse(
        user=human_profile(current_human),
        expires_at=browser_session.expires_at,
        csrf_token=csrf_token,
    )


@router.delete(
    "/api/v1/orbit/session",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_orbit_session(
    response: Response,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    csrf_token: Annotated[str | None, Header(alias=HUMAN_CSRF_HEADER)] = None,
) -> None:
    raw_session = request.cookies.get(HUMAN_SESSION_COOKIE, "")
    if raw_session:
        resolved = resolve_human_session(session, settings, raw_token=raw_session)
        if resolved is not None:
            user, browser_session = resolved
            if csrf_token is None or not verify_human_csrf_token(
                settings,
                browser_session=browser_session,
                raw_csrf_token=csrf_token,
            ):
                add_human_action_audit(
                    session,
                    human_user_id=user.id,
                    human_session_id=browser_session.id,
                    action="control.session_revocation_denied",
                    target_type="human_session",
                    target_id=str(browser_session.id),
                    outcome="denied",
                    reason_code="invalid_csrf_token",
                    request_id=request.state.request_id,
                )
                session.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "invalid_csrf_token",
                        "message": "A current same-origin CSRF token is required",
                    },
                )
        revoke_human_session(
            session,
            settings,
            raw_token=raw_session,
            request_id=request.state.request_id,
        )
    response.delete_cookie(
        key=HUMAN_SESSION_COOKIE,
        path="/api/v1",
        secure=settings.is_production,
        httponly=True,
        samesite="strict",
    )


@router.get("/api/v1/orbit/dashboard", response_model=OrbitDashboard)
def orbit_dashboard(
    current_human: CurrentHumanDep,
    session: SessionDep,
    settings: SettingsDep,
) -> OrbitDashboard:
    return build_orbit_dashboard(
        session,
        current_human,
        heartbeat_interval_seconds=settings.connector_heartbeat_interval_seconds,
    )


@router.get("/api/v1/orbit/agents", response_model=list[OrbitAgent])
def orbit_agents(
    current_human: CurrentHumanDep,
    session: SessionDep,
    settings: SettingsDep,
) -> list[OrbitAgent]:
    return build_orbit_dashboard(
        session,
        current_human,
        heartbeat_interval_seconds=settings.connector_heartbeat_interval_seconds,
    ).agents


@router.patch("/api/v1/orbit/agents/{agent_id}/handle", response_model=AgentProfile)
def update_orbit_agent_handle(
    agent_id: UUID,
    payload: OrbitAgentHandleUpdate,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> AgentProfile:
    _ = csrf
    ownership = session.get(AgentOwnership, agent_id)
    if ownership is None or ownership.human_user_id != current_human.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "agent_handle_access_denied",
                "message": "Only the Human owner can change this Agent short name",
            },
        )
    agent = session.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "agent_not_found", "message": "Agent was not found"},
        )
    previous_handle = agent.handle
    try:
        flush_agent_handle(session, agent, payload.handle)
    except HandleAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "handle_already_registered",
                "message": "This short Agent name is already in use",
                "details": {"handle": exc.handle, "suggestions": exc.suggestions},
            },
        ) from exc
    add_human_action_audit(
        session,
        human_user_id=current_human.id,
        human_session_id=(
            UUID(request.state.human_session_id)
            if getattr(request.state, "human_session_id", None)
            else None
        ),
        action="control.agent_handle_updated",
        target_type="agent",
        target_id=str(agent.id),
        outcome="success",
        request_id=request.state.request_id,
        audit_metadata={"previous_handle": previous_handle, "handle": agent.handle},
    )
    session.commit()
    session.refresh(agent)
    return agent_profile(agent)


@router.put("/api/v1/orbit/agents/{agent_id}/default", response_model=HumanProfile)
def update_orbit_default_agent(
    agent_id: UUID,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> HumanProfile:
    _ = csrf
    try:
        set_human_default_agent(
            session,
            user=current_human,
            agent_id=agent_id,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except AgentOwnerActionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "default_agent_access_denied",
                "message": "Only the Human owner can set this default Agent",
            },
        ) from exc
    return human_profile(current_human)


@router.delete(
    "/api/v1/orbit/agents/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_orbit_agent(
    agent_id: UUID,
    payload: OrbitAgentDelete,
    request: Request,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> None:
    _ = csrf, payload
    try:
        disable_owned_agent(
            session,
            user=current_human,
            agent_id=agent_id,
            human_session_id=human_session_id_from_request(request),
            request_id=request.state.request_id,
        )
    except AgentOwnerActionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "agent_delete_access_denied",
                "message": "Only the Human owner can delete this Agent",
            },
        ) from exc


@router.get("/api/v1/orbit/messages", response_model=list[OrbitMessage])
def orbit_messages(
    current_human: CurrentHumanDep,
    session: SessionDep,
    limit: Limit = 50,
) -> list[OrbitMessage]:
    return list_orbit_messages(session, current_human, limit=limit)


@router.get("/api/v1/orbit/threads", response_model=list[OrbitThreadSummary])
def orbit_threads(
    current_human: CurrentHumanDep,
    session: SessionDep,
    limit: Limit = 100,
    query: Search = None,
    agent_id: UUID | None = None,
    archived: bool = False,
) -> list[OrbitThreadSummary]:
    return list_orbit_threads(
        session,
        current_human,
        limit=limit,
        query=query,
        agent_id=agent_id,
        archived=archived,
    )


@router.get("/api/v1/orbit/threads/{thread_id}", response_model=OrbitThreadDetail)
def orbit_thread(
    thread_id: UUID,
    current_human: CurrentHumanDep,
    session: SessionDep,
) -> OrbitThreadDetail:
    try:
        return get_orbit_thread(session, current_human, thread_id=thread_id)
    except OrbitThreadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "thread_not_found", "message": "Thread was not found"},
        ) from exc


@router.post(
    "/api/v1/orbit/threads/{thread_id}/viewed",
    response_model=OrbitThreadViewState,
)
def orbit_thread_viewed(
    thread_id: UUID,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> OrbitThreadViewState:
    _ = csrf
    try:
        return mark_orbit_thread_viewed(session, current_human, thread_id=thread_id)
    except OrbitThreadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "thread_not_found", "message": "Thread was not found"},
        ) from exc


@router.put(
    "/api/v1/orbit/threads/{thread_id}/archive",
    response_model=OrbitThreadArchiveState,
)
def orbit_thread_archive(
    thread_id: UUID,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> OrbitThreadArchiveState:
    _ = csrf
    try:
        return archive_orbit_thread(session, current_human, thread_id=thread_id)
    except OrbitThreadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "thread_not_found", "message": "Thread was not found"},
        ) from exc


@router.delete(
    "/api/v1/orbit/threads/{thread_id}/archive",
    response_model=OrbitThreadArchiveState,
)
def orbit_thread_restore(
    thread_id: UUID,
    current_human: CurrentHumanDep,
    session: SessionDep,
    csrf: HumanCsrfDep,
) -> OrbitThreadArchiveState:
    _ = csrf
    try:
        return restore_orbit_thread(session, current_human, thread_id=thread_id)
    except OrbitThreadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "thread_not_found", "message": "Thread was not found"},
        ) from exc


@router.get("/api/v1/orbit/attachments/{attachment_id}")
def orbit_attachment_download(
    attachment_id: UUID,
    current_human: CurrentHumanDep,
    session: SessionDep,
    settings: SettingsDep,
) -> StreamingResponse:
    attachment, source = _visible_orbit_attachment_source(
        session,
        settings,
        current_human,
        attachment_id,
    )
    return StreamingResponse(
        _stream_and_close(source),
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": _attachment_disposition(attachment.filename, inline=False),
            "Content-Length": str(attachment.size),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/api/v1/orbit/attachments/{attachment_id}/preview")
def orbit_attachment_preview(
    attachment_id: UUID,
    current_human: CurrentHumanDep,
    session: SessionDep,
    settings: SettingsDep,
) -> Response:
    attachment, source = _visible_orbit_attachment_source(
        session,
        settings,
        current_human,
        attachment_id,
    )
    content_type = preview_content_type(attachment.content_type, attachment.filename)
    supported_types = {"application/pdf", "text/html", "application/zip", *_TEXT_PREVIEW_TYPES}
    if content_type not in supported_types:
        source.close()
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "attachment_preview_unsupported",
                "message": "This attachment type does not support an inline preview",
            },
        )
    if content_type == "application/zip":
        source = io.BytesIO(zip_directory(source).encode("utf-8"))
    if content_type in _TEXT_PREVIEW_TYPES or content_type == "application/zip":
        preview = _text_attachment_preview(attachment, source)
        return Response(
            content=preview,
            media_type="text/html",
            headers={
                "Cache-Control": "no-store",
                "Content-Disposition": _attachment_disposition(attachment.filename, inline=True),
                "Content-Security-Policy": (
                    "sandbox; default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; "
                    "form-action 'none'; frame-ancestors 'self'"
                ),
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            },
        )
    content_security_policy = (
        "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
        "font-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
        if content_type == "text/html"
        else "sandbox; default-src 'none'; frame-ancestors 'self'"
    )
    return StreamingResponse(
        _stream_and_close(source),
        media_type=content_type,
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": _attachment_disposition(attachment.filename, inline=True),
            "Content-Length": str(attachment.size),
            "Content-Security-Policy": content_security_policy,
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/api/v1/orbit/tasks", response_model=list[OrbitTask])
def orbit_tasks(
    current_human: CurrentHumanDep,
    session: SessionDep,
    limit: Limit = 50,
) -> list[OrbitTask]:
    return list_orbit_tasks(session, current_human, limit=limit)
