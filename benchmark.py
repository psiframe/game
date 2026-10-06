"""Headless benchmark runner for comparing mining strategies."""

from dataclasses import dataclass
from time import perf_counter
try:
    from .quantum_backend import Layout
    from .strategies import Strategy, RandomStrategy
except ImportError:
    from quantum_backend import Layout
    from strategies import Strategy, RandomStrategy


@dataclass(frozen=True)
class BenchmarkResult:
    strategy: str
    rounds: int
    hits: int
    elapsed: float
    round_trips: int = 0
    inspections: int = 0
    throughput: float = 0.0
    efficiency: float = 0.0

    @property
    def hit_rate(self) -> float:
        return self.hits / self.rounds if self.rounds else 0.0


def run_benchmark(strategy: Strategy | None = None, *, layout: Layout = Layout(4, 4), rounds: int = 100) -> BenchmarkResult:
    if rounds < 0:
        raise ValueError("rounds must be non-negative")
    strategy = strategy or RandomStrategy()
    start = perf_counter()
    hits = sum(1 for _ in range(rounds) if strategy.choose(layout) == 0)
    elapsed = perf_counter() - start
    return BenchmarkResult(type(strategy).__name__, rounds, hits, elapsed,
                           round_trips=rounds, inspections=rounds * layout.inspectors,
                           throughput=hits / elapsed if elapsed else float("inf"),
                           efficiency=hits / rounds if rounds else 0.0)


def benchmark_table(results: list[BenchmarkResult]) -> list[dict[str, object]]:
    return [{"strategy": r.strategy, "rounds": r.rounds, "hits": r.hits,
             "hit_rate": r.hit_rate, "elapsed": r.elapsed,
             "round_trips": r.round_trips, "inspections": r.inspections,
             "throughput": r.throughput, "efficiency": r.efficiency} for r in results]


if __name__ == "__main__":
    layout = Layout(miner_speeds=(1.0, 1.0), depth=2, inspectors=1)
    results = [
        run_benchmark(strategy(), layout=layout, rounds=1000)
        for strategy in (RandomStrategy,)
    ]
    for row in benchmark_table(results):
        print(
            f"{row['strategy']}: rounds={row['rounds']} hits={row['hits']} "
            f"hit_rate={row['hit_rate']:.1%} runtime={row['elapsed']:.4f}s"
        )
