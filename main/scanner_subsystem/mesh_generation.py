# 3D scanner software - Mesh generation

import math
from geometry import Vertex, Face


class MeshGenerator:
    """Generates 3D mesh from scan data"""
    
    def __init__(self):
        # Calibrated scale factors (mm per pixel)
        # Based on transformed image: 445x330 pixels = 2.75x2.4373 inches
        self.HEIGHT_SCALE = 0.188 # mm per pixel (vertical)
        self.RADIAL_SCALE = 0.157 # mm per pixel (horizontal)
        
    def cylindrical_to_cartesian(self, coord):
        """Convert cylindrical coordinates to cartesian"""
        height = coord.x * self.HEIGHT_SCALE
        theta = coord.y
        dist = coord.z * self.RADIAL_SCALE
        x = dist * math.cos(theta)
        y = dist * math.sin(theta)
        z = height
        return Vertex(int(x), int(y), int(z))

    @staticmethod
    def normalize_mesh_points(mesh_points):
        """Ensure all rows have same length by trimming to shortest"""
        if not mesh_points:
            return mesh_points
        
        shortest = min(len(line) for line in mesh_points)
        for line in mesh_points:
            while len(line) > shortest:
                line.pop(-2)
        return mesh_points

    def generate_mesh(self, mesh_points):
        """Generate vertices and faces from mesh points"""
        points = []
        faces = []

        # Generate first row
        first_row = []
        for i, coord in enumerate(mesh_points[0]):
            points.append(self.cylindrical_to_cartesian(coord))
            first_row.append(i + 1)

        prev_row = first_row

        # Generate remaining rows and faces
        for col_idx, column in enumerate(mesh_points):
            if col_idx == 0:
                continue

            index_start = prev_row[-1]
            current_row = []

            for point_idx in range(len(column) - 1):
                tl = index_start + point_idx + 1
                bl = tl + 1
                tr = prev_row[point_idx]
                br = prev_row[point_idx + 1]

                faces.append(Face(tl, tr, bl))
                faces.append(Face(bl, tr, br))

                points.append(self.cylindrical_to_cartesian(column[point_idx]))
                current_row.append(tl)

                if point_idx == len(column) - 2:
                    points.append(self.cylindrical_to_cartesian(column[point_idx + 1]))
                    current_row.append(bl)

                # Close the mesh on last column
                if col_idx == len(mesh_points) - 1:
                    tl_close = first_row[point_idx]
                    bl_close = first_row[point_idx + 1]
                    faces.append(Face(tl_close, tl, bl_close))
                    faces.append(Face(bl_close, tl, bl))

            prev_row = current_row

        return points, faces


class OBJFileWriter:
    """Writes 3D mesh data to OBJ file"""
    @staticmethod
    def write(filename, points, faces):
        """Write vertices and faces to OBJ file"""
        with open(filename, 'w') as f:
            for point in points:
                f.write(point.write() + "\n")
            for face in faces:
                f.write(face.write() + "\n")