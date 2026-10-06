"""Headless mining strategies."""

from dataclasses import dataclass
try:
    from .quantum_backend import Layout, measure
except ImportError:  # Running the module directly from the repository root.
    from quantum_backend import Layout, measure


class Strategy:
    def choose(self, layout: Layout, available: tuple[int, ...] | None = None) -> int:
        raise NotImplementedError

    def choose_upgrade(self, state: object) -> str | None:
        return None


@dataclass(frozen=True)
class RandomStrategy(Strategy):
    def choose(self, layout: Layout, available: tuple[int, ...] | None = None) -> int:
        outcomes = measure(layout, use_aer=False)
        choices = available or tuple(range(layout.width))
        return choices[outcomes[0][0] % len(choices)]


@dataclass(frozen=True)
class GreedyStrategy(Strategy):
    def choose(self, layout: Layout, available: tuple[int, ...] | None = None) -> int:
        choices = available or tuple(range(layout.width))
        return min(choices)

    def choose_upgrade(self, state: object) -> str | None:
        prices = getattr(state, "prices", {})
        return min(prices, key=prices.get) if prices else None


@dataclass
class RoundRobinStrategy(Strategy):
    cursor: int = 0

    def choose(self, layout: Layout, available: tuple[int, ...] | None = None) -> int:
        choices = available or tuple(range(layout.width))
        choice = choices[self.cursor % len(choices)]
        self.cursor += 1
        return choice


class NoInspectorStrategy(GreedyStrategy):
    def choose_upgrade(self, state: object) -> str | None:
        return "speed"


class RandomUpgradeStrategy(RoundRobinStrategy):
    def choose_upgrade(self, state: object) -> str | None:
        return ("miner", "speed", "inspector")[self.cursor % 3]


NoInspector = NoInspectorStrategy
Greedy = GreedyStrategy
Random = RandomUpgradeStrategy
STRATEGIES = {
    "no_inspector": NoInspectorStrategy,
    "greedy": GreedyStrategy,
    "random": RandomUpgradeStrategy,
    "round_robin": RoundRobinStrategy,
}
