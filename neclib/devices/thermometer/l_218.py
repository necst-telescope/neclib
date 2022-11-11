import astropy.units as u

import ogameasure

from ... import config
from .thermometer_base import Thermometer


class L218(Thermometer):

    Manufacturer = "Lakeshore"
    Model = "Model218"

    def __init__(self) -> None:
        com = ogameasure.gpib_prologix(
            config.rx_l218_host, gpibport=config.rx_l218_gpibadrr
        )
        self.thermometer = ogameasure.Lakeshore.model218(com)
        # GPIBで接続できるようにすること。

    def get_temp(self) -> u.Quantity:
        data = self.thermometer.kelvin_reading_query()
        return data * u.K

    def finalize(self) -> None:
        self.thermometer.close()
