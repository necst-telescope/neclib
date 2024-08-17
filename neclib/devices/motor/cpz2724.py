__all__ = ["CPZ2724"]

import struct
import time

from astropy import units as u

from ... import get_logger, utils
from .motor_base import Motor


class CPZ2724(Motor):
    """Digital I/O board for membrane opener of NANTEN2.

    Notes
    -----
    Configuration items for this device:

    rsw_id : {0, 1, ..., 16} or {"0", "1", ..., "9", "A", ..., "F"}
        Board identifier. This should be set to the same value as the rotary switch
        "RSW1" mounted on the side of the board. The board is shipped with default
        RSW1 setting of 0. This ID would be non-zero, when multiple PCI board of same
        model are mounted on a single FA (Factory Automation) controller.

    See defaults setting file in neclib/defaults/config.toml.
    """

    Manufacturer = "Interface"
    Model = "CPZ2724"

    Identifier = "rsw_id"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)
        self.rsw_id = self.Config.rsw_id

        self.speed_to_rate = float((7 / 12) * 10000)

        self.io = self._initialize_io()

    @utils.skip_on_simulator
    def _initialize_io(self):
        import pyinterface

        io = pyinterface.open(2724, self.rsw_id)
        if io is None:
            raise RuntimeError("Cannot communicate with the CPZ board.")

        io.initialize()

        return io

    # Antenna Control

    def set_speed(
        self,
        speed: float,
        axis: str,
    ):
        self.max_rate = self.Config.max_rate
        speed_float = float(speed) * self.speed_to_rate

        if speed_float > self.max_rate:
            speed_float = self.max_rate
        if speed_float < -self.max_rate:
            speed_float = self.max_rate

        self.antenna_move(int(speed_float), axis)
        return

    def get_speed(self, axis: str) -> float:
        word = None
        if axis == "az":
            word = "IN1_16"
        elif axis == "el":
            word = "IN17_32"
        else:
            raise ValueError(f"No valid axis : {axis}")
        status = self.io.input_word(word)
        status_int = struct.unpack("<h", status.bytes)
        (speed,) = status_int
        speed_deg = speed / 3600
        return speed_deg * u.deg / u.s

    def antenna_move(self, speed: int, axis: str) -> None:
        word = None
        if axis == "az":
            word = "OUT1_16"
        elif axis == "el":
            word = "OUT17_32"
        else:
            raise ValueError(f"No valid axis : {axis}")

        cmd = list(
            map(
                int, "".join([format(b, "08b")[::-1] for b in struct.pack("<h", speed)])
            )
        )  # [::-1] for little endian.
        self.io.output_word(word, cmd)

    def antenna_stop(self):
        self.antenna_move(0, "az")
        self.antenna_move(0, "el")

    def antenna_status(self) -> dict[str, str]:
        status_dict = {}
        for i in ["az", "el"]:
            speed = self.get_speed(i)
            if speed == 0:
                antenna_status = "STOP"
            else:
                antenna_status = "MOVE"
            status_dict[i] = antenna_status
        return status_dict

    def set_step(self, step: int, axis: str) -> None:
        pass

    def get_step(self, axis: str) -> int:
        return 0

    # Dome Control

    def dome_move(self, speed: str, turn: str):
        buffer = [0, 1, 0, 0]
        if turn == "right":
            buffer[0] = 0
        elif turn == "left":
            buffer[0] = 1
        else:
            raise ValueError(f"No valid turn direction : {turn}")
        if speed == "low":
            buffer[2:4] = [0, 0]
        elif speed == "mid":
            buffer[2:4] = [1, 0]
        elif speed == "high":
            buffer[2:4] = [0, 1]
        else:
            raise ValueError(f"No valid speed : {speed}")
        self.io.output_point(buffer, 1)
        return

    def dome_oc(self, pos: str) -> None:
        # posにはopen or close を入れる
        ret = self.dome_status()
        if (ret[1].lower() != pos) & (ret[3].lower() != pos):
            buff = self.Config.position[pos.lower()]
            self.io.output_point(buff, 5)
        return

    def dome_stop(self) -> None:
        buff = [0]
        self.io.output_point(buff, 2)
        return

    def dome_pose(self) -> None:
        buff = [0, 0]
        self.io.output_point(buff, 5)
        return

    def dome_fan(self, fan: str) -> None:
        # fanにはon or off を入れる
        if fan == "on":
            fan_bit = [1, 1]
            self.io.output_point(fan_bit, 9)
        else:
            fan_bit = [0, 0]
            self.io.output_point(fan_bit, 9)

    def dome_status(self):
        ret = self.io.input_point(2, 6)
        # dome 開閉中："DRIVE", domeの扉止まっている："OFF"
        if ret[0] == 1:
            self.right_act = "DRIVE"
            self.right_pos = "MOVE"
        else:
            self.right_act = "OFF"
            if (ret[1] == 1) & (ret[2] == 0):
                self.right_pos = "OPEN"
            elif (ret[1] == 0) & (ret[2] == 1):
                self.right_pos = "CLOSE"
            else:
                self.right_pos = "POSE"

        if ret[3] == 1:
            self.left_act = "DRIVE"
            self.left_pos = "MOVE"
        else:
            self.left_act = "OFF"
            if (ret[4] == 1) & (ret[5] == 0):
                self.left_pos = "OPEN"
            elif (ret[4] == 0) & (ret[5] == 1):
                self.left_pos = "CLOSE"
            else:
                self.left_pos = "POSE"

        return [self.right_act, self.right_pos, self.left_act, self.left_pos]

    def dome_limit_check(self):
        limit = self.io.input_point(12, 4)
        ret = 0
        if limit[0:4] == [0, 0, 0, 0]:
            ret = 0
        elif limit[0:4] == [1, 0, 0, 0]:
            ret = 1
        elif limit[0:4] == [0, 1, 0, 0]:
            ret = 2
        elif limit[0:4] == [1, 1, 0, 0]:
            ret = 3
        elif limit[0:4] == [0, 0, 1, 0]:
            ret = 4
        elif limit[0:4] == [1, 0, 1, 0]:
            ret = 5
        elif limit[0:4] == [0, 1, 1, 0]:
            ret = 6
        elif limit[0:4] == [1, 1, 1, 0]:
            ret = 7
        elif limit[0:4] == [0, 0, 0, 1]:
            ret = 8
        elif limit[0:4] == [1, 0, 0, 1]:
            ret = 9
        elif limit[0:4] == [0, 1, 0, 1]:
            ret = 10
        elif limit[0:4] == [1, 1, 0, 1]:
            ret = 11
        elif limit[0:4] == [0, 0, 1, 1]:
            ret = 12
        return ret

    # Membrane Control

    def memb_oc(self, pos: str) -> None:
        # posには open or close を入れる
        ret = self.memb_status()
        if ret[1].lower() != pos:
            buff = self.Config.position[pos.lower()]
            self.io.output_point(buff, 7)
        return

    def memb_pose(self) -> None:
        buff = [0, 0]
        self.io.output_point(buff, 7)
        return

    def memb_status(self) -> list[str, str]:
        ret = self.io.input_point(8, 3)
        if ret[0] == 0:
            self.memb_act = "OFF"
            if (ret[1] == 0) & (ret[2] == 0):
                self.memb_pos = "POSE"
            elif (ret[1] == 1) & (ret[2] == 0):
                self.memb_pos = "OPEN"
            elif (ret[1] == 0) & (ret[2] == 1):
                self.memb_pos = "CLOSE"
        else:
            self.memb_act = "DRIVE"
            self.memb_pos = "MOVE"
        return [self.memb_act, self.memb_pos]

    # M2 Control

    def m2_move(self, dist: int):
        status = self.m2_status()
        puls = self.um_to_puls(dist, status)
        if puls is None:
            raise ValueError("Please change distance.")
        self.MoveIndexFF(puls)

    def m2_status(self) -> list:
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
        self.pulse_rate = self.Config.pulse_rate

        puls = int(dist) * self.pulse_rate
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

    def MoveIndexFF(self, puls: int):
        self.cw = self.Config.cw
        self.ccw = self.Config.ccw
        self.motor_speed = self.Config.motor_speed

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

    def Strobe(self):
        time.sleep(0.01)
        self.io.output_byte("OUT9_16", [1, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(0.01)
        self.io.output_byte("OUT9_16", [0, 0, 0, 0, 0, 0, 0, 0])
        time.sleep(0.01)
        return

    # Drive Control
    def drive_move(self, pos) -> None:
        # pos = "on" or "off"
        buff = self.Config.drive_pos[pos.lower()]
        self.io.output_point(buff, 1)
        return

    def contactor_move(self, pos) -> None:
        # pos = "on" or "off"
        buff = self.Config.contactor_pos[pos.lower()]
        self.io.output_point(buff, 9)
        return

    def drive_contactor_status(self) -> list[str, str]:
        pos = self.io.input_byte("IN1_8").to_list()
        if pos[0] == 1 and pos[1] == 1:
            self.contactor_pos = "ON"
        else:
            self.contactor_pos = "OFF"
        if pos[2] == 1 and pos[3] == 1:
            self.drive_pos = "ON"
        else:
            self.drive_pos = "OFF"
        return [self.drive_pos, self.contactor_pos]

    def finalize(self) -> None:
        pass
