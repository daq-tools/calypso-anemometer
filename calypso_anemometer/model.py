# -*- coding: utf-8 -*-
# (c) 2022 Andreas Motl <andreas.motl@panodata.org>
# License: GNU Affero General Public License, Version 3
import dataclasses
import logging
import struct
from enum import Enum, IntEnum
from typing import Optional, Union

from calypso_anemometer.util import to_json

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class BleCharSpec:
    name: str
    uuid: str
    decoder: Optional[Union[Enum]] = None


@dataclasses.dataclass
class CalypsoDeviceInfo:
    ble_address: str
    manufacturer_name: str
    model_number: str
    serial_number: str
    hardware_revision: Optional[str]
    firmware_revision: Optional[str]
    software_revision: Optional[str]

    def asdict(self):
        return dataclasses.asdict(self)


class CalypsoDeviceMode(IntEnum):
    SLEEP = 0x00
    LOW_POWER = 0x01
    NORMAL = 0x02


class CalypsoDeviceDataRate(IntEnum):
    HZ_1 = 0x01
    HZ_4 = 0x04
    HZ_8 = 0x08


class CalypsoDeviceCompassStatus(IntEnum):
    OFF = 0x00
    ON = 0x01


@dataclasses.dataclass
class CalypsoDeviceStatus:
    mode: Optional[CalypsoDeviceMode] = None
    rate: Optional[CalypsoDeviceDataRate] = None
    compass: Optional[CalypsoDeviceCompassStatus] = None

    def aslabeldict(self):
        return {
            "mode": self.mode.name,
            "rate": self.rate.name,
            "compass": self.compass.name,
        }


@dataclasses.dataclass
class CalypsoReading:
    wind_speed: float
    wind_direction: int
    battery_level: int
    temperature: int
    roll: int
    pitch: int
    compass: int

    @classmethod
    def from_buffer(cls, buffer: bytearray):
        """
        Decoding cheat sheet by Fabian Tollenaar.
        https://github.com/decipherindustries/signalk-calypso-ultrasonic/blob/master/DECODE

        Length:   10
        Bytes:    0-1  2-3  4  5  6  7  8-9
        Ex. data: 0000 3F01 04 7C 00 00 0000
                  AABB CCDD EE FF GG HH IIJJ

        Decode:
        0-1.  Wind speed: hex2dec(BB AA) / 100
        2-3.  Wind direction: hex2dec(DD CC)
        4.    Battery level: hex2dec(EE) * 10
        5.    Temp level: hex2dec(FF) - 100
        6.    Roll: hex2dec(GG) - 90
        7.    Pitch: hex2dec(HH) - 90
        8-9.  Compass: 360 - hex2dec(JJ II)

        Ex.
        0-1.  hex2dec(00 00) => 0 / 100 => 0
        2-3.  hex2dec(01 3F) => 319 (degrees)
        4.    hex2dec(04) => 4 * 10 => 40%
        5.    hex2dec(7C) => 124 - 100 => 24 (degrees C)
        6.    hex2dec(00) => 0 - 90 => -90 (degrees)
        7.    hex2dec(00) => 0 - 90 => -90 (degrees)
        8-9.  360 - hex2dec(00 00) => 360 - 0 => 360

        """

        # Decode from binary.
        data = struct.unpack("HHBBBBH", buffer)

        # Decompose.
        (wind_speed, wind_direction, battery_level, temperature, roll, pitch, compass) = data

        # Apply adjustments.
        reading = cls(
            wind_speed=wind_speed / 100.0,
            wind_direction=wind_direction,
            battery_level=battery_level * 10,
            temperature=temperature - 100,
            roll=roll - 90,
            pitch=pitch - 90,
            compass=360 - compass,
        )
        return reading

    def adjusted(self):
        """
        Compensate sticky wind direction when wind speed goes zero.
        """
        if self.wind_speed == 0.0:
            return dataclasses.replace(self, wind_direction=0)
        return self

    def asdict(self):
        return dataclasses.asdict(self)

    def print(self):
        print(to_json(self))
