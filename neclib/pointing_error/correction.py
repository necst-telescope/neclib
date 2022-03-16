import numpy as np
from astropy.coordinates import SkyCoord
import xarray as xr


def apply_kisa_test(azel, hosei):

    if isinstance(azel, SkyCoord):

        az = azel.az.rad
        el = azel.alt.rad

    elif isinstance(azel, tuple):

        if isinstance(azel[0], np.ndarray):
            az = np.deg2rad(azel[0])
            el = np.deg2rad(azel[1])

        if isinstance(azel[0], xr.DataArray):
            az = np.deg2rad(azel[0].values)
            el = np.deg2rad(azel[1].values)

    else:
        raise (TypeError("Input must be a Skycoord or a tuple of ndarray or xarray"))

    with open(hosei, "r") as f:
        kisa = f.read().splitlines()
    kisa = [float(n) for n in kisa]

    kisa[3] = np.deg2rad(kisa[3])
    kisa[6] = np.deg2rad(kisa[6])
    kisa[8] = np.deg2rad(kisa[8])
    kisa[10] = np.deg2rad(kisa[10])
    kisa[19] = np.deg2rad(kisa[19])
    el_d = np.rad2deg(el)

    dx = (
        kisa[2] * np.sin(kisa[3] - az) * np.sin(el)
        + kisa[4] * np.sin(el)
        + kisa[0] * np.cos(el)
        + kisa[1]
        + kisa[5] * np.cos(2 * (kisa[6] - az)) * np.sin(el)
        + kisa[16]
        + kisa[18] * np.cos(el + kisa[19])
    ) / np.cos(el)

    dy = (
        -kisa[7] * np.cos(kisa[8] - az)
        - kisa[9] * np.sin(2 * (kisa[10] - az))
        + kisa[15]
        + kisa[11] * el_d
        + kisa[12] * el_d ** 2
        + kisa[13] * el_d ** 3
        + kisa[14] * el_d ** 4
        + kisa[17]
        - kisa[18] * np.sin(el + kisa[19])
        + kisa[20] * el_d
        + kisa[21] * el_d ** 2
        + kisa[22] * el_d ** 3
        + kisa[23] * el_d ** 4
    )

    if isinstance(azel, SkyCoord):

        paz = azel.az.deg + dx
        pel = azel.alt.deg + dy

    elif isinstance(azel, tuple):

        if isinstance(azel[0], np.ndarray):
            paz = azel[0] + dx
            pel = azel[1] + dy

        if isinstance(azel[0], xr.DataArray):
            paz = azel[0].values + dx
            pel = azel[1].values + dy
            
    return paz, pel