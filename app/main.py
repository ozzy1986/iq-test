"""API сервиса IQ-тестов: прохождение → paywall → mock-оплата → результат.

Правильные ответы, подсчёт и проверка доступа — только на сервере. Аккаунтов в MVP нет:
ключом служат случайные идентификаторы (UUIDv4) прохождения и профиля. Подписка
привязана к профилю и открывает отчёты по всем его прохождениям.
"""
import re
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import scoring
from .db import SessionLocal, engine
from .generator import CATEGORIES, MINUTES, TOTAL, build_test, public_questions
from .models import Base, Event, Payment, Subscription, TestSession, aware, now
from .payments import PaymentProvider, get_payment_provider
from .ratelimit import limit

PLAN = {"id": "monthly", "title": "Подписка на месяц", "amount": 29900, "currency": "RUB", "period_days": 30}
CLIENT_EVENTS = {"landing_view", "paywall_view", "checkout_view"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
MAX_BODY = 4096  # самое большое легитимное тело — email на оформлении


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="IQ test MVP", lifespan=lifespan, docs_url=None, redoc_url=None,
              openapi_url="/api/openapi.json")


@app.middleware("http")
async def reject_large_bodies(request, call_next):
    """Тела запросов крошечные; всё, что больше или без Content-Length, отбрасываем до чтения."""
    if request.method in ("POST", "PUT", "PATCH"):
        length = request.headers.get("content-length")
        if length is None and "transfer-encoding" in request.headers:
            return JSONResponse({"detail": "Нужен заголовок Content-Length"}, status_code=411)
        if length is not None and (not length.isdigit() or int(length) > MAX_BODY):
            return JSONResponse({"detail": "Слишком большой запрос"}, status_code=413)
    return await call_next(request)


async def db():
    async with SessionLocal() as session:
        yield session


async def load(session_id: str, s: AsyncSession, lock: bool = False) -> TestSession:
    if not UUID_RE.match(session_id):
        raise HTTPException(404, "Тест не найден")
    query = select(TestSession).where(TestSession.id == session_id)
    if lock:
        query = query.with_for_update()
    ts = (await s.execute(query)).scalar_one_or_none()
    if ts is None:
        raise HTTPException(404, "Тест не найден")
    return ts


async def subscription_of(profile_id: str, s: AsyncSession) -> Subscription | None:
    return (await s.execute(select(Subscription).where(Subscription.profile_id == profile_id))).scalar_one_or_none()


def has_access(sub: Subscription | None) -> bool:
    """Доступ открыт до конца оплаченного периода, даже если подписку уже отменили."""
    return sub is not None and aware(sub.current_period_end) > now()


def clean_email(value: str) -> str:
    email = value.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Проверьте адрес почты")
    return email


def sub_view(sub: Subscription | None) -> dict | None:
    if sub is None:
        return None
    return {
        "plan": sub.plan,
        "status": sub.status,
        "started_at": aware(sub.started_at).isoformat(),
        "current_period_end": aware(sub.current_period_end).isoformat(),
        "active": has_access(sub),
    }


def duration_sec(ts: TestSession) -> int:
    return int((aware(ts.finished_at) - aware(ts.created_at)).total_seconds())


def state_view(ts: TestSession, sub: Subscription | None) -> dict:
    out = {
        "id": ts.id,
        "profile_id": ts.profile_id,
        "status": ts.status,
        "questions": public_questions(ts.questions),
        "answers": ts.answers,
        "plan": PLAN,
        "subscription": sub_view(sub),
        "access": has_access(sub),
        "email": ts.email,
        "lead_email": ts.lead_email,
    }
    if ts.status == "finished":
        # Превью для paywall: только то, что не раскрывает сам результат.
        out["preview"] = {
            "duration_sec": duration_sec(ts),
            "answered": len(ts.answers),
            "total": len(ts.questions),
            "categories": list(CATEGORIES.values()),
        }
    return out


