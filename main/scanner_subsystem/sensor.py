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
        
        pulse_start = 0
        pulse_end = 0
        
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
        
        if pulse_end <= pulse_start:
            return None
        
        # Calculate distance (speed of sound = 34300 cm/s)
        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * 34300) / 2
        
        return distance

    def wait_for_part_placement(self, close_threshold=None, poll_interval=0.1, 
                               confirmations_required=3, samples_per_check=10,
                               outlier_tolerance=0.3):
        """
        Wait for gripper to place part with outlier rejection
        
        Args:
            close_threshold (float): Distance in cm considered "gripper present"
            poll_interval (float): Time between checks
            confirmations_required (int): Number of consecutive readings needed to confirm state
            samples_per_check (int): Number of samples to take per check
            outlier_tolerance (float): Reject readings more than this fraction away from median
                                       (e.g., 0.3 = reject if >30% different from median)
        """
        if close_threshold is None:
            close_threshold = self.threshold
        
        def get_filtered_distance(num_samples, tolerance):
            """Get averaged distance with outlier rejection"""
            distances = []
            for _ in range(num_samples):
                dist = self.get_distance()
                if dist is not None:
                    distances.append(dist)
                time.sleep(0.05)
            
            if not distances:
                return None
            
            # Calculate median
            distances.sort()
            mid = len(distances) // 2
            if len(distances) % 2 == 0:
                median = (distances[mid - 1] + distances[mid]) / 2
            else:
                median = distances[mid]
            
            # Filter outliers - keep only values within tolerance of median
            filtered = []
            for d in distances:
                deviation = abs(d - median) / median if median > 0 else 0
                if deviation <= tolerance:
                    filtered.append(d)
            
            # Average the filtered values
            if filtered:
                avg = sum(filtered) / len(filtered)
                if len(filtered) < len(distances):
                    print(f"      (Filtered {len(distances) - len(filtered)} outliers)")
                return avg
            else:
                # If all were outliers, just return median
                return median
        
        print(f"Waiting for gripper to place part... (threshold: {close_threshold:.2f} cm)")
        
        # Wait for gripper to appear
        print("  Waiting for gripper approach...")
        confirm_count = 0
        while confirm_count < confirmations_required:
            dist = get_filtered_distance(samples_per_check, outlier_tolerance)
            if dist is not None:
                if dist < close_threshold:
                    confirm_count += 1
                    print(f"    Confirmation {confirm_count}/{confirmations_required}: {dist:.2f} cm")
                else:
                    if confirm_count > 0:
                        print(f"    Reset (got {dist:.2f} cm)")
                    confirm_count = 0
            time.sleep(poll_interval)
        
        print(f"  ? Gripper confirmed present!")
        
        # Wait for gripper to retract
        time.sleep(0.5)
        print("  Waiting for gripper retract...")
        confirm_count = 0
        while confirm_count < confirmations_required:
            dist = get_filtered_distance(samples_per_check, outlier_tolerance)
            if dist is not None:
                if dist > close_threshold:
                    confirm_count += 1
                    print(f"    Confirmation {confirm_count}/{confirmations_required}: {dist:.2f} cm")
                else:
                    if confirm_count > 0:
                        print(f"    Reset (got {dist:.2f} cm)")
                    confirm_count = 0
            time.sleep(poll_interval)
        
        print(f"  ? Gripper confirmed retracted!")
        print("? Part placement complete!")
        return True
