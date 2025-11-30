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
        
        # Get dimensions
        ref_dims = ref.bounds[1] - ref.bounds[0]
        scan_dims = scan.bounds[1] - scan.bounds[0]
        
        # FOR CYLINDRICAL PARTS: Use average of X and Z for diameter
        ref_diameter = (ref_dims[0] + ref_dims[2]) / 2
        scan_diameter = (scan_dims[0] + scan_dims[2]) / 2
        ref_height = ref_dims[1]
        scan_height = scan_dims[1]
        
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
    
    # ... rest of your code but using only 2 dimensions
    '''
    def inspect(self, reference_obj, scanned_obj):
        """
        Check if scanned part dimensions match reference within tolerance
        
        Args:
            reference_obj: Path to reference CAD model (.obj)
            scanned_obj: Path to scanned part (.obj)
            
        Returns:
            dict with dimensions, errors, and pass/fail results
        """
        # Load meshes
        ref = trimesh.load(reference_obj)
        scan = trimesh.load(scanned_obj)
        
        # Fix reference Y/Z swap (scanner outputs X,Z=diameter, Y=height)
        ref.vertices = ref.vertices[:, [0, 2, 1]]  # Swap Y and Z
        
        # Get dimensions
        ref_dims = ref.bounds[1] - ref.bounds[0]
        scan_dims = scan.bounds[1] - scan.bounds[0]
        
        # Calculate signed differences (positive = oversize, negative = undersize)
        differences = scan_dims - ref_dims
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
            'reference': {'x': ref_dims[0], 'y': ref_dims[1], 'z': ref_dims[2]},
            'scanned': {'x': scan_dims[0], 'y': scan_dims[1], 'z': scan_dims[2]},
            'differences': {'x': differences[0], 'y': differences[1], 'z': differences[2]},
            'errors': {'x': errors[0], 'y': errors[1], 'z': errors[2]},
            'sizing': {'x': sizing[0], 'y': sizing[1], 'z': sizing[2]},
            'overall_sizing': overall_sizing,
            'max_error': np.max(errors),
            'passes': {'x': passes[0], 'y': passes[1], 'z': passes[2]},
            'passes_overall': np.all(passes),
            'tolerance': self.tolerance_mm
        }
        
        self._print_report(results)
        return results
    '''
    def _print_report(self, results):
        """Print inspection report"""
        r = results['reference']
        s = results['scanned']
        d = results['differences']
        sz = results['sizing']
        
        print("\n" + "="*60)
        print("QC INSPECTION REPORT")
        print("="*60)
        print(f"Reference: Diameter={r['diameter']:6.2f}mm  Height={r['height']:6.2f}mm")
        print(f"Scanned:   Diameter={s['diameter']:6.2f}mm  Height={s['height']:6.2f}mm")
        print(f"Diff:      Diameter={d['diameter']:+6.2f}mm  Height={d['height']:+6.2f}mm")
        print(f"Sizing:    Diameter={sz['diameter']:>9}  Height={sz['height']:>9}")
        print("-"*60)
        print(f"Max Error:       {results['max_error']:.2f} mm")
        print(f"Tolerance:       {results['tolerance']:.2f} mm")
        print(f"Overall Sizing:  {results['overall_sizing']}")
        print(f"Result:          {'✓ PASS' if results['passes_overall'] else '✗ FAIL'}")
        print("="*60)

'''
# ============================================
# USAGE
# ============================================

if __name__ == "__main__":
    # Create inspector with 1mm tolerance
    inspector = QCInspector(tolerance_mm=1.0)
    
    # Run inspection
    results = inspector.inspect(
        reference_obj='test_part.obj',
        scanned_obj='3d.obj'
    )
    
    # Access results programmatically
    if results['passes_overall']:
        print(f"\n✓ Part accepted - {results['overall_sizing']}")
    else:
        print(f"\n✗ Part rejected - {results['overall_sizing']}")
        print(f"  Max error: {results['max_error']:.2f}mm")
        
        # Show which dimensions failed
        for axis in ['x', 'y', 'z']:
            if not results['passes'][axis]:
                print(f"  {axis.upper()}: {results['sizing'][axis]} by {results['errors'][axis]:.2f}mm")
'''