"""
Noisy Bell-state experiment in ONE function: bell_experiment(...)

Switches:
  encode  : 3-qubit repetition code + majority vote
  ancilla : parity-check ancilla + post-selection
  zne     : zero-noise extrapolation (CNOT folding)

"Precision" = P(00) + P(11), shown in percent. 100% = perfect Bell state,
50% = pure noise (all four outcomes equally likely).

Requires:  pip install qiskit qiskit-aer numpy
"""
from collections import Counter

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError

# ============================ SETTINGS ============================
# Edit these. bell_experiment() uses them as its defaults.
NOISE = 0.05          # 2-qubit gate error (0 = clean, 1 = fully scrambled gate)
ENCODE = False        # True/False: 3-qubit repetition code
ANCILLA = False       # True/False: parity-check ancilla + post-selection
USE_ZNE = False       # True/False: zero-noise extrapolation
DEPTH = 5             # padding CNOT pairs
SHOTS = 5000
SCALES = (1, 3, 5)    # ZNE scale factors, odd integers only
ZNE_METHOD = "exponential"   # "linear", "richardson" or "exponential"
P1 = None             # 1-qubit gate error override (default: NOISE / 10)
P_READOUT = None      # readout error override (default: min(NOISE, 0.5))
SEED = None           # None = different result every run; integer = reproducible
# ==================================================================


