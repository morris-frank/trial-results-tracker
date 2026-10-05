import pytest

from trial_results_tracker.stats import wilson

# z = 1.959964 for 95%, so z^2 = 3.841459.


def test_zero_denominator_is_the_whole_unit_interval():
    assert wilson(0, 0) == (0.0, 1.0)


def test_p_zero_has_lower_bound_zero_and_upper_z2_over_n_plus_z2():
    assert wilson(0, 10) == (0.0, pytest.approx(3.841459 / 13.841459))


def test_p_one_has_upper_bound_one_and_lower_n_over_n_plus_z2():
    assert wilson(10, 10) == (pytest.approx(10 / 13.841459), 1.0)


def test_p_half_is_symmetric_about_one_half():
    # half-width = z * sqrt(n p (1 - p) + z^2 / 4) / (n + z^2)
    #            = 1.959964 * sqrt(3.460365) / 13.841459
    low, high = wilson(5, 10)
    assert low == pytest.approx(0.5 - 0.263407, abs=1e-6)
    assert high == pytest.approx(0.5 + 0.263407, abs=1e-6)


@pytest.mark.parametrize(
    ("k", "n", "low", "high"),
    [(81, 263, 0.2553, 0.3662), (15, 148, 0.0624, 0.1605)],  # Newcombe 1998, Stat Med 17:857
)
def test_matches_published_worked_examples(k, n, low, high):
    assert wilson(k, n) == (pytest.approx(low, abs=5e-5), pytest.approx(high, abs=5e-5))


@pytest.mark.parametrize(("k", "n"), [(-1, 10), (11, 10)])
def test_count_outside_zero_to_n_raises(k, n):
    with pytest.raises(ValueError):
        wilson(k, n)
