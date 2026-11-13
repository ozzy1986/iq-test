"""API сервиса IQ-тестов: прохождение → paywall → mock-оплата → результат.

Правильные ответы, подсчёт и проверка доступа — только на сервере. Идентификатор
прохождения (UUIDv4) служит ключом доступа к нему: аккаунтов в MVP нет.
"""
import re
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import scoring
from .db import SessionLocal, engine
from .models import Base, Event, Payment, Subscription, TestSession, aware, now
from .questions import BY_ID, CATEGORIES, QUESTIONS, public_questions

PLAN = {"id": "monthly", "title": "Подписка на месяц", "amount": 29900, "currency": "RUB", "period_days": 30}
CLIENT_EVENTS = {"landing_view", "paywall_view", "checkout_view"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="IQ test MVP", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json",
              redoc_url=None)


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


async def subscription_of(session_id: str, s: AsyncSession) -> Subscription | None:
    return (await s.execute(select(Subscription).where(Subscription.session_id == session_id))).scalar_one_or_none()


def has_access(sub: Subscription | None) -> bool:
    """Доступ открыт до конца оплаченного периода, даже если подписку уже отменили."""
    return sub is not None and aware(sub.current_period_end) > now()


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
        "status": ts.status,
        "questions": public_questions(),
        "answers": ts.answers,
        "plan": PLAN,
        "subscription": sub_view(sub),
        "access": has_access(sub),
        "email": ts.email,
    }
    if ts.status == "finished":
        # Превью для paywall: только то, что не раскрывает сам результат.
        out["preview"] = {
            "duration_sec": duration_sec(ts),
            "answered": len(ts.answers),
            "total": len(QUESTIONS),
            "categories": list(CATEGORIES.values()),
        }
    return out


def track(s: AsyncSession, name: str, session_id: str | None = None) -> None:
    s.add(Event(name=name, session_id=session_id))


@app.get("/api/health")
async def health(s: AsyncSession = Depends(db)):
    await s.execute(select(1))
    return {"status": "ok"}


@app.post("/api/sessions", status_code=201)
async def create_session(s: AsyncSession = Depends(db)):
    ts = TestSession(id=str(uuid.uuid4()), created_at=now(), status="started", answers={})
    s.add(ts)
    track(s, "quiz_start", ts.id)
    await s.commit()
    return state_view(ts, None)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str, s: AsyncSession = Depends(db)):
    ts = await load(session_id, s)
    return state_view(ts, await subscription_of(ts.id, s))


class AnswerIn(BaseModel):
    option: int = Field(ge=0, le=9)


@app.put("/api/sessions/{session_id}/answers/{question_id}")
async def put_answer(session_id: str, question_id: str, body: AnswerIn, s: AsyncSession = Depends(db)):
    question = BY_ID.get(question_id)
    if question is None or body.option >= len(question["options"]):
        raise HTTPException(422, "Нет такого вопроса или варианта")
    ts = await load(session_id, s, lock=True)
    if ts.status != "started":
        raise HTTPException(409, "Тест уже завершён")
    ts.answers = {**ts.answers, question_id: body.option}
    await s.commit()
    return {"answered": len(ts.answers), "total": len(QUESTIONS)}


@app.post("/api/sessions/{session_id}/finish")
async def finish(session_id: str, s: AsyncSession = Depends(db)):
    ts = await load(session_id, s, lock=True)
    if ts.status == "started":
        if len(ts.answers) < len(QUESTIONS):
            raise HTTPException(409, "Ответьте на все вопросы")
        result = scoring.score(ts.answers)
        ts.status = "finished"
        ts.finished_at = now()
        ts.score_raw, ts.score_max = result["score_raw"], result["score_max"]
        ts.iq, ts.percentile, ts.breakdown = result["iq"], result["percentile"], result["breakdown"]
        track(s, "quiz_finish", ts.id)
        await s.commit()
    return state_view(ts, await subscription_of(ts.id, s))  # результата здесь нет — он за paywall


class CheckoutIn(BaseModel):
    email: str = Field(max_length=254)


@app.post("/api/sessions/{session_id}/checkout")
async def checkout(session_id: str, body: CheckoutIn, s: AsyncSession = Depends(db)):
    """Имитация оплаты: платёжного провайдера нет, платёж сразу считается успешным."""
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "Проверьте адрес почты")
    ts = await load(session_id, s, lock=True)
    if ts.status != "finished":
        raise HTTPException(409, "Сначала завершите тест")
    sub = await subscription_of(ts.id, s)
    if not has_access(sub):  # повторный запрос не создаёт второй платёж
        period_end = now() + timedelta(days=PLAN["period_days"])
        s.add(Payment(session_id=ts.id, amount=PLAN["amount"], currency=PLAN["currency"], status="succeeded"))
        if sub is None:
            sub = Subscription(session_id=ts.id, plan=PLAN["id"], status="active", started_at=now(),
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
    sub = await subscription_of(ts.id, s)
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
    sub = await subscription_of(ts.id, s)
    if not has_access(sub):
        raise HTTPException(402, "Результат доступен по подписке")
    track(s, "result_view", ts.id)
    await s.commit()
    seconds = duration_sec(ts)
    return {
        "iq": ts.iq,
        "percentile": ts.percentile,
        "level": scoring.level_for(ts.iq),
        "correct": sum(c["correct"] for c in ts.breakdown.values()),
        "total": len(QUESTIONS),
        "duration_sec": seconds,
        "breakdown": [{"key": k, "title": CATEGORIES[k], **ts.breakdown[k]} for k in CATEGORIES],
        "insights": scoring.insights(ts.breakdown, seconds),
        "review": scoring.review(ts.answers),
        "subscription": sub_view(sub),
    }


class EventIn(BaseModel):
    name: str = Field(max_length=32)
    session_id: str | None = Field(default=None, max_length=36)


@app.post("/api/events", status_code=204)
async def post_event(body: EventIn, s: AsyncSession = Depends(db)):
    if body.name in CLIENT_EVENTS and (body.session_id is None or UUID_RE.match(body.session_id)):
        track(s, body.name, body.session_id)
        await s.commit()
