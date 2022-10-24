from astropy.coordinates import Angle

from neclib.parameters import PointingErrorData


class TestPointingErrorData:

    expected = {
        "dAz": Angle("5314.2466754691195arcsec"),
        "de": Angle("382arcsec"),
        "chi_Az": Angle("-27.743114809726713arcsec"),
        "omega_Az": Angle("-10.004233550100272deg"),
        "eps": Angle("-13.562343977659976arcsec"),
        "chi2_Az": Angle("-3.2283345930067489arcsec"),
        "omega2_Az": Angle("-34.73486665318979deg"),
        "chi_El": Angle("-30.046387189617871arcsec"),
        "omega_El": Angle("-16.233694100299584deg"),
        "chi2_El": Angle("-1.1446000035021269arcsec"),
        "omega2_El": Angle("-41.474874481601418deg"),
        "g": -0.17220574801726421,
        "gg": 0.0,
        "ggg": 0.0,
        "gggg": 0.0,
        "dEl": Angle("6520.2376117807198arcsec"),
        "de_radio": Angle("-394.46arcsec"),
        "del_radio": Angle("210.7228arcsec"),
        "cor_v": Angle("27.434arcsec"),
        "cor_p": Angle("-31.6497deg"),
        "g_radio": -0.454659,
        "gg_radio": 0.0128757,
        "ggg_radio": 0.000000,
        "gggg_radio": 0.000000,
    }

    def test_from_file(self, data_dir):
        actual = PointingErrorData.from_file(data_dir / "sample_pointing_param.toml")
        for name, value in self.expected.items():
            assert getattr(actual, name) == value
            assert actual[name] == value

    def test_from_text_file(self, data_dir):
        actual = PointingErrorData.from_text_file(
            data_dir / "sample_pointing_param.txt"
        )
        for name, value in self.expected.items():
            assert getattr(actual, name) == value
            assert actual[name] == value
