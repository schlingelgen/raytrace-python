# Description
'''
Its a Camera
'''

# Imports
import sys, numpy, math, time, random, threading
from multiprocessing import Process, Pool
import multiprocessing
from elements import *
from PIL import Image

# Constants
RECURSION_DEPTH = 1
PROCESSES_COUNT = multiprocessing.cpu_count()

__author__ = 'Jan Ningelgen'

# Keine Ahnung was genau dazu führt, aber das Eichhörchen lässt sich einfach nicht in annehmbarer Zeit rendern. (Mir ist bewusst dass es unfassbar viele Checks gibt)
# Dreiecke selbst funktionieren – die komplette Struktur jedoch konnte ich zeitlich nicht mehr mit Belichtung testen ...
# Und noch eine Frage: Bei genauerem Betrachten der Bilder (vor allem der nicht so hoch auflösenden) fällt so eine in regelmäßigen abständen, kreisförmig um die Kamera
# verlaufende 'Pixelanomalie' auf – woher kommt das? :(

# -----  Ray  ------------------------------------------------------------------------------------------ #

class Ray():
    ''' Ray '''
    def __init__(self, origin, direction):
        self.origin = origin                                                        # Point
        self.direction = direction.normalized()                                     # Vector
        length = numpy.linalg.norm(self.direction.values)
        if (length > 1.0001):
            print('VEKTOR NICHT NORMIERT: ', length)

    def __repr__(self):
        return 'Ray(%s, %s)' %(repr(self.origin), repr(self.direction))

    def pointAtParameter(self, t):
        return self.origin + self.direction.scaled(t)


# -----  Lense  ---------------------------------------------------------------------------------------- #

