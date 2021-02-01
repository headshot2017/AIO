# vectorial math stuff
# borrowed from tw source code

import math

class vec2:
    def __init__(self, x=0, y=0):
        self.x = float(x)
        self.y = float(y)

    def __sub__(self, other):
        if isinstance(other, vec2):
            self.x -= other.x
            self.y -= other.y
        else:
            self.x -= other
            self.y -= other
        return self

    def __add__(self, other):
        if isinstance(other, vec2):
            self.x += other.x
            self.y += other.y
        else:
            self.x += other
            self.y += other
        return self

    def __mul__(self, other):
        if isinstance(other, vec2):
            self.x *= other.x
            self.y *= other.y
        else:
            self.x *= other
            self.y *= other
        return self

    def __truediv__(self, other):
        if isinstance(other, vec2):
            self.x /= other.x
            self.y /= other.y
        else:
            self.x /= other
            self.y /= other
        return self

    def __floordiv__(self, other):
        if isinstance(other, vec2):
            self.x //= other.x
            self.y //= other.y
        else:
            self.x //= other
            self.y //= other
        return self

    def __repr__(self):
        return "vmath.vec2(%d,%d)"%(self.x,self.y)

def length(a):
	return math.sqrt(a.x*a.x + a.y*a.y)

def distance(a, b):
	return length(a-b)

def dot(a, b):
	return a.x*b.x + a.y*b.y

def normalize(v):
	l = (1./math.sqrt(v.x*v.x + v.y*v.y))
	return vec2(v.x*l, v.y*l)