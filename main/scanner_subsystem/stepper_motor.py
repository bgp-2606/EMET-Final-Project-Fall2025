import RPi.GPIO as GPIO
import time

class StepperMotor:
    """
    Class to control a NEMA 17 stepper motor with A4988 driver
    """
    
    def __init__(self, dir_pin, step_pin, steps_per_rev=200, microstep_multiplier=1):
        """
        Initialize the stepper motor controller
        
        Args:
            dir_pin (int): GPIO pin for direction control
            step_pin (int): GPIO pin for step control
            steps_per_rev (int): Steps per revolution for the motor (default 200 for 1.8° motor)
            microstep_multiplier (int): Microstepping multiplier set in hardware (1, 2, 4, 8, 16)
        """
        self.dir_pin = dir_pin
        self.step_pin = step_pin
        self.steps_per_rev = steps_per_rev
        self.microstep_multiplier = microstep_multiplier
        
        self._setup_gpio()
    
    def _setup_gpio(self):
        """Initialize GPIO pins"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup pins as outputs
        GPIO.setup(self.dir_pin, GPIO.OUT)
        GPIO.setup(self.step_pin, GPIO.OUT)
        
        # Set initial states
        GPIO.output(self.dir_pin, GPIO.LOW)
        GPIO.output(self.step_pin, GPIO.LOW)

    
    def step(self, steps, delay=0.001, direction=1):
        """
        Move the motor a specific number of steps
        
        Args:
            steps (int): Number of steps to take
            delay (float): Delay between steps in seconds (controls speed)
            direction (int): 1 for clockwise, 0 for counter-clockwise
        """
        GPIO.output(self.dir_pin, direction)
        
        for _ in range(steps):
            GPIO.output(self.step_pin, GPIO.HIGH)
            time.sleep(delay)
            GPIO.output(self.step_pin, GPIO.LOW)
            time.sleep(delay)
    
    def rotate_angle(self, angle, rpm=60, direction=1):
        """
        Rotate the motor by a specific angle at constant speed
        
        Args:
            angle (float): Angle to rotate in degrees
            rpm (int): Revolutions per minute (speed)
            direction (int): 1 for clockwise, 0 for counter-clockwise
        """
        # Calculate total steps needed for the angle
        microsteps_per_rev = self.steps_per_rev * self.microstep_multiplier
        total_steps = int((angle / 360.0) * microsteps_per_rev)
        
        # Calculate delay to achieve desired RPM
        delay = 60.0 / (rpm * microsteps_per_rev * 2)
        
        self.step(total_steps, delay, direction)
    
    def rotate_revolutions(self, revolutions, rpm=60, direction=1):
        """
        Rotate the motor by a specific number of revolutions
        
        Args:
            revolutions (float): Number of revolutions to rotate
            rpm (int): Revolutions per minute (speed)
            direction (int): 1 for clockwise, 0 for counter-clockwise
        """
        angle = revolutions * 360
        self.rotate_angle(angle, rpm, direction)
    
    def stop(self):
        """Stop the motor immediately"""
        GPIO.output(self.step_pin, GPIO.LOW)
    
    def cleanup(self):
        """Clean up GPIO pins"""
        GPIO.cleanup()
        print("GPIO cleanup complete")
