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
        self.tlp = (521.0, 250.0)
        self.trp = (1205.0, 195.0)
        self.brp = (1205.0, 790.0)
        self.blp = (521.0, 845.0)
        self.center_column = 352.0
    
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

        # NEW: Dynamically detect where object ends and turntable begins
        print("\n" + "="*60)
        print("TURNTABLE BOUNDARY DETECTION")
        print("="*60)
        debug_info = {}
        object_boundary = self.detect_turntable_by_direction_change(detected_cols, debug_info)
        print("="*60 + "\n")
        
        # Filter out everything below the boundary (turntable reflection)
        print(f"Filtering out rows {object_boundary + 1} to {h - 1} (turntable reflection)")
        for r in range(object_boundary + 1, h):
            detected_cols[r] = -1

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
        
        # Apply Gaussian smoothing to detected columns
        smoothed_cols = self.gaussian_smooth_line(detected_cols, valid_segments, sigma=5.0)
        
        # Create backG with smoothed line
        backG = np.zeros((h, w))
        for r in range(h):
            if smoothed_cols[r] != -1:
                backG[r, smoothed_cols[r]] = 1
        
        if save_intermediate:
            cv2.imwrite('intermediate_5_smoothed_line.jpg', backG * 255)
            
        return backG, bottom_row


    def detect_turntable_by_direction_change(self, detected_cols, debug_info=None):
        """
        Detect turntable by finding sudden changes in line direction.
        When laser goes from object to turntable, the angle changes abruptly.
        """
        h = len(detected_cols)
        window_size = 20  # Adjust this: larger = smoother but less sensitive
        angle_change_threshold = 65.0  # degrees, adjust based on testing
        
        if debug_info is not None:
            debug_info['angles'] = []
            debug_info['angle_diffs'] = []
        
        # Calculate local line angles using linear regression in sliding windows
        for r in range(h - window_size * 2, window_size, -5):  # Scan from bottom up
            # Get two consecutive windows
            window1_points = []
            window2_points = []
            
            for i in range(r - window_size, r):
                if 0 <= i < h and detected_cols[i] != -1:
                    window1_points.append((i, detected_cols[i]))
            
            for i in range(r, r + window_size):
                if 0 <= i < h and detected_cols[i] != -1:
                    window2_points.append((i, detected_cols[i]))
            
            # Need enough points in both windows
            if len(window1_points) < 10 or len(window2_points) < 10:
                continue
            
            # Fit lines to both windows
            y1, x1 = zip(*window1_points)
            y2, x2 = zip(*window2_points)
            
            # Calculate slopes using least squares
            slope1 = np.polyfit(y1, x1, 1)[0] if len(y1) > 1 else 0
            slope2 = np.polyfit(y2, x2, 1)[0] if len(y2) > 1 else 0
            
            # Convert slopes to angles
            angle1 = np.degrees(np.arctan(slope1))
            angle2 = np.degrees(np.arctan(slope2))
            
            if debug_info is not None:
                debug_info['angles'].append((r, angle1, angle2))
            
            # Check for significant angle change
            angle_diff = abs(angle2 - angle1)
            
            if debug_info is not None:
                debug_info['angle_diffs'].append((r, angle_diff))
            
            if angle_diff > angle_change_threshold:
                print(f"  Direction change detected at row {r}")
                print(f"    Angle before: {angle1:.1f}°, after: {angle2:.1f}°, diff: {angle_diff:.1f}°")
                if debug_info is not None:
                    debug_info['boundary_row'] = r
                    debug_info['boundary_reason'] = 'direction_change'
                return r
        
        # Fallback: return last detected point
        for r in range(h - 1, -1, -1):
            if detected_cols[r] != -1:
                if debug_info is not None:
                    debug_info['boundary_row'] = r
                    debug_info['boundary_reason'] = 'fallback_last_point'
                return r
        
        if debug_info is not None:
            debug_info['boundary_row'] = h - 1
            debug_info['boundary_reason'] = 'fallback_end'
        return h - 1

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
        """Extract cylindrical coordinates from processed image"""
        print(f"bottom row: {bottom_row}")
        coords = []
        for r, c_index in enumerate(np.argmax(processed_img, axis=1)):
            if processed_img[r, c_index] == 1:
                # CRITICAL: Ignore any points below bottom_row (noise)
                if r > bottom_row:
                    continue  # Skip this row - it's noise below the object
                
                height = bottom_row - r
                dist = c_index - self.center_column
                coords.append(Vertex(height, np.radians(theta), dist))
        
        print(f"Extracted {len(coords)} coordinates (noise below row {bottom_row} filtered)")
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
