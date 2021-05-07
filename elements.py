# Description
'''
Geometric Shapes, Points and Vectors
'''

# Imports
import math, numpy

__author__ = 'Jan Ningelgen'

# -----  Point -> (Vector -> (Color))  ----------------------------------------------------------------- #

class Point():
    ''' 3D Point wrapping NumPy operations '''
    def __init__(self,*args):
        # constructing Point with numpy Array
        if(len(args)==1 and hasattr(args[0], '__len__') and len(args[0])==3):
            self.values=args[0]
        # constructing Point with 3 values
        elif(len(args)==3):
            self.values=numpy.array([args[0],args[1],args[2]])
        else:
            print(args)
            print("unvalid number of arguments")
    
    def __repr__(self):
        return '%s(%s, %s, %s)' %(self.__class__.__name__, self.values[0], self.values[1], self.values[2])
    
    def __add__(self, other):
        return Point(numpy.add(self.values, other.values))
    
    def __sub__(self, other):
        temp = Vector(numpy.subtract(self.values, other.values))
        if temp.length() == 0:
            print('Länge 0: v1 ', self, ' v2 ', other)
        return Vector(numpy.subtract(self.values, other.values))

    def __getitem__(self, i):
        return self.values[i]


class Vector(Point):
    ''' 3D Vector '''
    def __init__(self, *args):
        super(Vector, self).__init__(*args)
    
    def __add__(self, other):
        return Vector(numpy.add(self.values, other.values))

    def length(self):
        return numpy.linalg.norm(self.values)

    def scaled(self, t):
        return Vector(numpy.multiply(self.values, t))
    
    def normalized(self):
        if self.length != 0:
            return self.scaled(1/(numpy.linalg.norm(self.values)))
        else:
            print('Error, vektor 0 lang')

    def dot(self, other):
        return numpy.dot(self.values, other.values)

    def cross(self, other):
        return Vector(numpy.cross(self.values, other.values))

    def reflect_on(self, normal):
        normal = normal.normalized()
        return self - normal.scaled(normal.dot(self)*2)


class Color(Vector):
    ''' Specialized 3D Vector only containing numbers betweeen 0.0 and 255.0 '''
    def __init__(self, *args):
        super(Vector, self).__init__(*args)

    def __add__(self, other):
        return Color(numpy.clip(numpy.add(self.values, other.values), a_min=0, a_max=255))
    
    def __sub__(self, other):
        return Color(numpy.subtract(self.values, other.values))

    def scaled(self, t):
        return Color(numpy.multiply(self.values, t))


# -----  Texture -> (Checkerboard)  -------------------------------------------------------------------- #

class Texture():
    ''' Handling Material and Object-Color-Computing '''
    def __init__(self, primary, material):
        self.primary=primary                                                # Color
        self.set_material(material)

    def set_material(self, material):
        self.ambient_factor     = material.ambient_factor                   # float   > 0
        self.diffuse_factor     = material.diffuse_factor                   # float   > 0
        self.specular_factor    = material.specular_factor                  # float   > 0   diffuse + specular <= 1
        self.reflection_factor  = material.reflection_factor                # float   > 0
        self.shininess_exponent = material.shininess_exponent               # float   > 1 

    def colorAt(self, p):
        return self.primary


class Checkerboard(Texture):
    ''' typical Checkerboard Texture '''
    def __init__(self, primary, secondary, material, size=5.0):
        super(Checkerboard, self).__init__(primary, material)
        self.secondary = secondary              # Color
        self.size = size
    
    def colorAt(self, p):
        v = Vector(p.values).scaled(1.0/self.size)
        if (int(abs(v[0]) + 0.5) + int(abs(v[1]) + 0.5) + int(abs(v[2]) + 0.5))%2:
            return self.primary
        else:
            return self.secondary


# -----  Material  ------------------------------------------------------------------------------------- #

class Material():
    ''' Handling color factors '''
    def __init__(self, ambient_factor, diffuse_factor, specular_factor, reflection_factor, shininess_exponent):
        self.ambient_factor = ambient_factor                    # float   > 0
        self.diffuse_factor = diffuse_factor                    # float   > 0
        self.specular_factor = specular_factor                  # float   > 0   diffuse + specular <= 1
        self.reflection_factor = reflection_factor              # float   > 0
        self.shininess_exponent = max(shininess_exponent, 1.0)  # float   > 1   


