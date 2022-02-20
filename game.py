import random, os, math, time
from functools import partial

from PyQt4 import QtCore, QtGui, QtOpenGL, uic
from pybass import *

import AIOprotocol, buttons, charselect, ini, vmath

INLINE_BLUE = 0
INLINE_GREEN = 1
INLINE_ORANGE = 2
INLINE_GRAY = 3

def plural(text, value):
	return text+"s" if value != 1 else text

directions = [
    "south",
    "southwest",
    "west",
    "northwest",
    "north",
    "northeast",
    "east",
    "southeast"
]

qtcolors = {
    0: QtGui.QColor(255, 255, 255),
    1: QtGui.QColor(0, 255, 0),
    2: QtGui.QColor(255, 0, 0),
    3: QtGui.QColor(255, 165, 0),
    4: QtGui.QColor(45, 150, 255),
    5: QtGui.QColor(255, 255, 0),
    6: 691337, # rainbow
    7: QtGui.QColor(255, 192, 203),
    8: QtGui.QColor(0, 255, 255),
    "_inline_grey": QtGui.QColor(187, 187, 187)
}

def getDirection(dir):
	if dir >= 0 and dir < len(directions):
		return directions[dir]
	return ""

def getCompactDirection(dir):
	if dir < 4:
		return "west"
	return "east"

def getColor(number):
	if number in qtcolors:
		return qtcolors[number]
	return QtGui.QColor(0,0,0)

class ICLineEdit(QtGui.QLineEdit):
	enter_pressed = False
	def __init__(self, window=None, ao_app=None):
		super(ICLineEdit, self).__init__(window)
		self.window = window
		self.ao_app = ao_app
	
	def keyPressEvent(self, event):
		if event.key() == QtCore.Qt.Key_Return and not event.isAutoRepeat():
			self.enter_pressed = True
		super(ICLineEdit, self).keyPressEvent(event)
	
	def keyReleaseEvent(self, event):
		if event.key() == QtCore.Qt.Key_Return and not event.isAutoRepeat():
			self.enter_pressed = False
		super(ICLineEdit, self).keyReleaseEvent(event)

class Broadcast(QtGui.QGraphicsItem):
	fadeType = 0
	def __init__(self, scene):
		super(Broadcast, self).__init__(scene=scene)
		theme = ini.read_ini("aaio.ini", "General", "Theme", "default")

		self.scene = scene
		self.pixmap = QtGui.QGraphicsPixmapItem(self)
		self.orig_pixmap = QtGui.QPixmap("data/themes/"+theme+"/broadcast.png")
		self.pixmap.setPixmap(self.orig_pixmap)
		self.text = QtGui.QGraphicsSimpleTextItem(self)
		
		aFont = QtGui.QFont("Tahoma", 8)
		self.fontmetrics = QtGui.QFontMetrics(aFont)
		self.setOpacity(0)
		self.fadeTimer = QtCore.QTimer()
		self.fadeTimer.timeout.connect(self.opacityTimer)
		self.waitTimer = QtCore.QTimer()
		self.waitTimer.timeout.connect(self.startFading)
		self.setZValue(99999)
	
	def boundingRect(self):
		return QtCore.QRectF(-self.pixmap.pixmap().size().width()/2, 0, self.pixmap.pixmap().size().width(), self.pixmap.pixmap().size().height())
	
	def paint(self, painter, option, widget):
		pass
	
	def opacityTimer(self):
		if self.fadeType == 0:
			if self.opacity() < 1:
				self.setOpacity(self.opacity() + 0.025)
			else:
				self.setOpacity(1)
				self.waitTimer.start(5000)
				self.fadeTimer.stop()
		
		elif self.fadeType == 1:
			if self.opacity() > 0:
				self.setOpacity(self.opacity() - 0.025)
			else:
				self.setOpacity(0)
				self.fadeTimer.stop()
	
	def startFading(self):
		self.fadeType = 1
		self.fadeTimer.start(50)
	
	def showText(self, text):
		apixmap = self.orig_pixmap
		width = self.fontmetrics.boundingRect(text).width()+6
		if width > self.orig_pixmap.size().width():
			apixmap = self.orig_pixmap.scaled(width, apixmap.size().height())
		
		self.pixmap.setPixmap(apixmap)
		
		self.pixmap.setPos(self.scene.sceneRect().width()/2 - (apixmap.size().width()/2), 0)
		self.text.setPos(self.pixmap.x() + ((self.pixmap.pixmap().size().width()/2) - (self.fontmetrics.boundingRect(text).width()/2)), 1)
		self.text.setText(text)
		self.fadeType = 0
		if self.waitTimer.isActive():
			self.waitTimer.stop()
		
		if not self.fadeTimer.isActive():
			self.fadeTimer.start(50)

class ExamineCross(QtGui.QGraphicsItem):
	def __init__(self, gameport, scene):
		self.gameport = gameport
		super(ExamineCross, self).__init__(scene=scene)
		
		self.hide()
		
		self.setZValue(100000)
		pen = QtGui.QPen()
		pen.setColor(QtGui.QColor(45, 150, 255))
		
		self.rect = QtGui.QGraphicsRectItem(-8, -8, 16, 16, self)
		self.vertical_line = QtGui.QGraphicsLineItem(0, -64, 0, 64, self)
		self.horizontal_line = QtGui.QGraphicsLineItem(-64, 0, 64, 0, self)
		
		self.rect.setPen(pen)
		self.vertical_line.setPen(pen)
		self.horizontal_line.setPen(pen)
	
	def boundingRect(self):
		return QtCore.QRectF(-64, -64, 128, 128)
	
	def paint(self, painter, option, widget):
		pass

class ExamineObj(QtGui.QGraphicsItem):
	def __init__(self, name, x, y, scene):
		super(ExamineObj, self).__init__(scene=scene)
		
		self.xx = x
		self.yy = y
		self.setZValue(100000)
		pen = QtGui.QPen()
		blackBrush = QtGui.QBrush(QtGui.QColor(0,0,0))
		whiteBrush = QtGui.QBrush(QtGui.QColor(255,255,255))
		font = QtGui.QFont("Arial", 10)
		fontmetric = QtGui.QFontMetrics(font)
		pen.setColor(QtGui.QColor(45, 150, 255))
		
		self.rect = QtGui.QGraphicsRectItem(-8, -8, 16, 16, self)
		self.vertical_line = QtGui.QGraphicsLineItem(0, -64, 0, 64, self)
		self.horizontal_line = QtGui.QGraphicsLineItem(-64, 0, 64, 0, self)
		self.textrect = QtGui.QGraphicsRectItem(16, 16, fontmetric.boundingRect(name).width(), fontmetric.boundingRect(name).height(), self)
		self.examined_by = QtGui.QGraphicsSimpleTextItem(name, self)
		
		self.rect.setPen(pen)
		self.vertical_line.setPen(pen)
		self.horizontal_line.setPen(pen)
		pen.setColor(QtGui.QColor(0, 0, 0))
		self.textrect.setPen(pen)
		self.textrect.setBrush(blackBrush)
		self.setPos(x, y)
		
		self.examined_by.setBrush(whiteBrush)
		self.examined_by.setFont(font)
		self.examined_by.setPos(16, 16)
		
		self.opacityTimer = QtCore.QTimer()
		self.opacityTimer.timeout.connect(self.opacitys)
		self.startToFadeTimer = QtCore.QTimer()
		self.startToFadeTimer.timeout.connect(partial(self.opacityTimer.start, 50))
		self.startToFadeTimer.setSingleShot(True)
		self.startToFadeTimer.start(5000)
		self.hide()
		
	def opacitys(self):
		self.setOpacity(self.opacity()-0.05)
		if self.opacity() <= 0:
			self.opacityTimer.stop()
	
	def boundingRect(self):
		return QtCore.QRectF(-64, -64, 128, 128)
	
	def paint(self, painter, option, widget):
		pass

class WTCEview(QtGui.QLabel):
	def __init__(self, parent):
		super(WTCEview, self).__init__(parent)
		self.parent = parent

		self.movie = QtGui.QMovie()
		self.movie.frameChanged.connect(self.frame_change)
		self.finalframe_timer = QtCore.QTimer()
		self.finalframe_timer.setSingleShot(False)
		self.finalframe_timer.timeout.connect(self.finished)
		self.viewport = self.parent.gameview.size()
		self.resize(self.viewport)
		self.move(self.viewport.width()/2 - (self.size().width()/2), self.viewport.height()/2 - (self.size().height()/2))
		self.hide()

	def frame_change(self, frame):
		if self.movie.state() != QtGui.QMovie.Running:
			return
		img = self.movie.currentImage()
		self.setPixmap(QtGui.QPixmap.fromImage(img.scaled(self.viewport)))
		if self.movie.currentFrameNumber() == self.movie.frameCount() - 1:
			self.finalframe_timer.start(self.movie.nextFrameDelay())

	def finished(self):
		self.finalframe_timer.stop()
		self.movie.stop()
		self.hide()

	def showWTCE(self, wtce):
		theme = ini.read_ini("aaio.ini", "General", "Theme", "default")

		self.finished()
		if wtce == 0:
			self.movie.setFileName("data/themes/"+theme+"/witnesstestimony.gif")
		elif wtce == 1:
			self.movie.setFileName("data/themes/"+theme+"/crossexamination.gif")
		elif wtce == 2:
			self.movie.setFileName("data/themes/"+theme+"/notguilty.gif")
		elif wtce == 3:
			self.movie.setFileName("data/themes/"+theme+"/guilty.gif")
		else:
			return
		self.show()
		self.movie.start()

class BaseCharacter(QtGui.QGraphicsPixmapItem):
	spinframes = []
	def __init__(self, scene):
		super(BaseCharacter, self).__init__(scene=scene)
		self.movie = QtGui.QMovie()
		self.movie.frameChanged.connect(self.frame_change)
		self.spinframe = QtGui.QImageReader()
		self.finalframe_timer = QtCore.QTimer()
		self.finalframe_timer.setSingleShot(True)
		self.finalframe_timer.timeout.connect(self.finished)
		self.loop = True
	
	def play(self, filename, loop):
		self.stop()
		self.loop = loop
		self.movie.setFileName(filename)
		self.movie.start()
	
	def playLastFrame(self, filename):
		self.stop()
		self.movie.setFileName(filename)
		self.spinframe.setFileName(filename)
		for i in range(self.spinframe.imageCount()):
			img = self.spinframe.read()
			if i == self.spinframe.imageCount()-1:
				self.setPixmap(QtGui.QPixmap.fromImage(img))
	
	def playSpin(self, filename, dir):
		self.stop()
		if self.spinframes:
			self.movie.setFileName(filename)
			self.setPixmap(self.spinframes[dir])
	
	def setSpin(self, image):
		self.spinframe.setFileName(image)
		self.spinframes = []
		for frame in range(self.spinframe.imageCount()):
			self.spinframes.append(QtGui.QPixmap.fromImage(self.spinframe.read()))
	
	def stop(self):
		self.finalframe_timer.stop()
		self.movie.stop()
	
	def finished(self):
		self.finalframe_timer.stop()
		self.movie.stop()
		self.afterStop()
		
	def afterStop(self):
		pass
	
	@QtCore.pyqtSlot(int)
	def frame_change(self, frame):
		if not self.finalframe_timer.isActive():
			self.setPixmap(self.movie.currentPixmap())
		
		if self.movie.frameCount() - 1 == frame and not self.loop:
			self.finalframe_timer.start(self.movie.nextFrameDelay())

