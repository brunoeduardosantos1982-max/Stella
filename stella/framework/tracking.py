"""TrackerProtocol — contrato estrutural para trackers de uso.

UsageTracker real (infra/usage_tracker.py) e FakeTracker (testing/fakes.py)
implementam este Protocol. Framework tipa contra ele para evitar acoplamento
com implementacao concreta.
"""

from __future__ import annotations

from typing import Protocol

from stella.infra.usage_tracker import UsageRecord


class TrackerProtocol(Protocol):
    """Contrato minimo de tracker de uso (estrutural — duck typing)."""

    def record(self, record: UsageRecord) -> None: ...
