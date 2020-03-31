"""
.. module:: logger
    :platform: Unix
    :synopsis: Module for logging information about the paltform

.. moduleauthor:: Graham Keenan <https://github.com/ShinRa26>

"""

import os
import sys
import time
import socket
import inspect
import logging
import threading
from queue import Queue

HERE = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

PLATFORM_NAME = "NANOBOT"
TERMINATE = "TERMINATE"
LOG_FOLDER = "/home/group/workspace/nanobot/nanobot_run/logs"
LOG_FILE = os.path.join(LOG_FOLDER, "{}.log".format(time.strftime("%Y%m%d_%H%M"))) # Needs personal project path

ARKENSTONE = ("130.209.221.130", 9000) # Change to remote address (Ask Graham)


class Logger(object):
    """
    Logger class with option for remote connection to log server (Arkenstone)

    Args:
        remote (bool): Use remote connection or not
    """
    
    def __init__(self, remote=False):
        self.logger = self.get_logger()
        self.msg_queue = Queue()
        self.client = None

        if remote:
            try:
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.connect(ARKENSTONE)
                self.remote_initialisation()
                self.log_thread = threading.Thread(target=self.remote_log, args=())
                self.log_thread.start()
            except Exception as e:
                print("Error connecting to Arkenstone, continuing offline.\nError: {}".format(e))


    def __del__(self):
        """
        Destructor for cleaning up the remote connection thread
        """

        try:
            self.msg_queue.put("TERMINATE")
            self.log_thread.join()
        except:
            pass # Only cleans up the thread if remote is active


    def get_logger(self) -> logging.Logger:
        """
        Sets up the logger object for logging messages

        Returns:
            logger (Logger): Logger object
        """

        logger = logging.getLogger(PLATFORM_NAME)
        logger.setLevel(logging.INFO)

        fh = logging.FileHandler(filename=LOG_FILE)
        fh.setLevel(logging.INFO)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s - %(name)s::%(levelname)s -- %(message)s")
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger


    def info(self, msg: str):
        """
        Logs a message with the logger.
        If there is a remote connection, add it to the message queue to be sent

        Args:
            msg (str): Message to log
        """

        msg = "{} -- {}".format(time.strftime("%d_%m_%Y:%H%M"), msg)
        if self.client:
            self.msg_queue.put(msg)

        self.logger.info(msg)


    def remote_initialisation(self):
        """
        Initialises the platform on hte remote server
        """

        self.client.sendall("{}::INIT".format(PLATFORM_NAME).encode())

    def remote_log(self):
        """
        Thread method for sending logged messages to the remote server
        """

        while True:
            msg = self.msg_queue.get()

            if msg == TERMINATE:
                self.cleanup()
                break

            msg = "{0}::LOG::{1}".format(PLATFORM_NAME, msg)
            self.client.sendall(msg.encode())


    def cleanup(self):
        """
        Closes down the connection to the remote server, if present
        """

        if self.client:
            print("Shutting down Arkenstone client...")
            self.client.shutdown(2)
            self.client.close()
