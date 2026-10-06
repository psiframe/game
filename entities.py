"""Serializable game entities used by headless and UI clients."""

from dataclasses import dataclass


@dataclass(slots=True)
class Miner:
    position: int = 0
    capacity: int = 10
    load: int = 0
    speed: float = 1.0
    round_trips: int = 0
    distance: float = 0.0

    def mine(self, amount: int = 1) -> int:
        collected = max(0, min(amount, self.capacity - self.load))
        self.load += collected
        return collected

    def unload(self) -> int:
        amount, self.load = self.load, 0
        return amount

    def tick(self, seconds: float, route_length: float = 1.0) -> bool:
        """Advance a continuous round trip; return true when one completes."""
        if seconds < 0 or route_length <= 0:
            raise ValueError("seconds must be non-negative and route_length positive")
        self.distance += seconds * self.speed
        completed = self.distance >= route_length
        if completed:
            self.distance %= route_length
            self.round_trips += 1
        return completed


@dataclass(slots=True)
class Inspector:
    position: int = 0
    level: int = 1
    observations: int = 0

    def inspect(self, outcome: bool | None = None) -> bool:
        self.observations += 1
        return bool(outcome) if outcome is not None else True


@dataclass(slots=True)
class Storage:
    capacity: int = 100
    amount: int = 0
    total_stored: int = 0

    def deposit(self, amount: int) -> int:
        accepted = max(0, min(amount, self.capacity - self.amount))
        self.amount += accepted
        self.total_stored += accepted
        return accepted

    def withdraw(self, amount: int) -> int:
        removed = max(0, min(amount, self.amount))
        self.amount -= removed
        return removed
