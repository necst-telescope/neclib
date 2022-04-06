from n_const import PointingError
import numpy as np

from .. import utils


def derive_pointing_error(az, el, pointing_params_file):
    az, el = utils.force_data_type(az, el)

    p = PointingError(pointing_params_file)

    dAz = (
        p.chi_Az * np.sin(p.omega_Az - az) * np.sin(el)
        + p.eps * np.sin(el)
        + p.chi2_Az * np.sin(2 * (p.omega2_Az - az)) * np.sin(el)
        + p.dAz * np.cos(el)
        + p.de
        + p.cor_v * np.cos(el + p.cor_p)
        + p.de_radio
    ) / np.cos(el)

    dEl = (
        -p.chi_El * np.cos(p.omega_El - az)
        - p.chi2_El * np.cos(2 * (p.omega2_El - az))
        + p.g * el
        + p.gg * el ** 2
        + p.ggg * el ** 3
        + p.gggg * el ** 4
        + p.dEl
        + p.g_radio * el
        + p.gg_radio * el ** 2
        + p.ggg_radio * el ** 3
        + p.gggg_radio * el ** 4
        - p.cor_v * np.sin(el + p.cor_p)
        + p.dEl_radio
    )

    return dAz, dEl


def enc2ref(az, el, pointing_params_file):
    dAz, dEl = derive_pointing_error(az, el, pointing_params_file)
    refracted_az = az + dAz
    refracted_el = el + dEl

    return refracted_az, refracted_el


def ref2enc(az, el, pointing_params_file):
    dAz, dEl = derive_pointing_error(az, el, pointing_params_file)
    encoder_az = az - dAz
    encoder_el = el - dEl

    return encoder_az, encoder_el
