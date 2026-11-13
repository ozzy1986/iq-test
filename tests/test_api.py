"""Сквозной сценарий воронки на временной SQLite-базе."""
import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db").replace("\\", "/")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.questions import QUESTIONS  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def start(client, answers="correct"):
    sid = client.post("/api/sessions").json()["id"]
    for q in QUESTIONS:
        option = q["correct"] if answers == "correct" else (q["correct"] + 1) % len(q["options"])
        assert client.put(f"/api/sessions/{sid}/answers/{q['id']}", json={"option": option}).status_code == 200
    return sid


def test_questions_do_not_leak_answers(client):
    body = client.post("/api/sessions").json()
    assert len(body["questions"]) == 12
    for q in body["questions"]:
        assert not {"correct", "explain", "difficulty", "cat"} & q.keys()


def test_cannot_finish_until_all_answered(client):
    sid = client.post("/api/sessions").json()["id"]
    client.put(f"/api/sessions/{sid}/answers/n1", json={"option": 0})
    assert client.post(f"/api/sessions/{sid}/finish").status_code == 409


def test_full_funnel(client):
    sid = start(client)
    finished = client.post(f"/api/sessions/{sid}/finish").json()
    assert finished["status"] == "finished" and finished["access"] is False
    assert "iq" not in str(finished)  # до оплаты результат не уходит на клиент
    assert finished["preview"]["answered"] == 12

    assert client.get(f"/api/sessions/{sid}/result").status_code == 402
    assert client.put(f"/api/sessions/{sid}/answers/n1", json={"option": 0}).status_code == 409
    assert client.post(f"/api/sessions/{sid}/checkout", json={"email": "not-an-email"}).status_code == 422

    paid = client.post(f"/api/sessions/{sid}/checkout", json={"email": " User@Example.com "}).json()
    assert paid["access"] is True and paid["subscription"]["status"] == "active"
    assert paid["email"] == "user@example.com"
    client.post(f"/api/sessions/{sid}/checkout", json={"email": "user@example.com"})  # идемпотентно

    result = client.get(f"/api/sessions/{sid}/result").json()
    assert result["iq"] == 140 and result["percentile"] == 99 and result["correct"] == 12
    assert len(result["review"]) == 12 and all(r["is_correct"] for r in result["review"])

    canceled = client.post(f"/api/sessions/{sid}/subscription/cancel").json()
    assert canceled["subscription"]["status"] == "canceled"
    assert canceled["access"] is True  # доступ сохраняется до конца оплаченного периода
    assert client.get(f"/api/sessions/{sid}/result").status_code == 200


def test_all_wrong_gives_floor(client):
    sid = start(client, answers="wrong")
    client.post(f"/api/sessions/{sid}/finish")
    client.post(f"/api/sessions/{sid}/checkout", json={"email": "a@b.ru"})
    result = client.get(f"/api/sessions/{sid}/result").json()
    assert result["iq"] == 72 and result["correct"] == 0
    assert result["level"]["title"] == "Ниже среднего"


def test_unknown_session_and_bad_input(client):
    assert client.get("/api/sessions/nope").status_code == 404
    assert client.get("/api/sessions/00000000-0000-4000-8000-000000000000").status_code == 404
    sid = client.post("/api/sessions").json()["id"]
    assert client.put(f"/api/sessions/{sid}/answers/zzz", json={"option": 0}).status_code == 422
    assert client.put(f"/api/sessions/{sid}/answers/n1", json={"option": 7}).status_code == 422
    assert client.post("/api/events", json={"name": "landing_view"}).status_code == 204
    assert client.get("/api/health").json() == {"status": "ok"}
