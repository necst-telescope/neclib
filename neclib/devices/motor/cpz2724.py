__all__ = ["CPZ2724"]

import time
from typing import Union

from ... import get_logger, utils
from .motor_base import Motor


class CPZ2724(Motor):
    # """Digital I/O board for membrane opener of NANTEN2.
    # Notes
    # -----
    # Configuration items for this device:
    # rsw_id : {0, 1, ..., 16} or {"0", "1", ..., "9", "A", ..., "F"}
    #     Board identifier. This should be set to the same value as the rotary switch
    #     "RSW1" mounted on the side of the board. The board is shipped with default
    #     RSW1 setting of 0. This ID would be non-zero, when multiple PCI board of same
    #     model are mounted on a single FA (Factory Automation) controller.
    # See defaults setting file in neclib/defaults/config.toml.
    # """

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
        else:
            raise ValueError(f"No valid axis : {axis}")

        return step

    def set_step(self, step: Union[str, int], status: list[int], axis: str) -> None:
        if axis == "memb":
            self.memb_move(step)
        elif axis == "m2":
            dist = step
            puls = self.um_to_puls(dist, status)
            self.MoveIndexFF(puls)
        else:
            raise ValueError(f"No valid axis : {axis}")

        return

    def get_speed(self, axis: str):
        pass

    def set_speed(self, speed: str):
        buffer = [0, 0, 0, 0]
        global stop
        if turn == "right":
            buffer[0] = 0
        else:
            buffer[0] = 1
        if speed == "low":
            buffer[2:4] = [0, 0]
        elif speed == "mid":
            buffer[2:4] = [1, 0]
        else:
            buffer[2:4] = [0, 1]
        if self.stop[0] == 1:
            buffer[1] = 0
        else:
            buffer[1] = 1
        self.io.output_point(buffer, 1)
        return

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

    def get_dome_status(self):
        ret = self.io.input_point(2, 6)
        if ret[0] == 0:
            self.right_act = "OFF"
        else:
            self.right_act = "DRIVE"

        if ret[1] == 0:
            if ret[2] == 0:
                self.right_pos = "MOVE"
            else:
                self.right_pos = "CLOSE"
        else:
            self.right_pos = "OPEN"

        if ret[3] == 0:
            self.left_act = "OFF"
        else:
            self.left_act = "DRIVE"

        if ret[4] == 0:
            if ret[5] == 0:
                self.left_pos = "MOVE"
            else:
                self.left_pos = "CLOSE"
        else:
            self.left_pos = "OPEN"
        return [self.right_act, self.right_pos, self.left_act, self.left_pos]

    def get_action(self) -> str:
        ret = self.io.input_point(1, 1)
        if ret == 0:
            self.move_status = "OFF"
        else:
            self.move_status = "DRIVE"
        return self.move_status

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

    def dome_stop(self):
        buff = [0]
        self.dio.output_point(buff, 2)
        return

    def dome_move(self, dist, pos, track=False) -> float:
        pos_arcsec = float(pos)  # [arcsec]
        pos = pos_arcsec / 3600.0
        pos = pos % 360.0
        dist = float(dist) % 360.0
        diff = dist - pos
        dir = diff % 360.0
        print("dir: ", dir)
        """
        if dir < 0:
            dir = dir*(-1)
        """
        if dir == 0:
            return dir
        # """
        # if dir < 0:
        #    if abs(dir) >= 180:
        #        turn = 'right'
        #    else:
        #        turn = 'left'
        # """
        else:
            if abs(dir) >= 180:
                turn = "left"
            else:
                turn = "right"
        if abs(dir) < 5.0 or abs(dir) > 355.0:
            speed = "low"
        elif abs(dir) > 15.0 and abs(dir) < 345.0:
            speed = "high"
        else:
            speed = "mid"
        if not abs(dir) < 1.5 and not abs(dir) > 358.5:
            self.set_speed(turn, speed)
            if track:
                time.sleep(0.1)
                return dir
        return dir

    def dome_open_close(self, pos: str) -> None:
        # posにはopen or close を入れる
        ret = self.get_dome_status()
        if ret[1] != pos and ret[3] != pos:
            buff = self.Config.position[pos.lower()]
            self.io.output_point(buff, 5)
            while ret[1] != pos and ret[3] != pos:
                time.sleep(5)
                ret = self.get_door_status()
        buff = [0, 0]
        self.io.output_point(buff, 5)
        return

    def dome_fan(self, fan):
        # fanにはon or off を入れる
        if fan == "on":
            fan_bit = [1, 1]
            dio.output_point(fan_bit, 9)
        else:
            fan_bit = [0, 0]
            dio.output_point(fan_bit, 9)
        return

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

    def finalize(self) -> None:
        pass
