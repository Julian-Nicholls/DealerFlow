from __future__ import annotations

import hashlib
import math
import random


class RandomStreams:
    """Independent deterministic RNG streams derived from one scenario seed."""

    def __init__(self, root_seed: int) -> None:
        self.root_seed = root_seed
        self._streams: dict[str, random.Random] = {}

    def get(self, name: str) -> random.Random:
        if name not in self._streams:
            material = f"{self.root_seed}:{name}".encode("utf-8")
            derived = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
            self._streams[name] = random.Random(derived)
        return self._streams[name]


def poisson(rng: random.Random, mean: float) -> int:
    """Knuth Poisson sampler; suitable for DealerFlow's small daily means."""
    if mean <= 0:
        return 0
    threshold = math.exp(-mean)
    product = 1.0
    k = 0
    while product > threshold:
        k += 1
        product *= rng.random()
    return k - 1
