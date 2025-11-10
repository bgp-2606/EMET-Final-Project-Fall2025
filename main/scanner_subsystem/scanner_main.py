# 3D scanner software - Main controller

import RPi.GPIO as GPIO
import time
from time import sleep
from gpiozero import PWMLED, Button

from stepper_motor import StepperMotor
from image_processing import ImageProcessor
from mesh_generation import MeshGenerator, OBJFileWriter
from email_sender import EmailSender


class Scanner3D:
    """Main 3D scanner controller"""
    def __init__(self, dir_pin=23, step_pin=24, button_pin=20, led_pin=21,
                 email_user='padl0005', email_pass='yA314402'):
        """
        Initialize 3D scanner
        
        Args:
            dir_pin (int): Direction pin for stepper motor
            step_pin (int): Step pin for stepper motor
            button_pin (int): GPIO pin for start button
            led_pin (int): GPIO pin for status LED
            email_user (str): Email username for sending results
            email_pass (str): Email password
        """
        # Hardware components
        self.motor = StepperMotor(dir_pin, step_pin)
        self.button = Button(button_pin)
        self.led = PWMLED(led_pin)
        
        # Processing components
        self.image_processor = ImageProcessor()
        self.mesh_generator = MeshGenerator()
        self.file_writer = OBJFileWriter()
        self.email_sender = EmailSender(email_user, email_pass)
        
        # Scan parameters
        self.angular_resolution =  40 # Number of angles to capture
        self.vertical_resolution = 50  # Number of vertical points per angle
        self.scan_rpm = 10  # Speed of rotation during scan


    def wait_for_start(self):
        """Wait for button press to start scan"""
        while not self.button.is_pressed:
            sleep(0.1)

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
                self.motor.rotate_angle(theta_inc, rpm=self.scan_rpm, direction=1)
                time.sleep(0.2)  # Brief pause for stability

        return mesh_points

    def run(self):
        """Main run loop"""
        try:
            while True:
                print("\n" + "="*50)
                print("3D Scanner Ready")
                print("="*50)
                print("Press button to start scan...")
                self.wait_for_start()
                
                print("\nStarting scan...")
                self.led.pulse()
                
                # Perform scan
                mesh_points = self.perform_scan()
                
                if not mesh_points:
                    print("\nError: No mesh points captured!")
                    self.led.off()
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
                
                # Send email
                try:
                    self.email_sender.send_file('padl0005@algonquinlive.com', filename)
                    print("Email sent successfully!")
                except Exception as e:
                    print(f"Failed to send email: {e}")
                
                self.led.off()
                print("\nScan complete! Ready for next scan.\n")
                
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            self.motor.stop()
            self.motor.cleanup()
            print("Cleanup complete")


if __name__ == "__main__":
    # Create scanner with default settings
    scanner = Scanner3D()
    scanner.run()
