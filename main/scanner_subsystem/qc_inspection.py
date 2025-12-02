import trimesh
import numpy as np

class QCInspector:
    """Simple dimensional quality control for 3D scanned parts"""
    
    def __init__(self, tolerance_mm=1.00):
        """
        Args:
            tolerance_mm: Maximum acceptable dimensional error in mm
        """
        self.tolerance_mm = tolerance_mm
    def inspect(self, reference_obj, scanned_obj):
        """
        Check if scanned part dimensions match reference within tolerance
        
        For cylindrical parts: X,Z = diameter, Y = height
        """
        # Load meshes
        ref = trimesh.load(reference_obj)
        scan = trimesh.load(scanned_obj)
        
        # Fix reference Y/Z swap (scanner outputs X,Z=diameter, Y=height)
        ref.vertices = ref.vertices[:, [0, 2, 1]]  # Swap Y and Z
        
        # Print detailed dimensions
        self.display_mesh_dimensions(ref,scan)
        
        # Get dimensions
        ref_dims = ref.bounds[1] - ref.bounds[0]
        scan_dims = scan.bounds[1] - scan.bounds[0]
        
        # FOR CYLINDRICAL PARTS: Use average of X and Z for diameter
        ref_diameter = (ref_dims[0] + ref_dims[1]) / 2
        scan_diameter = (scan_dims[0] + scan_dims[1]) / 2
        ref_height = ref_dims[2]
        scan_height = scan_dims[2]
        
        # Calculate differences for diameter and height only
        diameter_diff = scan_diameter - ref_diameter
        height_diff = scan_height - ref_height
        
        differences = np.array([diameter_diff, height_diff])
        errors = np.abs(differences)
        
        # Determine sizing
        sizing = []
        for diff in differences:
            if abs(diff) <= self.tolerance_mm:
                sizing.append('OK')
            elif diff > 0:
                sizing.append('OVERSIZE')
            else:
                sizing.append('UNDERSIZE')
                
        if 'UNDERSIZE' in sizing:
            overall_sizing = 'UNDERSIZE'  # Priority 1: Any undersize
        elif 'OVERSIZE' in sizing:
            overall_sizing = 'OVERSIZE'   # Priority 2: Any oversize (no undersize)
        else:
            overall_sizing = 'NOMINAL'    # Priority 3: All OK

        # Check tolerance
        passes = errors <= self.tolerance_mm
        
        # Build results
        results = {
            'reference': {'diameter': ref_diameter, 'height': ref_height},
            'scanned': {'diameter': scan_diameter, 'height': scan_height},
            'differences': {'diameter': differences[0], 'height': differences[1]},
            'errors': {'diameter': errors[0], 'height': errors[1]},
            'sizing': {'diameter': sizing[0], 'height': sizing[1]},
            'overall_sizing': overall_sizing,
            'max_error': np.max(errors),
            'passes': {'diameter': passes[0], 'height': passes[1]},
            'passes_overall': np.all(passes),
            'tolerance': self.tolerance_mm
        }
        
        #self._print_report(results)
        return results
    
    def get_cylinder_dimensions(self, mesh):
        """Extract diameter and height for cylindrical part"""
        extents = mesh.extents  # [x_size, y_size, z_size]

        # For overall dimensions, use bounding box
        diameter = (extents[0] + extents[1]) / 2
        height = extents[2]

        return diameter, height

    def display_mesh_dimensions(self, ref_mesh, scanned_mesh):
        """Display dimensional comparison between reference and scanned parts"""
        print("\n" + "="*50)
        print("DIMENSIONAL MEASUREMENTS")
        print("="*50)
        
        print("\n=== REFERENCE MESH ===")
        print(f"Bounding box extents (X, Y, Z): {ref_mesh.extents}")
        
        print("\n=== SCANNED MESH ===")
        print(f"Bounding box extents (X, Y, Z): {scanned_mesh.extents}")
        
        # Cylinder-specific measurements
        ref_diam, ref_height = self.get_cylinder_dimensions(ref_mesh)
        scan_diam, scan_height = self.get_cylinder_dimensions(scanned_mesh)
        
        print("\n=== CYLINDER MEASUREMENTS ===")
        print(f"Reference - Diameter: {ref_diam:.3f} mm, Height: {ref_height:.3f} mm")
        print(f"Scanned   - Diameter: {scan_diam:.3f} mm, Height: {scan_height:.3f} mm")
        print(f"\nDifference - Diameter: {scan_diam - ref_diam:+.3f} mm, Height: {scan_height - ref_height:+.3f} mm")
        print(f"Percent Error - Diameter: {100*(scan_diam - ref_diam)/ref_diam:+.2f}%, Height: {100*(scan_height - ref_height)/ref_height:+.2f}%")
        print("="*50 + "\n")
