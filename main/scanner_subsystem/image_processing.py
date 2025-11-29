# 3D scanner software - Image processing

from transform import four_point_transform
import cv2
import numpy as np
from time import sleep
from geometry import Vertex
import subprocess
from scipy import ndimage


class ImageProcessor:
    """Handles camera capture and image processing"""
    def __init__(self):
        self.tlp = (521.0, 344.0)
        self.trp = (1205.0, 310.0)
        self.brp = (1205.0, 771.0)
        self.blp = (521.0, 815.0)
        self.center_column = 352.0
        self.height_mm_per_pixel = 0.119069
        self.radial_mm_per_pixel = 0.157199
    
    def capture_image(self, filename='lineDetection.jpg'):
        """Capture an image using libcamera-still"""
        cmd = ["libcamera-still", "-o", filename, "--timeout", "1000",
               "--autofocus-mode", "manual", "--lens-position", "7.0"]
        subprocess.run(cmd, check=True)
        
        temp_img = cv2.imread(filename)
        img = cv2.resize(temp_img, (1663, 918))
        return img

    def process_image(self, img, save_intermediate=False):
        """Process image to extract line coordinates"""
        # Keep a copy of original for visualization
        original_img = img.copy() if save_intermediate else None
        
        # Apply perspective transform
        pts = np.array([self.tlp, self.trp, self.brp, self.blp])
        img = four_point_transform(img, pts)
        if save_intermediate:
            cv2.imwrite('intermediate_1_trans.jpg', img)
        
        # Extract red channel for additional filtering
        red_channel = img[:, :, 2]
        _, red_line = cv2.threshold(red_channel, 170, 255, cv2.THRESH_BINARY)
        
        if save_intermediate:
            cv2.imwrite('intermediate_3_red_only.jpg', red_line)
        
        # Extract all detected columns first (for continuity check)
        h, w = red_line.shape
        detected_cols = []
        
        for r in range(h):
            c_index = np.argmax(red_line[r, :])
            if red_line[r, c_index] != 0:
                detected_cols.append(c_index)
            else:
                detected_cols.append(-1)
                
        REMOVE_BOTTOM_ROWS = 15  # Adjust this value
        for r in range(max(0, h - REMOVE_BOTTOM_ROWS), h):
            detected_cols[r] = -1
        print(f"Removed bottom {REMOVE_BOTTOM_ROWS} rows (table reflections)")

        # Find bottom_row: Use the LOWEST detected point across ALL segments
        # This handles objects with multiple radii that create separate line segments
        
        # Strategy 1: Find ALL continuous sequences
        sequences = []
        current_sequence_start = -1
        
        for r in range(h):
            if detected_cols[r] != -1:
                if current_sequence_start == -1:
                    current_sequence_start = r
            else:
                if current_sequence_start != -1:
                    sequences.append((current_sequence_start, r - 1))
                    current_sequence_start = -1
        
        # Don't forget final sequence
        if current_sequence_start != -1:
            sequences.append((current_sequence_start, h - 1))
        
        print(f"Found {len(sequences)} line segment(s):")
        for i, (start, end) in enumerate(sequences):
            print(f"  Segment {i+1}: rows {start} to {end} (length: {end - start + 1})")
        
        # Strategy 2: Filter out noise (segments shorter than threshold)
        MIN_SEGMENT_LENGTH = 10  # Segments must be at least this many rows
        valid_segments = [(start, end) for start, end in sequences 
                          if (end - start + 1) >= MIN_SEGMENT_LENGTH]
        
        if len(valid_segments) < len(sequences):
            filtered_count = len(sequences) - len(valid_segments)
            print(f"  Filtered out {filtered_count} short segment(s) (likely noise)")
        
        # Strategy 3: Find the LOWEST point among all valid segments
        bottom_row = 0
        if valid_segments:
            # Get the maximum 'end' value (lowest row number)
            bottom_row = max(end for start, end in valid_segments)
            print(f"Bottom row: {bottom_row} (lowest point across all segments)")
        else:
            # Fallback: just use last detected point
            for r in range(h - 1, -1, -1):  # Search from bottom up
                if detected_cols[r] != -1:
                    bottom_row = r
                    break
            print(f"Bottom row: {bottom_row} (fallback: last detected point)")
        
