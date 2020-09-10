#!/usr/bin/env python


''' Watt.solutions temperature control console '''

from pymodbus.compat import IS_PYTHON3, PYTHON_VERSION
if IS_PYTHON3 and PYTHON_VERSION >= (3, 4):
    from pymodbus.client.sync import (
        ModbusSerialClient as ModbusClient)
    from pymodbus.constants import Endian
    from pymodbus.payload import BinaryPayloadDecoder
    from pymodbus.payload import BinaryPayloadBuilder
    from bidict import bidict
else:
    import sys
    sys.stderr("ERROR: Temp controller requires python 3.4 or above")
    sys.exit(1)


class TempCtrl(object):
    def __init__(self, port, baud=38400, unit=0x01):
        self.client = ModbusClient(port=port, baudrate=baud, method='rtu')
        self.unit = unit

    def close(self):
        self.client.close()

    # Read methods
    def read(self, address, length):
        rr = self.client.read_holding_registers(
            address, length, unit=self.unit)
        decoder = BinaryPayloadDecoder.fromRegisters(
            rr.registers, byteorder=Endian.Big, wordorder=Endian.Little)
        return decoder

    def read_float(self, address):
        return self.read(address, 2).decode_32bit_float()

    def read_uint(self, address):
        return self.read(address, 1).decode_16bit_uint()

    def read_dint(self, address):
        return self.read(address, 2).decode_32bit_uint()

    def read_string(self, address, len):
        return self.read(address, len * 8).decode_string()

    # Write method
    def write(self, address, type, value):
        builder = BinaryPayloadBuilder(
            byteorder=Endian.Big, wordorder=Endian.Little)
        if type == float:
            builder.add_32bit_float(value)
        elif type == int:
            builder.add_16but_uint(value)
        elif type == str:
            builder.add_string(value)
        else:
            print("Temp controller: Haven't implemented writing for type {}, ignoring".format(str(type)))
            return
        self.client.write_registers(address, builder.to_registers(), unit=self.unit)

    # Errors
    def get_input_error(self):
        return self.read_uint(362)

    def get_linearization_error(self):
        return self.read_uint(3614)

    # Properties
    @property
    def calibration_offset(self):
        return self.read_float(382)
    @calibration_offset.setter
    def calibration_offset(self, offset):
        self.write(382, float, offset)

    # @property
    # def a_value(self):
    #     ''' Same as temp? '''
    #     return self.read_float(3310)
    #
    # @property
    # def a_offset(self):
    #     return self.read_float(3324)
    # @a_offset.setter
    # def a_offset(self, offset):
    #     return self.write(3324, float, offset)

    control_modes = bidict({
        'Off': 62,
        'Auto': 10,
        'Manual': 54
    })
    @property
    def control_mode(self):
        return self.control_modes.inverse[self.read_uint(2360)]
    @control_mode.setter
    def control_mode(self, mode):
        if mode in self.control_modes:
            self.write(2360, int, self.control_modes[mode])
        else:
            print("Temp controller: Invalid control mode requested, ignoring")

    @property
    def heat_power(self):
        return self.read_float(2384)

    @property
    def cool_power(self):
        return self.read_float(2386)

    # @property
    # def process_value(self):
    #     ''' Same as temp??? '''
    #     return self.read_float(402)

    @property
    def setpoint(self):
        return self.read_float(2640)    # also 2652?
    @setpoint.setter
    def setpoint(self, temp):
        self.write(2640, float, temp)

    @property
    def temp(self):
        return self.read_float(360)     # also 402 and 3310?
    @temp.setter
    def temp(self, temp):
        ''' Alias for self.setpoint '''
        self.setpoint = temp

    def autotune_complete(self):
        return self.read_uint(2412) == 18

    @property
    def wordorder(self):
        ''' True if LoHi (desired), false if HiLo '''
        return self.read_uint(2968, 1) == 1331


if __name__ == '__main__':
    controller = TempCtrl('COM9')
    print("Current setpoint: ", controller.setpoint)
    print("Current temp: ", controller.temp)
    print("Setting to 50.0...")
    controller.setpoint = 50
    print("New setpoint: ", controller.setpoint)
    print("Setting to 80.0...")
    controller.setpoint = 80
    print("New setpoint: ", controller.setpoint)
    controller.close()
