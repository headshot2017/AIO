# vectorial math stuff
# borrowed from teeworlds source code

import math

class vec2:
    def __init__(self, x=0, y=0):
        if isinstance(x, vec2):
            self.x = x.x
            self.y = x.y
        else:
            self.x = float(x)
            self.y = float(y)

    def __sub__(self, other):
        if isinstance(other, vec2):
            return vec2(self.x-other.x, self.y-other.y)
        return vec2(self.x-other, self.y-other)

    def __add__(self, other):
        if isinstance(other, vec2):
            return vec2(self.x+other.x, self.y+other.y)
        return vec2(self.x+other, self.y+other)

    def __mul__(self, other):
        if isinstance(other, vec2):
            return vec2(self.x*other.x, self.y*other.y)
        return vec2(self.x*other, self.y*other)

    def __truediv__(self, other):
        if isinstance(other, vec2):
            return vec2(self.x/other.x, self.y/other.y)
        return vec2(self.x/other, self.y/other)

    def __floordiv__(self, other):
        if isinstance(other, vec2):
            return vec2(self.x//other.x, self.y//other.y)
        return vec2(self.x//other, self.y//other)

    def __neg__(self):
        return vec2(-self.x, -self.y)

    def __repr__(self):
        return "vmath.vec2(%.3f,%.3f)"%(self.x,self.y)


def length(a): # also magnitude
	return math.sqrt(a.x*a.x + a.y*a.y)

def distance(a, b):
	return length(a-b)

def dot(a, b):
	return a.x*b.x + a.y*b.y

def mix(a, b, amount):
    return a + (b - a) * amount

def round_to_int(f):
	return int(f + 0.5) if f > 0 else int(f - 0.5)

def normalize(v):
	div = math.sqrt(v.x*v.x + v.y*v.y)
	if div == 0: return vec2(0,0)
	l = (1./div)
	return vec2(v.x*l, v.y*l)