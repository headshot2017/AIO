from PyQt4 import QtCore, QtGui
from os import path
import ctypes, platform, ini, sys, __builtin__
import audio as AUDIO

__builtin__.audio = AUDIO
del AUDIO

osname = platform.system()
if osname == "Linux": QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_X11InitThreads) # Linux fix

missingfile = audio.checkAvailable()
if missingfile:
	QtGui.QMessageBox(QtGui.QMessageBox.Information, "Failed to launch game", "'%s' is missing on the game folder.\nThis file is required for audio playback.\nDid you extract all the game files correctly?" % missingfile)
	sys.exit(1)

audio.init()
from AIOApplication import AIOApplication
app = AIOApplication(sys.argv)

if not path.exists("data"):
	QtGui.QMessageBox(QtGui.QMessageBox.Information, "Failed to launch game", "The folder named \"data\" could not be found.\nDid you extract all the game files properly? The folder \"data\" must be situated in the same folder as the game exe.")
	sys.exit(1)

app.setWindowIcon(QtGui.QIcon("icon.ico"))
app.exec_()
audio.free()
