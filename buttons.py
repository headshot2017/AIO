from PyQt4.QtGui import *
from PyQt4.QtCore import *

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