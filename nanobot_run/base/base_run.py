"""
.. module:: base_run
    :platform: Unix
    :synopsis: Base class for experimental scripts

.. moduleauthor:: Graham Keenan <https://github.com/ShinRa26>

"""

import os
import sys
import time
import inspect

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
ROOT = os.path.join(HERE, "..", "..")
PLATFORM = os.path.join(ROOT, "nanobot", "software")
DATA = os.path.join(HERE, "..", "data")

sys.path.append(PLATFORM)

import utils.json_utils as json
from tools.manager import Manager
import operations.constants.common as cst
import operations.constants.info_keys as keys

# Single Experiments
SINGLE_FOLDER = "single_experiments"

class MethodNotImplemented(Exception):
    """Raised when a method has not been implemented in inheriting class
    """
    pass

class BaseExperiment(object):
    """Base class for an experiment run file.
    Inheriting class provides new methods and implementations for
    the reaction_protocol and process_protocol methods.
    """

    def __init__(self, info_file):
        self.info = json.read(os.path.relpath(info_file))

        if self.info[keys.ALGORITHM] == "single":
            self.root_xp_folder = os.path.join(
                DATA,
                SINGLE_FOLDER,
                self.info[keys.TITLE]
            )
        elif self.info[keys.ALGORITHM] == "GA":
            self.root_xp_folder = os.path.join(
                DATA,
                "genetic",
                self.info[keys.TITLE],
                str(self.info[keys.SEED])
            )

        self.manager = Manager()


    def __del__(self):
        """
        Kill all stirrers when closing the experiment
        """

        self.manager.set_ring_stir_rate(0)
        self.manager.wheel.home_all_modules()



    def preflush_pumps(self, preflush_vol=1.5):
        """
        Asks the user if they wish to preflush the pumps with reagents
        Ensures there is no dead volume within the tubing

        Keyword Arguments:
            preflush_vol {int/float} -- Volume to prime tubing with
        """

        preflush = self.manager.create_preflush_dict()

        ans = input("Do you wish to preflush the pumps? (y/n) ")

        if str(ans).lower() == "y":
            self.manager.log("Preflushing pumps: {}".format(preflush))
            for reagent in preflush.values():
                self.manager.triconts.transfer(
                    reagent.name,
                    reagent.volume,
                    reagent.in_valve,
                    reagent.out_valve
                )

            self.manager.turn_wheel(1)
            input("Replace the vial and press enter.")


    def prime_reductant(self, flush: float = 1.5):
        """ Asks the user if they wish to re-flush the reductant pump

        Args:
            flush (float): Flush volume (Default = 1.5)
        """

        ans = input("Re-flush reductant? (y/n) ")

        if str(ans).lower() == "y":
            self.manager.log(f"Re-flushing reductant: {flush}ml")
            self.manager.triconts.transfer("reductant", flush, "E", "I")
        self.manager.turn_wheel(1)
        input("Replace vial and press enter.")


    def activate_ring_stirrer(self, speed=25):
        """
        Activates the stirrers on the Ring
        """

        self.manager.set_ring_stir_rate(250)
        time.sleep(1)
        self.manager.set_ring_stir_rate(speed)


    def kill_ring_stirrers(self):
        """
        Kills the stirrers on the ring
        """

        self.manager.set_ring_stir_rate(0)


    def reaction_protocol(self):
        raise MethodNotImplemented("This method needs a definition!")


    def process_protocol(self):
        raise MethodNotImplemented("This needs a definition!")


    def full_protocol(self):
        raise MethodNotImplemented("This method needs a definition!")
