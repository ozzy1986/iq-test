"""Схема данных: прохождение теста, mock-платёж, подписка, события воронки."""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime | None) -> datetime | None:
    """SQLite теряет tzinfo — считаем, что в базе всегда UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class Base(DeclarativeBase):
    pass


class TestSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default="started")  # started | finished
    answers: Mapped[dict] = mapped_column(JSON, default=dict)  # {question_id: option_index}
    score_raw: Mapped[int | None] = mapped_column(Integer)
    score_max: Mapped[int | None] = mapped_column(Integer)
    iq: Mapped[int | None] = mapped_column(Integer)
    percentile: Mapped[int | None] = mapped_column(Integer)
    breakdown: Mapped[dict | None] = mapped_column(JSON)
    email: Mapped[str | None] = mapped_column(String(254))


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    amount: Mapped[int] = mapped_column(Integer)  # в копейках
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    provider: Mapped[str] = mapped_column(String(16), default="mock")
    status: Mapped[str] = mapped_column(String(16))  # succeeded


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), unique=True)
    plan: Mapped[str] = mapped_column(String(16), default="monthly")
    status: Mapped[str] = mapped_column(String(16))  # active | canceled
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Event(Base):
    """Шаги воронки — чтобы считать конверсию между экранами."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(32), index=True)
