# 3D scanner software - Main controller

import RPi.GPIO as GPIO
import time
from time import sleep
from gpiozero import PWMLED, Button

from sensor import UltrasonicSensor
from stepper_motor import StepperMotor
from image_processing import ImageProcessor
from mesh_generation import MeshGenerator, OBJFileWriter


class Scanner3D:
    """Main 3D scanner controller"""
    def __init__(self, dir1_pin=23, step1_pin=24, dir2_pin=25, step2_pin=12, 
                 switch_pin=16, green_led_pin=21, red_led_pin=20,
                 sensor_trig_pin=17, sensor_echo_pin=27):
        """
        Initialize 3D scanner
        
        Args:
            dir1_pin (int): Direction pin for stepper motor 1 (scanner table)
            step1_pin (int): Step pin for stepper motor 1 (scanner table)
            dir2_pin (int): Direction pin for stepper motor 2 (lid motor)
            step2_pin (int): Step pin for stepper motor 2 (lid motor)
            switch_pin (int): GPIO pin for the lid limit switch
            green_led_pin (int): GPIO pin for scanner status LED
            red_led_pin (int): GPIO pin for scanner fault LED
            sensor_trig_pin (int): GPIO pin for ultrasonic trigger
            sensor_echo_pin (int): GPIO pin for ultrasonic echo
        """
        # Hardware components
        self.motor1 = StepperMotor(dir1_pin, step1_pin, microstep_multiplier=32)
        self.motor2 = StepperMotor(dir2_pin, step2_pin, microstep_multiplier=16)
        self.switch = Button(switch_pin, bounce_time=0.05)
        self.sensor = UltrasonicSensor(sensor_trig_pin, sensor_echo_pin, detection_threshold=12.0)
        self.green_led = PWMLED(green_led_pin)
        self.red_led = PWMLED(red_led_pin)
        
        # Processing components
        self.image_processor = ImageProcessor()
        self.mesh_generator = MeshGenerator()
        self.file_writer = OBJFileWriter()
        
        # Scan parameters
        self.angular_resolution =  40 # Number of angles to capture
        self.vertical_resolution = 50  # Number of vertical points per angle
        self.scan_rpm = 10  # Speed of rotation during scan

        # Lid open/close parameter
        self.lid_angle = 360
        self.lid_rpm = 120
        self.lid_curr_pos = 0

    def perform_scan(self):
        """Execute a complete 3D scan"""
        mesh_points = []
        theta = 0
        theta_inc = 360.0 / self.angular_resolution

        print(f"Starting scan with {self.angular_resolution} angles")
        
        for scan_step in range(self.angular_resolution):
            # Capture and process image
            img = self.image_processor.capture_image()
            processed_img, bottom_row = self.image_processor.process_image(img, save_intermediate=True)
            
            # Extract coordinates
            coords = self.image_processor.extract_coordinates(processed_img, bottom_row, theta)
            coords = self.image_processor.downsample_coordinates(coords, self.vertical_resolution)
            
            if coords:
                mesh_points.append(coords)
                print(f"Step {scan_step + 1}/{self.angular_resolution}: "
                      f"Captured {len(coords)} points at angle {theta:.1f}°")
            else:
                print(f"Step {scan_step + 1}/{self.angular_resolution}: No points detected at {theta:.1f}°")

            # Move motor to next angle
            theta += theta_inc
            if scan_step < self.angular_resolution - 1:  # Don't rotate after last capture
                self.motor1.rotate_angle(theta_inc, rpm=self.scan_rpm, direction=1)
                time.sleep(0.2)  # Brief pause for stability

        return mesh_points

    def run(self):
        """Main run loop"""
        try:
            while True:
                print("\n" + "="*50)
                print("3D Scanner Ready")
                print("="*50)

                print("Place part on scanner table...")
                # Wait for part
                self.sensor.wait_for_part_placement()
                
                # Wait 5 seconds for robot gripper to move away
                time.sleep(5)
                
                print("Close lid...")
                #self.motor2.rotate_angle(self.lid_angle, rpm=self.lid_rpm, direction=0)
                
                print("Wait until lid is FULLY closed...")
                self.switch.wait_for_press()
                
                print("\nStarting scan...")
                self.green_led.pulse()
                
                # Perform scan
                mesh_points = self.perform_scan()
                
                if not mesh_points:
                    print("\nError: No mesh points captured!")
                    self.green_led.off()
                    self.red_led.pulse()
                    continue
                
                print(f"\nScan complete! Captured {len(mesh_points)} scan lines")
                
                # Generate mesh
                print("Generating 3D mesh...")
                mesh_points = self.mesh_generator.normalize_mesh_points(mesh_points)
                points, faces = self.mesh_generator.generate_mesh(mesh_points)
                
                print(f"Mesh generated: {len(points)} vertices, {len(faces)} faces")
                
                # Save to file
                filename = '3d.obj'
                self.file_writer.write(filename, points, faces)
                print(f"Mesh saved to {filename}")

                #self.motor2.rotate_angle(self.lid_angle, rpm=self.lid_rpm, direction=1)

                self.green_led.off()
                print("\nScan complete!\n")
                
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            self.motor1.stop()
            self.motor2.stop()
            self.motor1.cleanup()
            self.motor2.cleanup()
            print("Cleanup complete")


if __name__ == "__main__":
    # Create scanner with default settings
    scanner = Scanner3D()
    scanner.run()
