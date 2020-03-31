"""
.. module:: CameraControl
    :platform: Unix
    :synopsis: Module for interfacing with attached Webcams

.. moduleauthor:: Graham Keenan <https://github.com/ShinRa26>

"""

import os
import sys
import inspect

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
root_path = os.path.join(HERE, "..", "..")
op_path = os.path.join(HERE, "..")

sys.path.append(root_path)
sys.path.append(op_path)

from base_layer.camera import camera_setup


class CameraControl(object):
    """
    Class for controling the camera attached to the platform
    Allows for recording of a video and taking an image
    """
    def __init__(self):
        pass


    def record(self, video_name: str, duration: int):
        """
        Records a video to file

        Args:
            video_name (str): Location of where to save the video
            duration (int/float): Duration of the video
        """

        camera_setup.record_video(video_name, duration)


    def take_image(self, save_loc: str):
        """
        Takes an image and saves it to file

        Args:
            save_loc (str): Location to save the image
        """

        camera_setup.take_image(save_loc)
