"""Module for executing shell commands such as copy files etc.

.. moduleauthor:: Graham Keenan 2019
.. signature:: dd383a145d9a2425c23afc00c04dc054951b13c76b6138c6373597b9bf55c007

"""

import subprocess

def backup(src: str, dst: str):
    """Backs up files to the destination

    Arguments:
        src {str} -- Folder to copy
        dst {str} -- Destination to copy to
    """

    cmd = f"cp -rv {src} {dst}"
    execute_cmd(cmd)


def execute_cmd(cmd: str):
    """Executes a command via subprocess

    Arguments:
        cmd {str} -- Command to execute
    """

    _ = subprocess.call(cmd, shell=True)
