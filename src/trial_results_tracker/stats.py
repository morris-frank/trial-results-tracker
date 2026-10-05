"""Proportion confidence intervals for the headline (docs/plan.md T7). Pure, stdlib only."""

from math import sqrt

Z_95 = 1.959963984540054  # two-sided 95% normal quantile


def wilson(k: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials.

    With n = 0 nothing is known, so the interval is the whole of [0, 1].
    """
    if not 0 <= k <= n:
        raise ValueError(f"need 0 <= k <= n, got k={k}, n={n}")
    if n == 0:
        return 0.0, 1.0
    p = k / n
    z2 = z * z
    centre = (k + z2 / 2) / (n + z2)
    half = z * sqrt(n * p * (1 - p) + z2 / 4) / (n + z2)
    # Clamp float error so p = 0 and p = 1 give exact 0 and 1 bounds.
    return max(0.0, centre - half), min(1.0, centre + half)
