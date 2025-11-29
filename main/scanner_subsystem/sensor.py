import RPi.GPIO as GPIO
import time
from time import sleep

class UltrasonicSensor:
    """Ultrasonic distance sensor for part detection"""
    def __init__(self, trigger_pin, echo_pin, detection_threshold=12.0):
        """
        Initialize ultrasonic sensor
        
        Args:
            trigger_pin (int): GPIO pin for trigger
            echo_pin (int): GPIO pin for echo
            detection_threshold (float): Distance in cm below which part is detected
        """
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.threshold = detection_threshold
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trigger_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        GPIO.output(self.trigger_pin, GPIO.LOW)
        time.sleep(0.1)  # Let sensor settle
    
    def get_distance(self):
        """
        Measure distance in centimeters
        
        Returns:
            float: Distance in cm, or None if measurement fails
        """
        # Send trigger pulse
        GPIO.output(self.trigger_pin, GPIO.HIGH)
        time.sleep(0.00001)  # 10 microsecond pulse
        GPIO.output(self.trigger_pin, GPIO.LOW)
        
        # Wait for echo start (with timeout)
        timeout = time.time() + 0.1  # 100ms timeout
        while GPIO.input(self.echo_pin) == GPIO.LOW:
            pulse_start = time.time()
            if pulse_start > timeout:
                return None
        
        # Wait for echo end (with timeout)
        timeout = time.time() + 0.1
        while GPIO.input(self.echo_pin) == GPIO.HIGH:
            pulse_end = time.time()
            if pulse_end > timeout:
                return None
        
        # Calculate distance (speed of sound = 34300 cm/s)
        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * 34300) / 2
        
        return distance

    def wait_for_part_placement(self, close_threshold=None, poll_interval=0.1, 
                                        num_samples=15):
        """
        Wait for gripper using averaged distance readings
        
        Args:
            close_threshold (float): Distance in cm considered "gripper present"
            poll_interval (float): Time between checks
            num_samples (int): Number of samples to average for each check
        """
        if close_threshold is None:
            close_threshold = self.threshold
        
        def get_average_distance(samples):
            """Get average of multiple distance readings, filtering out None"""
            distances = []
            for _ in range(samples):
                dist = self.get_distance()
                if dist is not None:
                    distances.append(dist)
                time.sleep(0.05)
            if distances:
                return sum(distances) / len(distances)
            return None
        
        print(f"Waiting for gripper to place part... (threshold: {close_threshold:.2f} cm)")
        
        # Wait for gripper to appear
        print("  Waiting for gripper approach...")
        while True:
            avg_dist = get_average_distance(num_samples)
            if avg_dist is not None:
                print(f"    Average distance: {avg_dist:.2f} cm")
                if avg_dist < close_threshold:
                    print(f"  ✓ Gripper confirmed present!")
                    break
            time.sleep(poll_interval)
        
        # Wait for gripper to retract
        time.sleep(0.5)
        print("  Waiting for gripper retract...")
        while True:
            avg_dist = get_average_distance(num_samples)
            if avg_dist is not None:
                print(f"    Average distance: {avg_dist:.2f} cm")
                if avg_dist > close_threshold:
                    print(f"  ✓ Gripper confirmed retracted!")
                    break
            time.sleep(poll_interval)
        
        print("✓ Part placement complete!")
        return True
