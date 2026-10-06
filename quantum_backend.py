"""Headless quantum-round backend with an optional Qiskit Aer accelerator.

The fallback is intentionally deterministic: the same :class:`Layout`,
``shots`` and :class:`NoiseConfig` always produce the same cached batch.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import random


@dataclass(frozen=True, slots=True, init=False)
class Layout:
    """Immutable description of one mining circuit.

    ``miner_speeds`` is a tuple (one value per continuous miner).  ``depth``
    is the circuit depth and ``inspectors`` is the number of inspector
    qubits.  ``width`` is retained as a compatibility alias for callers that
    used the original rectangular-grid API.
    """

    miner_speeds: tuple[float, ...]
    depth: int
    inspectors: int

    def __init__(
        self,
        width: int | None = None,
        depth: int = 1,
        inspectors: int = 1,
        *,
        miner_speeds: tuple[float, ...] | list[float] | None = None,
        speeds: tuple[float, ...] | list[float] | None = None,
    ) -> None:
        values = miner_speeds if miner_speeds is not None else speeds
        if values is None:
            if width is None:
                raise TypeError("provide miner_speeds or width")
            values = (1.0,) * width
        values = tuple(float(value) for value in values)
        if not values or any(value <= 0 for value in values):
            raise ValueError("miner_speeds must contain positive values")
        if depth < 1 or inspectors < 0:
            raise ValueError("depth must be positive and inspectors non-negative")
        object.__setattr__(self, "miner_speeds", values)
        object.__setattr__(self, "depth", int(depth))
        object.__setattr__(self, "inspectors", int(inspectors))

    @property
    def width(self) -> int:
        return len(self.miner_speeds)

    @property
    def qubits(self) -> int:
        return self.width + self.inspectors

    @property
    def two_qubit_gates(self) -> int:
        return self.width * self.inspectors

    @property
    def cache_key(self) -> tuple[tuple[float, ...], int, int]:
        return (self.miner_speeds, self.depth, self.inspectors)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "qubits": self.qubits,
            "depth": self.depth,
            "two_qubit_gates": self.two_qubit_gates,
        }


@dataclass(frozen=True, slots=True)
class NoiseConfig:
    """Optional noise probabilities and deterministic simulator seed."""

    bit_flip: float = 0.0
    phase_flip: float = 0.0
    depolarizing: float = 0.0
    seed: int = 0

    def __post_init__(self) -> None:
        if any(not 0 <= value <= 1 for value in (self.bit_flip, self.phase_flip, self.depolarizing)):
            raise ValueError("noise probabilities must be between 0 and 1")


Outcome = tuple[int, bool]


def _fallback(layout: Layout, shots: int, noise: NoiseConfig) -> tuple[tuple[Outcome, ...], ...]:
    rng = random.Random(hash((layout.cache_key, noise.seed)) & ((1 << 64) - 1))
    batch = []
    for _ in range(shots):
        row = []
        for speed in layout.miner_speeds:
            data_bit = int(rng.random() < speed / (speed + 1.0))
            if rng.random() < max(noise.bit_flip, noise.depolarizing):
                data_bit ^= 1
            inspector_flag = bool(layout.inspectors and rng.randrange(layout.inspectors) == 0)
            row.append((data_bit, inspector_flag))
        batch.append(tuple(row))
    return tuple(batch)


def _aer_batch(layout: Layout, shots: int, noise: NoiseConfig) -> tuple[tuple[Outcome, ...], ...] | None:
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator
    except ImportError:
        return None
    circuit = QuantumCircuit(layout.qubits, layout.qubits)
    for qubit in range(layout.qubits):
        circuit.h(qubit)
    for miner in range(layout.width):
        for inspector in range(layout.inspectors):
            circuit.cx(miner, layout.width + inspector)
    circuit.measure(range(layout.qubits), range(layout.qubits))
    backend = AerSimulator(seed_simulator=noise.seed)
    counts = backend.run(transpile(circuit, backend), shots=shots).result().get_counts()
    rows: list[tuple[Outcome, ...]] = []
    for bits, count in sorted(counts.items()):
        value = bits.replace(" ", "")[::-1]
        outcome = tuple(
            (int(value[index]), bool(any(int(value[layout.width + j]) for j in range(layout.inspectors))))
            for index in range(layout.width)
        )
        rows.extend([outcome] * count)
    return tuple(rows)


@lru_cache(maxsize=256)
def _cached_batch(layout: Layout, shots: int, noise: NoiseConfig, use_aer: bool) -> tuple[tuple[Outcome, ...], ...]:
    if use_aer:
        result = _aer_batch(layout, shots, noise)
        if result is not None:
            return result
    return _fallback(layout, shots, noise)


def run_batch(layout: Layout, shots: int = 1, noise: NoiseConfig | None = None, *, use_aer: bool = True) -> tuple[tuple[Outcome, ...], ...]:
    """Return cached per-shot, per-miner ``(data_bit, inspector_flag)`` rows."""
    if shots < 1:
        raise ValueError("shots must be positive")
    return _cached_batch(layout, shots, noise or NoiseConfig(), use_aer)


def measure(layout: Layout, noise: NoiseConfig | None = None, *, use_aer: bool = True) -> tuple[Outcome, ...]:
    """Return one per-miner outcome from the cached batch."""
    return run_batch(layout, 1, noise, use_aer=use_aer)[0]


batch_for_layout = run_batch
one_shot = measure
NoiseModelConfig = NoiseConfig


def clear_cache() -> None:
    _cached_batch.cache_clear()


__all__ = ["Layout", "NoiseConfig", "Outcome", "run_batch", "batch_for_layout", "measure", "one_shot", "clear_cache"]