def bell_experiment(
    noise=NOISE,              # 2-qubit gate error (0 = clean, 1 = fully scrambled gate)
    encode=ENCODE,            # True/False: repetition code
    ancilla=ANCILLA,          # True/False: parity-check ancilla + post-selection
    zne=USE_ZNE,              # True/False: zero-noise extrapolation
    depth=DEPTH,              # padding CNOT pairs (more = more accumulated error)
    shots=SHOTS,
    scales=SCALES,            # ZNE noise scale factors, odd integers only
    zne_method=ZNE_METHOD,    # "linear", "richardson" or "exponential"
    p1=P1,                    # 1-qubit gate error override (default: noise / 10)
    p_readout=P_READOUT,      # readout error override (default: min(noise, 0.5))
    seed=SEED,                # None = different result every run; integer = reproducible
    verbose=True,             # print the four outcome percentages and the precision
):
    """Run the experiment, print the results, and return a dict:

        precision      : final precision in percent (ZNE-extrapolated if zne=True)
        good_fraction  : same value as a fraction (1.0 = perfect, 0.5 = noise)
        unmitigated    : good fraction at scale 1 (before ZNE extrapolation)
        kept_fraction  : share of shots kept at scale 1 (below 1.0 only with ancilla)
        outcome_probs  : {scale: {"00": p, "01": p, "10": p, "11": p}} (decoded logical bits "ba")
        counts         : decoded counts at scale 1
        points         : list of (scale, good_fraction, kept_fraction)
        n_cx           : number of CNOTs in the transpiled circuit at scale 1 (sanity check)
    """
    # ---------- checks ----------
    scales = list(scales) if zne else [1]
    if any(s < 1 or s % 2 == 0 for s in scales):
        raise ValueError("scales must be odd positive integers (1, 3, 5, ...)")

    # ---------- noise model ----------
    p2 = min(noise, 16 / 15)                              # max for 2-qubit depolarizing
    p1_ = min(noise / 10 if p1 is None else p1, 4 / 3)    # max for 1-qubit depolarizing
    p_ro = min(noise, 0.5) if p_readout is None else p_readout

    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(depolarizing_error(p1_, 1), ["h", "x", "sx", "id"])
    noise_model.add_all_qubit_quantum_error(depolarizing_error(p2, 2), ["cx"])
    noise_model.add_all_qubit_readout_error(
        ReadoutError([[1 - p_ro, p_ro], [p_ro, 1 - p_ro]])
    )

    # ---------- circuit builder ----------
    def build_circuit(fold):
        n = 3 if encode else 1                    # physical qubits per logical qubit
        qa = QuantumRegister(n, "qa")
        qb = QuantumRegister(n, "qb")
        qregs = [qa, qb]
        if ancilla:
            anc = QuantumRegister(1, "anc")
            qregs.append(anc)

        # Register order matters: Aer prints the LAST-added classical register first
        if encode:
            ca = ClassicalRegister(3, "ca")
            cb = ClassicalRegister(3, "cb")
            cregs = [ca, cb]
        else:
            c = ClassicalRegister(2, "c")
            cregs = [c]
        if ancilla:
            a = ClassicalRegister(1, "a")
            cregs.append(a)

        qc = QuantumCircuit(*qregs, *cregs)

        def cx(control, target):
            for _ in range(fold):                 # CX^fold = CX ideally, noise ~fold times larger
                qc.cx(control, target)

        # Prepare logical |+> on A, then fan out inside the block
        qc.h(qa[0])
        for i in range(1, n):
            cx(qa[0], qa[i])

        # Logical CNOT A -> B (transversal: one physical CNOT per qubit pair)
        for i in range(n):
            cx(qa[i], qb[i])

        # Padding: logical CNOT twice per layer = identity ideally, adds noisy gates
        for _ in range(depth):
            qc.barrier()
            for _ in range(2):
                for i in range(n):
                    cx(qa[i], qb[i])
        qc.barrier()

        if ancilla:
            # Parity check on the first physical qubit of each block
            cx(qa[0], anc[0])
            cx(qb[0], anc[0])
            qc.measure(anc[0], a[0])

        if encode:
            qc.measure(qa, ca)
            qc.measure(qb, cb)
        else:
            qc.measure(qa[0], c[0])
            qc.measure(qb[0], c[1])
        return qc

    # ---------- run one noise scale ----------
    def run_once(fold):
        # seed=None -> fresh random seed each call; "+ fold" keeps ZNE scales independent
        sim = AerSimulator(
            noise_model=noise_model,
            seed_simulator=None if seed is None else seed + fold,
        )
        # optimization_level=0 keeps the folded gates (higher levels would cancel them)
        qc = transpile(build_circuit(fold), sim, optimization_level=0)
        n_cx = qc.count_ops().get("cx", 0)
        memory = sim.run(qc, shots=shots, memory=True).result().get_memory()

        counts = Counter()
        for s in memory:
            parts = s.split()            # "0 101 110" = "a cb ca"  or  "0 11" = "a c"
            if ancilla and parts.pop(0) != "0":
                continue                 # post-select: discard flagged shots
            if encode:
                cb_bits, ca_bits = parts
                la = int(ca_bits.count("1") >= 2)    # majority vote
                lb = int(cb_bits.count("1") >= 2)
                counts[f"{lb}{la}"] += 1
            else:
                counts[parts[0]] += 1

        kept = sum(counts.values())
        probs = {k: (counts[k] / kept if kept else float("nan"))
                 for k in ("00", "01", "10", "11")}
        good = probs["00"] + probs["11"]
        return counts, good, kept / shots, probs, n_cx

    # ---------- run all scales ----------
    points, outcome_probs, first_counts, n_cx_first = [], {}, None, 0
    for s in scales:
        counts, good, kept, probs, n_cx = run_once(s)
        points.append((s, good, kept))
        outcome_probs[s] = probs
        if first_counts is None:
            first_counts, n_cx_first = counts, n_cx

    # ---------- ZNE extrapolation to scale 0 ----------
    if zne:
        x = np.array([p[0] for p in points], dtype=float)
        y = np.array([p[1] for p in points], dtype=float)
        if zne_method == "linear":
            final = float(np.polyval(np.polyfit(x, y, 1), 0.0))
        elif zne_method == "richardson":
            final = float(np.polyval(np.polyfit(x, y, len(x) - 1), 0.0))
        elif zne_method == "exponential":
            # good = 0.5 + A * exp(-b * scale); fit log(good - 0.5), evaluate at scale 0
            z = y - 0.5
            if np.all(z > 0):
                _, intercept = np.polyfit(x, np.log(z), 1)
                final = float(0.5 + np.exp(intercept))
            else:
                print("exponential fit not possible (values too close to 0.5); using linear")
                final = float(np.polyval(np.polyfit(x, y, 1), 0.0))
        else:
            raise ValueError("zne_method must be 'linear', 'richardson' or 'exponential'")
    else:
        final = points[0][1]

    # ---------- print ----------
    if verbose:
        print(f"noise used: 2-qubit={p2:.3f}  1-qubit={p1_:.3f}  readout={p_ro:.3f}   "
              f"CNOTs in circuit (scale 1): {n_cx_first}")
        print(f"encode={encode}  ancilla={ancilla}  zne={zne}  depth={depth}  shots={shots}")
        for s, good, kept in points:
            pr = outcome_probs[s]
            print(f"  scale {s}:  00 {pr['00']:6.1%} | 01 {pr['01']:6.1%} | "
                  f"10 {pr['10']:6.1%} | 11 {pr['11']:6.1%}   "
                  f"-> precision {good:6.1%}   (kept {kept:.1%})")
        label = f"ZNE-extrapolated ({zne_method})" if zne else "final"
        print(f"  {label} precision: {final:.1%}   (50% = pure noise, 100% = perfect)")
        if noise > 0 and n_cx_first == 0:
            print("  WARNING: no CNOTs in the transpiled circuit, so no gate noise is applied")
        if final > 1.0:
            print("  NOTE: extrapolated value is above 100%, which is an artifact of the fit")

    return {
        "precision": final * 100,
        "good_fraction": final,
        "unmitigated": points[0][1],
        "kept_fraction": points[0][2],
        "outcome_probs": outcome_probs,
        "counts": dict(first_counts),
        "points": points,
        "n_cx": n_cx_first,
    }


if __name__ == "__main__":
    # No arguments here on purpose: everything comes from the SETTINGS block at the top.
    result = bell_experiment()
    print("\nreturned precision:", round(result["precision"], 1), "%")
