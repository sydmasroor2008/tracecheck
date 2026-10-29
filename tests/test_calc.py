"""Tests for weighted averages, rounding and missing-input behaviour."""

import pytest

from tracecheck.calc import (
    mass_ratio,
    own_direct_per_tonne,
    round_specific,
    round_to,
    round_total,
    specific_embedded_emissions,
    weighted_average_see,
)


def test_weighted_average_by_mass():
    result = weighted_average_see([("A", 120, 2.0), ("B", 80, 1.0)])
    assert result.ok
    assert result.value == pytest.approx((120 * 2.0 + 80 * 1.0) / 200)


def test_weighted_average_single_supplier_equals_its_value():
    assert weighted_average_see([("A", 50, 1.7)]).value == pytest.approx(1.7)


def test_weighted_average_refuses_when_default_not_entered():
    result = weighted_average_see([("Supplier A", 120, 1.567), ("Trader B", 70, None)])
    assert result.value is None
    assert result.missing.startswith("input missing")
    assert "Trader B" in result.missing


def test_weighted_average_refuses_missing_tonnes():
    result = weighted_average_see([("A", None, 1.5)])
    assert result.value is None and "input missing" in result.missing


def test_weighted_average_zero_tonnes_is_an_error():
    result = weighted_average_see([("A", 0, 1.5)])
    assert result.value is None and "input error" in result.missing


@pytest.mark.parametrize("args", [(None, 170), (200, None)])
def test_mass_ratio_missing(args):
    result = mass_ratio(*args)
    assert result.value is None and "input missing" in result.missing


def test_mass_ratio_zero_product_is_an_error():
    assert mass_ratio(200, 0).value is None


def test_mass_ratio_includes_scrap_so_above_one():
    # Synthetic factory: 200 t consumed, 170 t product (30 t scrap).
    assert mass_ratio(200, 170).value > 1


@pytest.mark.parametrize("args", [(None, 56.1), (3.5, None)])
def test_own_direct_missing(args):
    result = own_direct_per_tonne(*args)
    assert result.value is None and "input missing" in result.missing


def test_see_refuses_when_precursor_value_missing():
    result = specific_embedded_emissions(0.196, [("rod from trader", 1.176, None)])
    assert result.value is None
    assert "default value not entered" in result.missing


def test_see_refuses_missing_own_and_empty_precursors():
    assert specific_embedded_emissions(None, [("rod", 1.1, 1.5)]).value is None
    assert specific_embedded_emissions(0.196, []).value is None


def test_rounding_half_up():
    assert round_to(2.0385, 3) == 2.039
    assert round_specific(1.1764705882) == 1.17647
    assert round_total(2.5) == 3
    assert isinstance(round_total(10.4), int)
