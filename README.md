# Nanomaterials Discovery

Software for the paper "A Nanomaterials Discovery Robot for the Darwinian Evolution of Shape Programmable Gold Nanoparticles" as published in Nature Communications.

![alt](https://user-images.githubusercontent.com/13821621/78034143-3a92ad80-735f-11ea-8186-88617e772eee.JPG)

# Software Requirements

This software requires the following:
* Python >= 3.6 ([Linux](http://docs.python-guide.org/en/latest/starting/install3/linux/) / [Windows](https://www.python.org/downloads/release/python-363/))
* [Arduino IDE](https://www.arduino.cc/en/Main/Software)
* [Arduino Command Handler](https://github.com/croningp/Arduino-CommandHandler)
* [Arduino Command Tools](https://github.com/croningp/Arduino-CommandTools)

## Python Libraries

To install all rquired Python libraries, run the following command: `pip install -r requirements.txt`

# Running The System

Information on firmware setup can be found [here](#arduino-firmware-setup)

The majority of the execution paramters for this platform are all defined in the platform's [`info.json`](nanobot_run/info.json) file. This defined how many generations of experiments to perform as well as which pumps to use, what parameters to use for the GA etc.

## Initial Start
* Make appropriate changes to the `info.json` file
* Navigate to `nanobot_analysis`
* Run the `heimddall.py` file
  * This will create the appropriate folders and populate them depending on algorithm type
  * Leave this window running if using `GA` mode

## Execution
* Navigate to `nanobot_run`
* Run either the `experiment.py` or `ga_experiment.py` file depending on your experiment mode
  * This will look in the appropriate filepaths set up by the `heimdall.py` script and begin to load and execute experiments
* Leave this to run and process experiments
  * `heimdall.py` will automatically process and store experimental data in the appropriate locations
  * This wil lalso update the GA algorithm with fitness values as the generations proceed.
* Once the generations are finished, the experiment has concluded.

# Arduino Firmware Setup

The following is a description of how to set up the Arduino firmware for use with Commanduino.

## Installation
Clone the following repositories and follow the basic set up instructions within (Works with Windows/Linux)
* [Arduino Command Handler](https://github.com/croningp/Arduino-CommandHandler)
* [Arduino Command Tools](https://github.com/croningp/Arduino-CommandTools)

## Basic Setup

* Include the Command Handler and Command Manager at the top of your file and create a CommandManager instance

```C++
#include <CommandHandler.h>
#include <CommandManager.h>
CommandManager cmdMgr;
```

* Include the basic Arduino devices you will be using e.g. AccelSteppers, Servos, etc.

```C++
#include <AccelStepper.h>
#include <LinearAccelStepperActuator.h>

/* Additional Modules if necessary */
```

* Next, include the "Command" version of all your included devices from above

```C++
#include <CommandAccelStepper.h>
#include <CommandLinearAccelStepperActuator.h>
```

* Now instantiate the Arduino device objects and their Command equivalents
    * Note: The numbers are pins and these may change depending on your setup  

```C++
AccelStepper stepper1(AccelStepper::DRIVER, 54, 55);
CommandLinearAccelStepperActuator cmdStepper(stepper1, 3, 38);

/* Additional Object creation */
```

## Setup Function

Within the setup function, we use the created CommandDevice objects and add them to the manager. Each object is given a unique ID that the user specifies.

```C++
void setup() {
    /* Here, "drive_wheel" is the unique ID */
    cmdStepper.registerToCommandManager(cmdMgr, "drive_wheel");

    /* Register the remaining devices in a similar fashion */
}
```

## Loop Function

The loop function only contains single call for the manager to update. Nothing else is required here.

```C++
void loop() {
    cmdMgr.update();
}
```

# Pin Mappings

One of the most common uses of Commanduino is controlling stepper motors for movement, pumps, etc. To be able to use multiple stepper motors on a single Arduino board, a RAMPS shield is used, giving access to 5 possible motor locations and a collection of pins for other devices. Below is a list of pin mappings for using multiple stepper motors on a single RAMPS shield.

```C++
X_STEP_PIN         54
X_DIR_PIN          55
X_ENABLE_PIN       38

Y_STEP_PIN         60
Y_DIR_PIN          61
Y_ENABLE_PIN       56

Z_STEP_PIN         46
Z_DIR_PIN          48
Z_ENABLE_PIN       62

E0_STEP_PIN         26
E0_DIR_PIN          28
E0_ENABLE_PIN       24

E1_STEP_PIN         36
E1_DIR_PIN          34
E1_ENABLE_PIN       30

X_MIN_PIN          3
X_MAX_PIN          2
Y_MIN_PIN          14
Y_MAX_PIN          15
Z_MIN_PIN          18
Z_MAX_PIN          19
```

# Commanduino Setup

This platform uses the COmmanduino library to facilitate all communication between the Arduino board and our Python interface.
More examples can be found [here](https://github.com/croningp/commanduino/tree/master/examples/commanddevices).

## Configuration File

Example config file:

```json
{
    "ios": [
        {
            "port": "/dev/ttyACM0"
        },
        {
            "port": "/dev/ttyACM1"
        },
        {
            "port": "/dev/ttyACM2"
        }
    ],
    "devices": {
        "wheel": {
            "command_id": "wheel",
            "config": {
                "reverted_switch": true,
                "revereted_driection": true,
                "enabled_acceleration": false,
                "speed": 12000,
                "homing_speed": 12000,
                "acceleration": 2000
            }
        },
        "module1": {
            "command_id": "modY",
            "config": {
                "add_whats_necessary_for_device": true
            }
        },
        ...

    }
}
```

### IOS

The ```ios``` key represents the USB port the Arduino port is connected to. Commanduino will scan these ports to find the appropriate Arduino attached. For a single arduino attached, the above setup for ```ios``` is sufficient but for multiple Arduinos, it is best to assign them to a single port only. This prevents clashes.  
For port names:

* Linux
    * `"/dev/ttyACM{number}"`
* Windows
    * `"COM{number}"`

### Devices

The ```devices``` key holds all the information for the devices attached to the Arduino board. In the example above, ```wheel``` and ```module1``` are the names Commanduino will use to access them. Inside the devices, we have the ```command_id``` and ```config```.
* ```command_id```
    * This is unique ID given in the Arduino file. (See [Arduino Setup](#arduino-setup))
* ```config```
    * Dependent on the device type. (See [Commanduino Device Examples](https://github.com/croningp/commanduino/tree/master/examples/commanddevices))

## Commanduino File

Example Commanduino file:

```python
import os
import sys
import json
import time
import inspect

from commanduino import CommandManager # <-- Important!

class CoreDevice(object):
    """
    Class representing a core Commanduino system.
    Allows access to the modules attached

    Args:
        config (str): path to the Commanduino config file
    """
    def __init__(self, config):
        self.mgr = CommandManager.from_configfile(config) # Creates the CommandManager with JSON configuration file

        # Can now access devices attached e.g.
        self.wheel = self.mgr.wheel
        self.module1 = self.mgr.module1
        # etc. etc.

    ...

```

# Authors

* Daniel Salley
* Graham Keenan
* Abhishek Sharma
* Jonathan Grizou
* Sergio Martin Marti

All software and designs were developed as members of the [Cronin Group (University of Glasgow)](http://www.chem.gla.ac.uk/cronin/)
