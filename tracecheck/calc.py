"""Plain arithmetic for TraceCheck. No internet, no AI.

Every function returns a Result. If any needed input is missing (None),
the Result has value=None and a clear 'input missing' message, and no
number is produced. Formulas follow docs/REGULATORY_NOTES.md (notes 4, 6,
10 and 11). All outputs are illustrative, for evidence preparation.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Sequence, Tuple


@dataclass(frozen=True)
class Result:
    value: Optional[float]
    missing: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.missing is None


def _missing(what: str) -> Result:
    return Result(value=None, missing=f"input missing: {what}")


def round_to(value: float, places: int) -> float:
    """Round half up (2.0385 -> 2.039), not banker's rounding."""
    quant = Decimal(1).scaleb(-places)
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))


def round_specific(value: float) -> float:
    """Specific values: at most 5 decimals (note 11)."""
    return round_to(value, 5)


def round_total(value: float) -> int:
    """Total embedded emissions: whole tonnes (note 11)."""
    return int(round_to(value, 0))


def mass_ratio(consumed_t: Optional[float], product_t: Optional[float]) -> Result:
    """mi = tonnes of precursor consumed / tonnes of product made (note 10).

    Consumed includes the steel that became scrap (note 4).
    """
    if consumed_t is None:
        return _missing("tonnes of precursor consumed")
    if product_t is None:
        return _missing("tonnes of product made")
    if product_t <= 0:
        return Result(None, "input error: tonnes of product made must be above zero")
    return Result(consumed_t / product_t)


def own_direct_per_tonne(fuel_gj_per_t: Optional[float],
                         ef_t_per_tj: Optional[float]) -> Result:
    """Own direct emissions per tonne of product from stationary fuel.

    GJ per tonne / 1000 = TJ per tonne; times t CO2 per TJ.
    """
    if fuel_gj_per_t is None:
        return _missing("fuel energy in GJ per tonne of product")
    if ef_t_per_tj is None:
        return _missing("fuel emission factor in t CO2 per TJ")
    return Result(fuel_gj_per_t / 1000 * ef_t_per_tj)


def specific_embedded_emissions(
    own_per_t: Optional[float],
    precursors: Sequence[Tuple[str, Optional[float], Optional[float]]],
    round_intermediates_to: Optional[int] = None,
) -> Result:
    """SEE = own per tonne + sum of (mi x SEE of each precursor) (note 10).

    precursors: list of (name, mi, precursor_see).
    round_intermediates_to: if set (e.g. 3), each intermediate is rounded,
    the way the Commission shows its worked example.
    """
    if own_per_t is None:
        return _missing("own direct emissions per tonne")
    if not precursors:
        return _missing("at least one precursor")

    def r(x: float) -> float:
        return round_to(x, round_intermediates_to) if round_intermediates_to is not None else x

    total = r(own_per_t)
    for name, mi, see in precursors:
        if mi is None:
            return _missing(f"mass ratio for precursor '{name}'")
        if see is None:
            return _missing(f"embedded emissions value for precursor '{name}' (default value not entered)")
        total += r(r(mi) * see)
    return Result(total)


def weighted_average_see(lots: Sequence[Tuple[str, Optional[float], Optional[float]]]) -> Result:
    """Mass-weighted average SEE across suppliers or years (note 6).

    lots: list of (supplier, tonnes, see). Any missing value stops the total.
    """
    if not lots:
        return _missing("at least one supplier lot")
    total_t = 0.0
    weighted = 0.0
    for supplier, tonnes, see in lots:
        if tonnes is None:
            return _missing(f"tonnes from supplier '{supplier}'")
        if see is None:
            return _missing(f"embedded emissions value for supplier '{supplier}' (default value not entered)")
        total_t += tonnes
        weighted += tonnes * see
    if total_t <= 0:
        return Result(None, "input error: total tonnes must be above zero")
    return Result(weighted / total_t)
