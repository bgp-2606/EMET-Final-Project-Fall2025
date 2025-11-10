# 3D scanner software - Geometry classes

class Vertex:
    """Represents a 3D vertex point"""
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def write(self):
        return f"v {self.x} {self.y} {self.z}"


class Face:
    """Represents a triangular face in 3D mesh"""
    def __init__(self, v1, v2, v3):
        self.v1 = v1
        self.v2 = v2
        self.v3 = v3

    def write(self):
        return f"f {self.v1} {self.v2} {self.v3}"