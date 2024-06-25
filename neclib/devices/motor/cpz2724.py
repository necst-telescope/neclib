__all__ = ["CPZ2724"]

import time
from typing import Union

from ... import get_logger, utils
from .motor_base import Motor


class CPZ2724(Motor):
    Manufacturer = "Interface"
    Model = "CPZ2724"

    Identifier = "rsw_id"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.rsw_id = self.Config.rsw_id
        self.cw = self.Config.cw
        self.ccw = self.Config.ccw
        self.puls_rate = self.Config.puls_rate
        self.motor_speed = self.Config.motor_speed

        self.io = self._initialize_io()

    @utils.skip_on_simulator
    def _initialize_io(self):
        import pyinterface

        self.io = pyinterface.open(2724, self.rsw_id)
        if self.io is None:
            raise RuntimeError("Cannot communicate with the CPZ board.")

        self.io.initialize()

        return self.io

    def get_step(self, axis: str):
        if axis == "memb":
            step = self.get_memb_status()
        elif axis == "m2":
            step = self.get_pos()

        return step

    def set_step(self, step: Union[str, int], axis: str) -> None:
        if axis == "memb":
            self.memb_move(step)
        elif axis == "m2":
            puls = self.um_to_puls(step)
            self.MoveIndexFF(puls)

        return super().set_step(step, axis)

    def get_speed(self, axis: str):
        pass

    def set_speed(self, speed: float, axis: str):
        pass

    def get_pos(self):
        buff = []
        buff2 = []
        in1_8 = self.io.input_byte("IN1_8").to_list()
        in9_16 = self.io.input_byte("IN9_16").to_list()

        if in9_16[6] == 1:  # [0,0,0,0,0,0,1,0]:
            m_limit_up = 1
        else:
            m_limit_up = 0
        if in9_16[7] == 1:  # [0,0,0,0,0,0,0,1]:
            m_limit_down = 1
        else:
            m_limit_down = 0

        for i in range(8):
            if i != 0 and in1_8 == [0, 0, 0, 0, 0, 0, 0, 0]:
                buff.append(0)
            if in1_8[i] == 0:
                buff.append(0)
            else:
                buff.append(1)

        for i in range(8):
            if i != 0 and in9_16 == [0, 0, 0, 0, 0, 0, 0, 0]:
                buff2.append(0)
            if in9_16[i] == 0:
                buff2.append(0)
            else:
                buff2.append(1)

        # calculate each digit
        total = (
            buff[0] * 1
            + buff[1] * 2
            + buff[2] * pow(2.0, 2.0)
            + buff[3] * pow(2.0, 3.0)
        ) / 100.0
        total = (
            total
            + (
                buff[4] * 1
                + buff[5] * 2
                + buff[6] * pow(2.0, 2.0)
                + buff[7] * pow(2.0, 3.0)
            )
            / 10.0
        )
        total2 = (
            buff2[0] * 1
            + buff2[1] * 2
            + buff2[2] * pow(2.0, 2.0)
            + buff2[3] * pow(2.0, 3.0)
        )
        total2 = total2 + (buff2[4] * 1) * 10

        m_pos = (total + total2) * pow(-1.0, (buff2[5] + 1))
        return [m_pos, m_limit_up, m_limit_down]

    def um_to_puls(self, dist: int, status: list[int]) -> int:
        puls = int(dist) * self.puls_rate
        if (
            dist / 1000.0 + float(status[0]) <= -4.0
            or dist / 1000.0 + float(status[0]) >= 5.5
        ):
            print("move limit")
            return
        if status[1] == 0 and puls < 0:
            print("can't move up direction")
            return
        if status[2] == 0 and puls > 0:
            print("can't move down direction")
            return
        return puls

    def get_memb_status(self):
        ret = self.io.input_point(8, 3)
        if ret[0] == 0:
            self.memb_act = "OFF"
        else:
            self.memb_act = "DRIVE"

        if ret[1] == 0:
            if ret[2] == 0:
                self.memb_pos = "MOVE"
            else:
                self.memb_pos = "CLOSE"
        else:
            self.memb_pos = "OPEN"
        return [self.memb_act, self.memb_pos]

    def memb_move(self, pos: str) -> None:
        ret = self.get_memb_status()
        if ret[1] != pos:
            buff = self.Config.position[pos.lower()]
            self.io.output_point(buff, 7)
            while ret[1] != pos:
                time.sleep(5)
                ret = self.get_memb_status()
        buff = [0, 0]
        self.io.output_point(buff, 7)

    def Strobe(self):
        time.sleep(0.01)
        self.io.output_byte("OUT9_16", [1, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(0.01)
        self.io.output_byte("OUT9_16", [0, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(0.01)
        return

    def MoveIndexFF(self, puls: int):
        if puls >= -65535 and puls <= 65535:
            # index mode
            self.io.output_byte("OUT1_8", [0, 0, 0, 1, 0, 0, 0, 0])
            self.Strobe()
            # step no.
            self.io.output_byte("OUT1_8", [1, 1, 1, 1, 1, 1, 1, 1])
            self.Strobe()
            # position set
            self.io.output_byte("OUT1_8", [0, 0, 0, 0, 0, 0, 1, 1])
            self.Strobe()
            # direction
            if puls >= 0:
                self.io.output_byte("OUT1_8", self.cw, fmt="<I")
                self.Strobe()
            else:
                self.io.output_byte("OUT1_8", self.ccw, fmt="<I")
                self.Strobe()
            # displacement
            self.io.output_byte("OUT1_8", [0, 0, 0, 0, 0, 0, 0, 0])
            self.Strobe()
            self.io.output_byte("OUT1_8", int(abs(puls) / 256), fmt="<I")
            self.Strobe()
            self.io.output_byte("OUT1_8", int(abs(puls) % 256), fmt="<I")
            self.Strobe()
            # start
            self.io.output_byte("OUT1_8", [0, 0, 0, 1, 1, 0, 0, 0])
            self.Strobe()
            time.sleep((abs(puls) / self.motor_speed / 10.0) + 1.0)
            print("Motor stopped")
        else:
            print("Puls number is over.")
            print("Please command x : 10*x [um]")
            return False
        return True
