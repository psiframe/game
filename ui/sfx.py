"""Procedurally generated sound effects, so the game needs no audio files.

Call ``init()`` once after ``pygame.init()``. If no audio device is available
the game keeps running silently.
"""

import math
import random
from array import array

import pygame

# name: (segments as (start_hz, end_hz, seconds), waveform, volume, noise mix, decay)
_SPECS = {
    "click":   ([(900, 700, 0.04)], "tri", 0.30, 0.0, 8.0),
    "start":   ([(440, 880, 0.35)], "tri", 0.30, 0.0, 2.0),
    "buy":     ([(660, 660, 0.07), (990, 990, 0.12)], "square", 0.12, 0.0, 3.0),
    "denied":  ([(220, 160, 0.15)], "square", 0.12, 0.0, 4.0),
    "mine":    ([(180, 90, 0.07)], "sine", 0.35, 0.7, 10.0),
    "gold":    ([(1320, 1320, 0.06), (1760, 1760, 0.18)], "sine", 0.25, 0.0, 4.0),
    "reject":  ([(880, 880, 0.08), (587, 587, 0.12)], "tri", 0.30, 0.0, 3.0),
    "error":   ([(140, 110, 0.30)], "square", 0.15, 0.0, 3.0),
    "refresh": ([(200, 900, 0.45)], "sine", 0.22, 0.5, 2.0),
    "pause":   ([(600, 400, 0.08)], "tri", 0.30, 0.0, 6.0),
}

_sounds = {}
_enabled = False
_suspended = False


def _render(segments, shape, volume, noise, decay):
    rate, size, channels = pygame.mixer.get_init()
    total = sum(int(rate * seconds) for _, _, seconds in segments)
    rng = random.Random(1)
    samples = array("h")
    phase = 0.0
    done = 0
    for start_hz, end_hz, seconds in segments:
        count = int(rate * seconds)
        for i in range(count):
            hz = start_hz + (end_hz - start_hz) * i / count
            phase += 2.0 * math.pi * hz / rate
            if shape == "square":
                wave = 1.0 if math.sin(phase) >= 0 else -1.0
            elif shape == "tri":
                wave = 2.0 / math.pi * math.asin(math.sin(phase))
            else:
                wave = math.sin(phase)
            if noise:
                wave = wave * (1.0 - noise) + rng.uniform(-1.0, 1.0) * noise
            # Short attack avoids clicks; exponential decay over the whole sound.
            envelope = math.exp(-decay * done / total) * min(1.0, i / (rate * 0.004))
            value = int(max(-1.0, min(1.0, wave * envelope * volume)) * 32767)
            samples.extend([value] * channels)
            done += 1
    return pygame.mixer.Sound(buffer=samples.tobytes())


def init():
    global _enabled
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(44100, -16, 1, 512)
        if pygame.mixer.get_init()[1] != -16:
            raise pygame.error("unsupported sample format")
        for name, spec in _SPECS.items():
            _sounds[name] = _render(*spec)
        _enabled = True
    except pygame.error as error:
        print(f"Sound disabled: {error}")
        _sounds.clear()
        _enabled = False


def play(name):
    if _enabled and not _suspended and name in _sounds:
        _sounds[name].play()


def suspend(value):
    """Silence sounds temporarily, e.g. while strategies are simulated."""
    global _suspended
    _suspended = value


def toggle():
    """Mute or unmute; returns True when sound is now on."""
    global _enabled
    if _sounds:
        _enabled = not _enabled
    return _enabled


def is_on():
    return _enabled
