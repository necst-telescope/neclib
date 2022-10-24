from typing import Tuple, Union

import astropy.units as u
import pytest
from astropy.coordinates import AltAz, Angle, EarthLocation, FK4, FK5, Galactic, ICRS
from astropy.coordinates.baseframe import BaseCoordinateFrame
from astropy.units import Quantity

from neclib.parameters import ObsParams, interval, off_point_coord


class TestObsParams:
    def test_val(self, data_dir):
        ObsParams.ParameterUnit = {"deg": ["LamdaOn", "LamdaOff"]}
        params = ObsParams.from_file(data_dir / "sample_radio_pointing.obs.toml")

        assert params.val.LamdaOn == 146.98871
        assert params.val.BetaOn == u.Quantity("13.278574deg")
        assert params.val.OTADEL is True

        assert params.LamdaOn == u.Quantity("146.98871deg")
        assert params.BetaOn == u.Quantity("13.278574deg")
        assert params.OTADEL is True

    def test_hot_observation_interval(self, data_dir):
        params = ObsParams.from_file(data_dir / "sample_radio_pointing.obs.toml")
        assert params.hot_observation_interval(unit="s") == (300, "time")
        with pytest.raises(u.UnitConversionError):
            params.hot_observation_interval(
                unit="point", points_per_scan=(params.METHOD + 1) / 2
            )
        with pytest.raises(u.UnitConversionError):
            params.hot_observation_interval(unit="scan")

    def test_off_observation_interval(self, data_dir):
        params = ObsParams.from_file(data_dir / "sample_radio_pointing.obs.toml")
        assert params.off_observation_interval(unit="scan") == (1, "scan")
        assert params.off_observation_interval(
            unit="point", points_per_scan=(params.METHOD + 1) / 2
        ) == (5, "point")
        with pytest.raises(u.UnitConversionError):
            params.off_observation_interval(unit="s")

    def test_off_point_coord(self, data_dir):
        params = ObsParams.from_file(data_dir / "sample_radio_pointing.obs.toml")
        assert params.off_point_coord(unit="deg") == (147.23930, 13.279295, "fk5")


class TestInterval:

    func_name = "interval"

    def test_conversion_from_scan(self):
        assert interval(u.Quantity("1scan"), unit="scan") == (1, "scan")
        assert interval(u.Quantity("1scan"), unit="point", points_per_scan=5) == (
            5,
            "point",
        )
        with pytest.raises(u.UnitConversionError):
            interval(u.Quantity("1scan"), unit="point")
        with pytest.raises(u.UnitConversionError):
            interval(u.Quantity("1scan"), unit="s", points_per_scan=5)

    def test_conversion_from_point(self):
        assert interval(u.Quantity("50point"), unit="point") == (50, "point")
        assert interval(u.Quantity("50point"), unit="scan", points_per_scan=5) == (
            10,
            "scan",
        )
        with pytest.raises(u.UnitConversionError):
            interval(u.Quantity("50point"), unit="scan")
        with pytest.raises(u.UnitConversionError):
            interval(u.Quantity("50point"), unit="s", points_per_scan=5)

    def test_conversion_from_time_units(self):
        assert interval(u.Quantity("5min"), unit="min") == (5, "time")
        assert interval(u.Quantity("5min"), unit="s") == (300, "time")
        with pytest.raises(u.UnitConversionError):
            interval(u.Quantity("300s"), unit="scan", points_per_scan=5)
        with pytest.raises(u.UnitConversionError):
            interval(u.Quantity("300s"), unit="point", points_per_scan=5)


CoordinateType = Tuple[u.Quantity, u.Quantity, Union[str, BaseCoordinateFrame]]

_LOC_NANTEN2 = EarthLocation(
    lon=Quantity("-67.70308139deg"),
    lat=Quantity("-22.96995611deg"),
    height=Quantity("4863.85m"),
)  # Make result insensitive to update of N-CONST


