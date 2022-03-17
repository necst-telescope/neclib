from n_const import PointingError
import numpy as np

from .. import utils


def derive_pointing_error(az, el, pointing_params_file):
    az, el = utils.force_data_type(az, el)

    params = PointingError(pointing_params_file)

    dx = (
        chi_Az * np.sin(omega_Az - az) * np.sin(el)
        + eps * np.sin(el)
        + chi2_Az * np.sin(2 * (omega2_Az - az)) * np.sin(el)
        + dAz * np.cos(el)
        + de
        + cor_v * np.cos(el + cor_p)
        + de_radio
    ) / np.cos(el)

    dy = (
        -chi_El * np.cos(omega_El - az)
        - chi2_El * np.cos(2 * (omega2_El - az))
        + g * el
        + gg * el ** 2
        + ggg * el ** 3
        + gggg * el ** 4
        + dEl
        + g_radio * el
        + gg_radio * el ** 2
        + ggg_radio * el ** 3
        + gggg_radio * el ** 4
        - cor_v * np.sin(el + cor_p)
        + dEl_radio
    )

    return dx, dy


def cor2ref(az, el, pointing_params_file):
    dx, dy = derive_pointing_error(az, el, pointing_params_file)
    refracted_az = az + dx
    refracted_el = el + dy

    return refracted_az, refracted_el


def ref2cor(az, el, pointing_params_file):
    dx, dy = derive_pointing_error(az, el, pointing_params_file)
    corrected_az = az - dx
    corrected_el = el - dy

    return corrected_az, corrected_el
