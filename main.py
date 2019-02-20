from PyQt4 import QtCore, QtGui
from os import path
from pybass import *
import ctypes

from AIOApplication import AIOApplication

import sys

if not path.exists("data"):
	ctypes.windll.user32.MessageBoxA(0, "the folder named \"data\" could not be found.\ndid you extract all the game files properly? the folder \"data\" must be situated in the same folder as the game.", "unable to launch game", 0) #if you're using linux, then i'm sorry, but not yet. just use wine for the time being
	sys.exit(1)

if not BASS_Init(-1, 44100, 0, 0, 0):
	sys.exit(1)

app = AIOApplication(sys.argv)
app.exec_()
BASS_Free()