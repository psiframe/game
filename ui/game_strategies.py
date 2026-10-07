"""Automatic players compared against the human on the end screen.

Each strategy is called about once per second of game time and may buy
upgrades through ``mine.buy``, exactly like a player pressing M, S or I.
"""


def _grow(mine):
    """Buy the cheaper of a miner or a speed upgrade, if affordable."""
    mine.buy(min(("miner", "speed"), key=mine.price))


class NoInspectors:
    name = "Baseline: no inspectors"

    def decide(self, mine):
        _grow(mine)


class AlwaysInspect:
    name = "Always inspect"

    def decide(self, mine):
        if not all(mine.inspectors):
            mine.buy("inspector")
            return
        _grow(mine)


class InspectWhenRisky:
    """Protect only once speed has pushed the error rate past a threshold."""

    def __init__(self, threshold=0.15):
        self.threshold = threshold
        self.name = f"Inspect when error >= {threshold:.0%}"

    def decide(self, mine):
        if mine.error >= self.threshold and not all(mine.inspectors):
            mine.buy("inspector")
            return
        _grow(mine)


def all_strategies():
    return [NoInspectors(), AlwaysInspect(), InspectWhenRisky()]
