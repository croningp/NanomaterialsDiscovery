"""
.. module:: experiment
    :platform: Unix
    :synopsis: Experiment child class for running the system

.. moduleauthor:: Graham Keenan (Cronin Group 2019)

"""

# Base Experiment class import
from base.base_run import BaseExperiment

# System imports
import os
import sys
import time
import inspect
import filetools

# Path setup
HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
DATA = os.path.join(HERE, "data")
ROOT = os.path.join(HERE, "..")
PLATFORM = os.path.join(ROOT, "nanobot", "software")
sys.path.append(PLATFORM)

# Platform imports
import utils.json_utils as json
import operations.constants.common as cst
import operations.constants.filenames as fn
import operations.constants.info_keys as keys

# Time to wait between reactions and analysis
WAIT_TIME = 1 * 60 * 60


def get_spectra_filenames(xp_path: str, ref: bool = False):
    """Gets the filepaths for the UV and IR spectra

    Args:
        xp_path (str): Experiment path. Gen path if Ref
        ref (bool, optional): Reference spectra or not. Defaults to False.

    Returns:
        str, str: UV and IR filepaths
    """

    if ref:
        uv_file = os.path.join(xp_path, fn.REF_UV_JSON)
    else:
        uv_file = os.path.join(xp_path, fn.UV_JSON)

    return uv_file


def check_xps_to_do(gen_path: str) -> list:
    """Checks for experiments to do in the current generation

    Checks for missing UV and IR spectra in each folder
    If missing, add to list

    Args:
        gen_path (str): Path to the current generation

    Returns:
        list: List of XP filepaths to execute
    """

    xps = []

    for xp_folder in sorted(filetools.list_folders(gen_path)):
        xp_files = [f for f in filetools.list_files(xp_folder)]
        uv_file = get_spectra_filenames(xp_folder)

        if not uv_file in xp_files:
            xps.append(xp_folder)

    return xps


def reference_spectra_present(gen_path: str) -> bool:
    """Checks for reference spectra in the current generation
    IF one is missing, retake reference for all

    Args:
        gen_path (str): Path to the current generation

    Returns:
        bool: References present or not
    """

    uv_file = get_spectra_filenames(gen_path, ref=True)
    if not os.path.exists(uv_file):
        return False

    return True

def check_generation_for_experiments(gen_path: str) -> list:
    """Checks the given generation for experiments to perform
    Looks for the presence of a 'signature.json' file
    If not present, checks for experiments to perform

    Args:
        gen_path (str): Path to the generation

    Returns:
        list: Experiments to do for the generation or nothing
    """

    sig_file = os.path.join(gen_path, fn.FITNESS_FILE)
    if os.path.exists(sig_file):
        return []

    return check_xps_to_do(gen_path)