def track(s: AsyncSession, name: str, session_id: str | None = None) -> None:
    s.add(Event(name=name, session_id=session_id))


@app.get("/api/health")
async def health(s: AsyncSession = Depends(db)):
    await s.execute(select(1))
    return {"status": "ok"}


@app.get("/api/plan")
async def get_plan():
    """Тариф и размер теста — единственный источник цены и цифр для всех экранов."""
    return {"plan": PLAN, "questions": TOTAL, "minutes": MINUTES}


class CreateIn(BaseModel):
    profile_id: str | None = Field(default=None, max_length=36)


@app.post("/api/sessions", status_code=201, dependencies=[limit("create", 12)])
async def create_session(body: CreateIn | None = None, s: AsyncSession = Depends(db)):
    """Новое прохождение с заново сгенерированными заданиями. Профиль — тот же, если он передан."""
    profile_id = body.profile_id if body and body.profile_id and UUID_RE.match(body.profile_id) else str(uuid.uuid4())
    ts = TestSession(id=str(uuid.uuid4()), profile_id=profile_id, created_at=now(), status="started", answers={},
                     questions=build_test(secrets.randbits(64)))
    s.add(ts)
    track(s, "quiz_start", ts.id)
    await s.commit()
    return state_view(ts, await subscription_of(profile_id, s))


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, s: AsyncSession = Depends(db)):
    ts = await load(session_id, s)
    return state_view(ts, await subscription_of(ts.profile_id, s))


class AnswerIn(BaseModel):
    option: int = Field(ge=0, le=9)


@app.put("/api/sessions/{session_id}/answers/{question_id}", dependencies=[limit("answer", 240)])
async def put_answer(session_id: str, question_id: str, body: AnswerIn, s: AsyncSession = Depends(db)):
    ts = await load(session_id, s, lock=True)
    question = next((q for q in ts.questions if q["id"] == question_id), None)
    if question is None or body.option >= len(question["options"]):
        raise HTTPException(422, "Нет такого вопроса или варианта")
    if ts.status != "started":
        raise HTTPException(409, "Тест уже завершён")
    ts.answers = {**ts.answers, question_id: body.option}
    await s.commit()
    return {"answered": len(ts.answers), "total": len(ts.questions)}


@app.post("/api/sessions/{session_id}/finish")
async def finish(session_id: str, s: AsyncSession = Depends(db)):
    ts = await load(session_id, s, lock=True)
    if ts.status == "started":
        if len(ts.answers) < len(ts.questions):
            raise HTTPException(409, "Ответьте на все вопросы")
        result = scoring.score(ts.questions, ts.answers)
        ts.status = "finished"
        ts.finished_at = now()
        ts.correct, ts.breakdown = result["correct"], result["breakdown"]
        ts.iq, ts.iq_margin, ts.percentile = result["iq"], result["margin"], result["percentile"]
        track(s, "quiz_finish", ts.id)
        await s.commit()
    return state_view(ts, await subscription_of(ts.profile_id, s))  # результата здесь нет — он за paywall


class EmailIn(BaseModel):
    email: str = Field(max_length=254)


@app.post("/api/sessions/{session_id}/lead", dependencies=[limit("lead", 10)])
async def save_lead(session_id: str, body: EmailIn, s: AsyncSession = Depends(db)):
    """Человек не готов платить сейчас, но оставил почту — результат сохраняется за ним."""
    email = clean_email(body.email)
    ts = await load(session_id, s, lock=True)
    if ts.status != "finished":
        raise HTTPException(409, "Сначала завершите тест")
    if ts.lead_email != email:
        ts.lead_email = email
        track(s, "lead_captured", ts.id)
        await s.commit()
    return state_view(ts, await subscription_of(ts.profile_id, s))