class Character(BaseCharacter):
	def __init__(self, scene, ao_app):
		super(Character, self).__init__(scene=scene)
		self.ao_app = ao_app
		self.setPos(0, 0)
		self.pressed_keys = set()
		self.translated = False
		self.chatbubblepix = QtGui.QGraphicsPixmapItem(scene=scene)
		self.setChatBubble(0)

		self.dir_nr = 0
		self.emoting = 0
		self.currentemote = -1
		self.xx = 0.0
		self.yy = 0.0
		self.xprevious = 0
		self.yprevious = 0
		self.xprevious2 = 0
		self.yprevious2 = 0
		self.hspeed = 0
		self.vspeed = 0
		self.walkspd = 6
		self.runspd = 12
		self.run = False
		self.smoothmoves = 0 #remote player smooth movement
		self.charid = -1
		self.zone = -1
		self.charprefix = ""
		self.sprite = ""
		self.blip = ""
		self.scale = 1
		self.walkanims = [[], 0, 0] #value 0 contains the animations, value 1 is the run animation, value 2 is the walk animation
		self.emotes = [[], [], [], [], [], []] #emotes, loop values, directions (east, west...), sound names, sound delays, offsets
		self.isPlayer = False
		self.maxwidth = 0
		self.maxheight = 0
		self.chatbubble = 0
		self.playFile = ["", 0, False, [0,0]] # filename, loop, is spin, offset
		self.moonwalk = False #are you ok Annie
		self.animTranslate = [0,0]
	
	def setChatBubble(self, value):
		self.chatbubble = value
		if value == 2:
			chatbubbl = QtGui.QImage("data/misc/chatbubble_green.png")
		else:
			chatbubbl = QtGui.QImage("data/misc/chatbubble.png")
		self.chatbubblepix.setPixmap(QtGui.QPixmap.fromImage(chatbubbl.scaled(chatbubbl.width()*2, chatbubbl.height()*2)))
	
	def afterStop(self):
		self.emoting = 2

	def collidesWithItem(self, other): # finally no one will get stuck on that fountain while spazzing erratically
		self.setPos(self.x() + self.hspeed, self.y() + self.vspeed)
		collides = super(Character, self).collidesWithItem(other)
		#print self.width
		self.setPos(self.x() - self.hspeed, self.y() - self.vspeed)
		return collides

	def shape(self):
		jm = QtGui.QPainterPath()
		nouis = self.boundingRect()
		nouis.setX(0)
		nouis.setY(nouis.height()-2)
		nouis.setWidth(1)
		nouis.setHeight(2)
		jm.addRect(nouis)
		return jm

	def changeChar(self, newcharid):
		self.charid = newcharid
		if newcharid == -1:
			self.setOpacity(0.5)
			return
			
		self.setOpacity(1)
		
		inipath = "data/characters/"+self.ao_app.charlist[newcharid]+"/char.ini"
		
		self.charprefix = ini.read_ini(inipath, "Options", "imgprefix")
		if self.charprefix:
			self.charprefix += "-"
		
		imgsize = QtGui.QPixmap("data/characters/"+self.ao_app.charlist[newcharid]+"/"+self.charprefix+"spin.gif").size()
		self.scale = ini.read_ini_float(inipath, "Options", "scale", 1.0)
		self.setScale(self.scale*2)
		
		if self.translated:
			self.translate(0, self.maxheight/4)
		
		self.maxwidth = imgsize.width()*(self.scale*2)
		self.maxheight = imgsize.height()*(self.scale*2)
		self.translate(0, -self.maxheight/4)
		self.translated = True
		self.setSpin("data/characters/"+self.ao_app.charlist[newcharid]+"/"+self.charprefix+"spin.gif")

		max_emotes = ini.read_ini_int(inipath, "Emotions", "total")
		self.emotes[0] = []
		self.emotes[1] = []
		self.emotes[2] = []
		self.emotes[3] = []
		self.emotes[4] = []
		self.emotes[5] = []
		for i in range(max_emotes):
			self.emotes[0].append(ini.read_ini(inipath, "Emotions", str(i+1)))
			self.emotes[1].append(ini.read_ini_int(inipath, "Emotions", str(i+1)+"_loop", 0))
			self.emotes[2].append(ini.read_ini(inipath, "Directions", str(i+1)).split("#"))
			self.emotes[3].append(ini.read_ini(inipath, "SoundN", str(i+1)).split("#"))
			self.emotes[4].append(ini.read_ini_int(inipath, "SoundT", str(i+1)))

			offsets = ini.read_ini(inipath, "Emotions", str(i+1)+"_offset", "0,0").split("#")
			offsetDict = {}
			for offsetStr in offsets:
				i = offsets.index(offsetStr)
				offset = offsetStr.split(",")
				offsetDict[self.emotes[2][-1][i]] = [int(offset[0]), int(offset[1])]
			self.emotes[5].append(offsetDict)

			# explaining the confusing emote offset lists:
			# [ all emotes
			#     { all directions for emote 0
			#         "west": [ x and y offset for this dir
			#             0,0
			#         ],
			#         "east": [ x and y offset for this dir
			#             0,0
			#         ]
			#     },
			#     { all directions for emote 1
			#         "west": [ x and y offset for this dir
			#             0,0
			#         ],
			#         "east": [ x and y offset for this dir
			#             0,0
			#         ]
			#     }
			# ]

		if not self.isPlayer:
			return
		
		self.emoting = 0
		self.currentemote = -1
		self.blip = ini.read_ini(inipath, "Options", "blip", "male")
		
		self.walkspd = ini.read_ini_int(inipath, "Options", "walkspeed", 6)
		self.runspd = ini.read_ini_int(inipath, "Options", "runspeed", 12)
		
		self.walkanims[0] = []
		for i in range(ini.read_ini_int(inipath, "WalkAnims", "total", 1)):
			self.walkanims[0].append(ini.read_ini(inipath, "WalkAnims", str(i+1), "walk"))
		self.walkanims[1] = ini.read_ini_int(inipath, "WalkAnims", "runanim", 1)-1
		
		self.playSpin("data/characters/"+self.ao_app.charlist[newcharid]+"/spin.gif", self.dir_nr) # "switching character while emote is playing" bug fixed
	
	def keyPressEvent(self, event):
		if self.isPlayer:
			if event.isAutoRepeat():
				return
			self.pressed_keys.add(event.key())
	
	def keyReleaseEvent(self, event):
		if self.isPlayer:
			if event.isAutoRepeat():
				return
			
			try:
				self.pressed_keys.remove(event.key())
			except:
				pass
			
	def setPlayer(self, on):
		self.isPlayer = on
	
	def moveReal(self, x, y):
		self.xx = x
		self.yy = y
	
	def setWalls(self, image):
		self.wallsImage = image
	
	def play(self, filename, loop, offset=[0,0]):
		self.playFile = [filename, loop, False, offset]

	def playSpin(self, filename, dir):
		self.playFile = [filename, dir, True, [0,0]]
		self.emoting = 0
		self.currentemote = -1

	def playLastFrame(self, filename, offset=[0,0]):
		super(Character, self).playLastFrame(filename)
		self.playFile[3] = offset

	def update(self, viewX, viewY):
		if self.isPlayer and self.charid != -1:
			newsprite = ""
			currsprite = os.path.basename(str(self.movie.fileName().toUtf8()))
			self.run = self.ao_app.controls["run"][0] in self.pressed_keys
			anim = self.walkanims[1] if self.run else self.walkanims[2]

			up = self.ao_app.controls["up"]
			down = self.ao_app.controls["down"]
			left = self.ao_app.controls["left"]
			right = self.ao_app.controls["right"]

			if (up[0] in self.pressed_keys and right[0] in self.pressed_keys) or (up[1] in self.pressed_keys and right[1] in self.pressed_keys):
				self.vspeed = -self.runspd if self.run else -self.walkspd
				self.hspeed = self.runspd if self.run else self.walkspd
				self.emoting = 0
				self.currentemote = -1
				if self.moonwalk:
					dirnr = AIOprotocol.SOUTHWEST
					dirname = "southwest"
				else:
					dirnr = AIOprotocol.NORTHEAST
					dirname = "northeast"
				self.dir_nr = dirnr
				newsprite = self.charprefix+self.walkanims[0][anim]+dirname+".gif"
				self.sprite = self.ao_app.charlist[self.charid]+"/"+self.walkanims[0][anim]+dirname+".gif"
			
			elif (up[0] in self.pressed_keys and left[0] in self.pressed_keys) or (up[1] in self.pressed_keys and left[1] in self.pressed_keys):
				self.vspeed = -self.runspd if self.run else -self.walkspd
				self.hspeed = -self.runspd if self.run else -self.walkspd
				self.emoting = 0
				self.currentemote = -1
				if self.moonwalk:
					dirnr = AIOprotocol.SOUTHEAST
					dirname = "southeast"
				else:
					dirnr = AIOprotocol.NORTHWEST
					dirname = "northwest"
				self.dir_nr = dirnr
				newsprite = self.charprefix+self.walkanims[0][anim]+dirname+".gif"
				self.sprite = self.ao_app.charlist[self.charid]+"/"+self.walkanims[0][anim]+dirname+".gif"
			
			elif (down[0] in self.pressed_keys and right[0] in self.pressed_keys) or (down[1] in self.pressed_keys and right[1] in self.pressed_keys):
				self.vspeed = self.runspd if self.run else self.walkspd
				self.hspeed = self.runspd if self.run else self.walkspd
				self.emoting = 0
				self.currentemote = -1
				if self.moonwalk:
					dirnr = AIOprotocol.NORTHWEST
					dirname = "northwest"
				else:
					dirnr = AIOprotocol.SOUTHEAST
					dirname = "southeast"
				self.dir_nr = dirnr
				newsprite = self.charprefix+self.walkanims[0][anim]+dirname+".gif"
				self.sprite = self.ao_app.charlist[self.charid]+"/"+self.walkanims[0][anim]+dirname+".gif"
			
			elif (down[0] in self.pressed_keys and left[0] in self.pressed_keys) or (down[1] in self.pressed_keys and left[1] in self.pressed_keys):
				self.vspeed = self.runspd if self.run else self.walkspd
				self.hspeed = -self.runspd if self.run else -self.walkspd
				self.emoting = 0
				self.currentemote = -1
				if self.moonwalk:
					dirnr = AIOprotocol.NORTHEAST
					dirname = "northeast"
				else:
					dirnr = AIOprotocol.SOUTHWEST
					dirname = "southwest"
				self.dir_nr = dirnr
				newsprite = self.charprefix+self.walkanims[0][anim]+dirname+".gif"
				self.sprite = self.ao_app.charlist[self.charid]+"/"+self.walkanims[0][anim]+dirname+".gif"
			
			elif up[0] in self.pressed_keys or up[1] in self.pressed_keys:
				self.vspeed = -self.runspd if self.run else -self.walkspd
				self.hspeed = 0
				self.emoting = 0
				self.currentemote = -1
				if self.moonwalk:
					dirnr = AIOprotocol.SOUTH
					dirname = "south"
				else:
					dirnr = AIOprotocol.NORTH
					dirname = "north"
				self.dir_nr = dirnr
				newsprite = self.charprefix+self.walkanims[0][anim]+dirname+".gif"
				self.sprite = self.ao_app.charlist[self.charid]+"/"+self.walkanims[0][anim]+dirname+".gif"
			
			elif down[0] in self.pressed_keys or down[1] in self.pressed_keys:
				self.vspeed = self.runspd if self.run else self.walkspd
				self.hspeed = 0
				self.emoting = 0
				self.currentemote = -1
				if self.moonwalk:
					dirnr = AIOprotocol.NORTH
					dirname = "north"
				else:
					dirnr = AIOprotocol.SOUTH
					dirname = "south"
				self.dir_nr = dirnr
				newsprite = self.charprefix+self.walkanims[0][anim]+dirname+".gif"
				self.sprite = self.ao_app.charlist[self.charid]+"/"+self.walkanims[0][anim]+dirname+".gif"
			
			elif left[0] in self.pressed_keys or left[1] in self.pressed_keys:
				self.vspeed = 0
				self.hspeed = -self.runspd if self.run else -self.walkspd
				self.emoting = 0
				self.currentemote = -1
				if self.moonwalk:
					dirnr = AIOprotocol.EAST
					dirname = "east"
				else:
					dirnr = AIOprotocol.WEST
					dirname = "west"
				self.dir_nr = dirnr
				newsprite = self.charprefix+self.walkanims[0][anim]+dirname+".gif"
				self.sprite = self.ao_app.charlist[self.charid]+"/"+self.walkanims[0][anim]+dirname+".gif"
			
			elif right[0] in self.pressed_keys or right[1] in self.pressed_keys:
				self.vspeed = 0
				self.hspeed = self.runspd if self.run else self.walkspd
				self.emoting = 0
				self.currentemote = -1
				if self.moonwalk:
					dirnr = AIOprotocol.WEST
					dirname = "west"
				else:
					dirnr = AIOprotocol.EAST
					dirname = "east"
				self.dir_nr = dirnr
				newsprite = self.charprefix+self.walkanims[0][anim]+dirname+".gif"
				self.sprite = self.ao_app.charlist[self.charid]+"/"+self.walkanims[0][anim]+dirname+".gif"
			
			else:
				self.hspeed = 0
				self.vspeed = 0
				newsprite = self.charprefix+"spin.gif"
				if self.emoting == 0 and self.currentemote == -1:
					self.sprite = self.ao_app.charlist[self.charid]+"/spin.gif"

			is30 = (self.ao_app.fps == 30)
			self.hspeed /= self.ao_app.fps / 30. * (1 if is30 else 1.4)
			self.vspeed /= self.ao_app.fps / 30. * (1 if is30 else 1.4)

			if currsprite != newsprite and self.emoting == 0 and self.currentemote == -1:
				if self.hspeed == 0 and self.vspeed == 0:
					self.playSpin("data/characters/"+self.ao_app.charlist[self.charid]+"/"+newsprite, self.dir_nr)
				else:
					self.play("data/characters/"+self.ao_app.charlist[self.charid]+"/"+newsprite, True, [0,0])
				
			if (self.hspeed != 0 or self.vspeed != 0) and self.chatbubble == 1:
				self.chatbubble = 0
				self.ao_app.tcpthread.sendChatBubble(0)

		if self.playFile[0]:
			aSize = QtGui.QPixmap(self.playFile[0]).size()
			self.animTranslate = [aSize.width()*self.scale, aSize.height()*self.scale]
			aWidth = aSize.width()*self.scale
			aHeight = aSize.height()*self.scale
			#aWidth = self.maxwidth/2
			#aHeight = self.maxheight/2
			offset = self.playFile[3]
			self.setPos(-viewX + self.xx - (aWidth) - offset[0], -viewY + self.yy - (aHeight*2) - offset[1])
			#self.setOffset(-self.animTranslate[0]/2, 0)

			if not self.playFile[2]:
				super(Character, self).play(self.playFile[0], self.playFile[1])
			else:
				super(Character, self).playSpin(self.playFile[0], self.playFile[1])
			self.playFile[0] = ""
		else:
			aSize = self.pixmap().size()
			self.animTranslate = [aSize.width()*self.scale, aSize.height()*self.scale]
			aWidth = aSize.width()*self.scale
			aHeight = aSize.height()*self.scale
			#aWidth = self.maxwidth/2
			#aHeight = self.maxheight/2
			offset = self.playFile[3]
			self.setPos(-viewX + self.xx - (aWidth) - offset[0], -viewY + self.yy - (aHeight*2) - offset[1])
			#self.setOffset(-self.animTranslate[0]/2, 0)
		
		self.xprevious2 = self.xprevious
		self.yprevious2 = self.yprevious
		self.xprevious = self.xx
		self.yprevious = self.yy
		self.xx += self.hspeed
		self.yy += self.vspeed
		
		if not self.isPlayer and (self.hspeed or self.vspeed):
			self.smoothmoves += 1
			if self.smoothmoves >= 3 * (self.ao_app.fps / 30.):
				self.hspeed = self.vspeed = 0
				self.smoothmoves = 0

