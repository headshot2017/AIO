from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os, ini

class AIOButton(QLabel):
	clicked = pyqtSignal()
	rightClicked = pyqtSignal()
	def __init__(self, parent=None):
		QLabel.__init__(self, parent)

	def mousePressEvent(self, ev):
		if ev.buttons() == Qt.LeftButton:
			self.clicked.emit()
		elif ev.buttons() == Qt.RightButton:
			self.rightClicked.emit()

class AIOIndexButton(QLabel):
	clicked = pyqtSignal(int)
	rightClicked = pyqtSignal(int)
	mouseEnter = pyqtSignal(int)
	mouseLeave = pyqtSignal(int)
	def __init__(self, parent=None, ind=-1):
		super(AIOIndexButton, self).__init__(parent)
		self.ind = ind
	
	def __del__(self):
		self.deleteLater()
	
	def event(self, event):
		if event.type() == QEvent.Enter:
			self.mouseEnter.emit(self.ind)
		elif event.type() == QEvent.Leave:
			self.mouseLeave.emit(self.ind)
		super(AIOIndexButton, self).event(event)
		return True
	
	def mousePressEvent(self, ev):
		if ev.buttons() == Qt.LeftButton:
			self.clicked.emit(self.ind)
		elif ev.buttons() == Qt.RightButton:
			self.rightClicked.emit(self.ind)

class AIOCharButton(AIOIndexButton):
	def __init__(self, parent, ao_app, ind):
		super(AIOCharButton, self).__init__(parent, ind)
		self.ind = ind
		self.ao_app = ao_app
		self.setPixmap(QPixmap("data/misc/char_icon.png"))
		self.resize(64, 64)
		
		self.charpic = QLabel(self)
		self.charpic.move(0, -8)
		
		self.show()
		self.showChar()
	
	def showChar(self):
		prefix = ini.read_ini("data/characters/"+self.ao_app.charlist[self.ind]+"/char.ini", "Options", "imgprefix")+"-"
		prefix = "" if prefix == "-" else prefix
		
		scale = True
		if os.path.exists("data/characters/"+self.ao_app.charlist[self.ind]+"/char_icon.png"):
			pix = QPixmap("data/characters/"+self.ao_app.charlist[self.ind]+"/char_icon.png")
			scale = False
		elif os.path.exists("data/characters/"+self.ao_app.charlist[self.ind]+"/"+prefix+"spin.gif"):
			pix = QPixmap("data/characters/"+self.ao_app.charlist[self.ind]+"/"+prefix+"spin.gif")
		else:
			pix = QPixmap("data/misc/error.gif")
		
		if scale:
			scale = ini.read_ini_float("data/characters/"+self.ao_app.charlist[self.ind]+"/char.ini", "Options", "scale", 1.0)*2
			self.charpic.setPixmap(pix.scaled(pix.size().width()*scale, pix.size().height()*scale))
			if self.charpic.pixmap().size().width() > self.pixmap().size().width():
				self.charpic.move(-(self.charpic.pixmap().size().width()/4) + 8, -8)
			elif self.charpic.pixmap().size().width() < self.pixmap().size().width():
				self.charpic.move((self.charpic.pixmap().size().width()/4) - 4, -8)
		else:
			self.charpic.setPixmap(pix)
			self.charpic.move(0, 0)
		
		self.charpic.show()
	
	def __del__(self):
		self.charpic.deleteLater()
		super(AIOCharButton, self).__del__()

class PenaltyBar(QLabel):
	minusClicked = pyqtSignal(int)
	plusClicked = pyqtSignal(int)
	def __init__(self, parent=None, type=0):
		super(PenaltyBar, self).__init__(parent)
		self.parent = parent
		self.penaltybars = []
		self.type = type
		self.health = 10
		self.resize(84, 14)

	def setupUi(self):
		if self.type == 0: #defense bar.
			for i in range(11):
				self.penaltybars.append(QPixmap("data/misc/defensebar"+str(i)+".png"))
			self.side = "def"
		elif self.type == 1: #prosecution bar
			for i in range(11):
				self.penaltybars.append(QPixmap("data/misc/prosecutionbar"+str(i)+".png"))
			self.side = "pro"
		self.minusbtn = AIOButton(self.parent)
		self.plusbtn = AIOButton(self.parent)
		self.minusbtn.setPixmap(QPixmap("data/misc/"+self.side+"minus.png"))
		self.plusbtn.setPixmap(QPixmap("data/misc/"+self.side+"plus.png"))
		self.minusbtn.clicked.connect(self.minusClick)
		self.plusbtn.clicked.connect(self.plusClick)
		self.setPixmap(self.penaltybars[10])
		self.minusbtn.show()
		self.plusbtn.show()
		self.show()

	def move(self, x, y):
		self.minusbtn.move(x-(9/2), y+(14/2)-(9/2))
		self.plusbtn.move(x+84-(9/2), y+(14/2)-(9/2))
		super(PenaltyBar, self).move(x, y)
	
	def plusClick(self):
		self.plusClicked.emit(self.type)
	
	def minusClick(self):
		self.minusClicked.emit(self.type)
	
	def setHealth(self, health):
		self.setPixmap(self.penaltybars[health])
		self.health = health

	def hide(self):
		self.minusbtn.hide()
		self.plusbtn.hide()
		super(PenaltyBar, self).hide()

	def show(self):
		self.minusbtn.show()
		self.plusbtn.show()
		super(PenaltyBar, self).show()