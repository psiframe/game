# Quantum Mine

## Setup and run

Install the dependencies from the repository root:

```text
pip install -r requirements.txt
```

Start the Pygame prototype:

```text
python ui\main.py
```

The game currently uses the deterministic fallback backend when Qiskit Aer is
not installed. Aer is optional while the quantum circuit is being developed.

## Controls

- Click `PLAY` to enter the mine.
- Press `1`-`9` or click a miner to select it.
- `M` adds a miner.
- `S` increases the selected miner's speed.
- `I` buys one inspector for the selected miner.

## Quantum mapping

Each miner is represented by one data qubit. Its speed is the number of
repeated `X`/`X` gate layers. Ideally the pair cancels and measures `0`.
Noise can produce a measured `1`, which represents a rock mined by mistake.
An inspector adds a toy ancilla parity check. A flagged load is rejected, but
the inspector does not prevent the underlying error.

The current documented fallback noise configuration is:

- `bit_flip=0.025`
- `depolarizing=0.01`
- deterministic seed `7`

The backend runs a cached batch of 1000 shots per layout and serves one
per-miner outcome per mining action. It never runs a circuit once per frame.

## Simplifications

This is an educational toy model, not a physical hardware model. It uses one
bit-flip-like error type, simplified readout/inspection behavior, and one
ancilla per protected miner. The fallback simulator is deterministic and is
used when Aer is unavailable. Real Aer circuit construction can be enabled by
installing the optional Qiskit packages.

## Benchmark

The headless benchmark module is available from the repository root:

```text
python benchmark.py
```

It is designed to compare no-inspector, greedy, random, and brute-force-style
strategies over the same deterministic seeds. The benchmark output reports
gold, purity, rejected loads, silent errors, shots, circuits, qubits, circuit
depth, and runtime. Inspector coverage and miner speed can be swept to expose
the break-even point where detection gains no longer justify its cost.
