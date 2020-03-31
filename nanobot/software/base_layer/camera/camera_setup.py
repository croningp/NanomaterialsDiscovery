"""
.. module:: camera_setup
    :platform: Unix
    :synopsis: Module for setting up a webcam for recording video

.. moduleauthor:: Graham Keenan <graham.keenan@glasgow.ac.uk>

"""
import os
import sys
import time
import inspect
HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

# adding parent directory to path, so we can access the utils easily
root_path = os.path.join(HERE, '..', "..")
base_path = os.path.join(HERE, "..")
sys.path.append(base_path)
sys.path.append(root_path)

from utils import json_utils

camera_config = json_utils.read("./camera-config.json")
control_config = camera_config["control_config"]

import cv2
import numpy as np


def record_video(save_loc: str, duration, fps=30):
    """
    Records a video to file

    Args:
        save_loc (str): path to save the video
        duration (int/float): Duration of the video
        fps (int): Frames per second of recording.
    """
    cap = cv2.VideoCapture(camera_config["device"])
    cap.set(cv2.CAP_PROP_AUTOFOCUS, control_config["focus_auto"])
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(save_loc, fourcc, fps, (640, 480))

    curr_time = time.time()

    while cap.isOpened():
        if time.time() > curr_time + duration:
            break
        ret, frame = cap.read()
        if ret == True:
            out.write(frame)
            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()


def take_image(save_loc: str):
    """
    Takes an image and saves it to file

    Args:
        save_loc (str): Path to save the image
    """
    cap = cv2.VideoCapture(0)
    _, image = cap.read()
    cv2.imwrite(save_loc, image)
    cap.release()
