"""
.. module:: tricont_control
    :platform: Unix, Windows
    :synopsis: Module for controlling Tricont pumps defined in the Base Layer

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

from base_layer.tricont import triconts
from operations.constants import common as cst

# Cleaning cycle
UV_IR_CLEANING_CYCLES = 2

# Valve positions to make logging more clear for the sample pump
SIX_WAY = {
    "2": "Sample Waste",
    "3": "Sample Inlet",
    "4": "Seeds",
    "5": "UV/IR",
    "6": "Sample Waste (Small)"
}

"""
REAGENT TUPLE:
Reagents to be passed to these functions should be in the form of tuples

Tuple can have two formats:
    * Pump name and volume
    * Pump name, volume, in_valve position, and out_valve position

Example with no valves passed: ("acid", 4.5)
Example with valves passed: ("acid", 4.5, "I", "O")

Anything other than these two won't be accepted and will raise an Exception

If no valve positions are given, default inlet and outlet positions are used ("I"/"O")
"""

class UndefinedPump(Exception):
    """Exception raised for when a pump isn't found in the PyCont controller
    """

class Reagent:
    def __init__(
            self,
            name: str,
            volume: str,
            in_valve=cst.EXTRA,
            out_valve=cst.INLET
        ):
        self.name = name
        self.volume = volume
        self.in_valve = in_valve
        self.out_valve = out_valve

    def __str__(self):
        return f"Reagent: {self.name} Volume: {self.volume}ml"


class TricontControl(object):
    """
    Class for controlling a set of tricont pumps
    Contains methods for dispensing, sampling, cleaning vials, etc.
    """

    def __init__(self, logger):
        self.logger = logger
        self.dispensing_pumps = []
        self.config = triconts.config
        self.controller = triconts.controller


    def get_tricont(self, pump_name: str):
        """
        Gets the Tricont pump attribute from the PyCont controller

        Args:
            pump_name (str): Name of the pump

        Returns:
            pump (C3000Controller): Pump object

        Raises:
            AttributeError: The pump is not present within the PyCont controller
        """

        try:
            return getattr(self.controller, pump_name)
        except AttributeError:
            raise UndefinedPump(
                f"Cannot find pump {pump_name} in PyCont Controller!"
            )


    def wait_until_pumps_idle(self):
        """Wait until all dispensing pumps are idle
        Used only for parallel dispense operation
        """

        for pump in self.dispensing_pumps:
            pump.wait_until_idle()


    def transfer(
            self,
            name: str,
            volume: float = 12.5,
            in_valve=cst.EXTRA,
            out_valve=cst.INLET
        ):
        """
        Waits until a pump is idle before transferring a volume

        Args:
            name (str): Name of the pump
            volume (int/float): Volume to transfer
            in_valve (str): Valve to pull from to
            out_valve (str): Valve to push towards
        """

        pump = self.get_tricont(name)
        pump.transfer(volume, in_valve, out_valve)


    def sequential_dispense(self, *reagents: tuple):
        """
        Dispenses reagents from their stock solutions to a vessel
        Reagents in the form of (pump_name, volume, in_valve, out_valve)
        In_valve and Out_valve are optional

        Args:
            reagents {tuple}: Variable args of tuples containing name,
                                volume, and optionally valve positions
        """

        for reagent in reagents:
            self.logger.info(f"Dispensing {reagent.name}: {reagent.volume}ml")

            self.transfer(
                reagent.name,
                reagent.volume,
                in_valve=reagent.in_valve,
                out_valve=reagent.out_valve
            )


    def parallel_dispense(self, *reagents: tuple, ordered=False):
        """Dispenses reagents in a parallel fashion
        Pumps simultaneously and delivers simultaneously if not ordered

        Arguments:
            *reagents {tuple} -- Variable args of tuples containing name,
                                    volume, and optionally valve positions

        Keyword Arguments:
            ordered {bool} -- If pumps should be delivered in order they are given
                                (default: {False})
        """

        # Set the current dispensing pumps
        self.dispensing_pumps = [
            self.get_tricont(reagent.name)
            for reagent in reagents
        ]

        # Check for pumps that exceed their maximum volume
        reagents, residual_volumes = self._check_reagent_volumes(*reagents)

        # Pump in volumes form pumps
        self._pump_volume(*reagents)

        # Wait until operation complete
        self.wait_until_pumps_idle()

        # Deliver volumes from pumps
        self._deliver_volume(*reagents, ordered=ordered)

        # Wait until operation complete
        self.wait_until_pumps_idle()

        # If we have any residual volumes, rerun the method
        if residual_volumes:
            self.parallel_dispense(*residual_volumes, ordered=ordered)

        # Clear pumps for next dispense operation
        self.dispensing_pumps = []


    def _check_reagent_volumes(self, *reagents: list) -> (list, list):
        """Determines if the volumes to be dispensed exceed their maximum volume
        Allows the pumps to pump full volumes

        Arguments:
            *reagents {tuple/list} Tuples or list of tuples

        Returns:
            list, list -- Regents that are fine and list of reagents with remaining volumes
        """

        volumes, remaining_volumes = [], []
        for pump, reagent in zip(self.dispensing_pumps, reagents):
            max_volume = pump.total_volume
            if reagent.volume > max_volume:
                # Calculate remaining volumes
                remaining_volume = reagent.volume - max_volume

                new_reagent = Reagent(
                    reagent.name,
                    remaining_volume,
                    reagent.in_valve,
                    reagent.out_valve
                )

                reagent.volume = max_volume

                remaining_volumes.append(new_reagent)
                volumes.append(reagent)
            else:
                volumes.append(reagent)


        return volumes, remaining_volumes


    def _pump_volume(self, *reagents: tuple):
        """Pumps volume specified in reagents
        Valve positions optionally defined in reagents

        Arguments:
            reagents {tuple/variable} -- Reagent tuples

        Raises:
            ReagentError -- If the reagent doesn't conform to expected format
        """

        for reagent in reagents:
            pump = self.get_tricont(reagent.name)
            pump.pump(reagent.volume, reagent.in_valve)


    def _deliver_volume(self, *reagents: tuple, ordered=False):
        """Delivers volume specified in reagents
        Valve postions optionally defined in reagents

        Arguments:
            *reagents {tuple}-- Variable args of tuples containing name,
                                volume, and optionally valve positions

        Keyword Arguments:
            ordered {bool} -- If volumes should be delivered in order given
                                (default: {False})
        """

        for reagent in reagents:
            self.logger.info(f"Dispensing {reagent.name}: {reagent.volume}ml")
            pump = self.get_tricont(reagent.name)

            pump.deliver(reagent.volume, reagent.out_valve)

            # Give a small wait time after addition of certain reagent(s)
            if reagent.name == "reductant":
                time.sleep(25)

            if ordered:
                # If ordered, will wait until the current pump has completed the operation
                pump.wait_until_idle()


    def take_sample(
            self,
            vol_in=0,
            vol_out=0,
            in_valve=cst.SAMPLE_INLET,
            out_valve=cst.SAMPLE_WASTE
        ):
        """Takes a sample form the designated sample pump.

        Pumps a volume then dispenses a smaller or equal volume

        Arguments:
            vol_in {int/float} -- Volume to draw into the syringe
            vol_out {int/float} -- Volume to push out from the syringe

        Keyword Arguments:
            in_valve {str} -- Valve position to draw in from (default: {cst.EXTRA})
            out_valve {str} -- Valve position to draw out from (default: {cst.INLET})

        Raises:
            Exception -- Volume in is less than volume out

        Returns:
            int/float -- Difference between volume in and volume out
        """

        sample_pump = self.get_tricont(cst.SAMPLE)

        if vol_in < vol_out:
            curr_vol = sample_pump.get_volume()
            if vol_out > curr_vol:
                self.logger.info(f"Cannot pump volume. In: {vol_in} Out: {vol_out}")
                raise Exception(f"Cannot pump volume. In: {vol_in} Out: {vol_out}")
            sample_pump.deliver(vol_out, out_valve, wait=True)
            return

        self.logger.info(
            f"Taking sample: {vol_in}ml (IN: {SIX_WAY[in_valve]}, OUT: {SIX_WAY[out_valve]})"
        )

        sample_pump.pump(vol_in, in_valve, wait=True)
        sample_pump.deliver(vol_out, out_valve, wait=True)

        return vol_in - vol_out


    def dispense_regia(self, volume: float):
        """Dispenses Aqua Regia and a small amount of water to purge the valve

        Args:
            volume (float): Volume of acid to dispense
        """

        self.transfer(cst.ACID, volume)
        self.transfer(cst.ACID, 1, in_valve=cst.OUTLET, out_valve=cst.EXTRA)


    def clean_routine(self):
        """Performs the full cleaning cycle
        """

        self.regia_purge()
        self.clean_uv_ir_lines()


    def regia_purge(self):
        """Purges the system with aqua regia
        """

        self.logger.info(f"Purging system with Aqua Regia")

        # Move acid
        self.dispense_regia(5)

        # Send through UV/IR
        self.take_sample(
            vol_in=5,
            vol_out=5,
            out_valve=cst.UV_IR
        )

        # Move to waste
        self.transfer(
            cst.CLEANING,
            volume=6,
            in_valve=cst.OUTLET,
            out_valve=cst.INLET
        )

        # Remove residue from waste valve
        self.transfer(
            cst.CLEANING,
            volume=2,
            out_valve=cst.INLET
        )


    def clean_uv_ir_lines(self):
        """Cleans the UV/IR lines with water/acetone
        """

        for i in range(UV_IR_CLEANING_CYCLES):
            self.logger.info(
                "Cleaning cycle (UV/IR): {}/{}".format(i+1, UV_IR_CLEANING_CYCLES)
            )

            # Water clean
            self.single_uv_ir_clear()


    def single_uv_ir_clear(self):
        """Dispenses solvent into UV/IR lines for cleaning
        Single itertion of UV/IR cleaning routine

        Arguments:
            pump_type {str} -- Pump to use

        Keyword Arguments:
            vol {float} -- Volume of cleaning solvent (default: {5})
        """

        # Pull in water
        self.transfer(
            cst.CLEANING,
            out_valve=cst.OUTLET
        )

        # Move through lines
        self.take_sample(
            vol_in=12,
            vol_out=12,
            out_valve=cst.UV_IR
        )

        # Move to waste
        self.transfer(
            cst.CLEANING, volume=12, in_valve=cst.OUTLET, out_valve=cst.INLET
        )

        # Remove small residue
        self.take_sample(
            vol_in=2,
            vol_out=2,
            in_valve=cst.SAMPLE_SM_WASTE,
            out_valve=cst.SAMPLE_WASTE
        )


    def finishing_clean(self, *pump_names):
        """
        Removes unwanted materials form pumps at the end of a run

        Args:
            pump_names (str): Series of pump names
        """

        for pump in pump_names:
            for _ in range(2):
                self.transfer(
                    pump, 0.5, in_valve=cst.OUTLET, out_valve=cst.EXTRA
                )
                self.transfer(
                    pump, 0.5, in_valve=cst.OUTLET, out_valve=cst.INLET
                )

    def dilute_sample(self):
        """
        Dilutes the sample by half
        """
        # Move half to waste
        self.transfer(
            cst.CLEANING, volume=5, in_valve=cst.OUTLET, out_valve=cst.INLET
        )

        # Fill with water
        self.transfer(
            cst.CLEANING, volume=5, in_valve=cst.EXTRA, out_valve=cst.OUTLET
        )
