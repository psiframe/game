# Quantum Mine

Quantum Mine is an educational Pygame mining game. You manage a small team
of miners, send them through a procedurally generated rock map, collect gold,
and decide when upgrades and inspectors are worth their cost.

The mining outcomes are inspired by a simplified noisy quantum circuit:

- A miner represents a data qubit.
- Speed represents repeated gate layers.
- A successful measurement represents valid gold.
- A measurement error represents a rock or impurity.
- An inspector represents a simple ancilla-based parity check that can detect
  some invalid loads.

This is a game and teaching model, not a simulation of physical mining or
quantum hardware.

## What you learn

The project is centered on the following quantum-computing ideas:

- **Noisy circuits:** build a circuit in Qiskit and run it with an Aer noise
  model.
- **Errors accumulate:** increasing the number of qubits and gate layers
  creates more opportunities for a bit flip or other error.
- **Detection versus correction:** a parity check can tell you that an error
  happened, but it does not identify the error's location or explain how to
  undo it.
- **Postselection:** discarding shots flagged by the check produces cleaner
  results, but leaves fewer usable results.
- **Noisy checks:** the ancilla and its measurements are noisy too, so an
  inspector can raise a false alarm or miss an error.
- **Break-even analysis:** protection is useful only until its cost and
  overhead cancel out the quality or throughput improvement. Finding this
  break-even point is the main finding of the project.

The game turns these ideas into decisions: increase speed and process more
layers, or pay for inspection and accept its cost and imperfect detection.

## Questions explored

The project is designed to investigate four related questions:

1. **How do errors change with scale?** Errors should grow as the circuit
   becomes larger and as speed adds more gate layers.
2. **What does an inspector really do?** Inspectors detect errors; they do not
   prevent them. They also have a purchase cost and introduce checking
   overhead.
3. **Can more protection make results worse?** Yes. There are layouts where
   adding protection reduces the overall result because its overhead outweighs
   the errors it removes.
4. **How close do players get to the optimum?** Player outcomes can be
   compared with the best strategy for the same layout and noise conditions.
   The comparison is expressed as a percentage of the optimal strategy's
   result when an optimal baseline is available.

## Requirements

- Python 3.9 or newer
- Pygame

Qiskit and Qiskit Aer are optional. The game uses its deterministic fallback
behavior when the optional quantum packages are not installed.

## Installation

Open a terminal in the repository root:

```powershell
cd C:\Users\...\game
```

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, run the game with the environment's
Python executable directly, or use Command Prompt:

```bat
.venv\Scripts\activate.bat
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Run the game

From the repository root, run:

```powershell
python ui\main.py
```

Click the start button to begin the transition into the mine. The game starts
with one miner and one shared storage unit positioned at the center of the map.

## How to play

### Select miners

- Click a miner to select it.
- Press `1` through `9` to select a miner by number.
- Click anywhere that is not a miner to clear the selection.
- The selected miner has a subtle white outline.

Miners work through different map rows. With multiple miners, row ownership is
distributed so each miner works a repeating set of rows rather than all miners
competing for the same row.

### Buy upgrades

Purchases use credits shown in the lower-left information panel:

- `M` buys a miner.
- `S` buys a speed upgrade for the selected miner.
- `I` buys an inspector for the selected miner.

When no miner is selected:

- `S` still performs a speed upgrade for the whole mining team.
- `I` selects the first miner without an inspector and buys the inspector if
  enough credits are available.

New miners inherit the current global speed. Speed upgrades increase movement
speed for all miners and also increase the modeled error rate, creating a
trade-off between throughput and impurities.

Prices increase by upgrade level. Selling a miner or inspector decreases its
corresponding upgrade level, so the next purchase returns to the previous
price tier.

### Sell upgrades

The custom management buttons are in the lower-right corner:

- **Sell miner $20**: sells the selected miner and refunds 20 credits. It is
  available only when at least two miners exist.
- **Sell inspector $20**: removes the inspector from the selected miner and
  refunds 20 credits.

Selling the last miner is not allowed. Selling removes the miner's active
state, target, load, row assignment, and inspector data.

### Collect gold and handle impurities

Each valid gold tile gives one gold ore. Gold ore is tracked separately from
credits. When valid gold reaches storage, the reward is based on its purity:

```text
credits earned = $20 × purity
```

For example, 100% purity earns $20 per ore, while 50% purity earns $10.

The game provides visual feedback:

- Green pulse: valid gold reached storage.
- Red pulse and vibration: an impurity reached storage undetected.
- Yellow pulse and vibration on the inspector: an impurity was detected and
  rejected.

### Refresh the map

The **Refresh map** button starts the existing map scrolling behavior. It is
enabled only after 120 seconds have elapsed since the latest completed scroll.
Miners continue working through the available layers and the map advances as
the mining cycle progresses.

## Information shown on screen

The lower-left panel displays:

- Current credits
- Gold ore collected
- Latest purity
- Accepted-load percentage
- Number of miners
- Current selection
- Selected miner speed, inspector status, and state
- Rejected loads and silent errors
- Current prices for miner, speed, and inspector upgrades

## Run the tests

The headless modules can be tested without opening the Pygame window:

```powershell
python -m unittest test_headless_modules.py
```

These tests cover deterministic backend output, miner/storage round trips, and
the round-robin strategy.

## Run the benchmark

To compare mining strategies and deterministic outcomes:

```powershell
python benchmark.py
```

The benchmark reports gold, purity, rejected loads, silent errors, shots,
circuits, qubits, circuit depth, and runtime. It is useful for exploring the
trade-off between faster mining and better impurity detection.

## Project structure

```text
quantum_game/
├── ui/
│   ├── main.py                 # Pygame game loop, map, miners, and UI
│   └── assets/                 # Rock, miner, inspector, storage, and UI art
├── quantum_backend.py          # Deterministic fallback and optional quantum backend
├── entities.py                 # Headless miner, inspector, and storage models
├── economy.py                  # Upgrade levels and price progression
├── strategies.py               # Benchmark mining strategies
├── benchmark.py                # Headless strategy benchmark
├── test_headless_modules.py    # Dependency-light automated tests
├── requirements.txt            # Required Python packages
└── README.md                   # This guide
```

## Simplifications and limitations

Quantum Mine intentionally simplifies several ideas:

- The fallback backend is deterministic and uses a fixed seed.
- Noise and inspection are educational abstractions.
- The visual game controller and headless benchmark models are separate
  implementations.
- The game does not persist progress between runs.
- Optional Qiskit Aer support is not required to play the prototype.
