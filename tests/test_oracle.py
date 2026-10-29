"""Reproduce the Commission's worked example (docs/TEST_ORACLE.md).

These are illustrative example values from Guidance 5d, Example 3.
They are not default values and not a real factory's values.
"""

import pytest

from tracecheck.calc import mass_ratio, own_direct_per_tonne, specific_embedded_emissions

GAS_GJ_PER_T = 3.5
GAS_EF = 56.1

CASES = [
    # name, precursor SEE, product t, consumed t, expected total
    ("carbon steel", 1.567, 17_000, 20_000, 2.039),
    ("stainless", 1.783, 8_200, 10_000, 2.371),
]


@pytest.mark.parametrize("name, see, product, consumed, expected", CASES)
def test_rounded_intermediates_match_exactly(name, see, product, consumed, expected):
    mi = mass_ratio(consumed, product).value
    own = own_direct_per_tonne(GAS_GJ_PER_T, GAS_EF).value
    result = specific_embedded_emissions(own, [("steel rod", mi, see)], round_intermediates_to=3)
    assert result.ok
    assert result.value == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize("name, see, product, consumed, expected", CASES)
def test_unrounded_within_tolerance(name, see, product, consumed, expected):
    mi = mass_ratio(consumed, product).value
    own = own_direct_per_tonne(GAS_GJ_PER_T, GAS_EF).value
    result = specific_embedded_emissions(own, [("steel rod", mi, see)])
    assert result.ok
    assert abs(result.value - expected) <= 0.002


def test_intermediate_values_shown_by_commission():
    assert round(mass_ratio(20_000, 17_000).value, 3) == 1.176
    assert round(mass_ratio(10_000, 8_200).value, 3) == 1.220
    assert round(own_direct_per_tonne(3.5, 56.1).value, 3) == 0.196


def test_precursor_share_about_ninety_percent():
    # Slide 4 claim: 1.843 / 2.039 of the carbon steel example comes from steel.
    mi = mass_ratio(20_000, 17_000).value
    steel_part = 1.567 * mi
    own = own_direct_per_tonne(3.5, 56.1).value
    share = steel_part / (steel_part + own)
    assert 0.89 < share < 0.91
