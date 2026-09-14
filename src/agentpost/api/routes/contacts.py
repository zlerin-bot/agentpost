from datetime import UTC, timedelta
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from agentpost.api.dependencies import CurrentAgentDep, SessionDep, SettingsDep
from agentpost.contacts.models import ContactPreference, ContactRequest
from agentpost.contacts.service import (
    contact_status,
    continue_contact,
    expired,
    lock_contact,
    unavailable,
)
from agentpost.control.auth import CurrentHumanDep
from agentpost.control.human_security import (
    HumanCsrfDep,
    add_human_action_audit,
    human_session_id_from_request,
)
from agentpost.control.models import AgentOwnership, HumanUser
from agentpost.identity.models import Agent, utc_now
from agentpost.security.rate_limit import client_rate_limit_subject, enforce_http_rate_limit
from agentpost.tasks.service import _human_agent

router = APIRouter(tags=["first-contact"])
Token = Annotated[str, Field(pattern=r"^gc_[A-Za-z0-9_-]{43}$")]


class Introduction(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    username: str = Field(min_length=1, max_length=32)
    sender_name: str = Field(min_length=1, max_length=100)
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    intent: Literal["greeting", "collaboration"] = "greeting"


class Claim(BaseModel):
    token: Token | None = None


class Preference(BaseModel):
    enabled: bool
    introduction: str = Field(default="", max_length=280)


class Decision(BaseModel):
    action: Literal[
        "accept", "decline", "continue", "reply", "block", "report", "request_collaboration"
    ]
    body: str = Field(default="", max_length=10000)


def digest(token):
    return sha256(token.encode()).hexdigest()


def guest_token(authorization):
    import re

    if not authorization or not re.fullmatch(r"Bearer gc_[A-Za-z0-9_-]{43}", authorization):
        raise HTTPException(
            401, detail={"code": "guest_proof_required", "message": "需要本次联系凭证"}
        )
    return authorization[7:]


def limit(request, session, settings, scope, amount, seconds, subject=None):
    enforce_http_rate_limit(
        request,
        session,
        settings,
        scope=f"contact.{scope}",
        subject=subject or client_rate_limit_subject(request),
        limit=amount,
        window_seconds=seconds,
    )


def public_target(session, username):
    person = session.scalar(
        select(HumanUser)
        .join(ContactPreference, ContactPreference.human_id == HumanUser.id)
        .where(
            HumanUser.username == username.lower(),
            HumanUser.status == "active",
            ContactPreference.enabled.is_(True),
        )
    )
    if not person or not _human_agent(
        session, human_id=person.id, agent_id=person.default_agent_id
    ):
        raise HTTPException(
            404,
            detail={
                "code": "public_contact_unavailable",
                "message": (
                    "暂无可用的公开联系入口，不代表对方没有账号；请核对用户名或请对方开启首次联系。"
                ),
            },
        )
    return person


def receipt(item):
    # Guest proof never returns task ID, other messages, private identity or Agent keys.
    return {
        "request_id": str(item.id),
        "status": "claimed" if item.sender_id else contact_status(item),
        "expires_at": item.expires_at.replace(tzinfo=UTC),
        "delivery": "saved_for_recipient",
        "agent_execution": "not_triggered_by_guest_request",
        "intent": item.intent,
        "reply": item.reply_body
        if not item.sender_id and not expired(item) and not item.blocked
        else None,
        "security_label": "external_agent_content",
    }


def submission_receipt(item, token, settings):
    result = receipt(item)
    result["registration_url"] = f"{settings.public_base_url.rstrip('/')}/contact"
    if not item.sender_id and not expired(item):
        result["registration_url"] += f"#claim={token}"
    return result


def view(item, session, user):
    person = session.get(HumanUser, item.recipient_id)
    sender = session.get(HumanUser, item.sender_id) if item.sender_id else None
    result = {
        "request_id": str(item.id),
        "status": contact_status(item),
        "decision": item.decision,
        "intent": item.intent,
        "reply": item.reply_body,
        "blocked": item.blocked,
        "reported": item.reported,
        "incoming": item.recipient_id == user.id,
        "sender_name": sender.display_name if sender else item.sender_name,
        "sender_verified": bool(sender),
        "recipient_username": person.username,
        "subject": item.subject,
        "body": item.body,
        "created_at": item.created_at.replace(tzinfo=UTC),
        "expires_at": item.expires_at.replace(tzinfo=UTC),
        "security_label": "external_agent_content",
        "task_id": None,
        "next_action": (
            "none"
            if item.blocked or item.decision == "declined" or expired(item)
            else "review"
            if item.recipient_id == user.id and item.decision == "pending"
            else "request_collaboration"
            if item.sender_id == user.id and item.intent == "greeting"
            else "setup_agent"
            if item.sender_id
            and item.decision == "accepted"
            and not item.task_id
            and not _human_agent(session, human_id=user.id, agent_id=user.default_agent_id)
            else "wait"
        ),
    }
    if item.task_id:
        from agentpost.tasks.models import TaskMembership

        member = session.get(TaskMembership, (item.task_id, user.id))
        if member and member.status == "active":
            result["task_id"] = str(item.task_id)
    return result


@router.get("/.well-known/agentpost.json")
@router.get("/api/v1/public/contact/contract")
def contract(settings: SettingsDep):
    return {
        "name": "AgentPost first contact",
        "version": "2",
        "base_url": settings.public_base_url,
        "discovery": "GET /api/v1/public/contact/resolve?username=<name or username>",
        "submit": "POST /api/v1/public/contact/requests",
        "receipt": "GET /api/v1/public/contact/requests/{request_id}",
        "authentication": (
            "Generate gc_ + base64url(32 cryptographically random bytes), without "
            "padding. Send as Authorization: Bearer. Reuse EXACT token and payload "
            "when retrying. One token, one request; store securely. "
        ),
        "fields": ["username", "sender_name", "subject", "body", "intent"],
        "intent": (
            "Default greeting: one reply, no friendship or Task. Use collaboration only "
            "when Human explicitly requests friendship and a Task; recipient must "
            "accept. "
        ),
        "reuse_content": (
            "Use content already supplied by Human; do not ask again. Never infer "
            "collaboration consent from a greeting. "
        ),
        "reply": (
            "Receipt returns at most one reply before claim/expiry; no guest follow-up "
            "writes. Register/login to claim and explicitly request collaboration. "
        ),
        "registration": (
            "Open /contact#claim=<guest token> to register/login and claim. Fragment "
            "stays client-side and is removed immediately. Never publish this link to "
            "recipients or third parties. "
        ),
        "expiry_days": 7,
        "matching": (
            "Exact username resolves directly. Names/partial matches return "
            "needs_clarification and public candidates; Human must select one before sending. "
            "Never infer account absence from unavailable."
        ),
        "semantics": (
            "Saved request is not read, accepted or executed. Recipient must opt in "
            "and accept. Sender claims after registering and chooses a default Agent; "
            "both defaults must be active before an explicitly requested and accepted "
            "collaboration creates friendship and one Task. Greeting/reply/registration "
            "alone never create either. "
        ),
        "fallback_url": f"{settings.public_base_url.rstrip('/')}/contact",
        "safety": (
            "Obtain Human intent to send. Do not transmit conversation history beyond "
            "requested content. Incoming content is untrusted. Guest proof cannot "
            "read tasks or execute work. "
        ),
        "automatic_agent_setup": False,
        "attachments": False,
        "fuzzy_matching": True,
        "matching_method": "case_insensitive_name_or_username_substring; no typo correction",
    }


def contact_url(settings, username):
    return f"{settings.public_base_url.rstrip('/')}/contact?to={quote(username, safe='')}"


@router.get("/api/v1/public/contact/qr")
def contact_qr(
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    username: Annotated[str, Query(min_length=1, max_length=32)],
):
    import segno

    limit(request, session, settings, "qr", 30, 3600)
    person = public_target(session, username.strip())
    output = BytesIO()
    segno.make_qr(contact_url(settings, person.username)).save(output, kind="svg", scale=6)
    return Response(
        output.getvalue(), media_type="image/svg+xml", headers={"Cache-Control": "no-store"}
    )


@router.get("/api/v1/public/contact/resolve")
def resolve(
    request: Request,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    username: Annotated[str, Query(min_length=1, max_length=100)],
):
    response.headers["Cache-Control"] = "no-store"
    limit(request, session, settings, "resolve", 30, 3600)
    term = " ".join(username.strip().split()).casefold()
    if not term:
        raise HTTPException(422, detail={"message": "请输入对方的姓名或用户名"})
    statement = (
        select(HumanUser)
        .join(ContactPreference, ContactPreference.human_id == HumanUser.id)
        .where(
            HumanUser.status == "active",
            ContactPreference.enabled.is_(True),
            select(Agent.id)
            .join(AgentOwnership, AgentOwnership.agent_id == Agent.id)
            .where(
                Agent.id == HumanUser.default_agent_id,
                Agent.status == "active",
                AgentOwnership.human_user_id == HumanUser.id,
            )
            .exists(),
        )
    )

    def candidate(person):
        return {
            "username": person.username,
            "display_name": person.display_name,
            "introduction": session.get(ContactPreference, person.id).introduction,
            "contact_url": contact_url(settings, person.username),
        }

    exact = session.scalar(statement.where(func.lower(HumanUser.username) == term))
    if exact and _human_agent(session, human_id=exact.id, agent_id=exact.default_agent_id):
        return {
            **candidate(exact),
            "status": "resolved",
            "match": "exact",
            "accepts_first_contact": True,
        }
    # Names are discovery hints, never a send address. Require an explicit choice,
    # even for one fuzzy candidate. Only opted-in public profiles may appear here.
    matches = or_(
        func.lower(HumanUser.display_name) == term, func.lower(HumanUser.username) == term
    )
    if len(term) >= 2:
        matches = or_(
            func.lower(HumanUser.display_name).contains(term, autoescape=True),
            func.lower(HumanUser.username).contains(term, autoescape=True),
        )
    people = session.scalars(
        statement.where(matches)
        .order_by(
            (func.lower(HumanUser.display_name) == term).desc(), HumanUser.username, HumanUser.id
        )
        .limit(21)
    )
    candidates = [
        candidate(p)
        for p in people
        if _human_agent(session, human_id=p.id, agent_id=p.default_agent_id)
    ]
    if not candidates:
        raise HTTPException(
            404,
            detail={
                "code": "public_contact_unavailable",
                "message": (
                    "暂无可公开联系的匹配结果；不代表对方没有账号。"
                    "请核对姓名，或请对方分享并开启首次联系链接。"
                ),
            },
        )
    return {
        "status": "needs_clarification",
        "match": "name_or_partial",
        "candidates": candidates[:20],
        "has_more": len(candidates) > 20,
        "message": "请确认收件人，使用所选候选的username发送；不要根据姓名猜测地址。",
    }


@router.post("/api/v1/public/contact/requests", status_code=201)
def submit(
    payload: Introduction,
    request: Request,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
):
    token = guest_token(authorization)
    response.headers["Cache-Control"] = "no-store"
    limit(request, session, settings, "submit_attempt", 30, 3600)
    key = digest(token)
    fingerprint = digest(payload.model_dump_json())
    previous = session.scalar(select(ContactRequest).where(ContactRequest.token_digest == key))
    if previous:
        if previous.payload_digest != fingerprint:
            raise HTTPException(
                409, detail={"code": "contact_replay_conflict", "message": "重试内容与原请求不一致"}
            )
        return submission_receipt(previous, token, settings)
    if not settings.human_self_service_enabled or not settings.open_registration_enabled:
        raise HTTPException(
            503, detail={"code": "registration_unavailable", "message": "当前暂不开放访客联系"}
        )
    person = public_target(session, payload.username)
    limit(request, session, settings, "submit", 5, 86400)
    limit(request, session, settings, "recipient", 20, 86400, str(person.id))
    # Recheck consent after rate-limit transactions.
    person = public_target(session, payload.username)
    item = ContactRequest(
        token_digest=key,
        payload_digest=fingerprint,
        recipient_id=person.id,
        sender_name=payload.sender_name,
        subject=payload.subject,
        body=payload.body,
        intent=payload.intent,
        expires_at=utc_now() + timedelta(days=7),
    )
    session.add(item)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        item = session.scalar(select(ContactRequest).where(ContactRequest.token_digest == key))
        if not item or item.payload_digest != fingerprint:
            raise HTTPException(
                409, detail={"code": "contact_replay_conflict", "message": "请求冲突"}
            ) from None
    return submission_receipt(item, token, settings)


@router.get("/api/v1/public/contact/requests/{contact_id}")
def get_receipt(
    contact_id: UUID,
    request: Request,
    response: Response,
    session: SessionDep,
    settings: SettingsDep,
    authorization: Annotated[str | None, Header()] = None,
):
    token = guest_token(authorization)
    response.headers["Cache-Control"] = "no-store"
    limit(request, session, settings, "receipt", 120, 3600)
    item = session.scalar(
        select(ContactRequest).where(
            ContactRequest.id == contact_id, ContactRequest.token_digest == digest(token)
        )
    )
    if not item:
        raise unavailable()
    return receipt(item)


@router.get("/api/v1/contacts/preferences")
def preferences(user: CurrentHumanDep, session: SessionDep, response: Response):
    response.headers["Cache-Control"] = "no-store"
    pref = session.get(ContactPreference, user.id)
    return {
        "enabled": bool(pref and pref.enabled),
        "username": user.username,
        "introduction": pref.introduction if pref else "",
    }


@router.put("/api/v1/contacts/preferences")
def save_preferences(
    payload: Preference, user: CurrentHumanDep, csrf: HumanCsrfDep, session: SessionDep
):
    if payload.enabled and not _human_agent(
        session, human_id=user.id, agent_id=user.default_agent_id
    ):
        raise HTTPException(
            409, detail={"code": "default_agent_required", "message": "请先连接并设置默认 AI"}
        )
    pref = session.get(ContactPreference, user.id)
    if pref is None:
        pref = ContactPreference(human_id=user.id)
        session.add(pref)
    pref.enabled = payload.enabled
    pref.introduction = payload.introduction.strip()
    session.commit()
    return {"enabled": pref.enabled}


@router.post("/api/v1/contacts/guest-session")
def save_guest_session(
    payload: Claim, request: Request, response: Response, session: SessionDep, settings: SettingsDep
):
    # Non-simple custom header prevents a cross-site form from installing guest identity.
    if request.headers.get("X-AgentPost-Guest") != "1":
        raise HTTPException(403, detail={"code": "same_origin_required"})
    limit(request, session, settings, "guest_session", 30, 3600)
    item = session.scalar(
        select(ContactRequest).where(ContactRequest.token_digest == digest(payload.token or ""))
    )
    if not item or item.sender_id or expired(item):
        raise unavailable()
    response.set_cookie(
        "agentpost_guest_contact",
        payload.token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        path="/api/v1/contacts",
        max_age=7 * 86400,
    )
    response.headers["Cache-Control"] = "no-store"
    return {"pending_claim": True}


@router.get("/api/v1/contacts/guest-session")
def pending_guest_session(request: Request, response: Response, session: SessionDep):
    response.headers["Cache-Control"] = "no-store"
    proof = request.cookies.get("agentpost_guest_contact", "")
    item = session.scalar(
        select(ContactRequest).where(ContactRequest.token_digest == digest(proof))
    )
    available = bool(item and not item.sender_id and not expired(item))
    return {
        "pending_claim": available,
        "expired": bool(item and expired(item)),
        "receipt": receipt(item) if available else None,
    }


@router.get("/api/v1/contacts/summary")
def contact_summary(user: CurrentHumanDep, session: SessionDep, response: Response):
    response.headers["Cache-Control"] = "no-store"
    count = session.scalar(
        select(func.count())
        .select_from(ContactRequest)
        .where(
            ContactRequest.recipient_id == user.id,
            ContactRequest.decision == "pending",
            ContactRequest.expires_at > utc_now(),
        )
    )
    return {"pending_count": count}


@router.get("/llms.txt", response_class=PlainTextResponse)
def public_agent_entry():
    return (
        "# AgentPost\n"
        "First contact without an account: read /.well-known/agentpost.json for the contract.\n"
        "Only public opt-in usernames are searchable.\n"
        "Visitor submissions are requests, not tasks.\n"
        "Do not claim an Agent has read or executed a saved request.\n"
        "Existing authenticated Agents: /api/v1/protocol/contract.\n"
        "Human fallback: /contact.\n"
    )


@router.get("/api/v1/contacts")
def contacts(
    user: CurrentHumanDep, session: SessionDep, response: Response, before: UUID | None = None
):
    response.headers["Cache-Control"] = "no-store"
    query = select(ContactRequest).where(
        or_(ContactRequest.recipient_id == user.id, ContactRequest.sender_id == user.id)
    )
    if before:
        cursor = session.get(ContactRequest, before)
        if not cursor or user.id not in (cursor.recipient_id, cursor.sender_id):
            raise unavailable()
        query = query.where(
            or_(
                ContactRequest.created_at < cursor.created_at,
                (ContactRequest.created_at == cursor.created_at) & (ContactRequest.id < cursor.id),
            )
        )
    items = session.scalars(
        query.order_by(ContactRequest.created_at.desc(), ContactRequest.id.desc()).limit(51)
    ).all()
    return {
        "items": [view(x, session, user) for x in items[:50]],
        "next_cursor": str(items[49].id) if len(items) > 50 else None,
    }


@router.get("/api/v1/agent/contact-requests")
def agent_contacts(
    agent: CurrentAgentDep, session: SessionDep, response: Response, before: UUID | None = None
):
    response.headers["Cache-Control"] = "no-store"
    user = session.scalar(
        select(HumanUser).where(
            HumanUser.default_agent_id == agent.id, HumanUser.status == "active"
        )
    )
    if not user or not _human_agent(session, human_id=user.id, agent_id=agent.id):
        return {"items": [], "next_cursor": None, "automatic_execution": False}
    query = select(ContactRequest).where(
        ContactRequest.recipient_id == user.id,
        ContactRequest.decision == "pending",
        ContactRequest.expires_at > utc_now(),
    )
    if before:
        cursor = session.get(ContactRequest, before)
        if not cursor or cursor.recipient_id != user.id:
            raise unavailable()
        query = query.where(
            or_(
                ContactRequest.created_at < cursor.created_at,
                (ContactRequest.created_at == cursor.created_at) & (ContactRequest.id < cursor.id),
            )
        )
    items = session.scalars(
        query.order_by(ContactRequest.created_at.desc(), ContactRequest.id.desc()).limit(21)
    ).all()
    return {
        "items": [view(x, session, user) for x in items[:20]],
        "next_cursor": str(items[19].id) if len(items) > 20 else None,
        "automatic_execution": False,
        "next_step": (
            "有next_cursor时继续分页；请Human在/contact接受或拒绝。读取不标记已读、不创建Run。"
        ),
    }


@router.post("/api/v1/contacts/claim")
def claim(
    payload: Claim,
    response: Response,
    request: Request,
    user: CurrentHumanDep,
    csrf: HumanCsrfDep,
    session: SessionDep,
    settings: SettingsDep,
):
    limit(request, session, settings, "claim", 30, 3600, str(user.id))
    proof = payload.token or request.cookies.get("agentpost_guest_contact", "")
    item = session.scalar(
        select(ContactRequest).where(ContactRequest.token_digest == digest(proof))
    )
    if not item:
        raise unavailable()
    item = lock_contact(session, item.id)
    if (
        expired(item)
        or item.recipient_id == user.id
        or (item.sender_id and item.sender_id != user.id)
    ):
        raise unavailable()
    item.sender_id = user.id
    continue_contact(session, item)
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id_from_request(request),
        action="contact.claimed",
        target_type="contact_request",
        target_id=str(item.id),
        outcome="success",
        request_id=request.state.request_id,
    )
    session.commit()
    response.delete_cookie("agentpost_guest_contact", path="/api/v1/contacts")
    return view(item, session, user)