@app.post("/api/sessions/{session_id}/checkout", dependencies=[limit("checkout", 10)])
async def checkout(session_id: str, body: EmailIn, s: AsyncSession = Depends(db),
                   provider: PaymentProvider = Depends(get_payment_provider)):
    """Оплата подписки. Провайдер сейчас — имитация (см. payments.py)."""
    email = clean_email(body.email)
    ts = await load(session_id, s, lock=True)
    if ts.status != "finished":
        raise HTTPException(409, "Сначала завершите тест")
    sub = await subscription_of(ts.profile_id, s)
    if not has_access(sub):  # повторный запрос не создаёт второй платёж
        charge = await provider.charge(amount=PLAN["amount"], currency=PLAN["currency"], email=email,
                                       reference=ts.id)
        s.add(Payment(session_id=ts.id, amount=PLAN["amount"], currency=PLAN["currency"],
                      provider=charge.provider, status="succeeded" if charge.succeeded else "failed"))
        if not charge.succeeded:
            await s.commit()  # неудачную попытку тоже сохраняем
            raise HTTPException(402, "Платёж не прошёл. Попробуйте ещё раз.")
        period_end = now() + timedelta(days=PLAN["period_days"])
        if sub is None:
            sub = Subscription(profile_id=ts.profile_id, plan=PLAN["id"], status="active", started_at=now(),
                               current_period_end=period_end)
            s.add(sub)
        else:
            sub.status, sub.started_at, sub.current_period_end, sub.canceled_at = "active", now(), period_end, None
        ts.email = email
        track(s, "payment_success", ts.id)
        await s.commit()
    return state_view(ts, sub)


@app.post("/api/sessions/{session_id}/subscription/cancel")
async def cancel_subscription(session_id: str, s: AsyncSession = Depends(db)):
    ts = await load(session_id, s, lock=True)
    sub = await subscription_of(ts.profile_id, s)
    if sub is None:
        raise HTTPException(404, "Подписки нет")
    if sub.status == "active":
        sub.status, sub.canceled_at = "canceled", now()
        track(s, "subscription_cancel", ts.id)
        await s.commit()
    return state_view(ts, sub)


@app.get("/api/sessions/{session_id}/result")
async def get_result(session_id: str, s: AsyncSession = Depends(db)):
    ts = await load(session_id, s)
    if ts.status != "finished":
        raise HTTPException(409, "Тест ещё не завершён")
    sub = await subscription_of(ts.profile_id, s)
    if not has_access(sub):
        raise HTTPException(402, "Результат доступен по подписке")
    attempts = (await s.execute(
        select(TestSession).where(TestSession.profile_id == ts.profile_id, TestSession.status == "finished")
        .order_by(TestSession.finished_at))).scalars().all()
    track(s, "result_view", ts.id)
    await s.commit()
    seconds = duration_sec(ts)
    return {
        "iq": ts.iq,
        "margin": ts.iq_margin,
        "percentile": ts.percentile,
        "level": scoring.level_for(ts.iq),
        "correct": ts.correct,
        "total": len(ts.questions),
        "duration_sec": seconds,
        "breakdown": [{"key": k, "title": CATEGORIES[k], **ts.breakdown[k]} for k in CATEGORIES],
        "insights": scoring.insights(ts.breakdown, seconds, len(ts.questions)),
        "review": scoring.review(ts.questions, ts.answers),
        # Динамика: все завершённые прохождения этого профиля — то, ради чего подписка продлевается.
        "history": [{"id": a.id, "finished_at": aware(a.finished_at).isoformat(), "iq": a.iq,
                     "current": a.id == ts.id} for a in attempts],
        "subscription": sub_view(sub),
    }


class EventIn(BaseModel):
    name: str = Field(max_length=32)
    session_id: str | None = Field(default=None, max_length=36)


@app.post("/api/events", status_code=204, dependencies=[limit("events", 60)])
async def post_event(body: EventIn, s: AsyncSession = Depends(db)):
    if body.name in CLIENT_EVENTS and (body.session_id is None or UUID_RE.match(body.session_id)):
        track(s, body.name, body.session_id)
        await s.commit()
