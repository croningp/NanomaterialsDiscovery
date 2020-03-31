import os
import sys
import time
import inspect
import filetools

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
BASE = os.path.join(HERE, "..", "..")
ROOT = os.path.join(BASE, "..")
PLATFORM = os.path.join(ROOT, "nanobot", "software")
RUN = os.path.join(ROOT, "nanobot_run")
DATA = os.path.join(RUN, "data", "genetic")

sys.path.append(PLATFORM)

import genetic.fitness as fitness_func
import utils.json_utils as json
import operations.constants.common as cst
import operations.constants.filenames as fn
import operations.constants.info_keys as keys

# Objective
TARGET_TO_INCREASE = 553 # 80nm sphere

# Peak to decrease if two peak system
TARGET_TO_DECREASE = 515


class Watcher(object):
    """
    Class for watching a series of experiment folders for UV files
    Once they have been found, they are processed and a fitness value given to the experiment

    Args:
        info (Dict): Information about the overall experiment
    """
    def __init__(self, info):
        self.info = info
        self.xp_path = self.get_xp_path()
        self.total_generations = self.info[keys.GENS]
        self.current_generation_number = 0


    def get_xp_path(self):
        """
        Gets the current experiment folder
        """
        path = os.path.join(DATA, self.info[keys.TITLE], str(self.info[keys.SEED]))
        filetools.ensure_dir(path)
        return path


    def parse_experiment(self):
        """
        Parses all generations in a given experimental run
        Takes a generation and obtains the fitness values for each experiment in each
        """
        for _ in range(self.total_generations):
            self.parse_generation()


    def parse_generation(self):
        """
        Watches a single generation folder for UV data
        Parses all experiments and obtains a fitness value for each and list of all values for 
        the generation

        Returns:
            fitness_list (List): List of fitness values for each experiment in the generation
        """
        gen_number = filetools.generate_n_digit_name(self.current_generation_number)
        current_generation_path = os.path.join(self.xp_path, gen_number)

        while not os.path.exists(current_generation_path):
            time.sleep(1)

        print("Currently watching generation: {}.".format(gen_number))
        if os.path.exists(os.path.join(current_generation_path, fn.FITNESS_FILE)):
            self.current_generation_number += 1
            print(
                f"Fitnesses already calculated for generation: {self.current_generation_number:04d}"
            )
            return

        fitness_list = self.parse_xp_folders(current_generation_path)
        self.write_fitness_to_file(current_generation_path, fitness_list)
        self.current_generation_number += 1


    def parse_xp_folders(self, generation_path):
        """
        Parses all experiments in a generation to get their fitnesses

        Args:
            generation_path (str): Path of the current generation folder

        Returns:
            fitnesses (List): List of all the fitnesses for a generation
        """
        fitnesses = []
        xp_folders = filetools.list_folders(generation_path)

        for xp in sorted(xp_folders):
            # Do not process the ideal experiment for fitness
            if "ideal" in xp:
                continue

            print(f"Experiment: {xp}")
            fitness = self.parse_uv_for_fitness(xp)
            print(f"Fitness: {fitness}")
            self.write_fitness_to_file(xp, fitness)
            fitnesses.append(fitness)
        return fitnesses


    def parse_uv_for_fitness(self, xp_folder):
        """
        Waits until a UV file is present and processes it for a fitness value

        Args:
            xp_folder (str): Path of the folder to watch

        Returns:
            fitness (float): Fitness for the experiment
        """
        uv_file = os.path.join(xp_folder, fn.UV_JSON)
        while not os.path.exists(uv_file):
            time.sleep(1)
        uv_data = self.parse_file(uv_file)
        print("Calculating fitness of {}.".format(xp_folder))
        return self.calculate_fitness(uv_data)


    def calculate_fitness(self, uv_data):
        """
        Calculates the fitness for a set of UV data

        Args:
            uv_data (Dict): Series of UV data contianing wavelength and absorbance

        Returns:
            fitness (float): Fitness value of the UV data
        """
        wavelength = uv_data[cst.WAVELENGTH]
        absorbance = uv_data[cst.ABSORBANCE]

        # Do new fitness here
        # return fitness_func.rods_fitness(wavelength, absorbance)
        return fitness_func.octahedron_fitness(wavelength, absorbance)


    def write_fitness_to_file(self, xp_path, fitness):
        """
        Writes the fitness value to the experiment folder

        Args:
            xp_path (str): path to the experiment folder
            fitness (float/List): Fitness value to write or List of fitnesses
        """
        filename = os.path.join(xp_path, fn.FITNESS_FILE)
        data = {
            "fitness": fitness
        }
        json.write(data, filename)


    def parse_file(self, path):
        """
        Parses a JSON file

        Args:
            path (str): path to file

        Returns:
            json_data (Dict): JSON data as a dictionary
        """
        while self.is_file_busy(path):
            time.sleep(0.5)
        return json.read(path)


    def is_file_busy(self, path, modified_time=1):
        """
        Checks of a file is currently busy (being written to)

        Args:
            path (str): Path to file
            modified_time (int/float): Time to wait until it is checked after initial check
        """
        time_start = os.stat(path).st_mtime
        time.sleep(modified_time)
        time_end = os.stat(path).st_mtime
        return time_end > time_start
