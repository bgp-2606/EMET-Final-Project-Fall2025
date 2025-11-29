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
            overall_sizing = 'UNDERSIZE'
        elif all(res == 'OVERSIZE' for res in sizing):
            overall_sizing = 'OVERSIZE'
        elif all(res == 'OK' for res in sizing):
            overall_sizing = 'OK'

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
    
    def _print_report(self, results):
        """Print inspection report"""
        r = results['reference']
        s = results['scanned']
        d = results['differences']
        e = results['errors']
        sz = results['sizing']
        
        print("\n" + "="*60)
        print("QC INSPECTION REPORT")
        print("="*60)
        print(f"Reference: X={r['x']:6.2f}mm  Y={r['y']:6.2f}mm  Z={r['z']:6.2f}mm")
        print(f"Scanned:   X={s['x']:6.2f}mm  Y={s['y']:6.2f}mm  Z={s['z']:6.2f}mm")
        print(f"Diff:      X={d['x']:+6.2f}mm  Y={d['y']:+6.2f}mm  Z={d['z']:+6.2f}mm")
        print(f"Sizing:    X={sz['x']:>9}  Y={sz['y']:>9}  Z={sz['z']:>9}")
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