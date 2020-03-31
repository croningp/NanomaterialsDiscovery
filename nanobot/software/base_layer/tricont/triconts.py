"""
.. module:: triconts
    :platform: Unix, Windows
    :synopsis: Module for interfacing with Tricontinent C3000 pumps through PyCont

.. moduleauthor:: Graham Keenan <https://github.com/ShinRa26>

"""

import os
import inspect
import logging
import json

logging.basicConfig(level=logging.INFO)

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
from pycont.controller import MultiPumpController

config_path = os.path.join(HERE, "pycont_config.json")
controller = MultiPumpController.from_configfile(config_path)

with open(config_path) as f:
    config = json.load(f)

controller.smart_initialize()

pumps = controller.get_pumps(controller.pumps)
for pump in pumps:
    pump.go_to_volume(0)
