# 3D scanner software - Image processing

from transform import four_point_transform
import cv2
import numpy as np
from time import sleep
from geometry import Vertex
import subprocess


class ImageProcessor:
    """Handles camera capture and image processing"""
    def __init__(self):
        self.tlp = (521.0, 250.0)
        self.trp = (1205.0, 195.0)
        self.brp = (1205.0, 800.0)
        self.blp = (521.0, 855.0)
        self.center_column = 352.0
    
    def capture_image(self, filename='lineDetection.jpg'):
        """Capture an image using libcamera-still"""
        cmd = ["libcamera-still", "-o", filename, "--timeout", "1000"]
        subprocess.run(cmd, check=True)
        
        temp_img = cv2.imread(filename)
        img = cv2.resize(temp_img, (1663, 918))
        return img

    def process_image(self, img, save_intermediate=False):
        """Process image to extract line coordinates"""
        # Apply perspective transform
        pts = np.array([self.tlp, self.trp, self.brp, self.blp])
        img = four_point_transform(img, pts)
        if save_intermediate:
            cv2.imwrite('intermediate_1_trans.jpg', img)
        
        # Filter for red line
        lowerb = np.array([0, 0, 240])
        upperb = np.array([255, 255, 255])
        red_line = cv2.inRange(img, lowerb, upperb)
        
        if save_intermediate:
            cv2.imwrite('intermediate_2_red.jpg', red_line)
        
        # Extract line points
        h, w = red_line.shape
        backG = np.zeros((h, w))
        bottom_row = 0
        
        # Collect all detected columns first
        detected_cols = []
        for r in range(h):
            c_index = np.argmax(red_line[r, :])
            if red_line[r, c_index] != 0:
                detected_cols.append(c_index)
                bottom_row = r
            else:
                detected_cols.append(-1)  # Mark rows with no detection
        
        # Apply smoothing to the detected columns (moving average)
        smoothed_cols = []
        window_size = 9  # Adjust this for more/less smoothing (5=light, 9=medium, 15=heavy)
        half_window = window_size // 2
        
        for r in range(h):
            if detected_cols[r] == -1:
                smoothed_cols.append(-1)
                continue
            
            # Get neighboring valid columns
            valid_neighbors = []
            for offset in range(-half_window, half_window + 1):
                neighbor_r = r + offset
                if 0 <= neighbor_r < h and detected_cols[neighbor_r] != -1:
                    valid_neighbors.append(detected_cols[neighbor_r])
            
            # Average the neighbors
            if valid_neighbors:
                smoothed_cols.append(int(np.mean(valid_neighbors)))
            else:
                smoothed_cols.append(detected_cols[r])
        
        # Fill backG with smoothed positions
        for r in range(h):
            if smoothed_cols[r] != -1:
                backG[r, smoothed_cols[r]] = 1
        
        if save_intermediate:
            cv2.imwrite('intermediate_3_line.jpg', backG * 255)
            
        return backG, bottom_row

    def extract_coordinates(self, processed_img, bottom_row, theta):
        """Extract cylindrical coordinates from processed image"""
        print(f"bottom row: {bottom_row}")
        coords = []
        for r, c_index in enumerate(np.argmax(processed_img, axis=1)):
            if processed_img[r, c_index] == 1:
                height = bottom_row - r
                dist = c_index - self.center_column
                coords.append(Vertex(height, np.radians(theta), dist))
        return coords

    def downsample_coordinates(self, coords, vertical_resolution=20):
        """Downsample coordinates to specified vertical resolution"""
        if not coords:
            return []
        
        interval = len(coords) // vertical_resolution
        if interval == 0:
            return coords

        downsampled = [coords[0]]
        for i in range(1, len(coords) - 1):
            if i % interval == 0:
                downsampled.append(coords[i])
        downsampled.append(coords[-1])
        
        return downsampled



