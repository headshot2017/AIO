from PyQt4 import QtCore, QtGui
from os import path
import ctypes, ini, sys

if not path.exists("bass.dll"):
	ctypes.windll.user32.MessageBoxA(0, "bass.dll is missing on the game folder.\nthis file is required for audio playback.\ndid you extract all the game files correctly?", "unable to launch game", 0)
	sys.exit(1)
from pybass import *

from AIOApplication import AIOApplication

if not path.exists("data"):
	ctypes.windll.user32.MessageBoxA(0, "the folder named \"data\" could not be found.\ndid you extract all the game files properly? the folder \"data\" must be situated in the same folder as the game.", "unable to launch game", 0) #if you're using linux, then i'm sorry, but not yet. just use wine for the time being
	sys.exit(1)

device = ini.read_ini_int("aaio.ini", "Audio", "Device", -1)

if not BASS_Init(device, 44100, 0, 0, 0):
	sys.exit(1)

app = AIOApplication(sys.argv)
app.setWindowIcon(QtGui.QIcon("icon.ico"))
app.exec_()
BASS_Free()