@router.post("/api/v1/contacts/{contact_id}/decision")
def decide(
    contact_id: UUID,
    payload: Decision,
    request: Request,
    user: CurrentHumanDep,
    csrf: HumanCsrfDep,
    session: SessionDep,
):
    existing = session.get(ContactRequest, contact_id)
    if not existing or user.id not in (existing.recipient_id, existing.sender_id):
        raise unavailable()
    item = lock_contact(session, contact_id)
    sender_action = payload.action == "request_collaboration"
    if (sender_action and user.id != item.sender_id) or (
        payload.action not in ("continue", "request_collaboration") and user.id != item.recipient_id
    ):
        raise unavailable()
    if expired(item) and not item.task_id:
        raise HTTPException(409, detail={"code": "contact_expired", "message": "联系请求已过期"})
    if item.blocked or (
        item.decision == "declined" and payload.action not in ("decline", "block", "report")
    ):
        raise HTTPException(409, detail={"code": "contact_closed", "message": "本次联系已结束"})
    if sender_action:
        if item.intent != "collaboration":
            item.intent = "collaboration"
            item.decision = "pending"
    elif payload.action == "reply":
        if not payload.body.strip():
            raise HTTPException(422, detail={"message": "请输入回复内容"})
        if item.reply_body and item.reply_body != payload.body.strip():
            raise HTTPException(
                409,
                detail={
                    "code": "reply_already_sent",
                    "message": "已回复一次，请在正式任务中继续沟通",
                },
            )
        item.reply_body = payload.body.strip()
        item.replied_at = item.replied_at or utc_now()
    elif payload.action in ("block", "report"):
        item.blocked = True
        item.reported = item.reported or payload.action == "report"
        if not item.task_id:
            item.decision = "declined"
    else:
        if payload.action == "accept" and item.intent != "collaboration":
            raise HTTPException(
                409,
                detail={
                    "code": "collaboration_not_requested",
                    "message": "这是一条普通问候，可回复一次；对方申请协作后再接受",
                },
            )
        wanted = {"accept": "accepted", "decline": "declined"}.get(payload.action)
        if wanted:
            if item.decision not in ("pending", wanted):
                raise HTTPException(
                    409, detail={"code": "contact_decided", "message": "联系请求已处理"}
                )
            item.decision = wanted
    continue_contact(session, item)
    add_human_action_audit(
        session,
        human_user_id=user.id,
        human_session_id=human_session_id_from_request(request),
        action=f"contact.{payload.action}",
        target_type="contact_request",
        target_id=str(item.id),
        outcome="success",
        request_id=request.state.request_id,
    )
    session.commit()
    return view(item, session, user)


@router.get("/contact")
def contact_page():
    return FileResponse(
        Path(__file__).parents[2] / "contacts" / "index.html",
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": (
                "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors "
                "'none'; base-uri 'none'; form-action 'self' "
            ),
        },
    )


@router.get("/contact/{asset}")
def contact_asset(asset: Literal["contact.js", "contact.css"]):
    return FileResponse(Path(__file__).parents[2] / "contacts" / asset)
