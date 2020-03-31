"""
.. module:: wheel_control
    :platform: Unix
    :synopsis: Module for interfacing with the Commanduino core device in the Base Layer

.. moduleauthor:: Graham Keenan <https://github.com/ShinRa26>

"""

import os
import sys
import time
import inspect

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
root_path = os.path.join(HERE, "..", "..")
op_path = os.path.join(HERE, "..")
sys.path.append(op_path)
sys.path.append(root_path)

import constants.common as cst
from base_layer.commanduino_setup.core_device import CoreDevice
from commanduino.commanddevices.commanddevice import CommandTimeOutError

""" CONSTANTS """
FULL_WHEEL_TURN = 6400
PUMP_INCREMENT = 8000
MODULE_LOWER = 31000
REST_POSITION = 15000

WHEEL_CONFIG = os.path.join(HERE, "..", "configs", "wheel_config.json")


class WheelControl(CoreDevice):
    """
    Class for controlling a Geneva Wheel system
    Contains methods for rotation, modular drivers, pumps, etc.
    Assumes the user has at least one Geneva wheel, one modular driver, and one peristaltic
    pump attached to their rig.

    Inherits:
        CoreDevice: Commanduino Base Device

    Args:
        config (str): Path to the config
    """

    def __init__(self):
        CoreDevice.__init__(self, WHEEL_CONFIG)
        self.home_all_modules()


    def turn_wheel(self, n_turns: int, wait=True):
        """
        Turns the Geneva Wheel n_turns times

        Args:
            n_turns (int): Number of turns
        """

        try:
            drive_wheel = self.get_device_attribute(cst.WHEEL_NAME)
            for _ in range(n_turns):
                drive_wheel.move(FULL_WHEEL_TURN, wait=wait)
        except CommandTimeOutError:
            print("Commanduino -- Timeout error, ignore.")


    def move_module(self, mod_name: str, pos: int, wait=True):
        """
        Moves the modular driver to a set position

        Args:
            mod_name (str): Name of the module
            pos (int/float): Number of steps to move
            wait (bool): Wait for the device to be idle, default set to True
        """

        try:
            module = self.get_device_attribute(mod_name)
            module.move_to(pos, wait=wait) # -ve due to inverted direction
        except CommandTimeOutError:
            print("Commanduino -- Timeout error, ignore.")


    def lower_module(self, mod_name: str, wait=True):
        """
        Lowers the modular driver

        Args:
            mod_name (str): Name of the modular driver
            wait (bool): Wait for the device to be idle, default set to true
        """

        self.move_module(mod_name, MODULE_LOWER, wait=wait)


    def home_module(self, mod_name: str, wait=True):
        """
        Brings the module back to its home position

        Args:
            mod_name (str): Name of the module
            wait (bool): Wait for the device to be idle, default set to true
        """

        try:
            module = self.get_device_attribute(mod_name)
            module.home(wait=wait)
        except CommandTimeOutError:
            print("Commanduino -- Timeout error, ignore.")


    def home_all_modules(self, wait=True):
        """Homes all the modules and places them in a rest position
        For weight reasons

        Keyword Arguments:
            wait {bool} -- Whether to wait for th operations to complete (default: {True})
        """
        self.home_module(cst.MSD1, wait=wait)
        self.home_module(cst.DUAL_BODY, wait=wait)
        self.home_module(cst.DUAL_SYRINGE, wait=wait)

        self.move_module(cst.DUAL_SYRINGE, REST_POSITION, wait=wait)
        self.move_module(cst.DUAL_BODY, REST_POSITION, wait=wait)


    def run_peri_pump(self, pump_name: str, num_secs: int):
        """
        Runs a peristaltic pump for num_secs time

        Args:
            pump_name (str): Name of the pump
            num_secs (int/float): Number of seconds to run for
        """

        pump = self.get_device_attribute(pump_name)
        curr_time = time.time()
        while time.time() < (curr_time + num_secs):
            pump.move(PUMP_INCREMENT)


    def set_ring_stir_rate(self, value: int):
        """Sets the stirrer rate for the main ring

        Arguments:
            value {int} -- Value to set the PWM to
        """
        if self.valid_device(cst.RING):
            ring = self.get_device_attribute(cst.RING)
            ring.set_pwm_value(value)
        else:
            print("\"{}\" is not recognised in the manager!".format(cst.RING))