class ChatboxWidget(QtGui.QWidget):
    def __init__(self, parent):
        super(ChatboxWidget, self).__init__(parent)
        self.parent = parent

class AIOGraphicsView(QtGui.QGraphicsView):
    def __init__(self, scene, parent):
        super(AIOGraphicsView, self).__init__(scene, parent)
        self.parent = parent
        self.scene = scene
        self.setMouseTracking(True)
        if ini.read_ini_int("aaio.ini", "Advanced", "opengl", 0): # render with OpenGL (experimental)
            self.gameview.setViewport(QtOpenGL.QGLWidget())

        theme = ini.read_ini("aaio.ini", "General", "Theme", "default")
        self.gameScale = ini.read_ini_float("data/themes/"+theme+"/theme.ini", "Theme", "scale", 1.0)
        self.scale(self.gameScale)

        self.dyncam = False
        self.dynOffset = vmath.vec2()

    def setupUi(self, ao_app):
        self.ao_app = ao_app

    def scale(self, newScale):
        self.resetMatrix()
        super(AIOGraphicsView, self).scale(newScale, newScale)
        self.gameScale = newScale

    def playerLookDirection(self, pos):
        x2, y2 = pos.x(), pos.y()
        player = self.parent.characters[self.ao_app.player_id]
        x1 = player.x()+(player.maxwidth/2)
        y1 = player.y()+(player.maxheight/4)

        old_dir_nr = player.dir_nr

        if x2 > x1 and y2 > y1-64 and y2 < y1+64:
            player.dir_nr = AIOprotocol.EAST
        elif x2 > x1+64 and y2 > y1+64:
            player.dir_nr = AIOprotocol.SOUTHEAST
        elif x2 > x1+64 and y2 < y1-64:
            player.dir_nr = AIOprotocol.NORTHEAST
        elif x2 < x1 and y2 > y1-64 and y2 < y1+64:
            player.dir_nr = AIOprotocol.WEST
        elif x2 < x1-64 and y2 > y1+64:
            player.dir_nr = AIOprotocol.SOUTHWEST
        elif x2 < x1-64 and y2 < y1-64:
            player.dir_nr = AIOprotocol.NORTHWEST
        elif y2 > y1 and x2 > x1-64 and x2 < x1+64:
            player.dir_nr = AIOprotocol.SOUTH
        elif y2 < y1 and x2 > x1-64 and x2 < x1+64:
            player.dir_nr = AIOprotocol.NORTH
        player.playSpin("data/characters/"+self.ao_app.charlist[player.charid]+"/"+player.charprefix+"spin.gif", player.dir_nr)

    def mouseMoveEvent(self, event):
        player = self.parent.characters[self.ao_app.player_id]
        if self.dyncam and player.charid != -1:
            remapped = self.mapFromParent(event.pos())
            clickpoint = self.mapToScene(remapped)

            x2, y2 = clickpoint.x(), clickpoint.y()

            mouse = vmath.vec2(x2 - (self.scene.sceneRect().width()/2), y2 - (self.scene.sceneRect().height()/2))
            
            length = vmath.length(mouse)
            CameraMaxDistance = 200.
            DeadZone = 50.
            FollowFactor = 200. / 100.
            MaxDistance = 200.
            MouseMax = min(CameraMaxDistance/FollowFactor + DeadZone, MaxDistance);

            if length > MouseMax:
                mouse = vmath.normalize(mouse) * MouseMax
                length = MouseMax

            OffsetAmount = max(length-DeadZone, 0.0) * FollowFactor
            self.dynOffset = vmath.normalize(mouse) * OffsetAmount

            if player.hspeed == 0 and player.vspeed == 0: # standing still
                self.playerLookDirection(clickpoint)

    def mouseDoubleClickEvent(self, event):
        self.dyncam = True

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.parent.characters.has_key(self.ao_app.player_id): # click to look at that direction
            if self.parent.characters[self.ao_app.player_id].charid != -1:
                remapped = self.mapFromParent(event.pos())
                self.playerLookDirection(self.mapToScene(remapped))

            if self.parent.parent.examining: # omfg this is ugly
                a = QtCore.QPointF(self.parent.parent.examiner.pos() - self.parent.zonebackground.pos()) # UGLY
                self.parent.parent.examineSpot(a) # UGLY

        super(AIOGraphicsView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.dyncam:
            self.dyncam = False

class GamePort(QtGui.QWidget):
	def __init__(self, parent, ao_app=None):
		super(GamePort, self).__init__(parent)
		self.parent = parent
		self.ao_app = ao_app
		self.gamescene = QtGui.QGraphicsScene(0, 0, 512, 384, self)
		self.gameview = AIOGraphicsView(self.gamescene, self)
		self.gameview.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.black))
		self.gameview.show()
		
		self.zonebackground = QtGui.QGraphicsPixmapItem(scene=self.gamescene)
		self.zonewalls = QtGui.QGraphicsPixmapItem(scene=self.gamescene)
		self.zonewalls.hide()
		self.zoneforegrounds = []
		
		self.zonebackground.setZValue(-10000)
		self.characters = {}

	def resize(self, width, height):
		super(GamePort, self).resize(width, height)
		self.gamescene.setSceneRect(0, 0, width / self.gameview.gameScale, height / self.gameview.gameScale)
		self.gameview.resize(width+2, height+2)
		self.parent.chatboxwidget.move(width/2 - (self.parent.chatboxwidget.size().width()/2), height - self.parent.chatboxwidget.size().height())

	def scale(self, newScale):
		self.gameview.scale(newScale)
		self.resize(self.size().width(), self.size().height())

	def setupUi(self, ao_app, gamewidget):
		self.parent = gamewidget
		self.ao_app = ao_app
		self.gameview.setupUi(ao_app)
		self.resize(self.size().width(), self.size().height())
		ao_app.installEventFilter(self)
	
	def eventFilter(self, source, event):
		if self.characters.has_key(self.ao_app.player_id):
			if source == self.gameview or source == self.parent.chatboxwidget:
				if event.type() == QtCore.QEvent.KeyPress:
					try:
						self.characters[self.ao_app.player_id].keyPressEvent(event)
					except:
						pass
				elif event.type() == QtCore.QEvent.KeyRelease:
					try:
						self.characters[self.ao_app.player_id].keyReleaseEvent(event)
					except:
						pass

		return super(GamePort, self).eventFilter(source, event)
	
	def initCharacter(self, ind):
		self.characters[ind] = Character(ao_app=self.ao_app, scene=self.gamescene)
		self.characters[ind].show()
		return self.characters[ind]
	
	def deleteCharacter(self, ind):
		self.characters[ind].stop()
		self.gamescene.removeItem(self.characters[ind].chatbubblepix)
		self.gamescene.removeItem(self.characters[ind])
		del self.characters[ind]
	
	def getViewCoords(self, outOfBounds=False):
		player_id = self.ao_app.player_id
		width = self.img.width()*2
		height = self.img.height()*2
		
		if self.characters[player_id].charid != -1:
			viewX = self.characters[player_id].xx - (self.size().width()/(self.gameview.gameScale*2))
			viewY = self.characters[player_id].yy-(self.size().height()/(self.gameview.gameScale*2))-(self.characters[player_id].maxheight)
		else:
			viewX = self.characters[player_id].xx - (self.size().width()/2)
			viewY = self.characters[player_id].yy-(self.size().height()/1.25)

		if self.gameview.dyncam:
			viewX += self.gameview.dynOffset.x
			viewY += self.gameview.dynOffset.y

		if not outOfBounds:
			if viewX > width-(self.size().width() / self.gameview.gameScale):
				viewX = width-(self.size().width() / self.gameview.gameScale)
			if viewX < 0:
				viewX = 0
			if viewY > height-(self.size().height() / self.gameview.gameScale):
				viewY = height-(self.size().height() / self.gameview.gameScale)
			if viewY < 0:
				viewY = 0

			# center the camera if the viewport is bigger than background
			if (self.size().width() / self.gameview.gameScale) > width:
				viewX = -(self.size().width() / self.gameview.gameScale)/2 + (width/2)
			if (self.size().height() / self.gameview.gameScale) > height:
				viewY = -(self.size().height() / self.gameview.gameScale)/2 + (height/2)
		
		return viewX, viewY
	
	def moveView(self, viewX, viewY):
		self.zonebackground.setPos(-viewX, -viewY)
		self.zonewalls.setPos(-viewX, -viewY)
		for fg in self.zoneforegrounds:
			fg[0].setPos(-viewX + fg[1], -viewY + fg[2])
		
		player_id = self.ao_app.player_id
		mychar = self.characters[player_id]
		if mychar.collidesWithItem(self.zonewalls) and mychar.isPlayer: # good lord why
			mychar.xx = mychar.xprevious
			mychar.yy = mychar.yprevious
		
		for char in self.characters.values():
			char.setZValue(char.yy  - (char.pixmap().size().height()*2) + (char.maxheight*0.75))
			char.chatbubblepix.setZValue(char.zValue())
			char.chatbubblepix.setPos(-viewX + char.xx + - (char.chatbubblepix.pixmap().size().width()/2), -viewY + char.yy - (char.pixmap().size().height()*char.scale+char.maxheight))
			if char.chatbubble:
				char.chatbubblepix.show()
			else:
				char.chatbubblepix.hide()
	
	def setBackground(self, bg):
		if os.path.exists(bg+".png"):
			self.img = QtGui.QImage(bg+".png")
			print "[client]", "load png background \"%s\", exists: %s" % (bg+".png", os.path.exists(bg+".png"))
		elif os.path.exists(bg+".gif"):
			self.img = QtGui.QImage(bg+".gif")
			print "[client]", "load gif background \"%s\", exists: %s" % (bg+".gif", os.path.exists(bg+".gif"))

		print "[client]", "background QImage is null: %s" % self.img.isNull()
		self.zonebackground.setPixmap(QtGui.QPixmap.fromImage(self.img.scaled(self.img.width()*2, self.img.height()*2)))

