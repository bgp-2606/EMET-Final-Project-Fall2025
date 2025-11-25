import trimesh
import numpy as np

ref = trimesh.load('test_part.obj')
scan = trimesh.load('3d.obj')

ref_dims = ref.bounds[1] - ref.bounds[0]
scan_dims = scan.bounds[1] - scan.bounds[0]
error = np.abs(ref_dims - scan_dims)

print(f"Reference: X={ref_dims[0]:.2f}, Y={ref_dims[1]:.2f}, Z={ref_dims[2]:.2f} mm")
print(f"Scanned:   X={scan_dims[0]:.2f}, Y={scan_dims[1]:.2f}, Z={scan_dims[2]:.2f} mm")
print(f"Error:     X={error[0]:.2f}, Y={error[1]:.2f}, Z={error[2]:.2f} mm")
print(f"Max error: {np.max(error):.2f} mm")