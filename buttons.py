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
		prefix = ao_app.ini_read_string("data/characters/"+ao_app.charlist[ind]+"/char.ini", "Options", "imgprefix")+"-"
		prefix = "" if prefix == "-" else prefix
		
		if os.path.exists("data/characters/"+ao_app.charlist[ind]+"/"+prefix+"spin.gif"):
			pix = QPixmap("data/characters/"+ao_app.charlist[ind]+"/"+prefix+"spin.gif")
		else:
			pix = QPixmap("data/misc/error.gif")
		self.charpic.setPixmap(pix.scaled(pix.size().width()*2, pix.size().height()*2))
		self.charpic.show()
		self.show()
	
	def __del__(self):
		self.charpic.deleteLater()
		super(AIOCharButton, self).__del__()