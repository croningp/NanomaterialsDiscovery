"""
.. module:: manager
    :platform: Unix
    :synopsis: Module for managing the Operational layer components

.. moduleauthor:: Graham Keenan <https://github.com/ShinRa26>

"""

# System imports
import os
import sys
import inspect
import numpy as np
import time

# Path setup
HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
root_path = os.path.join(HERE, "..")
sys.path.append(root_path)

# Platform import
import utils.mail as mail
from utils.logger import Logger
import utils.json_utils as json
import utils.shell_commands as sh
import operations.constants.common as cst
import operations.constants.filenames as fn
from operations.uv.uv_control import UVControl
from operations.wheel.wheel_control import WheelControl
from operations.triconts.tricont_control import TricontControl, Reagent


class Manager(object):
    """
    Class representing a manager which governs the entire platform
    Wrapper around certain operations for the platform and general management
    """

    def __init__(self):
        # Initialise the logging module
        self.logger = Logger()

        # Initialise the tricont pumps
        self.triconts = TricontControl(self.logger)

        # Initialise the Wheel system
        self.wheel = WheelControl()

        # # Initialise the UV control
        self.uv = UVControl(integration_time=1)

        # Current Generation Path
        self.current_generation = ""


    def update_generation_path(self, new_path: str):
        """Updates the current path of the generation

        Arguments:
            new_path {str} -- Updated path
        """

        self.current_generation = new_path


    def normalise_parameters(
            self,
            params: dict,
            pumps: list,
            normalised_volume: float
        ) -> dict:
        """
        Normalises the parameters of an experiment into values that can be used by the pumps
        Algorithm generates arbitrary values, these need to be translated into volumes
        Essentially, rounds up the values to the normalised_volume

        Args:
            params (Dict): Parameters for the experiment
            pumps (List): List of the pumps in use
            normalised_volume (int/float): Volume to normalise for (Volume fo the vial)

        Returns:
            normalised_pumps (Dict): Dictionary containing the
                                     pump names and their corresponding volumes
        """

        # Dict to hold new pumps
        normalised_pumps = {}

        # Get algorithm values
        alg_values = [params[pump] for pump in pumps]

        # If the pump isnt present in the list, it's a static volume
        # Subtract volume form normalisation volume
        for pump in params.keys():
            if pump not in pumps:
                normalised_volume -= params[pump]
                normalised_pumps[pump] = params[pump]

        # Normalise volumes
        normalised_values = (alg_values/np.sum(alg_values)) * normalised_volume

        # Add to dict
        for pos, pump in enumerate(pumps):
            normalised_pumps[pump] = normalised_values[pos]

        seeds = normalised_pumps.pop("seeds")
        normalised_pumps["seeds"] = seeds

        return self.convert_params_to_tuple_dict(normalised_pumps)


    def create_preflush_dict(self) -> dict:
        """Creates Reagents to preflush the pumps

        Returns:
            dict: Regents to preflush pumps with
        """

        preflush_vol = 1.5

        return {
            "silver": Reagent("silver", preflush_vol),
            "surfactant": Reagent("surfactant", preflush_vol),
            "gold": Reagent("gold", preflush_vol),
            "reductant": Reagent("reductant", preflush_vol),
            "seeds": Reagent("seeds", preflush_vol),
            "cleaning": Reagent("cleaning", 10, in_valve="E", out_valve="E")
        }


    def convert_params_to_tuple_dict(self, params: dict) -> dict:
        """
        Converts a dictionary of pump parameters to a dictionary of tuples

        Args:
            params (dict): Params to convert

        Returns:
            tuple_params (dict): Parameters as a dict of tuples
        """

        tuple_dict = {}
        for key, value in params.items():
            tuple_dict[key] = Reagent(key, value)

        return tuple_dict


    def _create_reagent_list(self, *reagents: tuple) -> list:
        reagent_list = [
            Reagent(*reagent) for reagent in reagents
        ]

        return reagent_list


    def dispense(self, reagents: dict, ignore_turn=False):
        """
        Dispenses reagents into a vial and rotates the wheel

        Args:
            reagents (Dict): Dictionary containing the pump names and values
        """

        reagents = [reagent for reagent in reagents.values()]
        self.triconts.sequential_dispense(*reagents)

        if not ignore_turn:
            self.turn_wheel(cst.WHEEL_TURN)


    def dispense_single_reagent(
            self,
            name: str,
            volume: float,
            ignore_turn=False
        ):
        """
        Dispenses a single reagent from the pump

        Args:
            name (str): Name of the reagent pump
            volume (int/float): Volume to dispense
        """

        self.log(f"Dispensing reagent: {name} ({volume}ml)")
        self.triconts.transfer(name, volume)

        if not ignore_turn:
            self.turn_wheel(cst.WHEEL_TURN)


    def obtain_uv_spectra(
            self, xp_path: str = "", ref: bool = False, dilute: bool = False
        ):
        """Obtain spectra from the UV

        Args:
            xp_path (str, optional): Path for the sample spectrum. Defaults to "".
            ref (bool, optional): Reference spectrum or not. Defaults to False.
        """

        # Lower the module
        self.wheel.lower_module(cst.MSD1)

        # Take water for reference
        if ref:
            self.log(f"Reference collection for: {self.current_generation}")
            self.triconts.transfer(cst.CLEANING, 10, out_valve=cst.OUTLET)

        # Dilute and stir if set
        if dilute:
            self.triconts.dilute_sample()
            self.set_ring_stir_rate(200)
            time.sleep(1)
            self.set_ring_stir_rate(20)
            time.sleep(5)
            self.set_ring_stir_rate(0)

        # Set the speed lower to ensure no air is taken
        self.set_pump_speed("sample", 5000)

        # Transfer into UV/IR lines
        remaining_vol = self.triconts.take_sample(
            vol_in=10,
            vol_out=8,
            out_valve=cst.UV
        )

        # Set back to default
        self.set_pump_speed("sample", 8000)

        # Get reference spectra
        if ref:
            self.log("Obtaining UV reference")
            self.uv.obtain_reference_spectrum(
                os.path.join(self.current_generation, fn.REF_UV_IMG),
                os.path.join(self.current_generation, fn.REF_UV_JSON)
            )

        # Get real spectra
        else:
            # Get UV spectrum of sample
            self.log(f"Obtaining UV spectrum for {xp_path}")
            self.uv.obtain_spectrum(
                os.path.join(self.current_generation, fn.REF_UV_JSON),
                os.path.join(xp_path, fn.UV_JSON),
                os.path.join(xp_path, fn.UV_IMG)
            )

        # Clear line
        self.triconts.take_sample(
            vol_out=remaining_vol,
            out_valve=cst.UV
        )

        # Remove Liquid from vial
        self.triconts.transfer(
            cst.CLEANING,
            in_valve=cst.OUTLET,
            out_valve=cst.INLET
        )

        # Add water to vial
        self.triconts.transfer(
            cst.CLEANING,
            volume=8,
            out_valve=cst.OUTLET
        )

        # Move water through sample lines
        self.triconts.take_sample(
            vol_in=10,
            vol_out=10,
            out_valve=cst.UV
        )

        # Move water to waste
        self.triconts.transfer(
            cst.CLEANING,
            in_valve=cst.OUTLET,
            out_valve=cst.INLET
        )

        # Home the module
        self.wheel.home_module(cst.MSD1)


    def obtain_seeds_uv(self):
        """Obtains a UV of the seeds used each generation
        """

        # Lower the module and take a sample to UV/IR
        self.wheel.lower_module(cst.MSD1)

        # Slow pump down for seed delivery
        self.set_pump_speed("sample", 5000)
        remaining_vol = self.triconts.take_sample(
            vol_in=7,
            vol_out=4,
            in_valve=cst.SEEDS,
            out_valve=cst.UV
        )

        # Reset the speed
        self.set_pump_speed("sample", 8000)
        self.log(f"Taking seed reference")

        # Get UV spectrum
        self.uv.obtain_spectrum(
            os.path.join(self.current_generation, fn.REF_UV_JSON),
            os.path.join(self.current_generation, fn.SEEDS_UV_JSON),
            os.path.join(self.current_generation, fn.SEEDS_UV_IMG)
        )

        # Transfer remaining volume
        self.triconts.take_sample(
            vol_out=remaining_vol,
            out_valve=cst.UV
        )

        # Move seeds back into stock bottle
        self.triconts.transfer(
            cst.CLEANING,
            in_valve=cst.OUTLET,
            out_valve=cst.INLET
        )

        # Move Aqua Regia into vial for cleaning
        self.triconts.dispense_regia(5)

        # Purge the UV/IR line with regia
        self.triconts.take_sample(
            vol_in=7,
            vol_out=7,
            out_valve=cst.UV
        )

        # Move regia to waste
        self.triconts.transfer(
            cst.CLEANING,
            in_valve=cst.OUTLET,
            out_valve=cst.INLET
        )

        # Do 2 runs of water through the UV/IR path to remove excess Regia
        for _ in range(2):
            self.triconts.transfer(
                cst.CLEANING,
                out_valve=cst.OUTLET
            )

            self.triconts.take_sample(
                vol_in=12,
                vol_out=12,
                out_valve=cst.UV
            )

            self.triconts.transfer(
                cst.CLEANING,
                volume=12,
                in_valve=cst.OUTLET,
                out_valve=cst.INLET
            )

        # Home the module
        self.wheel.home_module(cst.MSD1)


    def clean_vial(self):
        """
        Cleans a vial using the cleaning routine defined in TricontControl
        """

        self.wheel.lower_module(cst.MSD1)
        self.triconts.clean_routine()
        self.wheel.home_module(cst.MSD1)
        self.wheel.turn_wheel(cst.WHEEL_TURN)


    def finishing_clean(self, *pump_names):
        """
        Removes unwanted material form pump valves

        Args:
            pump_names (str): Name of the pumps
        """

        self.wheel.lower_module(cst.MSD1)
        self.triconts.finishing_clean(*pump_names)
        self.wheel.home_module(cst.MSD1)


    def set_pump_speed(self, name: str, speed: int):
        """
        Sets the speed of the pump

        Args:
            name (str): Name of the pump
            speed (int): Speed to set
        """

        pump = self.triconts.get_tricont(name)
        pump.set_default_top_velocity(speed)
        pump.set_top_velocity(speed)


    def turn_wheel(self, n_turns: int):
        """
        Turns the wheel n_turns times

        Args:
            n_turns (int): Number of times to turn the wheel
        """

        self.wheel.turn_wheel(n_turns)


    def set_ring_stir_rate(self, val: int):
        """
        Sets the stirring rate of the vial stirrers

        Args:
            val (int): PWM value to set (0-255)
        """

        self.log("Ring stirring set to {}".format(val))
        self.wheel.set_ring_stir_rate(val)


    def send_mail(self, msg: str, flag=0):
        """
        Sends an email to each address in the common constants list

        Args:
            msg (str): Message to send
            flag (int): Flag to determine the type of message
                0: Basic notification
                1: System has crashed
        """

        mail.notify(cst.PLATFORM_NAME, cst.EMAILS, msg, flag=flag)


    def log(self, msg: str):
        """
        Logs a message using the logger

        Args:
            msg (str): Message to log
        """

        self.logger.info(msg)


    def backup_files(self, src: str, dst=fn.DEFAULT_BACKUP):
        """Backs up files to a given location via shell command

        Arguments:
            src {str} -- Folder to backup

        Keyword Arguments:
            dst {str} -- Location of where to copy to (default: {fn.DEFAULT_BACKUP})
        """

        sh.backup(src, dst)


if __name__ == "__main__":
    mgr = Manager()