class GameWidget(QtGui.QWidget):
	ao_app = None
	player = None
	m_chatmsg = ""
	m_color = 0
	rainbow_counter = 0
	next_character_is_not_special = False
	message_is_centered = False
	current_display_speed = 3
	message_display_speed = (30, 40, 50, 60, 75, 100, 120)
	entire_message_is_blue = False
	inline_color_stack = [] #"colour" is for EU nobos
	inline_blue_depth = 0
	tick_pos = 0
	blip_pos = 0
	blip_rate = 1
	blip = None
	finished_chat = True
	ic_delay = 0
	infinite_cam = False
	message_id = 0 # anti-lag spam
    
	def __init__(self, _ao_app):
		super(GameWidget, self).__init__()
		self.ao_app = _ao_app
		
		self.ao_app.tcpthread.musicChange.connect(self.onMusicChange)
		self.ao_app.tcpthread.playerCreate.connect(self.onPlayerCreate)
		self.ao_app.tcpthread.playerDestroy.connect(self.onPlayerDestroy)
		self.ao_app.tcpthread.zoneChange.connect(self.onPlayerZone)
		self.ao_app.tcpthread.charChange.connect(self.onPlayerChar)
		self.ao_app.tcpthread.movementPacket.connect(self.onMovementPacket)
		self.ao_app.tcpthread.examinePacket.connect(self.onExaminePacket)
		self.ao_app.tcpthread.emoteSound.connect(self.onEmoteSound)
		self.ao_app.tcpthread.OOCMessage.connect(self.onOOCMessage)
		self.ao_app.tcpthread.ICMessage.connect(self.onICMessage)
		self.ao_app.tcpthread.broadcastMessage.connect(self.onBroadcast)
		self.ao_app.tcpthread.chatBubble.connect(self.onChatBubble)
		self.ao_app.tcpthread.evidenceChanged.connect(self.onEvidenceChanged)
		self.ao_app.tcpthread.penaltyBar.connect(self.onPenaltyBar)
		self.ao_app.tcpthread.WTCEMessage.connect(self.onWTCEMessage)
		self.ao_app.tcpthread.gotPing.connect(self.onGotPing)
		

		
		self.aSound = ["", -1, 0] #filename, delay, zone
		self.mychatcolor = 0
		self.myrealization = 0
		self.myevidence = -1
		
		self.playing = False
		
		self.testtimer = QtCore.QBasicTimer()
		self.tcptimer = QtCore.QBasicTimer()
		self.ticks = 0

		self.chatbubbletimer = QtCore.QTimer()
		self.chatbubbletimer.setSingleShot(True)
		self.chatbubbletimer.timeout.connect(partial(self.ao_app.tcpthread.sendChatBubble, 0))

		# good riddance to like 200 lines of code...

		theme = ini.read_ini("aaio.ini", "General", "Theme", "default")
		uic.loadUi("data/themes/"+theme+"/game.ui", self) # plant the bomb

		self.realizationbtn_off = QtGui.QPixmap("data/themes/"+theme+"/realization.png")
		self.realizationbtn_on = QtGui.QPixmap("data/themes/"+theme+"/realization_pressed.png")


		self.useMusicToggle = (ini.read_ini("data/themes/"+theme+"/theme.ini", "Theme", "music_toggle") == "1")
		self.useOOCToggle = (ini.read_ini("data/themes/"+theme+"/theme.ini", "Theme", "ooc_toggle") == "1")
		self.useChatlogToggle = (ini.read_ini("data/themes/"+theme+"/theme.ini", "Theme", "chatlog_toggle") == "1")
		self.useEmoteToggle = (ini.read_ini("data/themes/"+theme+"/theme.ini", "Theme", "emote_toggle") == "1")

		if self.useMusicToggle:
			if not hasattr(self, "musiclist"):
				self.musiclist = QtGui.QListWidget(self)
				self.musiclist.resize(0,0)
			if self.musiclist.size() == QtCore.QSize(0,0):
				self.musiclist.resize(self.size().width()/2, self.size().height()/2)
			self.musiclist.move(self.size().width()/2 - (self.musiclist.size().width()/2), self.size().height()/2 - (self.musiclist.size().height()/2))
			self.musiclist.hide()
			self.musicToggle.clicked.connect(self.toggleMusicList)

		if self.useOOCToggle:
			if not hasattr(self, "oocwidget"):
				self.oocwidget = QtGui.QWidget(self)
				uic.loadUi("data/themes/"+theme+"/ooc.ui", self.oocwidget)
				self.oocinput = self.oocwidget.oocinput
				self.oocnameinput = self.oocwidget.oocnameinput
				self.oocchat = self.oocwidget.oocchat
			self.oocwidget.move(self.size().width()/2 - (self.oocwidget.size().width()/2), self.size().height()/2 - (self.oocwidget.size().height()/2))
			self.oocwidget.hide()
			self.oocToggle.clicked.connect(self.onOOCButton)

		if self.useChatlogToggle:
			if not hasattr(self, "chatlog"):
				self.chatlog = QtGui.QTextEdit(self)
				self.chatlog.setReadOnly(True)
			if self.chatlog.size() == QtCore.QSize(0,0):
				self.chatlog.resize(self.size().width()/2, self.size().height()/2)
			self.chatlog.move(self.size().width()/2 - (self.chatlog.size().width()/2), self.size().height()/2 - (self.chatlog.size().height()/2))
			self.chatlog.hide()
			self.chatlogToggle.clicked.connect(self.onLogButton)
		else:
			self.chatboxwidget.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

		if self.useEmoteToggle:
			pixmap = QtGui.QPixmap("data/themes/"+theme+"/emote_bar.png")
			if not hasattr(self, "emotebar"):
				self.emotebar = QtGui.QLabel(self)
				self.emotebar.setPixmap(pixmap)

			oldpos = (self.emotebar.x(), self.emotebar.y())
			newpos = (self.size().width()/2 - (pixmap.size().width()/2), 0)
			diffpos = (newpos[0] - oldpos[0], newpos[1] - oldpos[1])

			self.emotebar.resize(pixmap.size().width(), pixmap.size().height())
			self.emotebar.move(newpos[0], newpos[1])
			self.prevemotepage.move(self.prevemotepage.x() + diffpos[0], self.prevemotepage.y() + diffpos[1])
			self.nextemotepage.move(self.nextemotepage.x() + diffpos[0], self.nextemotepage.y() + diffpos[1])
			self.emotebar.hide()
			self.emoteToggle.clicked.connect(self.onEmoteToggle)

		self.movemenu = QtGui.QMenu()
		self.textcolormenu = QtGui.QMenu()
		self.colors = ["white", "green", "red", "orange", "blue", "yellow", "rainbow", "pink", "cyan"]
		for color in self.colors:
			self.textcolormenu.addAction(color)

		self.gameview.setupUi(_ao_app, self)
		self.scaleslider.setValue(ini.read_ini_int("data/themes/"+theme+"/theme.ini", "Theme", "scale", 1))

		self.broadcastObj = Broadcast(self.gameview.gamescene)
		self.broadcastObj.setPos(0, 64)

		self.wt_button.ind = 0
		self.ce_button.ind = 1
		self.notguilty_button.ind = 2
		self.guilty_button.ind = 3

		self.ic_input.textChanged.connect(self.ic_typing)
		self.chattext.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.chattext.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.movebtn.clicked.connect(self.onMoveButton)
		self.switchbtn.clicked.connect(self.onSwitchButton)
		self.examinebtn.clicked.connect(self.onExamineButton)
		self.evidencebtn.clicked.connect(self.onEvidenceButton)
		self.textcolorbtn.clicked.connect(self.onTextColorButton)
		self.realizationbtn.clicked.connect(self.onRealizationButton)
		self.prevemotepage.clicked.connect(self.onPrevEmotePage)
		self.nextemotepage.clicked.connect(self.onNextEmotePage)
		self.oocinput.returnPressed.connect(self.onOOCReturn)
		self.musicslider.valueChanged.connect(self.changeMusicVolume)
		self.soundslider.valueChanged.connect(self.changeSoundVolume)
		self.blipslider.valueChanged.connect(self.changeBlipVolume)
		self.scaleslider.valueChanged.connect(self.gameview.scale)
		self.walkanim_dropdown.currentIndexChanged.connect(self.changeWalkAnim)
		self.runanim_dropdown.currentIndexChanged.connect(self.changeRunAnim)
		self.wt_button.clicked.connect(self.onWTCEButton)
		self.ce_button.clicked.connect(self.onWTCEButton)
		self.notguilty_button.clicked.connect(self.onWTCEButton)
		self.guilty_button.clicked.connect(self.onWTCEButton)
		self.ooclogin.clicked.connect(self.onOOCLoginBtn)
		self.musiclist.itemDoubleClicked.connect(self.onMusicClicked)

		self.ic_input.ao_app = _ao_app

		self.realizationmenu = QtGui.QMenu()
		self.realizations = ["Disabled", "sfx-realization", "sfx-lightbulb"]
		for typ in self.realizations:
			self.realizationmenu.addAction(typ)
		
		self.emotemenu = QtGui.QMenu()
		self.emotemenuActions = [self.emotemenu.addAction("Play"), self.emotemenu.addAction("Play on chat")]
		self.emote_on_chat = -1
		self.evidence_page = 0

		self.emotebuttons = []
		spacing = 2
		x_mod_count = y_mod_count = 0
		left, top = (6, 8)
		width, height = (self.emotebar.size().width(), self.emotebar.size().height())
		columns = (width - 40) / (spacing + 40) + 1
		rows = (height - 40) / (spacing + 40) + 1
		self.max_emotes_on_page = columns * rows
		self.current_emote_page = 0
		for i in range(self.max_emotes_on_page):
			x_pos = (40 + spacing) * x_mod_count
			y_pos = (40 + spacing) * y_mod_count
			self.emotebuttons.append(buttons.AIOIndexButton(self.emotebar, i))
			self.emotebuttons[i].setGeometry(left+x_pos, top+y_pos, 40, 40)
			self.emotebuttons[i].clicked.connect(self.onEmoteClicked)
			self.emotebuttons[i].rightClicked.connect(self.onEmoteRightClicked)
			self.emotebuttons[i].show()
			x_mod_count += 1
			if x_mod_count == columns:
				x_mod_count = 0
				y_mod_count += 1

		self.musiclist.setVerticalStepsPerItem(1)
		self.musiclist.verticalScrollBar().setSingleStep(1)

		self.penaltybars = [self._penaltybar1, self._penaltybar2]
		for i in range(2):
			self.penaltybars[i].type = i
			self.penaltybars[i].setupUi(self, theme)
			self.penaltybars[i].minusClicked.connect(self.onPenaltyBarMinus)
			self.penaltybars[i].plusClicked.connect(self.onPenaltyBarPlus)

		self.wtceview = WTCEview(self.gameview)
		
		self.charselect.setupUi(self, _ao_app)
		self.charselect.charClicked.connect(self.confirmChar_clicked)
		self.disconnectbtn.clicked.connect(self.ao_app.stopGame)

		self.evidencedialog = EvidenceDialog(self, _ao_app) # use None instead of self for a separate window
		self.evidencedialog.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint)
		self.evidencedialog.move((self.size().width() - self.evidencedialog.size().width()) / 2, (self.size().height() - self.evidencedialog.size().height()) / 2)
		self.evidencedialog.setFixedSize(self.evidencedialog.size())
		self.evidencedialog.presentClicked.connect(self.onPresentButton)

		self.evidenceanim = EvidenceAnim(self.gameview, _ao_app)
		self.evidenceanim.move(32, 32)

		self.evidencebuttons = []
		spacing = 4
		x_mod_count = y_mod_count = 0
		left, top = 40, 40
		width, height = self.evidencedialog.size().width()-64, self.evidencedialog.size().height()-64
		columns = (width - 70) / (spacing + 70) + 1
		rows = (height - 70) / (spacing + 70) + 1
		self.max_evidence_on_page = columns * rows
		for i in range(self.max_evidence_on_page):
			x_pos = (70 + spacing) * x_mod_count
			y_pos = (70 + spacing) * y_mod_count
			self.evidencebuttons.append(buttons.AIOIndexButton(self.evidencedialog.evidence_list, i))
			self.evidencebuttons[i].setGeometry(left+x_pos, top+y_pos, 70, 70)
			self.evidencebuttons[i].clicked.connect(self.onEvidenceClicked)
			self.evidencebuttons[i].mouseEnter.connect(self.onEvidenceMouseEnter)
			self.evidencebuttons[i].show()
			x_mod_count += 1
			if x_mod_count == columns:
				x_mod_count = 0
				y_mod_count += 1
		self.evidencedialog.hide()

		self.chatTickTimer = QtCore.QTimer()
		self.chatTickTimer.timeout.connect(self.chatTick)

		if self.useMusicToggle: self.musiclist.raise_()
		if self.useOOCToggle: self.oocwidget.raise_()
		if self.useChatlogToggle: self.chatlog.raise_()

		self.examines = []
		self.examining = False
		self.spawned_once = False
		self.realizationsnd = BASS_StreamCreateFile(False, "data/sounds/general/sfx-realization.wav", 0, 0, 0)
		self.lightbulbsnd = BASS_StreamCreateFile(False, "data/sounds/general/sfx-lightbulb.wav", 0, 0, 0)

	def onOOCLoginBtn(self):
		password, ok = QtGui.QInputDialog.getText(self, "Login as moderator", "Enter password.")
		if password and ok:
			name = str(self.oocnameinput.text().toUtf8())
			self.ao_app.tcpthread.sendOOC(name, "/login "+password.toUtf8())
	
	def changeWalkAnim(self, ind):
		self.player.walkanims[2] = ind
	def changeRunAnim(self, ind):
		self.player.walkanims[1] = ind
    
	def onGotPing(self, ping):
		self.pinglabel.setText("Ping: %d" % ping)
	
	def changeMusicVolume(self, value):
		#print "new music volume"
		self.ao_app.musicvol = value
		if self.ao_app.music:
			BASS_ChannelSetAttribute(self.ao_app.music, BASS_ATTRIB_VOL, value / 100.0)
	
	def changeSoundVolume(self, value):
		#print "new sound volume"
		self.ao_app.sndvol = value
		if self.ao_app.sound:
			BASS_ChannelSetAttribute(self.ao_app.sound, BASS_ATTRIB_VOL, value / 100.0)
		if self.ao_app.GUIsound:
			BASS_ChannelSetAttribute(self.ao_app.GUIsound, BASS_ATTRIB_VOL, value / 100.0)
		if self.ao_app.WTCEsound:
			BASS_ChannelSetAttribute(self.ao_app.WTCEsound, BASS_ATTRIB_VOL, value / 100.0)
	
	def changeBlipVolume(self, value):
		#print "new blip volume"
		self.ao_app.blipvol = value
		if self.blip:
			BASS_ChannelSetAttribute(self.blip, BASS_ATTRIB_VOL, value / 100.0)
	
	def onPresentButton(self, ind):
		self.ao_app.playGUISound("data/sounds/general/sfx-selectblip2.wav")
		self.myevidence = ind
	
	def onPenaltyBar(self, contents):
		bar, health = contents
		self.penaltybars[bar].setHealth(health)

	def onPenaltyBarMinus(self, bar):
		self.ao_app.tcpthread.sendPenaltyBar(bar, self.penaltybars[bar].health-1)

	def onPenaltyBarPlus(self, bar):
		self.ao_app.tcpthread.sendPenaltyBar(bar, self.penaltybars[bar].health+1)

	def onWTCEMessage(self, wtcetype):
		self.wtceview.showWTCE(wtcetype)
		sounds = ["sfx-testimony2.wav", "sfx-testimony2.wav", "sfx-notguilty.wav", "sfx-guilty2.wav", "sfx-testimony.wav", "sfx-rebuttal.wav"]
		if wtcetype >= 0 and wtcetype < len(sounds):
			self.ao_app.playWTCESound("data/sounds/general/"+sounds[wtcetype])

	def onWTCEButton(self, ind):
		self.ao_app.tcpthread.sendWTCE(ind)

	def onEvidenceChanged(self, contents):
		type, zone = contents.pop(0), contents.pop(0)
		if self.player.zone != zone:
			return
		
		if type == AIOprotocol.EV_ADD:
			name, desc, image = contents
			self.ao_app.evidencelist.append([name, desc, image])
		elif type == AIOprotocol.EV_EDIT:
			ind, name, desc, image = contents
			self.ao_app.evidencelist[ind] = [name, desc, image]
		elif type == AIOprotocol.EV_DELETE:
			ind, = contents
			del self.ao_app.evidencelist[ind]
		elif type == AIOprotocol.EV_FULL_LIST:
			self.ao_app.evidencelist = contents
		
		self.set_evidence_page()
	
	def set_evidence_page(self):
		self.evidencedialog.evidenceprevpage.hide()
		self.evidencedialog.evidencenextpage.hide()
		
		total_evidence = len(self.ao_app.evidencelist)+1
		for button in self.evidencebuttons:
			button.hide()
		
		total_pages = total_evidence / self.max_evidence_on_page
		evidence_on_page = 0
		
		if total_evidence % self.max_evidence_on_page != 0:
			total_pages += 1
			if total_pages > self.evidence_page + 1:
				evidence_on_page = self.max_evidence_on_page
			else:
				evidence_on_page = total_evidence % self.max_evidence_on_page
		else:
			evidence_on_page = self.max_evidence_on_page
			
		if total_pages > self.evidence_page + 1:
			self.evidencedialog.evidencenextpage.show()
		if self.evidence_page > 0:
			self.evidencedialog.evidenceprevpage.show()
			
		for n_evidence in range(evidence_on_page):
			n_real_evidence = n_evidence + self.evidence_page * self.max_evidence_on_page
			
			if n_real_evidence == total_evidence - 1:
				self.evidencebuttons[n_evidence].setPixmap(QtGui.QPixmap("data/misc/add_evidence.png"))
				self.evidencebuttons[n_evidence].isAddButton = True
			else:
				final_file = "data/evidence/"+self.ao_app.evidencelist[n_real_evidence][2]
				if os.path.exists(final_file):
					self.evidencebuttons[n_evidence].setPixmap(QtGui.QPixmap(final_file))
				else:
					self.evidencebuttons[n_evidence].setPixmap(QtGui.QPixmap("data/evidence/unknown.png"))
				self.evidencebuttons[n_evidence].isAddButton = False
			self.evidencebuttons[n_evidence].show()
	
	def onNextEvidencePage(self):
		self.evidence_page += 1
		self.set_evidence_page()
	
	def onPrevEvidencePage(self):
		self.evidence_page -= 1
		self.set_evidence_page()
	
	def onEvidenceClicked(self, ind):
		real_ind = ind + self.evidence_page * self.max_evidence_on_page
		self.ao_app.playGUISound("data/sounds/general/sfx-evidenceshoop.wav")
		if not self.evidencebuttons[ind].isAddButton:
			self.evidencedialog.showEvidence([real_ind] + self.ao_app.evidencelist[real_ind])
		else:
			self.evidencedialog.createEvidence()
	
	def onEvidenceMouseEnter(self, ind):
		real_ind = ind + self.evidence_page * self.max_evidence_on_page
		if not self.evidencebuttons[ind].isAddButton:
			self.evidencedialog.evidencelist_name.setText(self.ao_app.evidencelist[real_ind][0])
		else:
			self.evidencedialog.evidencelist_name.setText("Add evidence...")
		self.ao_app.playGUISound("data/sounds/general/sfx-selectblip.wav")
	
	def onEvidenceButton(self):
		self.evidencedialog.setVisible(not self.evidencedialog.isVisible())
		if self.useMusicToggle: self.musiclist.hide()
		if self.useOOCToggle: self.oocwidget.hide()
		if self.useChatlogToggle: self.chatlog.hide()
		if self.useEmoteToggle:
			self.emotebar.hide()
			self.prevemotepage.hide()
			self.nextemotepage.hide()

	def toggleMusicList(self):
		self.musiclist.setVisible(not self.musiclist.isVisible())
		self.evidencedialog.hide()
		if self.useOOCToggle: self.oocwidget.hide()
		if self.useChatlogToggle: self.chatlog.hide()
		if self.useEmoteToggle:
			self.emotebar.hide()
			self.prevemotepage.hide()
			self.nextemotepage.hide()

	def onLogButton(self):
		self.chatlog.setVisible(not self.chatlog.isVisible())
		if self.useMusicToggle: self.musiclist.hide()
		if self.useOOCToggle: self.oocwidget.hide()
		self.evidencedialog.hide()
		if self.useEmoteToggle:
			self.emotebar.hide()
			self.prevemotepage.hide()
			self.nextemotepage.hide()
	
	def onOOCButton(self):
		self.oocwidget.setVisible(not self.oocwidget.isVisible())
		if self.useMusicToggle: self.musiclist.hide()
		if self.useChatlogToggle: self.chatlog.hide()
		self.evidencedialog.hide()
		if self.useEmoteToggle:
			self.emotebar.hide()
			self.prevemotepage.hide()
			self.nextemotepage.hide()

	def onEmoteToggle(self):
		vis = not self.emotebar.isVisible()
		self.emotebar.setVisible(vis)
		if self.showPrevEmotes: self.prevemotepage.setVisible(vis)
		if self.showNextEmotes: self.nextemotepage.setVisible(vis)
		self.oocwidget.hide()
		self.musiclist.hide()
		self.chatlog.hide()
		self.evidencedialog.hide()

	def onChatBubble(self, contents):
		cid, on = contents
		if not self.gameview.characters.has_key(cid):
			return
		if self.gameview.characters[cid].zone != self.player.zone:
			self.gameview.characters[cid].chatbubble = 0
			return
		
		self.gameview.characters[cid].setChatBubble(on)
	
	def onBroadcast(self, contents):
		zone, message = contents
		if zone != -1 and self.player.zone != zone:
			return
		
		self.broadcastObj.showText(message.decode("utf-8"))
	
	def onOOCReturn(self):
		name = str(self.oocnameinput.text().toUtf8())
		text = str(self.oocinput.text().toUtf8())
		if name and text:
			self.oocinput.clear()
			if text.lower() == "/moonwalk": # don't tell anyone this exists...
				self.player.moonwalk = not self.player.moonwalk
				if self.player.moonwalk:
					self.oocchat.append("you know i'm bad, i'm bad")

			elif text.lower() == "/to_infinity": # infinite camera
				self.infinite_cam = not self.infinite_cam
				if self.infinite_cam: self.oocchat.append("...AND BEYOND!")
            
			elif text.lower() == "/area": # coming from AO?
				self.onMoveButton()

			elif text.startswith("/code "): # execute piece of code
				exec text.replace("/code ", "", 1).replace("\\N", "\n")

			else:
				self.ao_app.tcpthread.sendOOC(name, text)
	
	def onICMessage(self, contents):
		name, chatmsg, blip, zone, color, realization, clientid, evidence = contents
		if zone != self.player.zone:
			return

		if not self.finished_chat and self.gameview.characters.has_key(self.m_chatClientID): # talking player was interrupted, rude
			self.gameview.characters[self.m_chatClientID].setChatBubble(0)
		if self.gameview.characters.has_key(clientid):
			self.gameview.characters[clientid].setChatBubble(2)
		
		if clientid == self.ao_app.player_id: # your message arrived.
			self.message_id = random.randint(100000000, 999999999)
			self.ic_input.clear()
			if self.chatbubbletimer.isActive(): self.chatbubbletimer.stop()
			if self.myrealization != 0:
				self.myrealization = 0
				self.realizationbtn.setPixmap(self.realizationbtn_off)
			if self.myevidence >= 0: self.myevidence = -1
			if self.emote_on_chat >= 0: self.onEmoteClicked(self.emote_on_chat)
		
		evidence -= 1
		name = name.replace("<", "&lt;").replace(">", "&gt;").decode("utf-8")
		self.m_chatmsg = chatmsg.decode("utf-8")
		self.m_chatClientID = clientid

		char_id = 0 if not self.gameview.characters.has_key(clientid) else self.gameview.characters[clientid].charid
		printname = self.ao_app.charlist[char_id] + (" ["+name+"]" if self.ao_app.charlist[char_id] != name else "")
		msg = "<b>%s:</b> %s" % (printname, self.m_chatmsg.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br />"))
		if evidence >= 0:
			msg += "<br /><b>"+printname+"</b> presented an evidence: "
			try:
				msg += self.ao_app.evidencelist[evidence][0]
			except:
				msg += "NULL (%d)" % evidence
			
			try:
				filename = "data/evidence/"+self.ao_app.evidencelist[evidence][2]
			except:
				filename = "data/evidence/unknown.png"
			
			if not os.path.exists(filename):
				filename = "data/evidence/unknown.png"
			
			self.evidenceanim.showAnim(filename)
		else:
			if self.evidenceanim.isVisible():
				self.evidenceanim.hideAnim()
		
		self.finished_chat = False
		self.m_color = color
		self.chatlog.append(msg)
		
		if self.blip:
			BASS_StreamFree(self.blip)
		self.blip = BASS_StreamCreateFile(False, "data/sounds/general/sfx-blip"+blip+".wav", 0, 0, 0)
		BASS_ChannelSetAttribute(self.blip, BASS_ATTRIB_VOL, self.ao_app.blipvol / 100.0)
		
		self.chattext.clear()
		self.chatname.setText(name)
		self.chattext.setStyleSheet("background-color: rgba(0, 0, 0, 0);\ncolor: "+QtGui.QColor(color).name())
		
		if len(self.m_chatmsg) >= 2:
			self.message_is_centered = self.m_chatmsg.startswith("~~")
		else:
			self.chattext.setAlignment(QtCore.Qt.AlignLeft)
		
		if realization == 1:
			BASS_ChannelPlay(self.realizationsnd, True)
		elif realization == 2:
			BASS_ChannelPlay(self.lightbulbsnd, True)
		
		self.inline_color_stack = []
		self.tick_pos = 0
		self.blip_pos = 0
		self.inline_blue_depth = 0
		self.current_display_speed = 3
		self.chatTickTimer.start(self.message_display_speed[self.current_display_speed])
	
	def chatTick(self):
		self.chatTickTimer.stop()
		formatting_char = False
		
		if self.message_is_centered:
			self.m_chatmsg = self.m_chatmsg.strip("~~")
		
		if self.tick_pos >= len(self.m_chatmsg) and not self.finished_chat:
			self.finished_chat = True
			if self.gameview.characters.has_key(self.m_chatClientID):
				self.gameview.characters[self.m_chatClientID].setChatBubble(0)
		else:
			f_character2 = self.m_chatmsg[self.tick_pos]
			f_character = QtCore.QString(f_character2)
			
			if f_character == " " or f_character == "<" or f_character == "\n" or f_character == "\r":
				self.chattext.insertPlainText(f_character)
			
			elif f_character == "\\" and not self.next_character_is_not_special:
				self.next_character_is_not_special = True
				formatting_char = True
			
			elif f_character == "{" and not self.next_character_is_not_special:
				self.current_display_speed += 1
				formatting_char = True
			
			elif f_character == "}" and not self.next_character_is_not_special:
				self.current_display_speed -= 1
				formatting_char = True
			
			elif f_character == "|" and not self.next_character_is_not_special: #orange.
				if self.inline_color_stack:
					if self.inline_color_stack[-1] == INLINE_ORANGE:
						del self.inline_color_stack[-1]
					else:
						self.inline_color_stack.append(INLINE_ORANGE)
				else:
					self.inline_color_stack.append(INLINE_ORANGE)
				formatting_char = True
			
			elif f_character == "(" and not self.next_character_is_not_special: #blue.
				self.inline_color_stack.append(INLINE_BLUE)
				self.chattext.insertHtml("<font color=\"" + getColor(4).name() + "\">" + f_character + "</font>")
				
				self.inline_blue_depth += 1
			
			elif f_character == ")" and not self.next_character_is_not_special and self.inline_color_stack:
				if self.inline_color_stack[-1] == INLINE_BLUE:
					del self.inline_color_stack[-1]
					self.chattext.insertHtml("<font color=\"" + getColor(4).name() + "\">" + f_character + "</font>")
					
					if self.inline_blue_depth > 0:
						self.inline_blue_depth -= 1
						
				else:
					self.next_character_is_not_special = True
					self.tick_pos -= 1
			
			elif f_character == "[" and not self.next_character_is_not_special: #gray.
				self.inline_color_stack.append(INLINE_GRAY)
				self.chattext.insertHtml("<font color=\"" + getColor("_inline_grey").name() + "\">" + f_character + "</font>")
			
			elif f_character == "]" and not self.next_character_is_not_special and self.inline_color_stack:
				if self.inline_color_stack[-1] == INLINE_GRAY:
					del self.inline_color_stack[-1]
					self.chattext.insertHtml("<font color=\"" + getColor("_inline_grey").name() + "\">" + f_character + "</font>")
				else:
					self.next_character_is_not_special = True
					self.tick_pos -= 1
			
			elif f_character == "`" and not self.next_character_is_not_special: #green.
				if self.inline_color_stack:
					if self.inline_color_stack[-1] == INLINE_GREEN:
						del self.inline_color_stack[-1]
						formatting_char = True
					else:
						self.inline_color_stack.append(INLINE_GREEN)
						formatting_char = True
				else:
					self.inline_color_stack.append(INLINE_GREEN)
					formatting_char = True
			
			else:
				self.next_character_is_not_special = False
				if self.inline_color_stack:
					top_color = self.inline_color_stack[-1]
					if top_color == INLINE_ORANGE:
						self.chattext.insertHtml("<font color=\"" + getColor(3).name() + "\">" + f_character + "</font>")
					elif top_color == INLINE_BLUE:
						self.chattext.insertHtml("<font color=\"" + getColor(4).name() + "\">" + f_character + "</font>")
					elif top_color == INLINE_GREEN:
						self.chattext.insertHtml("<font color=\"" + getColor(1).name() + "\">" + f_character + "</font>")
					elif top_color == INLINE_GRAY:
						self.chattext.insertHtml("<font color=\"" + getColor("_inline_grey").name() + "\">" + f_character + "</font>")
					else:
						self.chattext.insertHtml(f_character)
				else:
					if self.m_color == 691337: #rainbow. yes, yes, i know, silly value.
						if self.rainbow_counter == 0:
							html_color = getColor(2).name() #red
						elif self.rainbow_counter == 1:
							html_color = getColor(3).name() #orange
						elif self.rainbow_counter == 2:
							html_color = getColor(5).name() #yellow
						elif self.rainbow_counter == 3:
							html_color = getColor(1).name() #green
						else:
							html_color = getColor(4).name() #blue
							self.rainbow_counter = -1
						
						self.rainbow_counter += 1
						self.chattext.insertHtml("<font color=\"" + html_color + "\">" + f_character + "</font>")
					else:
						self.chattext.insertHtml(f_character)
				
				if self.message_is_centered:
					self.chattext.setAlignment(QtCore.Qt.AlignCenter)
				else:
					self.chattext.setAlignment(QtCore.Qt.AlignLeft)
			
			if self.m_chatmsg[self.tick_pos] != " ":
				if self.blip_pos % self.blip_rate == 0 and not formatting_char:
					self.blip_pos = 0
					BASS_ChannelPlay(self.blip, True)
					
				self.blip_pos += 1
			
			self.tick_pos += 1
			
			if self.current_display_speed < 0:
				self.current_display_speed = 0
			elif self.current_display_speed > 6:
				self.current_display_speed = 6
			
			if formatting_char:
				self.chatTickTimer.start(1)
			else:
				self.chatTickTimer.start(self.message_display_speed[self.current_display_speed])
	
	def onOOCMessage(self, contents):
		name, text = contents
		
		dank_url_regex = QtCore.QRegExp("\\b(https?://\\S+\\.\\S+)\\b")
		text = QtCore.QString(text).replace("<", "&lt;").replace(">", "&gt;").replace(dank_url_regex, "<a href='\\1'>\\1</a>").replace("\n", "<br />")
		
		name = name.replace("<", "&lt;").replace(">", "&gt;")
		self.oocchat.append("<b>"+name+":</b> "+text)
	
	def onPrevEmotePage(self):
		self.current_emote_page -= 1
		self.set_emote_page()
		
	def onNextEmotePage(self):
		self.current_emote_page += 1
		self.set_emote_page()
	
	def onRealizationButton(self):
		selection = self.realizationmenu.exec_(QtGui.QCursor.pos())
		if selection:
			for i in range(len(self.realizationmenu.actions())):
				if selection == self.realizationmenu.actions()[i]:
					if i != 0:
						self.realizationbtn.setPixmap(self.realizationbtn_on)
					else:
						self.realizationbtn.setPixmap(self.realizationbtn_off)
					self.myrealization = i
	
	def onTextColorButton(self):
		selection = self.textcolormenu.exec_(QtGui.QCursor.pos())
		if selection:
			for i in range(len(self.textcolormenu.actions())):
				if selection == self.textcolormenu.actions()[i]:
					self.mychatcolor = i
	
	def onMoveButton(self):
		selection = self.movemenu.exec_(QtGui.QCursor.pos())
		if selection:
			for i in range(len(self.movemenu.actions())):
				if selection == self.movemenu.actions()[i]:
					self.ao_app.tcpthread.setZone(i)
	
	def onExaminePacket(self, contents):
		char_id, zone, x, y, showname = contents
		if zone != self.player.zone: return
		showname = showname.decode("utf-8")

		printname = self.ao_app.charlist[char_id] + (" ["+showname+"]" if showname else "")
		self.examines.append(ExamineObj(printname, x, y, self.gameview.gamescene))
	
	def onExamineButton(self, clicked_inGame=False):
		if self.examining:
			if not clicked_inGame:
				self.ao_app.playGUISound("data/sounds/general/sfx-cancel.wav")
			else:
				self.ao_app.playGUISound("data/sounds/general/sfx-selectblip2.wav")
			self.gameview.gamescene.removeItem(self.examiner)
			del self.examiner
		else:
			self.ao_app.playGUISound("data/sounds/general/sfx-selectblip2.wav")
			self.examiner = ExamineCross(self.gameview, self.gameview.gamescene)
		self.examining = not self.examining
	
	def onSwitchButton(self):
		self.ao_app.tcpthread.setChar(-1)
	
	def showCharSelect(self):
		self.IngameWidgets.setCurrentWidget(self.charselect)
		if self.useMusicToggle: self.musiclist.hide()
		if self.useOOCToggle: self.oocwidget.hide()
		if self.useEmoteToggle:
			self.emotebar.hide()
			self.prevemotepage.hide()
			self.nextemotepage.hide()
		self.evidencedialog.hide()

	def onEmoteSound(self, contents):
		char_id, filename, delay, zone = contents
		self.aSound = ["data/sounds/general/"+filename+".wav", time.time()*1000 + delay, zone]

	def onEmoteRightClicked(self, ind):
		selection = self.emotemenu.exec_(QtGui.QCursor.pos())
		if selection:
			if selection == self.emotemenu.actions()[0]: # play normally
				self.onEmoteClicked(ind)
			else: # play on chat
				self.emote_on_chat = ind
	
	def onEmoteClicked(self, ind):
		self.emote_on_chat = -1

		real_ind = ind + self.current_emote_page * self.max_emotes_on_page
		self.player.emoting = 1
		self.player.currentemote = real_ind
		
		emote = self.player.emotes[0][real_ind]
		loop = self.player.emotes[1][real_ind]
		emotedir = self.player.emotes[2][real_ind]
		sound = random.choice(self.player.emotes[3][real_ind])
		sound_delay = self.player.emotes[4][real_ind]
		
		found_dir = ""
		for dir in emotedir:
			if getDirection(self.player.dir_nr) == dir:
				found_dir = dir
		if not found_dir:
			found_dir = getCompactDirection(self.player.dir_nr)

		self.player.dir_nr = directions.index(found_dir)
		offset = self.player.emotes[5][real_ind][found_dir] if found_dir in self.player.emotes[5][real_ind] else [0,0]

		filename = "data/characters/"+self.ao_app.charlist[self.player.charid]+"/"+self.player.charprefix+emote+found_dir+".gif"
		self.player.sprite = self.ao_app.charlist[self.player.charid]+"/"+emote+found_dir+".gif"

		if sound:
			self.onEmoteSound([self.player.charid, sound, sound_delay, self.player.zone])
			self.ao_app.tcpthread.sendEmoteSound(sound, sound_delay)
		
		self.player.play(filename, loop, offset)
	
	def set_emote_page(self):
		# these two are for if a theme uses emote_toggle
		self.showPrevEmotes = False
		self.showNextEmotes = False

		self.prevemotepage.hide()
		self.nextemotepage.hide()
		
		total_emotes = ini.read_ini_int("data/characters/"+self.ao_app.charlist[self.player.charid]+"/char.ini", "Emotions", "total")
		for button in self.emotebuttons:
			button.hide()
		
		total_pages = total_emotes / self.max_emotes_on_page
		emotes_on_page = 0
		if total_emotes % self.max_emotes_on_page != 0:
			total_pages += 1
			if total_pages > self.current_emote_page + 1:
				emotes_on_page = self.max_emotes_on_page
			else:
				emotes_on_page = total_emotes % self.max_emotes_on_page
		else:
			emotes_on_page = self.max_emotes_on_page
		if total_pages > self.current_emote_page + 1:
			if self.emotebar.isVisible(): self.nextemotepage.show()
			self.showNextEmotes = True
		if self.current_emote_page > 0:
			if self.emotebar.isVisible(): self.prevemotepage.show()
			self.showPrevEmotes = True
		for n_emote in range(emotes_on_page):
			n_real_emote = n_emote + self.current_emote_page * self.max_emotes_on_page
			self.emotebuttons[n_emote].setPixmap(QtGui.QPixmap("data/characters/"+self.ao_app.charlist[self.player.charid]+"/buttons/"+str(n_real_emote+1)+".png"))
			self.emotebuttons[n_emote].show()

		if not self.useEmoteToggle:
			self.prevemotepage.setVisible(self.showPrevEmotes)
			self.nextemotepage.setVisible(self.showNextEmotes)
	
	def onMusicChange(self, msg):
		filename, char_id, showname = msg
		showname = showname.decode("utf-8")

		if char_id > -1:
			name = self.ao_app.charlist[char_id] + (" ["+showname+"]" if showname else "")
			name2 = showname if showname else self.ao_app.charlist[char_id]
			self.chatlog.append("<b>%s</b> changed the music to %s" % (name, filename.replace("<", "&#60;").replace(">", "&#62;")))
			self.broadcastObj.showText("%s played song %s" % (name2, filename))
		else:
			self.chatlog.append("The music was changed to %s" % filename.replace("<", "&#60;").replace(">", "&#62;"))
			self.broadcastObj.showText("The music was changed to %s" % filename)

		self.ao_app.playMusic(filename)
	
	def onPlayerCreate(self, contents):
		player, char, zone = contents
		if self.gameview.characters.has_key(player):
			return

		self.gameview.initCharacter(player)
		self.gameview.characters[player].changeChar(char)
		self.gameview.characters[player].zone = zone
	
	def onPlayerDestroy(self, player):
		if player in self.gameview.characters: self.gameview.deleteCharacter(player)

	def onPlayerZone(self, contents):
		client, zone = contents
		if not self.gameview.characters.has_key(client):
			return
		
		self.gameview.characters[client].zone = zone
		if client == self.ao_app.player_id:
			self.setZone(zone)
		else:
			if zone == self.player.zone:
				self.onChatBubble([client, self.gameview.characters[client].chatbubble])
			else:
				self.onChatBubble([client, 0])
	
	def onPlayerChar(self, contents):
		client, char = contents
		if not self.gameview.characters.has_key(client):
			return
		
		if client == self.ao_app.player_id: # pogYou
			self.player.changeChar(char)
			if char == -1: # booted to character selection
				self.showCharSelect()
			else:
				walk = self.player.walkanims[2]
				run = self.player.walkanims[1]
				self.walkanim_dropdown.clear()
				self.runanim_dropdown.clear()
				self.walkanim_dropdown.addItems(self.player.walkanims[0])
				self.runanim_dropdown.addItems(self.player.walkanims[0])
				self.walkanim_dropdown.setCurrentIndex(walk)
				self.runanim_dropdown.setCurrentIndex(run)
				self.current_emote_page = 0
				self.set_emote_page()
				self.hideCharSelect()
				if not self.spawned_once:
					inipath = "data/zones/"+self.ao_app.zonelist[self.player.zone][0]+".ini"
					x, y = ini.read_ini(inipath, "Game", "spawn", "0,0").split(",")
					self.player.moveReal(float(x), float(y))
					self.spawned_once = True

				self.showname_input.setPlaceholderText(self.ao_app.charlist[char])
		else:
			self.gameview.characters[client].changeChar(char)
	
	def onMovementPacket(self, contents):
		for move in contents:
			client, x, y, hspeed, vspeed, sprite, emoting, dir_nr, currentemote = move
			if not self.gameview.characters.has_key(client):
				continue

			char = self.gameview.characters[client]
			if not char.isPlayer and char.smoothmoves <= 0:
				char.hspeed = (x - char.xx) / (3 * (self.ao_app.fps / 30.))
				char.vspeed = (y - char.yy) / (3 * (self.ao_app.fps / 30.))
			char.sprite = sprite

			if self.player:
				if char.zone != self.player.zone:
					char.hide()
				else:
					char.show()
					aSprite = sprite.split("\\" if "\\" in sprite else "/")
					if len(aSprite) < 2:
						continue
					oldpath = char.movie.fileName()
					fullpath = "data/characters/"+aSprite[0]+"/"+char.charprefix+aSprite[1]
					if not os.path.exists(fullpath):
						fullpath = "data/misc/error.gif"

					if oldpath != fullpath or char.dir_nr != dir_nr or char.emoting != emoting: # "The other player's game sometimes fails to show the right direction the character's looking at." fixed
						char.dir_nr = dir_nr
						char.emoting = emoting
						if aSprite[1].lower() == "spin.gif":
							char.playSpin(fullpath, dir_nr)
						else:
							#print currentemote, char.sprite, len(char.emotes[5]), len(char.emotes[2])
							offset = char.emotes[5][currentemote][getDirection(dir_nr)] if currentemote >= 0 and currentemote < len(char.emotes[5]) and getDirection(dir_nr) in char.emotes[5][currentemote] else [0,0]
							if emoting == 0 or emoting == 1:
								char.play(fullpath, True, offset)
							else:
								char.playLastFrame(fullpath, offset)
	
	def onMusicClicked(self, item):
		self.ao_app.tcpthread.sendMusicChange(item.text().toUtf8(), str(self.showname_input.text().toUtf8()))
	
	def setZone(self, ind):
		if self.player.zone != ind:
			if self.evidenceanim.isVisible():
				self.evidenceanim.hideAnim()
		
		self.player.zone = ind
		zone = "data/zones/"+self.ao_app.zonelist[ind][0]
		self.gameview.setBackground(zone)
		
		for examine in self.examines:
			self.gameview.gamescene.removeItem(examine)
			examine.startToFadeTimer.stop()
			examine.opacityTimer.stop()
		self.examines = []
		
		inipath = zone+".ini"
		x, y = ini.read_ini(inipath, "Game", "spawn", "0,0").split(",")
		if self.spawned_once:
			self.player.moveReal(float(x), float(y))
		
		walls = QtGui.QImage(zone+"_solids.png")
		self.gameview.zonewalls.setPixmap(QtGui.QPixmap.fromImage(walls.scaled(walls.width()*2, walls.height()*2)))
		
		for fg in self.gameview.zoneforegrounds:
			self.gameview.gamescene.removeItem(fg[0])
			
		self.gameview.zoneforegrounds = []
		for i in range(ini.read_ini_int(inipath, "Background", "foregrounds")):
			file = ini.read_ini(inipath, "Background", str(i+1))
			fg_x = ini.read_ini_float(inipath, "Background", str(i+1)+"_x")
			fg_y = ini.read_ini_float(inipath, "Background", str(i+1)+"_y")
			fg_image = QtGui.QImage(zone+"_"+file+".png")
			
			self.gameview.zoneforegrounds.append([QtGui.QGraphicsPixmapItem(scene=self.gameview.gamescene), fg_x, fg_y])
			self.gameview.zoneforegrounds[i][0].setPixmap(QtGui.QPixmap.fromImage(fg_image.scaled(fg_image.width()*2, fg_image.height()*2)))
			self.gameview.zoneforegrounds[i][0].setOffset(0, -fg_image.height()*2)
			self.gameview.zoneforegrounds[i][0].setZValue(fg_y)
	
	def confirmChar_clicked(self, selection):
		self.ao_app.tcpthread.setChar(selection)
		
	def hideCharSelect(self):
		self.IngameWidgets.setCurrentWidget(self.IngameUI)
	
	def ic_typing(self):
		if self.ic_input.text():
			if self.chatbubbletimer.isActive():
				self.chatbubbletimer.stop()
			self.chatbubbletimer.start(5000)
		
			if not self.player.chatbubble:
				self.ao_app.tcpthread.sendChatBubble(1)
				self.player.chatbubble = 1
	
	def ic_return(self):
		text = str(self.ic_input.text().toUtf8())[:256+64]
		showname = str(self.showname_input.text().toUtf8())

		if self.mychatcolor != 6: #rainbow.
			color = getColor(self.mychatcolor).rgb()
		else:
			color = 691337

		if text and self.finished_chat and self.ic_delay == 0:
			self.ao_app.tcpthread.sendIC(text, self.player.blip, color, self.myrealization, self.myevidence+1, showname, self.message_id)
			self.ic_delay = 3
	
	def timerEvent(self, event):
		if not self.playing:
			self.testtimer.stop()
			self.tcptimer.stop()
		
		if event.timerId() == self.testtimer.timerId(): # game
			self.updateGame()
		elif event.timerId() == self.tcptimer.timerId(): # networking
			self.ticks += 1
			if self.ticks % 10 == 0: # send movement
				self.ao_app.tcpthread.sendMovement(self.player.xx, self.player.yy, self.player.hspeed, self.player.vspeed, self.player.sprite, self.player.emoting, self.player.dir_nr, self.player.currentemote)
			if self.ticks % (60*3) == 0: # ping
				self.ao_app.tcpthread.sendPing()

	def examineSpot(self, pos):
		self.ao_app.tcpthread.sendExamine(pos.x(), pos.y(), str(self.showname_input.text().toUtf8()))
		self.onExamineButton(True)

	def mousePressEvent(self, event):
		super(GameWidget, self).mousePressEvent(event)
		focused_widget = self.childAt(event.pos())
		if isinstance(focused_widget, QtGui.QLineEdit):
			focused_widget.clearFocus()
		elif focused_widget != self.musiclist and self.useMusicToggle and self.musiclist.isVisible():
			self.musiclist.hide()
		elif focused_widget != self.chatlog and self.useChatlogToggle and self.chatlog.isVisible():
			self.chatlog.hide()
		elif focused_widget not in (self.evidencedialog.evidence_list, self.evidencedialog.evidence_editor) and self.evidencedialog.isVisible():
			self.evidencedialog.hide()
		elif focused_widget not in (self.oocwidget, self.oocchat, self.oocinput, self.oocnameinput) and self.useOOCToggle and self.oocwidget.isVisible():
			self.oocwidget.hide()
		elif focused_widget not in (self.emotebar,) and self.useEmoteToggle and self.emotebar.isVisible():
			self.onEmoteToggle() # hide
	
	def updateGame(self):
		if self.ic_delay > 0:
			self.ic_delay -= 1
		if self.ic_input.enter_pressed:
			self.ic_return()
		
		viewX, viewY = self.gameview.getViewCoords(self.infinite_cam)
		zoneamount = [0 for i in self.ao_app.zonelist]
		for char in self.gameview.characters.values():
			if char.zone >= 0 and char.zone < len(zoneamount):
				zoneamount[char.zone] += 1
			
			char.update(viewX, viewY)
		self.gameview.moveView(viewX, viewY)
		self.areainfo.setText("Zone %d: %s (%d %s)" % (self.player.zone, self.ao_app.zonelist[self.player.zone][1], zoneamount[self.player.zone], plural("player", zoneamount[self.player.zone])))
		for i in range(len(self.movemenuActions)):
			self.movemenuActions[i].setText(str(i)+": "+self.ao_app.zonelist[i][1]+" ("+plural("%d player" % (zoneamount[i]), zoneamount[i])+")")
		
		if self.examining:
			clickpoint = self.gameview.mapFromGlobal(QtGui.QCursor.pos())
			remapped = self.gameview.gameview.mapFromParent(clickpoint)
			self.examiner.setPos(self.gameview.gameview.mapToScene(remapped))
			self.examiner.show()
		
		if self.aSound[1] > -1 and self.aSound[2] == self.player.zone: # "An SFX, that a player makes in any area, plays everywhere, in every other and its' own area." fixed
			if time.time()*1000 >= self.aSound[1]: # milliseconds
				self.ao_app.playSound(self.aSound[0])
				self.aSound[1] = -1
		
		if self.examines:
			for examine in self.examines:
				examine.setPos(self.gameview.zonebackground.mapToScene(examine.xx, examine.yy))
				examine.show()
			if self.examines[0].opacity() <= 0:
				self.gameview.gamescene.removeItem(self.examines[0])
				del self.examines[0]
	
	def startGame(self):
		self.ic_delay = 0
		self.ic_input.enter_pressed = False
		self.message_id = random.randint(100000000, 999999999)
		self.finished_chat = True
		self.myevidence = -1
		self.oocchat.clear()
		self.chatlog.clear()
		self.chatname.clear()
		self.chattext.clear()
		self.musiclist.clear()
		self.movemenu.clear()
		self.movemenuActions = []
		self.charselect.showCharList(self.ao_app.charlist)
        
		self.musicslider.setValue(self.ao_app.musicvol)
		self.soundslider.setValue(self.ao_app.sndvol)
		self.blipslider.setValue(self.ao_app.blipvol)

		aFont = QtGui.QFont("Tahoma", 8)
		
		for i in range(len(self.ao_app.zonelist)):
			self.movemenuActions.append(self.movemenu.addAction(str(i)+": "+self.ao_app.zonelist[i][1]))
		
		for music in self.ao_app.musiclist:
			item = QtGui.QListWidgetItem()
			item.setFont(aFont)
			item.setText(music)
			if os.path.exists("data/sounds/music/"+music):
				item.setBackgroundColor(QtGui.QColor(128, 255, 128))
			else:
				item.setBackgroundColor(QtGui.QColor(255, 96, 96))
			self.musiclist.addItem(item)
		
		self.set_evidence_page()
		
		QtGui.QMessageBox.information(self, "Server Message Of The Day", self.ao_app.motd)
		
		self.oocnameinput.setText(ini.read_ini("aaio.ini", "General", "OOC name"))
		if not self.oocnameinput.text() or self.oocnameinput.text().startsWith("Player "):
			self.oocnameinput.setText("Player %d" % self.ao_app.player_id)

		if not self.showname_input.text():
			self.showname_input.setText(ini.read_ini("aaio.ini", "General", "Showname"))

		self.gameview.initCharacter(self.ao_app.player_id)
		self.player = self.gameview.characters[self.ao_app.player_id]
		self.setZone(self.ao_app.defaultzoneid)
		self.player.setPlayer(True)
		self.testtimer.start(1000./self.ao_app.fps, self)
		self.tcptimer.start(1./60 * 1000, self) # ticks 1/60 per sec
		self.ticks = 0
		self.playing = True
        
		self.showCharSelect()
	
	def stopGame(self):
		self.ic_input.enter_pressed = False
		if not self.playing:
			return
		
		for i in self.gameview.characters.keys():
			self.gameview.deleteCharacter(i)

		self.testtimer.stop()
		self.tcptimer.stop()
		self.playing = False

class EvidenceDialog(QtGui.QWidget):
	presentClicked = QtCore.pyqtSignal(int)
	def __init__(self, parent, ao_app):
		super(EvidenceDialog, self).__init__(parent)
		self.ao_app = ao_app

		theme = ini.read_ini("aaio.ini", "General", "Theme", "default")
		uic.loadUi("data/themes/"+theme+"/court_record.ui", self)

		self.myevidencefolder = os.path.abspath("data/evidence").replace("\\", "/")
		self.evidencepicture.setStyleSheet("color: black")
		self.evidenceeditor_name.textChanged.connect(self.changesMade)
		self.evidencepicture.clicked.connect(self.changePicture)
		self.evidencedesc.textChanged.connect(self.changesMade)
		self.evidenceclose.clicked.connect(self.closeDialog)
		self.savechanges.clicked.connect(self.saveChanges)
		self.deletebtn.clicked.connect(self.deleteEvidence)
		self.presentbtn.clicked.connect(self.onPresentButton)

		imgfiles = os.listdir("data/evidence")
		self.imgfiles = []
		for file in imgfiles:
			if file.lower().endswith(".png") and file.lower() != "unknown.png":
				self.imgfiles.append(file)

		self.savechanges.hide()
		self.hide()
	
	def changesMade(self, *args, **kwargs):
		if not self.isVisible():
			return
		self.savechanges.show()
	
	def onPresentButton(self):
		self.presentClicked.emit(self.ind)
		self.stackedWidget.setCurrentWidget(self.evidence_list)
		self.hide()
	
	def closeDialog(self, playSnd=True):
		if playSnd:
			self.ao_app.playGUISound("data/sounds/general/sfx-cancel.wav")
		self.savechanges.hide()
		self.deletebtn.hide()
		self.stackedWidget.setCurrentWidget(self.evidence_list)
	
	def changePicture(self):
		if not self.isVisible():
			return

		file = str(QtGui.QFileDialog.getOpenFileName(self, "Select evidence image", "data/evidence", "Images (*.jpg *.png *.gif *.bmp)").toUtf8())
		if file:
			folder, filename = os.path.split(file)
			folder = folder.replace("\\", "/")
			if not folder.startswith(self.myevidencefolder):
				QtGui.QMessageBox.critical(self, "Evidence image", "You can't select evidence images outside of the evidence folder.")
				return
			self.evidencepicname.setText(filename)
			self.evidencepicture.setPixmap(QtGui.QPixmap(file))
			self.changesMade()
	
	def saveChanges(self):
		name, desc, image = str(self.evidenceeditor_name.text().toUtf8()), str(self.evidencedesc.toPlainText().toUtf8()), str(self.evidencepicname.text().toUtf8())
		if not name: return

		if not self.creatingEvidence:
			self.ao_app.tcpthread.sendEvidence(AIOprotocol.EV_EDIT, self.ind, name, desc, image)
		else:
			self.ao_app.tcpthread.sendEvidence(AIOprotocol.EV_ADD, name, desc, image)
			self.stackedWidget.setCurrentWidget(self.evidence_list)
		self.savechanges.hide()
	
	def deleteEvidence(self):
		self.ao_app.tcpthread.sendEvidence(AIOprotocol.EV_DELETE, self.ind)
		self.savechanges.hide()
		self.deletebtn.hide()
		self.stackedWidget.setCurrentWidget(self.evidence_list)
	
	def showEvidence(self, ev):
		self.ind, name, desc, image = ev
		self.evidenceeditor_name.setText(name)
		self.evidencedesc.setPlainText(desc)

		self.evidencepicname.setText(image)
		if os.path.exists("data/evidence/"+image):
			self.evidencepicture.setPixmap(QtGui.QPixmap("data/evidence/"+image))
		else:
			self.evidencepicture.setPixmap(QtGui.QPixmap("data/evidence/unknown.png"))
		
		self.creatingEvidence = False
		self.deletebtn.show()
		self.presentbtn.show()
		self.savechanges.hide()
		self.stackedWidget.setCurrentWidget(self.evidence_editor)
	
	def createEvidence(self):
		self.evidenceeditor_name.clear()
		self.evidencedesc.clear()
		self.evidencepicname.setText("empty.png")
		self.evidencepicture.setPixmap(QtGui.QPixmap("data/evidence/empty.png"))
		self.creatingEvidence = True
		self.presentbtn.hide()
		self.deletebtn.hide()
		self.savechanges.hide()
		self.stackedWidget.setCurrentWidget(self.evidence_editor)

	def setVisible(self, visible):
		super(EvidenceDialog, self).setVisible(visible)
		self.stackedWidget.setCurrentWidget(self.evidence_list)
		self.evidencelist_name.clear()

	def hide(self):
		super(EvidenceDialog, self).hide()
		self.stackedWidget.setCurrentWidget(self.evidence_list)

	def show(self):
		super(EvidenceDialog, self).show()
		self.evidencelist_name.clear()


class EvidenceAnim(QtGui.QLabel):
	def __init__(self, parent, ao_app):
		super(EvidenceAnim, self).__init__(parent)
		self.ao_app = ao_app
		
		self.animTimer = QtCore.QTimer(self)
		self.animTimer.timeout.connect(self.animTimeout)
		self.animType = 0
		
		self.maxSize = QtCore.QSize(70, 70)
		self.minSize = QtCore.QSize(0, 0)
		self.resize(0, 0)
		self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignLeft)
		self.hide()
	
	def animTimeout(self):
		if self.animType == 0:
			if self.size() == self.maxSize:
				self.animTimer.stop()
				return
			self.resize(self.size().width() + 10, self.size().height() + 10)
		elif self.animType == 1:
			if self.size() == self.minSize:
				self.animTimer.stop()
				self.hide()
				return
			self.resize(self.size().width() - 10, self.size().height() - 10)
	
	def showAnim(self, image):
		self.setPixmap(QtGui.QPixmap(image))
		self.ao_app.playGUISound("data/sounds/general/sfx-evidenceshoop.wav")
		self.show()
		self.animType = 0
		self.animTimer.start(35)
	
	def hideAnim(self):
		self.animType = 1
		self.animTimer.start(35)
