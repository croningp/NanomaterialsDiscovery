"""
JSON Wrappers

.. moduleauthor:: Graham Keenan <https://github.com/ShinRa26>
"""

import json

def read(filepath: str) -> dict:
    """
    Reads a JSON file and returns a python dictionary

    Args:
        filepath (str): File to read

    Returns:
        data (Dict): Python dictionary representation of the JSON data
    """

    with open(filepath) as f_d:
        return json.load(f_d)


def write(data: dict, filepath: str):
    """
    Writes a python dictionary to a JSON file

    Args:
        filepath (str): File to write to
        data (Dict): Data to write to JSON
    """
    with open(filepath, "w") as f_d:
        json.dump(data, f_d, indent=4)
