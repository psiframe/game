"""Trip outcomes: is a load an impurity, and does the inspector flag it?

Every random draw is keyed by (test-case seed, tile, attempt) instead of
coming from one shared random stream. Two strategies playing the same test
case therefore face exactly the same errors at the same error rate, no matter
how many miners they own or when they buy upgrades. This is what makes the
end-screen comparison fair.

Hook for the quantum backend: replace the bodies of ``is_error`` and
``inspector_flags`` with calls to the Qiskit simulation, keeping the
signatures and deriving the simulator seed from ``seed``, ``tile`` and
``attempt`` so results stay reproducible.
"""

import random
from random_quantum import bell_experiment
# A noisy inspector sometimes rejects a valid load (false alarm).
FALSE_ALARM_RATE = 0.03


"""
import numpy as np

def normalize_to_0_1(data):
    data = np.asarray(data)
    min_val = np.min(data)
    max_val = np.max(data)
    if max_val == min_val:
        return np.zeros_like(data)
    return (data - min_val) / (max_val - min_val)   
"""


def roll(*key):
    """Deterministic number in [0, 1) for a given key."""
    return random.Random("-".join(map(str, key))).random()


def detection_rate(error_rate):
    return min(0.95, 0.65 + error_rate)


def is_error(seed, tile, attempt, error_rate):
    return roll(seed, "error", *tile, attempt) < error_rate


def inspector_flags(miner_count, inspector_presence, efficiency):
    """
    #(seed, tile, attempt, is_impurity, error_rate):
    draw = roll(seed, "inspect", *tile, attempt)
    if is_impurity:
        return draw < detection_rate(error_rate)
    return draw < FALSE_ALARM_RATE
    """

    # to be importned in thsi file later
    result = bell_experiment(
        noise=0.05,              # 2-qubit gate error (0 = clean, 1 = fully scrambled gate)
        encode=(True if miner_count>3 else False ),            # True/False: repetition code
        ancilla=inspector_presence,          # True/False: parity-check ancilla + post-selection
        zne=(True if efficiency> 0.95 else False),              # True/False: zero-noise extrapolation
        depth=5,              # padding CNOT pairs (more = more accumulated error)
        shots=5000,
        scales=(1, 3, 5),            # ZNE noise scale factors, odd integers only
        zne_method="exponential",    # "linear", "richardson" or "exponential"
        p1=None,                    # 1-qubit gate error override (default: noise / 10)
        p_readout=None,      # readout error override (default: min(noise, 0.5))
        seed=None,                # None = different result every run; integer = reproducible
        verbose=True,             # print the four outcome percentages and the precision
    )

    print(result)
    return result["good_fraction"]#/100
    


def pick(seed, tile, attempt, options):
    """Deterministically choose which rock tile an erroneous trip hits."""
    return options[int(roll(seed, "rock", *tile, attempt) * len(options))]