class Lense():
    ''' Lense '''
    def __init__(self, origin, center, up, fow):

        # default
        self.w = 256
        self.h = 256

        # Lense Params
        self.origin = origin                                                        # Point
        self.center = center                                                        # Point
        self.up = up                                                                # Vector

        # Lense Coord-System
        self.f = (self.center - self.origin).normalized()                           # Vector
        self.s = (self.f.cross(self.up)).normalized()                               # Vector
        self.u = (self.s.cross(self.f)).normalized()                                # Vector

        self.fow = fow                                                              # angle
        self.pixels = []
    
    def capture(self, scene, resolution, filename='default.png'):

        start_time = time.time()
        computing_progress = 0

        self.h = resolution['height']
        self.w = resolution['width']
        self.aspect_ratio = self.w / (self.h * 1.)
        self.scene = scene
        # sensor size
        self.sensor_height = 2*math.tan(self.fow/2.0)
        self.sensor_width = self.sensor_height * self.aspect_ratio
        # pixel size
        self.pixel_height = self.sensor_height / (self.h-1)
        self.pixel_width = self.sensor_width / (self.w-1)

        print('|-- Computing Pixel Colors')
        with multiprocessing.Pool(PROCESSES_COUNT) as pool:
            self.pixels = pool.map(self.compute_row, range(self.h))

        print('|-- Saving Image')
        self.save_image(filename)

        print('|-- Execution completed in %.2f seconds ' %(time.time() - start_time))
    
    def compute_row(self, y):
        ''' Computing a Pixel Row bases on y (height) param '''
        row = [self.trace(self.compute_ray(x,y)).values for x in range(self.w)]
        return row
    
    def compute_ray(self, x, y):
        ycomp = self.u.scaled((self.h-y)*self.pixel_height - self.sensor_height/2)
        xcomp = self.s.scaled(x*self.pixel_width - self.sensor_width/2)
        return Ray(self.origin, self.f + xcomp + ycomp)

    def trace(self, ray, depth=RECURSION_DEPTH):

        # reset for new Ray
        closest_d = math.inf
        closest_b = None

        # check intersection for each barrier
        for b in self.scene.barriers:
            dist = b.intersectionParameter(ray)
            # distance must be greater 0, update if smaller than current leastdist
            if dist and dist < closest_d and dist > 0:
                closest_d = dist
                closest_b = b
        
        # when intersection found, compute color
        if closest_b:
            intersection = ray.pointAtParameter(closest_d)
            if depth==0:
                return self.compute_light(closest_b, intersection, ray.direction)
            else:
                normal = closest_b.normalAt(intersection)
                reflected_ray = Ray(intersection, ray.direction.reflect_on(normal))
                return self.compute_light(closest_b, intersection, ray.direction) + self.trace(reflected_ray, depth-1).scaled(closest_b.get_reflection_factor())
        return Color(0,0,0)

    def compute_light(self, barrier, origin, dir):
        ''' Computes Color of Point(origin) on Barrier(barrier) with viewing direction Vector(dir) '''
        a  = self.ambient(barrier, origin)                                              # ambient lighting
        ds = self.diffuse_specular(barrier, origin, dir, self.scene.lights[0])          # diffuse and specular lighting
        return a + ds

    def ambient(self, barrier, origin):
        total_factor = barrier.get_ambient_factor() * self.scene.global_ambient_factor
        return barrier.colorAt(origin).scaled(total_factor)
    
    def diffuse_specular(self, barrier, origin, dir, source):
        ''' computes diffuse and specular light at >point< on >barrier< with >source< as light and >dir< as viewing point vector '''

        normal = barrier.normalAt(origin)
        bs  = (source.origin - origin).normalized()                                     # Vector (Point on barrier to lightsource)
        bsr = bs.scaled(-1).reflect_on(normal)                                          # Vector
        diffuse_cos  = bs.dot(normal)                                                   # float  (cos of angle between vectors)
        specular_cos = max(bsr.dot(dir.scaled(-1)),0)                                   # float  (cos of angle between vectors)
        light_ray = Ray(origin, bs)

        if diffuse_cos <= 0:
            return Color(0,0,0)                                                         # if angle > 90° -> shadow
        # else check every barrier
        else:
            for b in self.scene.barriers:

                dist = b.intersectionParameter(light_ray)
                if dist and dist > 0 and b != barrier:                                                   # if intersecting -> shadow [TODO: Not occuring, WHY?!]
                    return Color(0,0,0)

        # compute total factors based on texture and angle
        total_diffuse_factor  = barrier.get_diffuse_factor()*diffuse_cos
        total_specular_factor = barrier.get_specular_factor()*(specular_cos**barrier.get_shininess_exponent())

        # comute color based on factors
        diffuse_color  = source.color.scaled(total_diffuse_factor)
        specular_color = source.color.scaled(total_specular_factor)

        return diffuse_color + specular_color
    
    def set_scene(self, scene):
        self.scene = scene

    def save_image(self, filename):
        arr = numpy.array(self.pixels, dtype=numpy.uint8)
        img = Image.fromarray(arr, 'RGB')
        img.save(filename)
        self.pixels = []


# -----  Scene  ---------------------------------------------------------------------------------------- #

class Scene():
    ''' Handling Barriers, Lights and global light '''
    def __init__(self, barriers=[], lights=[], global_ambient_factor=0.7, ambient_light=Color(50,50,50)):
        self.BACKGROUND_COLOR = Color(0,0,0)
        self.barriers = []
        self.lights = []
        self.put_barriers(barriers)
        self.put_lights(lights)
        self.ambient_light=ambient_light
        self.global_ambient_factor = global_ambient_factor

    def put_barriers(self, barriers):
        for b in barriers:
            if isinstance(b, Barrier):
                self.barriers.append(b)
            else:
                print('%s is not a Barrier' %(repr(b)))
    
    def put_lights(self, lights):
        for l in lights:
            if isinstance(l, Light):
                self.lights.append(l)
        
    def show_barriers(self):
        for b in self.barriers:
            print(b)


# -----  Build  ---------------------------------------------------------------------------------------- #

