import astropy.units as u
import ogameasure

from .thermometer_base import Thermometer


class Model218(Thermometer):

    Manufacturer = "LakeShore"
    Model = "Model218"

    Identifier = "host"

    def __init__(self) -> None:
        com = ogameasure.gpib_prologix(host=self.Config.host, gpibport=self.Config.port)
        self.thermometer = ogameasure.Lakeshore.model218(com)

    def get_temp(self) -> u.Quantity:
        data = self.thermometer.kelvin_reading_query()
        return data * u.K

    def finalize(self) -> None:
        self.thermometer.com.close()
