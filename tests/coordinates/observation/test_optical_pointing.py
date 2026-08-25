import pandas as pd
import pytest
from astropy.time import Time

from neclib import config
from neclib.coordinates.observations.optical_pointing import (
    BSC5ParseError,
    OpticalPointingSpec,
    _sort_serpentine_bins,
)


def _set_field(record, first_byte, last_byte, value):
    width = last_byte - first_byte + 1
    assert len(value) == width
    record[first_byte - 1 : last_byte] = value


def _sirius_record():
    record = [" "] * 197
    _set_field(record, 1, 4, "2491")
    _set_field(record, 5, 14, "  9Alp CMa")
    _set_field(record, 44, 44, " ")
    _set_field(record, 76, 77, "06")
    _set_field(record, 78, 79, "45")
    _set_field(record, 80, 83, "08.9")
    _set_field(record, 84, 84, "-")
    _set_field(record, 85, 86, "16")
    _set_field(record, 87, 88, "42")
    _set_field(record, 89, 90, "58")
    _set_field(record, 103, 107, "-1.46")
    _set_field(record, 149, 154, "-0.553")
    _set_field(record, 155, 160, "-1.205")
    return "".join(record)


def test_bsc5_sirius_fields_preserve_signs_and_full_name():
    spec = object.__new__(OpticalPointingSpec)

    row = spec._parse_catalog_line_fixed_width(_sirius_record())

    assert row["hr"] == 2491
    assert row["name"] == "9Alp CMa"
    assert row["vmag"] == pytest.approx(-1.46)
    assert row["pmra"] == pytest.approx(-0.553)
    assert row["pmdec"] == pytest.approx(-1.205)


def test_bsc5_removed_record_is_intentionally_skipped():
    spec = object.__new__(OpticalPointingSpec)
    record = [" "] * 197
    _set_field(record, 1, 4, "9999")

    assert spec._parse_catalog_line_fixed_width("".join(record)) is None


def test_bsc5_short_record_fails_explicitly():
    spec = object.__new__(OpticalPointingSpec)

    with pytest.raises(BSC5ParseError, match="too short"):
        spec._parse_catalog_line_fixed_width("2491")


def test_bsc5_malformed_numeric_field_is_not_silently_skipped():
    spec = object.__new__(OpticalPointingSpec)
    spec.now = Time("J2000")
    record = list(_sirius_record())
    _set_field(record, 103, 107, "abcde")

    with pytest.raises(BSC5ParseError, match="line=1"):
        spec._catalog_to_pandas(["".join(record)])


def test_serpentine_bins_are_half_open_and_empty_bins_do_not_flip_direction():
    data = pd.DataFrame(
        {
            "name": ["a", "boundary", "c", "d"],
            "az": [1.0, 25.0, 76.0, 77.0],
            "el": [20.0, 30.0, 10.0, 40.0],
        }
    )

    result = _sort_serpentine_bins(data, lower=0.0, upper=100.0, width=25.0)

    assert result["name"].tolist() == ["a", "boundary", "c", "d"]
    assert result["name"].value_counts().to_dict() == {
        "a": 1,
        "boundary": 1,
        "c": 1,
        "d": 1,
    }


def test_estimate_time_uses_resolved_mount_azimuth():
    spec = object.__new__(OpticalPointingSpec)
    data = pd.DataFrame(
        {
            "az": [359.0, 1.0],
            "mount_az": [359.0, 361.0],
            "el": [45.0, 45.0],
        }
    )

    expected = 30.0 + 2.0 / config.antenna.max_speed_az.value
    assert spec.estimate_time(data) == pytest.approx(expected)