# -----  Barrier -> (Sphere, Plane, Triangle)  --------------------------------------------------------- #

class Barrier():
    ''' Super Class for each Barrier handling Texture and Material '''
    def __init__(self, texture):
        self.texture = texture
    
    def intersectionParamenter(self, ray):
        return None
    
    def colorAt(self, p):
        return self.texture.colorAt(p)
    
    def get_ambient_factor(self):
        return self.texture.ambient_factor

    def get_diffuse_factor(self):
        return self.texture.diffuse_factor
    
    def get_specular_factor(self):
        return self.texture.specular_factor

    def get_shininess_exponent(self):
        return self.texture.shininess_exponent

    def get_reflection_factor(self):
        return self.texture.reflection_factor


class Sphere(Barrier):
    ''' Sphere Barrier (center of Class Point) '''
    def __init__(self, center, radius, texture):
        super(Sphere, self).__init__(texture)
        self.center = center                    # Point
        self.radius = radius                    # int

    def __repr__(self):
        return 'Sphere(%s, %s)' %(repr(self.center), str(self.radius))

    def intersectionParameter(self, ray):
        co = self.center - ray.origin
        v = co.dot(ray.direction)
        discriminant = v**2 - co.dot(co) + self.radius**2
        if discriminant < 0:
            return None
        else:
            return v - math.sqrt(discriminant)
    
    def normalAt(self, p):
        return (p - self.center).normalized()


class Plane(Barrier):
    ''' Plane Barrier (point on plane of Class Point, normal of Class Vector) '''
    def __init__(self, point, normal, texture):
        super(Plane, self).__init__(texture)
        self.point = point                      # Point
        self.normal = normal.normalized()       # Vector
    
    def __repr__(self):
        return 'Plane(%s, %s)' %(repr(self.point), repr(self.normal))

    def intersectionParameter(self, ray):
        op = ray.origin - self.point
        a = op.dot(self.normal)
        b = ray.direction.dot(self.normal)
        if b:
            return -a/b
        else:
            return None
    
    def normalAt(self, p):
        return self.normal


class Triangle(Barrier):
    ''' Triangle Barrier (corner Points a,b,c of Class Point) '''
    def __init__(self, a, b, c, texture=Texture(Color(80, 80, 80), Material(1.0, 0.5, 0.5, 0.5, 5.0))):
        super(Triangle, self).__init__(texture)
        self.a = a                              # Point
        self.b = b                              # Point
        self.c = c                              # Point
        self.u = self.b - self.a                # Vector
        self.v = self.c - self.a                # Vector
    
    def __repr__(self):
        return 'Triangle(%s, %s, %s)' %(repr(self.a), repr(self.b), repr(self.c))

    def intersectionParameter(self, ray):
        w = ray.origin - self.a
        dv = ray.direction.cross(self.v)
        dvu = dv.dot(self.u)
        if dvu == 0.0:
            return None
        wu = w.cross(self.u)
        r = dv.dot(w) / dvu
        s = wu.dot(ray.direction) / dvu
        if 0 <= 0 <= r <= 1 and 0 <= s <= 1 and r + s <= 1:
            return wu.dot(self.v) / dvu
        else:
            return None

    def normalAt(self, p):
        return self.u.cross(self.v).normalized()

def build_triangular_network(path):
    ''' Creating Vertices (Point(v x y z)) and Faces /Triangle(f v1_ord v2_ord v3_ord)) out of lines '''
    vertices = ['cheat']
    faces = []
    with open(path) as data:
        for line in data.readlines():
            temp = line.split()
            if temp[0] == 'v':
                vertices.append(Point(float(temp[1]), float(temp[2]), float(temp[3])))
            elif temp[0] == 'f':
                faces.append(Triangle(vertices[int(temp[1])], vertices[int(temp[2])], vertices[int(temp[3])]))
    return faces


# -----  Light  ---------------------------------------------------------------------------------------- #

class Light():
    ''' Light for Scene '''
    def __init__(self, origin=Point(0,0,0), color=Color(255,255,255)):
        self.origin = origin                    # Point
        self.color = color                      # Color
    
    def __repr__(self):
        return 'Shiny little thing called light'

# Constants
#DEFAULT_MATERIAL = Material(1.0, 0.5, 0.5, 0.5, 5.0)
#DEFAULT_TEXTURE  = Texture(Color(80, 80, 80), DEFAULT_MATERIAL)