def build_bounce_gif(lense, scene, sphere, plane):

    acceleration = Vector(0,-0.1,0)
    velocity     = Vector(-0.8, -1, -1)

    for x in range(71):
        velocity += acceleration
        sphere.center += velocity

        if(sphere.center[1]-sphere.radius < plane.point[1]):
            velocity.values[1] = velocity.values[1] * -1
            sphere.center.values[1] = plane.point.values[1] + sphere.radius
        
        lense.capture(sc, {'width': int(256*5), 'height': int(256*3)}, 'bouncing_gif2/bouncing%02d.png' %(x))
        # imageio for python gif generation

if __name__ == "__main__":

    # Computing 640 * 384 Pixel Image (Depth 3)
    # 1 Process 73 Seconds
    # 8 Processes 29 Seconds (Number of Cores)

    # TODO: Woher kommen die in Abständen, kreisförmig um die Linse auftretenden Pixelanomalien?

    # Materials
    shiny10 = Material(1.0, 0.1, 0.9, 0.8, 40.0)
    shiny05 = Material(1.0, 0.2, 0.7, 0.5, 5.0)

    # Textures
    plain_green  = Texture(Color(18, 148, 52), shiny10)
    plain_blue   = Texture(Color(18, 42, 148), shiny10)
    plain_red    = Texture(Color(201,52,14), shiny10)
    plain_yellow = Texture(Color(201, 195, 14), shiny10)
    plain_pink   = Texture(Color(219, 31, 172), shiny05)
    plain_grey   = Texture(Color(10, 10, 10), shiny10)
    check_black  = Checkerboard(Color(150,150,150), Color(0,0,0), shiny05, 8.0)

    # Barriers
    sphere0 = Sphere(Point(11,-2,-44),8, plain_grey)
    sphere1 = Sphere(Point(-5,-2,-31),8, plain_grey)
    sphere2 = Sphere(Point(15,10,-30), 10, plain_blue)
    sphere3 = Sphere(Point(17, 25, -6), 8, plain_grey)
    sphere4 = Sphere(Point(2.5,3,-10), 2, plain_red)
    sphere5 = Sphere(Point(-2.5,3,-10), 2, plain_green)
    sphere6 = Sphere(Point(0,7,-10), 2, plain_blue)
    plane  = Plane(Point(0,0,0), Vector(0,1,0), check_black)
    plane1 = Plane(Point(0,-10,0), Vector(0.5,0.75,0), plain_grey)
    triangle = Triangle(Point(2.5,3,-10), Point(-2.5,3,-10), Point(0,7,-10), plain_yellow)

    # Shiny Little Thing Called Light
    light0 = Light(Point(30, 30, 10), Color(20, 153, 255))
    light1 = Light(Point(30, 30, 10), Color(100, 200, 255))

    # Lense
    lense = Lense(Point(0,1.8,10), Point(0,3,0), Vector(0,1,0), 45)
    lense1 = Lense(Point(0,2,10), Point(0,3,0), Vector(0,1,0), 45)

    # Eichhorn
    squirrel = build_triangular_network('squirrel_aligned_lowres.obj')

    # Scenes
    sc0 = Scene([sphere0, sphere1, plane], [light1], 0.1)
    sc1 = Scene([*squirrel], [light1],0.6)
    sc2 = Scene([triangle, sphere0], [light1], 0.4)
    sc3 = Scene([sphere3, plane], [light1], 0.6)
    sc4 = Scene([sphere4, sphere5, sphere6, triangle, plane], [light1])
    
    #build_bounce_gif(lense0, scene3, sphere3, plane)   Das dauert!

    # Shoot the Shot
    #lense.capture(sc0, {'width': int(512*10), 'height': int(512*6)})
    lense1.capture(sc4, {'width': int(512*5), 'height': int(512*3)}, 'vorlage.png')
    lense.capture(sc1, {'width': int(512), 'height': int(512)})