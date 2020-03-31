"""Watcher file that creates and watches all experiment folders created by the algorithms

.. moduleauthor:: Graham Keenan 2019

"""

import os
import sys
import time
import inspect
from typing import Optional, Dict
from multiprocessing import Process

# Locations
HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
ALGORITHMS = os.path.join(HERE, "algorithms")
ROOT = os.path.join(HERE, "..")
PLATFORM = os.path.join(ROOT, "nanobot", "software")
RUN = os.path.join(ROOT, "nanobot_run")
sys.path.append(ALGORITHMS)
sys.path.append(PLATFORM)

# Platform imports
import utils.json_utils as json
import operations.constants.filenames as fn
import operations.constants.info_keys as keys


# Supported Algorithms
GA = "GA"
SINGLE = "single"


def get_watchers(info: dict) -> Optional:
    """
    Gets the Creators and Watchers for the experimental run
    Type of Creator and Watcher depend on the type of algorithm in use

    Args:
        info (Dict): Information about the current experiment

    Returns:
        creator (Creator): Folder generator and assessor of the experiment
        watcher (Watcher): File watcher for the experiment
    """

    alg_type = info[keys.ALGORITHM]

    if alg_type == GA:
        from algorithms.genetic.creator import Creator
        from algorithms.genetic.watcher import Watcher

        return Creator(info), Watcher(info)

    if alg_type == SINGLE:
        from algorithms.single.single_creator import SingleExperimentCreator

        return SingleExperimentCreator(info)

    raise Exception("Algorithm type \"{}\" is not supported!".format(alg_type))

def guard_the_genetic_realm(info: Dict):
    """Manages the processes of Creator and Watcher for the Genetic Algorithm

    Arguments:
        info {dict} -- Experimental information file
    """

    creator, watcher = get_watchers(info)

    creator_process = Process(target=creator.initialise, args=())
    watcher_process = Process(target=watcher.parse_experiment, args=())

    print("Starting Creator and Watcher processes...")
    creator_process.start()
    time.sleep(5)  # Give short pause to let folder be created
    watcher_process.start()

    creator_process.join()
    watcher_process.join()
    print("Successfully joined Creator and Watcher processes.")


def guard_the_single_realm(info: Dict):
    """Calls the single experiment creator to create a single experimental run of X reactions

    Arguments:
        info {dict} -- Experimental information file
    """

    creator = get_watchers(info)

    print("Creating single experiment...")
    creator.create_generation()


def guard_the_realm():
    """Creates watchers and generation managers dependent on algorithm choice
    """

    info = json.read(os.path.join(RUN, fn.INFO_FILE))

    if info[keys.ALGORITHM] == GA:
        guard_the_genetic_realm(info)
    elif info[keys.ALGORITHM] == SINGLE:
        guard_the_single_realm(info)


if __name__ == "__main__":
    guard_the_realm()