#         # Strategy 4: Straighten each valid segment by averaging
#         print("\nStraightening segments:")
#         for i, (start, end) in enumerate(valid_segments):
#             # Calculate average column for this segment
#             segment_cols = [detected_cols[r] for r in range(start, end + 1) 
#                             if detected_cols[r] != -1]
#             
#             if segment_cols:  # Make sure we have valid data
#                 avg_col = np.mean(segment_cols)
#                 print(f"  Segment {i+1} (rows {start}-{end}): avg column = {avg_col:.1f}")
#                 
#                 # Set all rows in this segment to the average
#                 for r in range(start, end + 1):
#                     if detected_cols[r] != -1:
#                         detected_cols[r] = int(round(avg_col))
        
        # Fill gaps between segments
        print("\nFilling gaps between segments:")
        for i in range(len(valid_segments) - 1):
            _, current_end = valid_segments[i]
            next_start, _ = valid_segments[i + 1]
            
            if next_start == current_end + 1:
                col_current = detected_cols[current_end]
                col_next = detected_cols[next_start]
                
                if col_current != -1 and col_next != -1:
                    min_col = int(min(col_current, col_next))
                    max_col = int(max(col_current, col_next))
                    print(f"  Filling row {next_start}: columns {min_col} to {max_col}")

        
        # Apply Gaussian smoothing to detected columns
        #smoothed_cols = self.gaussian_smooth_line(detected_cols, valid_segments, sigma=3.0)
        smoothed_cols = detected_cols
        
        # Create backG with smoothed line AND horizontal connectors
        backG = np.zeros((h, w))

        # First pass: draw detected points
        for r in range(h):
            if smoothed_cols[r] != -1:
                backG[r, int(smoothed_cols[r])] = 1

        # Second pass: draw horizontal connectors between segments
        for i in range(len(valid_segments) - 1):
            _, current_end = valid_segments[i]
            next_start, _ = valid_segments[i + 1]
            
            if next_start == current_end + 1:
                col_current = smoothed_cols[current_end]
                col_next = smoothed_cols[next_start]
                
                if col_current != -1 and col_next != -1:
                    min_col = int(min(col_current, col_next))
                    max_col = int(max(col_current, col_next))
                    backG[next_start, min_col:max_col+1] = 1
        
        if save_intermediate:
            cv2.imwrite('intermediate_5_smoothed_line.jpg', backG * 255)
            
            # Create visualization showing detected line with reference lines
            print("\nCreating visualization...")
            vis_img = four_point_transform(original_img, pts)
            
            # Draw the detected points on the visualization (green dots)
            for r, c_index in enumerate(np.argmax(backG, axis=1)):
                if backG[r, c_index] == 1:
                    cv2.circle(vis_img, (int(c_index), int(r)), 2, (0, 255, 0), -1)
            
            # Draw center line (blue)
            cv2.line(vis_img, 
                    (int(self.center_column), 0), 
                    (int(self.center_column), h), 
                    (255, 0, 0), 2)
            
            # Draw bottom row line (red)
            cv2.line(vis_img, (0, bottom_row), (w, bottom_row), (0, 0, 255), 2)
            
            cv2.imwrite('test_visualization.jpg', vis_img)
            print(f"✓ Visualization saved to: test_visualization.jpg")
            print(f"  Green dots: detected line points")
            print(f"  Blue line: center column reference")
            print(f"  Red line: bottom row reference")
            
        return backG, bottom_row

    def gaussian_smooth_line(self, detected_cols, valid_segments, sigma=2.0):
        """
        Apply Gaussian smoothing to the detected line coordinates.
        
        Args:
            detected_cols: List of detected column positions (-1 for no detection)
            valid_segments: List of (start, end) tuples for continuous line segments
            sigma: Standard deviation for Gaussian kernel (controls smoothing strength)
        
        Returns:
            List of smoothed column positions
        """
        h = len(detected_cols)
        smoothed_cols = [-1] * h
        
        # Process each valid segment separately to avoid smoothing across gaps
        for start_row, end_row in valid_segments:
            segment_length = end_row - start_row + 1
            
            # Extract the segment data (only valid detections)
            segment_cols = []
            segment_rows = []
            
            for r in range(start_row, end_row + 1):
                if detected_cols[r] != -1:
                    segment_cols.append(detected_cols[r])
                    segment_rows.append(r)
            
            if len(segment_cols) < 3:
                # Too few points for meaningful smoothing, just copy original
                for r in range(start_row, end_row + 1):
                    smoothed_cols[r] = detected_cols[r]
                continue
            
            # Convert to numpy arrays for easier processing
            segment_cols = np.array(segment_cols, dtype=float)
            segment_rows = np.array(segment_rows)
            
            # Apply Gaussian filter to the column positions
            # Use sigma to control smoothing strength (larger = more smoothing)
            smoothed_segment = ndimage.gaussian_filter1d(segment_cols, sigma=sigma)
            
            # Map the smoothed values back to the original row positions
            for i, row in enumerate(segment_rows):
                smoothed_cols[row] = int(round(smoothed_segment[i]))
            
            # Fill in any gaps within the segment using interpolation
            for r in range(start_row, end_row + 1):
                if detected_cols[r] == -1 and smoothed_cols[r] == -1:
                    # Find nearest smoothed values for interpolation
                    prev_valid = None
                    next_valid = None
                    
                    # Look backwards for previous valid point
                    for prev_r in range(r - 1, start_row - 1, -1):
                        if smoothed_cols[prev_r] != -1:
                            prev_valid = (prev_r, smoothed_cols[prev_r])
                            break
                    
                    # Look forwards for next valid point
                    for next_r in range(r + 1, end_row + 1):
                        if smoothed_cols[next_r] != -1:
                            next_valid = (next_r, smoothed_cols[next_r])
                            break
                    
                    # Interpolate if we have both neighbors
                    if prev_valid and next_valid:
                        prev_row, prev_col = prev_valid
                        next_row, next_col = next_valid
                        
                        # Linear interpolation
                        alpha = (r - prev_row) / (next_row - prev_row)
                        interpolated_col = prev_col + alpha * (next_col - prev_col)
                        smoothed_cols[r] = int(round(interpolated_col))
        
        print(f"Applied Gaussian smoothing with sigma={sigma}")
        return smoothed_cols

    def extract_coordinates(self, processed_img, bottom_row, theta):
        """Extract cylindrical coordinates in MILLIMETERS"""
        coords = []
        for r, c_index in enumerate(np.argmax(processed_img, axis=1)):
            if processed_img[r, c_index] == 1:
                if r > bottom_row:
                    continue
                
                # Convert pixels to millimeters
                height_px = bottom_row - r
                dist_px = c_index - self.center_column
                print(f"HEIGHT_PX {height_px}")
                height_mm = height_px * self.height_mm_per_pixel
                dist_mm = dist_px * self.radial_mm_per_pixel
                
                coords.append(Vertex(height_mm, np.radians(theta), dist_mm))
                #coords.append(Vertex(height_px, np.radians(theta), dist_px))
        
        print(f"Extracted {len(coords)} coordinates in mm")
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