class Experiment(BaseExperiment):
    """Experimental run script

    Args:
        reactions (bool): Execute reaction protocol
        analysis (bool): Execute analysis protocol

    Inherits:
        BaseExperiment: Base experiment class with common functions
    """
    def __init__(self, reactions: bool = True, analysis: bool = True):
        BaseExperiment.__init__(self, "./info.json")
        self.do_reactions = reactions
        self.do_analysis = analysis


    def __del__(self):
        """Send an email once the script has concluded"
        """

        self.manager.send_mail(f"Experiment {self.info[keys.TITLE]} is complete!")


    def reaction_protocol(self, xp_list: list, normalise: bool = False):
        """Dispensing protocol
        Loads in parameters for each experiment and dispenses reagents

        Args:
            xp_list (list): List of experimental paths to load in
        """

        # Iterate through each experiment
        for xp_path in xp_list:
            # Log experiment
            self.manager.log(f"Conducting experiment: {xp_path}")

            # Load in parameters
            params = json.read(
                os.path.join(xp_path, fn.PARAMS_FILE)
            )

            # Convert parameters for dispensing
            if normalise:
                params = self.manager.normalise_parameters(
                    params,
                    self.info[keys.PUMPS],
                    10
                )
            else:
                params = self.manager.convert_params_to_tuple_dict(params)

            # Dispense all reagents
            self.manager.log(f"Dispensing reagents: {params}")

            # Pump sequentially
            for pump, reagent in params.items():
                self.manager.dispense_single_reagent(pump, reagent.volume, ignore_turn=True)

                # Give time for reducing
                if pump == "reductant":
                    time.sleep(25)

            # Turn the wheel
            self.manager.turn_wheel(1)


    def analysis_protocol(self, xp_list: list):
        """Analysis protocol for analysing each experiment
        Iterates through each experiment to obtain UV/IR spectra
        and cleans the vial afterwards

        Args:
            xp_list (list): List of experiments to analyse
        """

        # Iterate through each experiment
        for xp_path in xp_list:
            # Log experiment
            self.manager.log(f"Analysing experiment: {xp_path}")

            # Obtain experimental spectra
            self.manager.obtain_uv_ir_spectra(xp_path=xp_path, dilute=True)

            # Clean the vial and tubing
            self.manager.clean_vial()


    def protocol(self):
        """Executes protocols depending on which flags are set

        Raises:
            Exception: General exception to catch common errors like pumps stalling
        """

        # Preflush the reagent pumps -- Always ask!
        self.manager.log(f"Initialising experiment: {self.info['title']}")
        self.preflush_pumps()

        # Iterate through X generations
        for n_gen in range(self.info[keys.GENS]):
            # Check for experiments to do in the current generation
            gen_path = os.path.join(self.root_xp_folder, f"{n_gen:04d}")
            xp_list = check_generation_for_experiments(gen_path)

            # No experiments to conduct, skip to next generation
            if not xp_list:
                self.manager.log(
                    f"No experiments to do for {gen_path}, skipping!"
                )
                continue

            # Update the generation path for the manager
            self.manager.update_generation_path(gen_path)

            # Take reference spectra if absent from generation
            if not reference_spectra_present(gen_path):
                self.manager.log(
                    f"Obtaining reference for generation: {gen_path}"
                )
                self.manager.obtain_uv_ir_spectra(ref=True)
                # self.manager.obtain_seeds_uv_ir()

            # Conduct reactions if flag set
            if self.do_reactions:
                # Let user know we're starting
                self.manager.send_slack_message("Starting reaction sequence. :middle_finger:")

                # Activate the stirrers on the ring
                self.activate_ring_stirrer()

                # Execute reaction
                try:
                    self.reaction_protocol(xp_list)

                # Catch any errors such as pumps failing
                except Exception as ex:
                    self.manager.send_mail(f"Error: {ex}", flag=1)
                    self.manager.log(f"Error: {ex}")
                    raise Exception(f"It's broken... {ex}")

                # Stop the stirrers after dispensing
                self.kill_ring_stirrers()

                # Wait for a set time after dispensing
                self.manager.log(f"Waiting for {int(WAIT_TIME/60)} mins...")
                self.manager.send_slack_message(
                    f"Finished dispensing, waiting {int(WAIT_TIME/60/60)} hours. Remember Stirrers!"
                )
                time.sleep(WAIT_TIME)


                # Move into sample position
                self.manager.turn_wheel(2)

            # Analyse reactions if flag set
            if self.do_analysis:
                # Let user know we're analysing
                self.manager.send_slack_message("Starting analysis. :middle_finger:")

                # Analyse reaction
                try:
                    self.analysis_protocol(xp_list)

                # Catch any errors such as pumps failing
                except Exception as ex:
                    self.manager.send_mail(f"Error: {ex}", flag=1)
                    self.manager.log(f"Error: {ex}")
                    raise Exception(f"It's broken... {ex}")

            # Inform user generation is complete
            self.manager.send_mail(
                f"Generation {n_gen:04d} complete!", flag=2
            )

            # Send slack message
            self.manager.send_slack_message(f"Generation {n_gen:04d} complete! :middle_finger:")


if __name__ == "__main__":
    if "-a" in sys.argv:
        Experiment(reactions=False).protocol()
    elif "-r" in sys.argv:
        Experiment(analysis=False).protocol()
    else:
        Experiment().protocol()