class TestOffPointCoord:
    """All the expected values are calculated in ``tests/_expectation/obsparam.py``"""

    func_name = "off_point_coord"

    def test_coorsys_as_astropy_class(self):
        off_point_coord(absolute=(Angle("0h0m0s"), Angle("0d0m0s"), AltAz), unit="deg")
        off_point_coord(absolute=(Angle("0h0m0s"), Angle("0d0m0s"), FK4), unit="deg")
        off_point_coord(absolute=(Angle("0h0m0s"), Angle("0d0m0s"), FK5), unit="deg")
        off_point_coord(
            absolute=(Angle("0h0m0s"), Angle("0d0m0s"), Galactic), unit="deg"
        )
        off_point_coord(absolute=(Angle("0h0m0s"), Angle("0d0m0s"), ICRS), unit="deg")

    def test_coordsys_as_astropy_instance(self):
        off_point_coord(
            absolute=(Angle("0h0m0s"), Angle("0d0m0s"), AltAz()), unit="deg"
        )
        off_point_coord(absolute=(Angle("0h0m0s"), Angle("0d0m0s"), FK4()), unit="deg")
        off_point_coord(absolute=(Angle("0h0m0s"), Angle("0d0m0s"), FK5()), unit="deg")
        off_point_coord(
            absolute=(Angle("0h0m0s"), Angle("0d0m0s"), Galactic()), unit="deg"
        )
        off_point_coord(absolute=(Angle("0h0m0s"), Angle("0d0m0s"), ICRS()), unit="deg")

    given_absolute_point = (Angle("1h2m3s"), Angle("10d20m30s"), "fk5")
    expected_absolute_point = (15.5125, 10.341666666666667, "fk5")

    def test_no_coordinate_conversion(self):
        assert off_point_coord(
            absolute=self.given_absolute_point, unit="deg"
        ) == pytest.approx(self.expected_absolute_point)

    given_on_point = (Angle("15h25m35s"), Angle("50d40m30s"), "fk5")
    given_on_point_arcsec = (Angle("833025arcsec"), Angle("182430arcsec"), "fk5")
    given_offset_1 = (Angle("3arcsec"), Angle("20arcsec"), "fk5")
    given_offset_2 = (Angle("3arcsec"), Angle("20arcsec"), "galactic")

    expected_coord_1 = (231.39666666666662, 50.68055555555555, "fk5")
    expected_coord_1_arcsec = (833028, 182450, "fk5")
    expected_coord_1_coslat_applied = (231.39714832316068, 50.68055555555555, "fk5")

    expected_coord_2 = (82.44271070930702, 52.557240552547405, "galactic")
    expected_coord_2_arcsec = (296793.7585535053, 189206.06598917066, "galactic")
    expected_coord_2_coslat_applied = (
        82.44324788740413,
        52.557240552547405,
        "galactic",
    )

    def test_coordinate_conversion(self):
        assert off_point_coord(
            on_point=self.given_on_point,
            offset=self.given_offset_1,
            coslat_applied=True,
            unit="deg",
        ) == pytest.approx(self.expected_coord_1)
        assert off_point_coord(
            on_point=self.given_on_point,
            offset=self.given_offset_2,
            coslat_applied=True,
            unit="deg",
        ) == pytest.approx(self.expected_coord_2)

    def test_coordinate_conversion_with_coslat_factor_apply(self):
        assert off_point_coord(
            on_point=self.given_on_point,
            offset=self.given_offset_1,
            coslat_applied=False,
            unit="deg",
        ) == pytest.approx(self.expected_coord_1_coslat_applied)
        assert off_point_coord(
            on_point=self.given_on_point,
            offset=self.given_offset_2,
            coslat_applied=False,
            unit="deg",
        ) == pytest.approx(self.expected_coord_2_coslat_applied)
        # Confirm approximation tolerance is small enough to distinguish the difference.
        with pytest.raises(AssertionError):
            assert off_point_coord(
                on_point=self.given_on_point,
                offset=self.given_offset_1,
                coslat_applied=False,
                unit="deg",
            ) == pytest.approx(self.expected_coord_1)
        with pytest.raises(AssertionError):
            assert off_point_coord(
                on_point=self.given_on_point,
                offset=self.given_offset_2,
                coslat_applied=False,
                unit="deg",
            ) == pytest.approx(self.expected_coord_2)

    def test_conversion_to_other_unit(self):
        assert off_point_coord(
            on_point=self.given_on_point,
            offset=self.given_offset_1,
            coslat_applied=True,
            unit="arcsec",
        ) == pytest.approx(self.expected_coord_1_arcsec)
        assert off_point_coord(
            on_point=self.given_on_point,
            offset=self.given_offset_2,
            coslat_applied=True,
            unit="arcsec",
        ) == pytest.approx(self.expected_coord_2_arcsec)

    def test_conversion_from_other_unit(self):
        assert off_point_coord(
            on_point=self.given_on_point_arcsec,
            offset=self.given_offset_1,
            coslat_applied=True,
            unit="deg",
        ) == pytest.approx(self.expected_coord_1)
        assert off_point_coord(
            on_point=self.given_on_point_arcsec,
            offset=self.given_offset_2,
            coslat_applied=True,
            unit="deg",
        ) == pytest.approx(self.expected_coord_2)

    altaz_kwargs = {"location": _LOC_NANTEN2, "obstime": "2022-04-21T04:24:50"}

    given_altaz_on_point = (Angle("195d10m5s"), Angle("30d40m50s"), "altaz")
    given_offset_3 = (Angle("3arcsec"), Angle("20arcsec"), "altaz")
    given_offset_4 = (Angle("3arcsec"), Angle("20arcsec"), "fk5")

    expected_coord_3 = (195.1688888888889, 30.686111111111114, "altaz")
    expected_coord_3_coslat_applied = (195.16902451908985, 30.686111111111114, "altaz")

    expected_coord_4 = (150.61421593988243, -74.32810403593722, "fk5")
    expected_coord_4_coslat_applied = (150.61646862802112, -74.32810403593722, "fk5")

    def test_conversion_from_AltAz_coordinate(self):
        assert off_point_coord(
            on_point=self.given_altaz_on_point,
            offset=self.given_offset_3,
            coslat_applied=True,
            unit="deg",
            **self.altaz_kwargs,
        ) == pytest.approx(self.expected_coord_3)
        assert off_point_coord(
            on_point=self.given_altaz_on_point,
            offset=self.given_offset_4,
            coslat_applied=True,
            unit="deg",
            **self.altaz_kwargs,
        ) == pytest.approx(self.expected_coord_4)

    def test_conversion_from_AltAz_coordinate_with_coslat_factor_apply(self):
        assert off_point_coord(
            on_point=self.given_altaz_on_point,
            offset=self.given_offset_3,
            coslat_applied=False,
            unit="deg",
            **self.altaz_kwargs,
        ) == pytest.approx(self.expected_coord_3_coslat_applied)
        assert off_point_coord(
            on_point=self.given_altaz_on_point,
            offset=self.given_offset_4,
            coslat_applied=False,
            unit="deg",
            **self.altaz_kwargs,
        ) == pytest.approx(self.expected_coord_4_coslat_applied)

    given_fk5_on_point = (Angle("15h25m35s"), Angle("50d40m30s"), "fk5")
    given_offset_5 = (Angle("3arcsec"), Angle("20arcsec"), "altaz")

    expected_coord_5 = (15.296886084116135, 13.483960609274352, "altaz")
    expected_coord_5_coslat_applied = (15.296909685964089, 13.483960609274352, "altaz")

    def test_conversion_to_AltAz_coordinate(self):
        assert off_point_coord(
            on_point=self.given_fk5_on_point,
            offset=self.given_offset_5,
            coslat_applied=True,
            unit="deg",
            **self.altaz_kwargs,
        ) == pytest.approx(self.expected_coord_5)

    def test_conversion_to_AltAz_coordinate_with_coslat_factor_apply(self):
        assert off_point_coord(
            on_point=self.given_fk5_on_point,
            offset=self.given_offset_5,
            coslat_applied=False,
            unit="deg",
            **self.altaz_kwargs,
        ) == pytest.approx(self.expected_coord_5_coslat_applied)

    given_multiple_absolute_points = (
        Angle(["1h2m3s", "2h3m4s", "3h4m5s"]),
        Angle(["30d40m50s", "20d30m40s", "10d20m30s"]),
        "fk5",
    )
    expected_multiple_absolute_points = (
        [15.5125, 30.76666667, 46.02083333],
        [30.68055556, 20.51111111, 10.34166667],
        "fk5",
    )

    def test_multiple_absolute_data(self):
        result = off_point_coord(
            absolute=self.given_multiple_absolute_points, unit="deg"
        )
        assert result[0] == pytest.approx(self.expected_multiple_absolute_points[0])
        assert result[1] == pytest.approx(self.expected_multiple_absolute_points[1])
        assert result[2] == self.expected_multiple_absolute_points[2]

    given_multiple_on_points = (
        Angle(["1h2m3s", "2h3m4s", "3h4m5s"]),
        Angle(["30d40m50s", "20d30m40s", "10d20m30s"]),
        "fk5",
    )
    given_single_offset = (Angle("3arcsec"), Angle("20arcsec"), "galactic")
    expected_multiple_coords_1 = (
        [125.62726517, 144.78171157, 168.08358605],
        [-32.13011099, -39.29685896, -40.61739643],
        "galactic",
    )

    def test_multiple_on_points_with_single_offset(self):
        result = off_point_coord(
            on_point=self.given_multiple_on_points,
            offset=self.given_single_offset,
            coslat_applied=True,
            unit="deg",
        )
        assert result[0] == pytest.approx(self.expected_multiple_coords_1[0])
        assert result[1] == pytest.approx(self.expected_multiple_coords_1[1])
        assert result[2] == self.expected_multiple_coords_1[2]

    given_multiple_offsets = (
        Angle(["1arcsec", "2arcsec", "3arcsec"]),
        Angle(["10arcsec", "20arcsec", "30arcsec"]),
        "galactic",
    )
    expected_multiple_coords_2 = (
        [125.62670961, 144.7814338, 168.08358605],
        [-32.13288877, -39.29685896, -40.61461865],
        "galactic",
    )

    def test_multiple_on_points_with_multiple_offsets(self):
        result = off_point_coord(
            on_point=self.given_multiple_on_points,
            offset=self.given_multiple_offsets,
            coslat_applied=True,
            unit="deg",
        )
        assert result[0] == pytest.approx(self.expected_multiple_coords_2[0])
        assert result[1] == pytest.approx(self.expected_multiple_coords_2[1])
        assert result[2] == self.expected_multiple_coords_2[2]
