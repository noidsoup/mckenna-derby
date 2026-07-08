import datetime as dt

import pytest

from mckenna_derby.timewave import Timewave, ZERO_DATE

# (value at 1000 days before zero, value at 12345.678 days before zero),
# verified against the compiled twz-point.c reference implementation.
GOLDEN = {
    "kelley": (0.0035158793131510, 0.0412491142607616),
    "watkins": (0.0035394941057478, 0.0412491142878900),
    "sheliak": (0.0033364068894159, 0.0202409528079362),
    "huangti": (0.0006744748070126, 0.0059600465473974),
}


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_matches_reference_c_implementation(name):
    tw = Timewave(name)
    v1000, v12345 = GOLDEN[name]
    assert tw.value_at_days_to_zero(1000) == pytest.approx(v1000, abs=1e-12)
    assert tw.value_at_days_to_zero(12345.678) == pytest.approx(v12345, abs=1e-12)


def test_zero_point_is_zero():
    assert Timewave("kelley").value_at_days_to_zero(0) == 0.0


def test_mirrored_extension_after_zero_date():
    tw = Timewave("kelley")
    v_before, m_before = tw.value_on(ZERO_DATE - dt.timedelta(days=500))
    v_after, m_after = tw.value_on(ZERO_DATE + dt.timedelta(days=500))
    assert m_before is False
    assert m_after is True
    assert v_after == pytest.approx(v_before)


def test_invalid_number_set_rejected():
    with pytest.raises(ValueError):
        Timewave("nonsense")


def test_negative_days_rejected():
    with pytest.raises(ValueError):
        Timewave("kelley").value_at_days_to_zero(-1)
