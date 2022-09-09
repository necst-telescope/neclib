import astropy.constants as const
import astropy.units as u
import pytest
from astropy.coordinates import EarthLocation, FK5
from astropy.time import Time

from neclib.coordinates import CoordCalculator

obstime = pytest.mark.parametrize(
    "obstime", [1662697435.261011, Time(1662697435.261011, format="unix")]
)
temperature = pytest.mark.parametrize(
    "temperature", [290 << u.K, (290 << u.K).to("deg_C", equivalencies=u.temperature())]
)
obs_spectrum = pytest.mark.parametrize(
    "obs_spectrum", [{"obsfreq": 230 << u.GHz}, {"obswl": const.c / (230 << u.GHz)}]
)


class TestCoordCalculator:

    location = EarthLocation("138.472153deg", "35.940874deg", "1386m")
    pressure = 850 << u.hPa
    humidity = 0.5

    @obstime
    def test_get_altaz_by_name_no_weather(self, data_dir, obstime):
        bodies = [
            ("sun", 221.4475811, 49.819631),
            ("RCW38", 213.67880546, -10.01465125),
        ]
        calc = CoordCalculator(self.location, data_dir / "sample_pointing_param.toml")
        for body, az_deg, el_deg in bodies:
            az, el = calc.get_altaz_by_name(body, obstime)
            assert az.to("deg").value == pytest.approx(az_deg)
            assert el.to("deg").value == pytest.approx(el_deg)

    @obstime
    @temperature
    @obs_spectrum
    def test_get_altaz_by_name_solar_system(
        self, data_dir, obstime, temperature, obs_spectrum
    ):
        bodies = [
            ("sun", 221.44758569, 49.83187031),
            ("moon", 69.04964711, -52.6282665),
            ("mercury", 187.29019581, 44.69952053),
            ("venus", 239.37897575, 47.53142283),
            ("mars", 305.58636077, -13.57467281),
            ("jupiter", 9.3499979, -54.50739779),
            ("saturn", 77.65120141, -43.49320294),
            ("uranus", 321.43299915, -29.8428896),
            ("neptune", 28.91602113, -55.55108824),
        ]
        calc = CoordCalculator(
            self.location,
            data_dir / "sample_pointing_param.toml",
            pressure=self.pressure,
            temperature=temperature,
            relative_humidity=self.humidity,
            **obs_spectrum,
        )
        for body, az_deg, el_deg in bodies:
            az, el = calc.get_altaz_by_name(body, obstime)
            assert az.to("deg").value == pytest.approx(az_deg)
            assert el.to("deg").value == pytest.approx(el_deg)

    @obstime
    @temperature
    @obs_spectrum
    def test_get_altaz_by_name_other_body(
        self, data_dir, obstime, temperature, obs_spectrum
    ):
        bodies = [
            ("IRC+10216", 251.1451957, 41.59059866),
            ("RCW38", 213.67881876, -9.83537973),
        ]
        calc = CoordCalculator(
            self.location,
            data_dir / "sample_pointing_param.toml",
            pressure=self.pressure,
            temperature=temperature,
            relative_humidity=self.humidity,
            **obs_spectrum,
        )
        for body, az_deg, el_deg in bodies:
            az, el = calc.get_altaz_by_name(body, obstime)
            assert az.to("deg").value == pytest.approx(az_deg)
            assert el.to("deg").value == pytest.approx(el_deg)

    @obstime
    def test_get_altaz_no_weather(self, data_dir, obstime):
        cases = [
            (10, 20, "fk5", "deg"),
            (10 << u.deg, 20 << u.deg, "fk5", None),
            (10, 20, "fk5", u.deg),
            (10 << u.deg, 20 << u.deg, FK5, None),
            (10, 20, FK5, u.deg),
        ]
        expected_az = 1.19021183
        expected_el = -35.78464637

        calc = CoordCalculator(self.location, data_dir / "sample_pointing_param.toml")
        for lon, lat, frame, unit in cases:
            az, el = calc.get_altaz(lon, lat, frame, obstime=obstime, unit=unit)
            assert az.to("deg").value == pytest.approx(expected_az)
            assert el.to("deg").value == pytest.approx(expected_el)

    @obstime
    @temperature
    @obs_spectrum
    def test_get_altaz(self, data_dir, obstime, temperature, obs_spectrum):
        cases = [
            (10, 20, "fk5", "deg"),
            (10 << u.deg, 20 << u.deg, "fk5", None),
            (10, 20, "fk5", u.deg),
            (10 << u.deg, 20 << u.deg, FK5, None),
            (10, 20, FK5, u.deg),
        ]
        expected_az = 1.19019765
        expected_el = -35.66559995

        calc = CoordCalculator(
            self.location,
            data_dir / "sample_pointing_param.toml",
            pressure=self.pressure,
            temperature=temperature,
            relative_humidity=self.humidity,
            **obs_spectrum,
        )
        for lon, lat, frame, unit in cases:
            az, el = calc.get_altaz(lon, lat, frame, obstime=obstime, unit=unit)
            assert az.to("deg").value == pytest.approx(expected_az)
            assert el.to("deg").value == pytest.approx(expected_el)

    @obstime
    def test_get_altaz_array(self, data_dir, obstime):
        cases = [
            ([10, 10], [20, 20], "fk5", "deg"),
            ([10, 10] << u.deg, [20, 20] << u.deg, "fk5", None),
            ([10, 10], [20, 20], "fk5", u.deg),
            ([10, 10] << u.deg, [20, 20] << u.deg, FK5, None),
            ([10, 10], [20, 20], FK5, u.deg),
        ]
        expected_az = [1.19021183, 1.19021183]
        expected_el = [-35.78464637, -35.78464637]

        calc = CoordCalculator(self.location, data_dir / "sample_pointing_param.toml")
        for lon, lat, frame, unit in cases:
            az, el = calc.get_altaz(lon, lat, frame, obstime=obstime, unit=unit)
            assert az.to("deg").value == pytest.approx(expected_az)
            assert el.to("deg").value == pytest.approx(expected_el)
