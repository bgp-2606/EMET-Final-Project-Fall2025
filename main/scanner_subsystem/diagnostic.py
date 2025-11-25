import trimesh
import numpy as np

def compare_dimensions(reference_obj, scanned_obj):
    """Compare external dimensions only (not volume)"""
    ref = trimesh.load(reference_obj)
    scan = trimesh.load(scanned_obj)
    
    print("=== EXTERNAL DIMENSIONS ===")
    ref_dims = ref.bounds[1] - ref.bounds[0]
    scan_dims = scan.bounds[1] - scan.bounds[0]
    
    print(f"Reference: X={ref_dims[0]:.2f}, Y={ref_dims[1]:.2f}, Z={ref_dims[2]:.2f} mm")
    print(f"Scanned:   X={scan_dims[0]:.2f}, Y={scan_dims[1]:.2f}, Z={scan_dims[2]:.2f} mm")
    
    # Calculate errors
    error = np.abs(ref_dims - scan_dims)
    print(f"Error:     X={error[0]:.2f}, Y={error[1]:.2f}, Z={error[2]:.2f} mm")
    
    # Calculate percentage errors
    pct_error = (error / ref_dims) * 100
    print(f"Error %:   X={pct_error[0]:.1f}%, Y={pct_error[1]:.1f}%, Z={pct_error[2]:.1f}%")
    
    # Calculate scale correction needed
    scale_corrections = ref_dims / scan_dims
    print(f"\nScale corrections needed:")
    print(f"X: {scale_corrections[0]:.4f}")
    print(f"Y: {scale_corrections[1]:.4f}")
    print(f"Z: {scale_corrections[2]:.4f}")
    
    avg_correction = np.mean(scale_corrections)
    print(f"Average: {avg_correction:.4f}")
    
    # Calculate new mm_per_pixel value
    current_mm_per_pixel = 30.5 / 265
    new_mm_per_pixel = current_mm_per_pixel * avg_correction
    
    print(f"\n=== CALIBRATION UPDATE ===")
    print(f"Current mm_per_pixel: {current_mm_per_pixel:.6f}")
    print(f"New mm_per_pixel:     {new_mm_per_pixel:.6f}")
    print(f"\nUpdate in image_processing.py:")
    print(f"self.mm_per_pixel = {new_mm_per_pixel:.6f}")
    
    return new_mm_per_pixel

# Run it
new_value = compare_dimensions('test_part.obj', '3d.obj')