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

# A noisy inspector sometimes rejects a valid load (false alarm).
FALSE_ALARM_RATE = 0.03


def roll(*key):
    """Deterministic number in [0, 1) for a given key."""
    return random.Random("-".join(map(str, key))).random()


def detection_rate(error_rate):
    return min(0.95, 0.65 + error_rate)


def is_error(seed, tile, attempt, error_rate):
    return roll(seed, "error", *tile, attempt) < error_rate


def inspector_flags(seed, tile, attempt, is_impurity, error_rate):
    draw = roll(seed, "inspect", *tile, attempt)
    if is_impurity:
        return draw < detection_rate(error_rate)
    return draw < FALSE_ALARM_RATE


def pick(seed, tile, attempt, options):
    """Deterministically choose which rock tile an erroneous trip hits."""
    return options[int(roll(seed, "rock", *tile, attempt) * len(options))]