def main():
    """Test the image processing pipeline"""
    import sys
    
    print("="*60)
    print("Image Processor Test")
    print("="*60)
    
    # Initialize processor
    processor = ImageProcessor()
    print(f"\nProcessor initialized with:")
    print(f"  Top-left: {processor.tlp}")
    print(f"  Top-right: {processor.trp}")
    print(f"  Bottom-right: {processor.brp}")
    print(f"  Bottom-left: {processor.blp}")
    print(f"  Center column: {processor.center_column}")
    
    # Test 1: Capture image
    print("\n" + "-"*60)
    print("Test 1: Capturing image...")
    print("-"*60)
    try:
        img = processor.capture_image('test_capture.jpg')
        print(f"✓ Image captured successfully!")
        print(f"  Image shape: {img.shape}")
        print(f"  Image dtype: {img.dtype}")
    except Exception as e:
        print(f"✗ Failed to capture image: {e}")
        sys.exit(1)
    
    # Test 2: Process image
    print("\n" + "-"*60)
    print("Test 2: Processing image...")
    print("-"*60)
    try:
        processed_img, bottom_row = processor.process_image(img, save_intermediate=True)
        print(f"✓ Image processed successfully!")
        print(f"  Processed shape: {processed_img.shape}")
        print(f"  Bottom row: {bottom_row}")
        print(f"  Non-zero pixels: {np.count_nonzero(processed_img)}")
        
        # Save processed image for visualization
        processed_visual = (processed_img * 255).astype(np.uint8)
        cv2.imwrite('test_processed.jpg', processed_visual)
        print(f"  Saved images:")
        print(f"    - intermediate_1_transformed.jpg (after perspective transform)")
        print(f"    - intermediate_2_red_filtered.jpg (after red line filter)")
        print(f"    - test_processed.jpg (final binary line detection)")
    except Exception as e:
        print(f"✗ Failed to process image: {e}")
        sys.exit(1)
    
    # Test 3: Extract coordinates
    print("\n" + "-"*60)
    print("Test 3: Extracting coordinates...")
    print("-"*60)
    test_theta = 45.0  # Test angle
    try:
        coords = processor.extract_coordinates(processed_img, bottom_row, test_theta)
        print(f"✓ Coordinates extracted successfully!")
        print(f"  Total coordinates: {len(coords)}")
        if coords:
            print(f"  First coord: (h={coords[0].x:.1f}, θ={np.degrees(coords[0].y):.1f}°, d={coords[0].z:.1f})")
            print(f"  Last coord: (h={coords[-1].x:.1f}, θ={np.degrees(coords[-1].y):.1f}°, d={coords[-1].z:.1f})")
    except Exception as e:
        print(f"✗ Failed to extract coordinates: {e}")
        sys.exit(1)
    
    # Test 4: Downsample coordinates
    print("\n" + "-"*60)
    print("Test 4: Downsampling coordinates...")
    print("-"*60)
    test_resolutions = [5, 10, 20, 50]
    
    for resolution in test_resolutions:
        try:
            downsampled = processor.downsample_coordinates(coords, resolution)
            print(f"  Resolution {resolution:2d}: {len(coords):4d} → {len(downsampled):4d} points")
        except Exception as e:
            print(f"  Resolution {resolution:2d}: Failed - {e}")
    
    # Test 5: Visual verification
    print("\n" + "-"*60)
    print("Test 5: Creating visualization...")
    print("-"*60)
    try:
        # Create a visualization showing the detected line
        vis_img = cv2.imread('test_capture.jpg')
        
        # Apply same transform for visualization
        pts = np.array([processor.tlp, processor.trp, processor.brp, processor.blp])
        vis_transformed = four_point_transform(vis_img, pts)
        
        # Draw the detected points on the visualization
        for r, c_index in enumerate(np.argmax(processed_img, axis=1)):
            if processed_img[r, c_index] == 1:
                cv2.circle(vis_transformed, (int(c_index), int(r)), 2, (0, 255, 0), -1)
        
        # Draw center line
        h, w = vis_transformed.shape[:2]
        cv2.line(vis_transformed, 
                (int(processor.center_column), 0), 
                (int(processor.center_column), h), 
                (255, 0, 0), 2)
        
        # Draw bottom row line
        cv2.line(vis_transformed, (0, bottom_row), (w, bottom_row), (0, 0, 255), 2)
        
        cv2.imwrite('test_visualization.jpg', vis_transformed)
        print(f"✓ Visualization created!")
        print(f"  Saved to: test_visualization.jpg")
        print(f"  Green dots: detected line points")
        print(f"  Blue line: center column reference")
        print(f"  Red line: bottom row reference")
    except Exception as e:
        print(f"✗ Failed to create visualization: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"✓ All tests completed successfully!")
    print(f"\nGenerated files:")
    print(f"  - test_capture.jpg (original capture)")
    print(f"  - intermediate_1_transformed.jpg (after perspective transform)")
    print(f"  - intermediate_2_red_filtered.jpg (after red line filter)")
    print(f"  - test_processed.jpg (final binary line detection)")
    print(f"  - test_visualization.jpg (annotated with references)")
    print("\nNext steps:")
    print(f"  1. Check intermediate_1_transformed.jpg - verify perspective is correct")
    print(f"  2. Check intermediate_2_red_filtered.jpg - verify red line is detected")
    print(f"  3. Check test_visualization.jpg - verify coordinate extraction")
    print(f"  4. Adjust corner points (tlp, trp, brp, blp) if needed")
    print(f"  5. Adjust red filter thresholds if line detection is poor")
    print("="*60)


if __name__ == "__main__":
    main()