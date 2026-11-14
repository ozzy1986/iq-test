"""Калибровка сложности заданий по накопленным ответам.

Сложности заданы экспертно (пять уровней), поэтому шкала может быть сдвинута: если задания
на деле легче, чем предполагалось, все получают завышенный IQ. Калибровка это исправляет:
для каждого типа задания берётся реальная доля решивших и подбирается такая сложность,
при которой модель предсказывает именно эту долю.

Запуск: python -m app.calibrate            (на сервере — раз в сутки, см. deploy/calibrate.sh)

Допущение: участники теста распределены как N(0, 1). Аудитория сайта — не срез населения,
поэтому после калибровки результат означает «место среди прошедших этот тест».
"""
import argparse
import asyncio
import math
from collections import defaultdict

from sqlalchemy import select

from .db import SessionLocal, engine
from .models import Base, Calibration, TestSession, aware, now
from .scoring import DIFFICULTY, DISCRIMINATION, GRID

MIN_RESPONSES = 30  # меньше — данных мало, оставляем экспертную оценку
PRIOR_WEIGHT = 30  # экспертная оценка весит как столько же ответов: сглаживает малые выборки
MIN_SECONDS = 120  # быстрее 30 заданий не решить — это клики наугад, в расчёт не берём
LIMIT = 3.5

WEIGHTS = [math.exp(-t * t / 2) for t in GRID]
TOTAL_WEIGHT = sum(WEIGHTS)


def expected_pass_rate(b: float, guess: float) -> float:
    """Какая доля участников N(0, 1) решит задание сложности b (с учётом угадывания)."""
    solved = sum(w * (guess + (1 - guess) / (1 + math.exp(-DISCRIMINATION * (t - b)))) for t, w in zip(GRID, WEIGHTS))
    return solved / TOTAL_WEIGHT


def difficulty_from_pass_rate(rate: float, guess: float) -> float:
    """Обратная задача: сложность, при которой ожидаемая доля решивших равна наблюдаемой."""
    low, high = -LIMIT, LIMIT
    for _ in range(40):  # доля решивших монотонно падает с ростом сложности — делим отрезок пополам
        middle = (low + high) / 2
        if expected_pass_rate(middle, guess) > rate:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def collect(sessions: list[tuple[list[dict], dict]]) -> dict[str, dict]:
    """Сводка по типам заданий: сколько раз встречалось, сколько раз решено."""
    stats: dict[str, dict] = defaultdict(lambda: {"total": 0, "correct": 0, "guess": 0.0, "prior": 0.0})
    for questions, answers in sessions:
        for q in questions:
            if "kind" not in q:
                continue
            row = stats[q["kind"]]
            row["total"] += 1
            row["correct"] += answers.get(q["id"]) == q["correct"]
            row["guess"] += 1 / len(q["options"])
            row["prior"] = DIFFICULTY[q["difficulty"]]
    return stats


def calibrate(stats: dict[str, dict]) -> dict[str, dict]:
    """Новые сложности для типов заданий, по которым набралось достаточно ответов."""
    out = {}
    for kind, row in stats.items():
        n = row["total"]
        if n < MIN_RESPONSES:
            continue
        rate = row["correct"] / n
        observed = difficulty_from_pass_rate(rate, row["guess"] / n)
        blended = (n * observed + PRIOR_WEIGHT * row["prior"]) / (n + PRIOR_WEIGHT)
        out[kind] = {"difficulty": round(blended, 3), "responses": n, "pass_rate": round(rate, 4),
                     "prior": row["prior"]}
    return out


async def run(min_seconds: int = MIN_SECONDS) -> dict[str, dict]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        finished = (await s.execute(select(TestSession).where(TestSession.status == "finished"))).scalars().all()
        honest = [(t.questions, t.answers) for t in finished
                  if (aware(t.finished_at) - aware(t.created_at)).total_seconds() >= min_seconds]
        result = calibrate(collect(honest))
        existing = {c.kind: c for c in (await s.execute(select(Calibration))).scalars()}
        for kind, row in result.items():
            record = existing.get(kind) or Calibration(kind=kind)
            record.difficulty, record.responses, record.pass_rate = row["difficulty"], row["responses"], row["pass_rate"]
            record.updated_at = now()
            s.add(record)
        await s.commit()
    await engine.dispose()
    print(f"прохождений: {len(finished)}, из них в расчёте: {len(honest)}, откалибровано типов: {len(result)}")
    for kind, row in sorted(result.items()):
        print(f"  {kind:28} n={row['responses']:<6} решили {row['pass_rate']:.0%}   "
              f"сложность {row['prior']:+.1f} → {row['difficulty']:+.2f}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--min-seconds", type=int, default=MIN_SECONDS,
                        help="не учитывать прохождения быстрее этого времени")
    asyncio.run(run(parser.parse_args().min_seconds))
