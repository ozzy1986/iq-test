"""Платёжный провайдер за абстракцией: API зависит от протокола, а не от реализации.

Сейчас подключена имитация. Чтобы принять настоящие платежи, достаточно написать
класс с тем же методом `charge` и вернуть его из `get_payment_provider`.
"""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Charge:
    provider: str
    succeeded: bool


class PaymentProvider(Protocol):
    async def charge(self, *, amount: int, currency: str, email: str, reference: str) -> Charge: ...


class MockProvider:
    """Имитация по ТЗ: карта не запрашивается, платёж всегда успешен."""

    async def charge(self, *, amount: int, currency: str, email: str, reference: str) -> Charge:
        return Charge(provider="mock", succeeded=True)


def get_payment_provider() -> PaymentProvider:
    return MockProvider()
