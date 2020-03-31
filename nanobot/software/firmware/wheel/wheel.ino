/**
#define X_STEP_PIN         54
#define X_DIR_PIN          55
#define X_ENABLE_PIN       38

#define Y_STEP_PIN         60
#define Y_DIR_PIN          61
#define Y_ENABLE_PIN       56

#define Z_STEP_PIN         46
#define Z_DIR_PIN          48
#define Z_ENABLE_PIN       62

#define E0_STEP_PIN         26
#define E0_DIR_PIN          28
#define E0_ENABLE_PIN       24

#define E1_STEP_PIN         36
#define E1_DIR_PIN          34
#define E1_ENABLE_PIN       30

 #define X_MIN_PIN          3
 #define X_MAX_PIN          2
 #define Y_MIN_PIN          14
 #define Y_MAX_PIN          15
 #define Z_MIN_PIN          18
 #define Z_MAX_PIN          19
 **/

#include <CommandHandler.h>
#include <CommandManager.h>
CommandManager cmdMgr;

/* Include the base files needed such as Accel Stepper, Servo etc */
#include <AccelStepper.h>
#include <LinearAccelStepperActuator.h>

/* Include the "Command" version of the above */
#include <CommandAccelStepper.h>
#include <CommandLinearAccelStepperActuator.h>

//PWM for fans
#include <CommandAnalogWrite.h>

// Laser Power Control
#include <CommandDigitalWrite.h>


/* Set up the base objects and Command objects */
AccelStepper stepperX(AccelStepper::DRIVER, 54, 55);
CommandLinearAccelStepperActuator X(stepperX, 3, 38);

AccelStepper stepperY(AccelStepper::DRIVER, 60, 61);
CommandLinearAccelStepperActuator Y(stepperY, 14, 56);

AccelStepper stepperZ(AccelStepper::DRIVER, 46, 48);
CommandLinearAccelStepperActuator Z(stepperZ, 18, 62);

AccelStepper stepperE0(AccelStepper::DRIVER, 26, 28);
CommandLinearAccelStepperActuator E0(stepperE0, 2, 24);

AccelStepper stepperE1(AccelStepper::DRIVER, 36, 34);
CommandLinearAccelStepperActuator E1(stepperE1, 15, 30);


//PWM
CommandAnalogWrite ring(8);
CommandAnalogWrite laser(4);


/* Do this for the rest of your devices */

void setup() {
    Serial.begin(115200); // Always 115200

    /* Register devices to the command manager */
    X.registerToCommandManager(cmdMgr, "wheel"); 
    Y.registerToCommandManager(cmdMgr, "zdsd");
    Z.registerToCommandManager(cmdMgr, "sdsd");
    E0.registerToCommandManager(cmdMgr, "msd1"); 
    E1.registerToCommandManager(cmdMgr, "pumpE1");
    
    /* Do this for the rest of your devices */
    ring.registerToCommandManager(cmdMgr, "ring");
    laser.registerToCommandManager(cmdMgr, "laser");

    cmdMgr.init();
}

void loop() {
    cmdMgr.update();
    /* Nothing else needed here */
}
