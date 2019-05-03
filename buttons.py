from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os

class AIOButton(QLabel):
	clicked = pyqtSignal()
	rightClicked = pyqtSignal()
	def __init__(self, parent):
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
	def __init__(self, parent, ind):
		super(AIOIndexButton, self).__init__(parent)
		self.ind = ind
	
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
		
		self.charpic = QLabel(self)
		self.charpic.move(0, -8)
		
		self.show()
	
	def showChar(self):
		prefix = self.ao_app.ini_read_string("data/characters/"+self.ao_app.charlist[self.ind]+"/char.ini", "Options", "imgprefix")+"-"
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
			scale = self.ao_app.ini_read_float("data/characters/"+self.ao_app.charlist[self.ind]+"/char.ini", "Options", "scale", 1)*2
			self.charpic.setPixmap(pix.scaled(pix.size().width()*scale, pix.size().height()*scale))
			if self.charpic.pixmap().size().width() > self.pixmap().size().width():
				self.charpic.move(-(self.charpic.pixmap().size().width()/4) + 8, -8)
			self.charpic.show()
		else:
			self.setPixmap(pix)
			self.charpic.hide()
	
	def __del__(self):
		self.charpic.deleteLater()
		super(AIOCharButton, self).__del__()