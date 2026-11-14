"""Сквозной сценарий воронки на временной SQLite-базе."""
import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db").replace("\\", "/")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import main  # noqa: E402
from app.generator import TOTAL, build_test  # noqa: E402
from app.main import app  # noqa: E402
from app.payments import Charge, get_payment_provider  # noqa: E402
from app.ratelimit import limiter  # noqa: E402

SEED = 42
QUESTIONS = build_test(SEED)  # с фиксированным seed тест знает верные ответы


@pytest.fixture(autouse=True)
def deterministic(monkeypatch):
    limiter.reset()
    monkeypatch.setattr(main.secrets, "randbits", lambda _: SEED)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def start(client, answers="correct", profile=None):
    body = client.post("/api/sessions", json={"profile_id": profile}).json()
    for q in QUESTIONS:
        option = q["correct"] if answers == "correct" else (q["correct"] + 1) % len(q["options"])
        assert client.put(f"/api/sessions/{body['id']}/answers/{q['id']}", json={"option": option}).status_code == 200
    return body["id"], body["profile_id"]


def test_questions_do_not_leak_answers(client):
    body = client.post("/api/sessions").json()
    assert len(body["questions"]) == TOTAL == 30
    for q in body["questions"]:
        assert not {"correct", "explain", "difficulty", "cat"} & q.keys()


def test_each_attempt_gets_new_questions(client, monkeypatch):
    monkeypatch.undo()  # настоящая случайность
    first, second = (client.post("/api/sessions").json()["questions"] for _ in range(2))
    assert first != second


def test_cannot_finish_until_all_answered(client):
    sid = client.post("/api/sessions").json()["id"]
    client.put(f"/api/sessions/{sid}/answers/q1", json={"option": 0})
    assert client.post(f"/api/sessions/{sid}/finish").status_code == 409


def test_full_funnel(client):
    sid, _ = start(client)
    finished = client.post(f"/api/sessions/{sid}/finish").json()
    assert finished["status"] == "finished" and finished["access"] is False
    assert "iq" not in str(finished)  # до оплаты результат не уходит на клиент
    assert finished["preview"]["answered"] == 30

    assert client.get(f"/api/sessions/{sid}/result").status_code == 402
    assert client.put(f"/api/sessions/{sid}/answers/q1", json={"option": 0}).status_code == 409
    assert client.post(f"/api/sessions/{sid}/checkout", json={"email": "not-an-email"}).status_code == 422

    paid = client.post(f"/api/sessions/{sid}/checkout", json={"email": " User@Example.com "}).json()
    assert finished["offer"] == {"trial": True, "amount": 2900, "days": 7}
    assert paid["access"] is True and paid["subscription"]["status"] == "active"
    assert paid["subscription"]["trial"] is True  # первая оплата — пробные 7 дней за 29 ₽
    assert paid["offer"]["trial"] is False  # второй раз пробный период не предлагается
    assert paid["email"] == "user@example.com"
    client.post(f"/api/sessions/{sid}/checkout", json={"email": "user@example.com"})  # идемпотентно

    result = client.get(f"/api/sessions/{sid}/result").json()
    assert result["iq"] >= 135 and result["percentile"] == 99 and result["correct"] == 30
    assert 3 <= result["margin"] <= 10
    assert len(result["review"]) == 30 and all(r["is_correct"] for r in result["review"])
    assert [h["current"] for h in result["history"]] == [True]

    canceled = client.post(f"/api/sessions/{sid}/subscription/cancel").json()
    assert canceled["subscription"]["status"] == "canceled"
    assert canceled["access"] is True  # доступ сохраняется до конца оплаченного периода
    assert client.get(f"/api/sessions/{sid}/result").status_code == 200


def test_subscription_covers_retakes_and_keeps_history(client):
    first, profile = start(client)
    client.post(f"/api/sessions/{first}/finish")
    client.post(f"/api/sessions/{first}/checkout", json={"email": "a@b.ru"})

    second, same_profile = start(client, answers="wrong", profile=profile)
    assert same_profile == profile
    assert client.post(f"/api/sessions/{second}/finish").json()["access"] is True  # paywall не показывается
    history = client.get(f"/api/sessions/{second}/result").json()["history"]
    assert [h["id"] for h in history] == [first, second] and history[0]["iq"] > history[1]["iq"]

    stranger, other_profile = start(client)  # чужой профиль подписку не получает
    assert other_profile != profile
    assert client.post(f"/api/sessions/{stranger}/finish").json()["access"] is False


def test_lead_email_is_saved_without_payment(client):
    sid, _ = start(client)
    assert client.post(f"/api/sessions/{sid}/lead", json={"email": "lead@b.ru"}).status_code == 409
    client.post(f"/api/sessions/{sid}/finish")
    assert client.post(f"/api/sessions/{sid}/lead", json={"email": "bad"}).status_code == 422
    saved = client.post(f"/api/sessions/{sid}/lead", json={"email": "Lead@B.ru"}).json()
    assert saved["lead_email"] == "lead@b.ru" and saved["access"] is False


def test_all_wrong_gives_low_score(client):
    sid, _ = start(client, answers="wrong")
    client.post(f"/api/sessions/{sid}/finish")
    client.post(f"/api/sessions/{sid}/checkout", json={"email": "a@b.ru"})
    result = client.get(f"/api/sessions/{sid}/result").json()
    assert result["iq"] < 70 and result["correct"] == 0
    assert result["level"]["title"] == "Ниже среднего"


def test_unknown_session_and_bad_input(client):
    assert client.get("/api/sessions/nope").status_code == 404
    assert client.get("/api/sessions/00000000-0000-4000-8000-000000000000").status_code == 404
    sid = client.post("/api/sessions").json()["id"]
    assert client.put(f"/api/sessions/{sid}/answers/zzz", json={"option": 0}).status_code == 422
    assert client.put(f"/api/sessions/{sid}/answers/q1", json={"option": 9}).status_code == 422
    assert client.post("/api/events", json={"name": "landing_view"}).status_code == 204
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.post("/api/sessions", json={"profile_id": "garbage"}).json()["profile_id"] != "garbage"


def test_plan_is_public(client):
    body = client.get("/api/plan").json()
    assert body["plan"]["trial_amount"] == 2900 and body["plan"]["trial_days"] == 7
    assert body["plan"]["amount"] == 39900 and body["questions"] == 30 and body["minutes"] > 0


def test_declined_payment_keeps_paywall(client):
    class Declining:
        async def charge(self, **_):
            return Charge(provider="test", succeeded=False)

    sid, _ = start(client)
    client.post(f"/api/sessions/{sid}/finish")
    app.dependency_overrides[get_payment_provider] = Declining
    try:
        assert client.post(f"/api/sessions/{sid}/checkout", json={"email": "a@b.ru"}).status_code == 402
    finally:
        app.dependency_overrides.clear()
    assert client.get(f"/api/sessions/{sid}").json()["access"] is False
    assert client.get(f"/api/sessions/{sid}/result").status_code == 402


def test_rate_limit_on_session_creation(client):
    codes = [client.post("/api/sessions").status_code for _ in range(14)]
    assert codes[:12] == [201] * 12 and codes[12:] == [429, 429]
    assert "Retry-After" in client.post("/api/sessions").headers


def test_oversized_body_is_rejected(client):
    huge = {"name": "landing_view", "session_id": None, "pad": "x" * 10_000}
    assert client.post("/api/events", json=huge).status_code == 413
