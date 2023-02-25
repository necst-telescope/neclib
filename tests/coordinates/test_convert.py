import time

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import AltAz, SkyCoord, get_body
from astropy.time import Time

from neclib import config
from neclib.coordinates import CoordCalculator

from ..conftest import configured_tester_factory


class TestCoordCalculator(configured_tester_factory("config_default")):
    def test_diffraction_param_type(self) -> None:
        calc = CoordCalculator(location=config.location)
        assert isinstance(calc.obswl, u.Quantity)
        assert isinstance(calc.obsfreq, u.Quantity)
        assert isinstance(calc.relative_humidity, u.Quantity)
        assert isinstance(calc.pressure, u.Quantity)
        assert isinstance(calc.temperature, u.Quantity)

    def test_diffraction_param_update(self) -> None:
        calc = CoordCalculator(location=config.location)
        calc.obswl = 1.0
        calc.obsfreq = 1.0
        calc.relative_humidity = 1.0
        calc.pressure = 1.0
        calc.temperature = 1.0
        assert calc.obswl == 1.0 * u.mm
        assert calc.obsfreq == 1.0 * u.GHz
        assert calc.relative_humidity == 1.0 * u.dimensionless_unscaled
        assert calc.pressure == 1.0 * u.hPa
        assert calc.temperature == 1.0 * u.deg_C

    def test_get_body(self) -> None:
        calc = CoordCalculator(location=config.location)
        now = Time(time.time(), format="unix")

        # Solar system body
        coord = calc.get_body("jupiter", now).fk5
        expected = get_body("jupiter", now, calc.location).fk5
        assert coord.data.lon.value == pytest.approx(expected.data.lon.value)
        assert coord.data.lat.value == pytest.approx(expected.data.lat.value)

        # Non-solar system body
        coord = calc.get_body("m31", now).fk5
        expected = SkyCoord.from_name("m31", frame="icrs").fk5
        assert coord.data.lon.value == pytest.approx(expected.data.lon.value)
        assert coord.data.lat.value == pytest.approx(expected.data.lat.value)

    class TestTransformTo:
        def test_same_frame(self) -> None:
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(0, 0, unit="deg", frame="fk5")
            transformed = calc.transform_to(coord, "fk5")
            assert transformed.data.lon.value == pytest.approx(coord.data.lon.value)
            assert transformed.data.lat.value == pytest.approx(coord.data.lat.value)

        def test_similar_frame(self) -> None:
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(0, 0, unit="deg", frame="fk5")
            transformed = calc.transform_to(coord, "fk4")
            expected = coord.transform_to("fk4")
            assert transformed.data.lon.value != pytest.approx(coord.data.lon.value)
            assert transformed.data.lat.value != pytest.approx(coord.data.lat.value)
            assert transformed.data.lon.value == pytest.approx(expected.data.lon.value)
            assert transformed.data.lat.value == pytest.approx(expected.data.lat.value)

        def test_different_frame(self) -> None:
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(0, 0, unit="deg", frame="fk5")
            transformed = calc.transform_to(coord, "galactic")
            expected = coord.transform_to("galactic")
            assert transformed.data.lon.value != pytest.approx(coord.data.lon.value)
            assert transformed.data.lat.value != pytest.approx(coord.data.lat.value)
            assert transformed.data.lon.value == pytest.approx(expected.data.lon.value)
            assert transformed.data.lat.value == pytest.approx(expected.data.lat.value)

        def test_to_altaz_frame(self) -> None:
            now = time.time()
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(0, 0, unit="deg", frame="fk5")

            # Test with obstime as an argument
            transformed = calc.transform_to(coord, "altaz", obstime=now)
            expected = coord.transform_to(
                AltAz(obstime=Time(now, format="unix"), location=config.location)
            )
            assert transformed.data.lon.value != pytest.approx(coord.data.lon.value)
            assert transformed.data.lat.value != pytest.approx(coord.data.lat.value)
            assert transformed.data.lon.value == pytest.approx(expected.data.lon.value)
            assert transformed.data.lat.value == pytest.approx(expected.data.lat.value)

            # Test with obstime contained in frame object
            transformed = calc.transform_to(
                coord, AltAz(obstime=Time(now, format="unix"))
            )
            expected = coord.transform_to(
                AltAz(obstime=Time(now, format="unix"), location=config.location)
            )
            assert transformed.data.lon.value != pytest.approx(coord.data.lon.value)
            assert transformed.data.lat.value != pytest.approx(coord.data.lat.value)
            assert transformed.data.lon.value == pytest.approx(expected.data.lon.value)
            assert transformed.data.lat.value == pytest.approx(expected.data.lat.value)

        def test_from_altaz_frame(self) -> None:
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(
                0,
                0,
                unit="deg",
                frame="altaz",
                location=config.location,
                obstime=Time(time.time(), format="unix"),
            )
            transformed = calc.transform_to(coord, "fk5")
            expected = coord.transform_to("fk5")
            assert transformed.data.lon.value != pytest.approx(coord.data.lon.value)
            assert transformed.data.lat.value != pytest.approx(coord.data.lat.value)
            assert transformed.data.lon.value == pytest.approx(expected.data.lon.value)
            assert transformed.data.lat.value == pytest.approx(expected.data.lat.value)

        def test_from_altaz_to_altaz(self) -> None:
            now = Time(time.time(), format="unix")
            calc = CoordCalculator(location=config.location)
            coord = SkyCoord(
                0, 0, unit="deg", frame="altaz", location=config.location, obstime=now
            )
            transformed = calc.transform_to(coord, "altaz")
            assert transformed.data.lon.value == pytest.approx(coord.data.lon.value)
            assert transformed.data.lat.value == pytest.approx(coord.data.lat.value)

        def test_altaz_with_no_obstime_is_error(self) -> None:
            with pytest.raises(ValueError):
                calc = CoordCalculator(location=config.location)
                coord = SkyCoord(
                    0, 0, unit="deg", frame="altaz", location=config.location
                )
                calc.transform_to(coord, "fk5")
            with pytest.raises(ValueError):
                calc = CoordCalculator(location=config.location)
                coord = SkyCoord(
                    0, 0, unit="deg", frame="fk5", location=config.location
                )
                calc.transform_to(coord, "altaz")
            with pytest.raises(ValueError):
                calc = CoordCalculator(location=config.location)
                coord = SkyCoord(
                    0, 0, unit="deg", frame="altaz", location=config.location
                )
                calc.transform_to(coord, "altaz", obstime=0)
            with pytest.raises(ValueError):
                calc = CoordCalculator(location=config.location)
                coord = SkyCoord(
                    0, 0, unit="deg", frame="altaz", location=config.location
                )
                calc.transform_to(coord, "altaz")

        def test_frame_name_dialect(self) -> None:
            calc = CoordCalculator(location=config.location)

            # J2000 <-> FK5
            coord = SkyCoord(0, 0, unit="deg", frame="fk5")
            transformed = calc.transform_to(coord, "j2000")
            assert transformed.data.lon.value == pytest.approx(coord.data.lon.value)
            assert transformed.data.lat.value == pytest.approx(coord.data.lat.value)

            # B1950 <-> FK4
            coord = SkyCoord(0, 0, unit="deg", frame="fk4")
            transformed = calc.transform_to(coord, "b1950")
            assert transformed.data.lon.value == pytest.approx(coord.data.lon.value)
            assert transformed.data.lat.value == pytest.approx(coord.data.lat.value)

            # Horizontal <-> AltAz
            now = Time(time.time(), format="unix")
            coord = SkyCoord(
                0, 0, unit="deg", frame="altaz", location=config.location, obstime=now
            )
            transformed = calc.transform_to(coord, "horizontal")
            assert transformed.data.lon.value == pytest.approx(coord.data.lon.value)
            assert transformed.data.lat.value == pytest.approx(coord.data.lat.value)

    class TestToApparentAltAz:
        def test_length(self) -> None:
            calc = CoordCalculator(location=config.location)
            now = Time(time.time(), format="unix")

            # Auto-generate the obstime
            coord = SkyCoord(0, 0, unit="deg", frame="fk5")
            transformed = calc.to_apparent_altaz(coord)
            assert coord.size == 1
            assert transformed.size == config.antenna_command_frequency

            # Single obstime specified
            coord = SkyCoord(0, 0, unit="deg", frame="fk5", obstime=now)
            transformed = calc.to_apparent_altaz(coord)
            assert coord.size == 1
            assert transformed.size == config.antenna_command_frequency

            # Single obstime specified for multiple coordinates
            coord = SkyCoord([0, 0, 0], [0, 0, 0], unit="deg", frame="fk5", obstime=now)
            transformed = calc.to_apparent_altaz(coord)
            assert coord.size == 3
            assert transformed.shape == (3, config.antenna_command_frequency)

            # All obstime specified
            coord = SkyCoord(
                [0, 0, 0],
                [0, 0, 0],
                unit="deg",
                frame="fk5",
                obstime=Time(np.r_[now.unix, now.unix, now.unix], format="unix"),
            )
            transformed = calc.to_apparent_altaz(coord)
            assert coord.size == 3
            assert transformed.size == 3

        def test_dont_track_altaz(self) -> None:
            calc = CoordCalculator(location=config.location)
            now = Time(time.time(), format="unix")
            coord = SkyCoord(
                0, 0, unit="deg", frame="altaz", location=config.location, obstime=now
            )
            transformed = calc.to_apparent_altaz(coord)
            assert coord.size == 1
            assert transformed.size == config.antenna_command_frequency
            assert transformed.data.lon.value == pytest.approx(coord.data.lon.value)
            assert transformed.data.lat.value == pytest.approx(coord.data.lat.value)
