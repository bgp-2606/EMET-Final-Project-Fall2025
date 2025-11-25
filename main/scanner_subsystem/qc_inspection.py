import trimesh
import numpy as np

def compare_obj_files(reference_obj, scanned_obj, tolerance_mm=0.5):
    """
    Compare scanned part against reference CAD model
    """
    # Load meshes
    ref_mesh = trimesh.load(reference_obj)
    scan_mesh = trimesh.load(scanned_obj)
    
    # CRITICAL: Ensure unit consistency
    # If SolidWorks exports in mm and scanner outputs in different units
    # scan_mesh.apply_scale(1000)  # Example: meters to mm
    
    # Check if units are wrong
    print(f"Reference volume: {ref_mesh.volume:.2f}")
    print(f"Scanned volume: {scan_mesh.volume:.2f}")

    # Align meshes using ICP registration
    print("Aligning meshes...")
    matrix, transformed, cost = trimesh.registration.mesh_other(
        scan_mesh, ref_mesh, samples=1000
    )
    
    # Compute closest point distances from scanned to reference
    print("Computing deviations...")
    distances, closest_points, triangle_id = trimesh.proximity.closest_point(
        ref_mesh, transformed.vertices
    )
    
    # Statistics
    max_dev = np.max(distances)
    mean_dev = np.mean(distances)
    rms_dev = np.sqrt(np.mean(distances**2))
    percentile_95 = np.percentile(distances, 95)
    
    # Tolerance check
    points_within_tol = np.sum(distances <= tolerance_mm)
    pass_rate = (points_within_tol / len(distances)) * 100
    
    results = {
        'max_deviation': max_dev,
        'mean_deviation': mean_dev,
        'rms_deviation': rms_dev,
        '95th_percentile': percentile_95,
        'pass_rate': pass_rate,
        'passes_inspection': max_dev <= tolerance_mm,
        'total_points': len(distances)
    }
    
    return results, distances, transformed

# Use it
results, distances, aligned_mesh = compare_obj_files(
    'test_part.obj', 
    '3d.obj', 
    tolerance_mm=0.5
)

print(f"\n=== Inspection Results ===")
print(f"Max Deviation: {results['max_deviation']:.3f} mm")
print(f"Mean Deviation: {results['mean_deviation']:.3f} mm")
print(f"RMS Deviation: {results['rms_deviation']:.3f} mm")
print(f"95th Percentile: {results['95th_percentile']:.3f} mm")
print(f"Pass Rate: {results['pass_rate']:.1f}%")
print(f"PASS: {results['passes_inspection']}")