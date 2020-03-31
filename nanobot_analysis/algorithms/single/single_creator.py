"""Module for creating a single experiment with parameters defined in the information file.

Similar implementation to that in the ALC Creator

.. moduleauthor:: Graham Keenan 2019

"""

import os
import sys
import inspect
import filetools
from typing import Dict

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
ROOT = os.path.join(HERE, "..", "..", "..")
RUN = os.path.join(ROOT, "nanobot_run")
DATA = os.path.join(RUN, "data")
PLATFORM = os.path.join(ROOT, "nanobot", "software")

sys.path.append(PLATFORM)

# Platform imports
import utils.json_utils as json
import operations.constants.filenames as fn
import operations.constants.info_keys as keys

class SingleExperimentCreator(object):
    """Class for creating a single experiment folder structure

    Pretty much reimplements the ALC creator but for a single run

    Arguments:
        info {dict} -- Info from info file
    """
    def __init__(self, info: Dict):
        self.info = info
        self.xp_path = self.generate_xp_path()
        self.params = self.info[keys.SINGLE]


    def generate_xp_path(self) -> str:
        """Generates a path to the experiment folder
        Creates the flder if it doesn't exist already

        Returns:
            str -- Experiment path
        """
        path = os.path.join(
            DATA,
            "single_experiments",
            self.info[keys.TITLE]
        )

        filetools.ensure_dir(path)

        return path


    def create_generation(self):
        """Creates the experiment folder and populates all folders with params.

        Params are defined in the Info file
        """
        gen_number = filetools.generate_n_digit_name(0)
        gen_folder = os.path.join(self.xp_path, gen_number)
        filetools.ensure_dir(gen_folder)
        print(f"Creating generation: {os.path.relpath(gen_folder)}")

        for xp_num in range(self.info[keys.XP]):
            xp_folder_name = filetools.generate_n_digit_name(xp_num)
            xp_folder = os.path.join(gen_folder, xp_folder_name)
            filetools.ensure_dir(xp_folder)

            params_file = os.path.join(xp_folder, fn.PARAMS_FILE)
            json.write(self.params, params_file)
