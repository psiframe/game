"""Upgrade prices and economy helpers."""
from dataclasses import dataclass

UPGRADES = {
    "miner": (40, 65, 100, 150, 220),
    "speed": (25, 40, 70, 110, 160),
    "inspector": (35, 60, 100, 160, 240),
    "capacity": (20, 35, 55, 85, 125),
}
UPGRADE_PRICES = UPGRADES


@dataclass
class Economy:
    """Mutable wallet and upgrade levels for a continuous mining run."""

    credits: int = 0
    levels: dict[str, int] | None = None

    def __post_init__(self) -> None:
        self.levels = dict(self.levels or {})

    def buy(self, upgrade: str) -> int:
        level = self.levels.get(upgrade, 0)
        price = upgrade_price(upgrade, level)
        if self.credits < price:
            raise ValueError("insufficient credits")
        self.credits -= price
        self.levels[upgrade] = level + 1
        return price


def upgrade_price(upgrade: str, level: int) -> int:
    """Return the price for a zero-based level, or raise for invalid input."""
    if upgrade not in UPGRADES or level < 0:
        raise ValueError(f"unknown upgrade or level: {upgrade!r}, {level}")
    prices = UPGRADES[upgrade]
    return prices[level] if level < len(prices) else prices[-1] + prices[-1] // 2 * (level - len(prices) + 1)
