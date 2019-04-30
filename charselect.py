from PyQt4 import QtCore, QtGui
import buttons

class CharSelect(QtGui.QWidget):
	charClicked = QtCore.pyqtSignal(int)
	
	def __init__(self, parent, ao_app):
		super(CharSelect, self).__init__(parent)
		self.ao_app = ao_app
		
		self.charscroller = QtGui.QScrollArea(self)
		self.charscroller.setGeometry(16, 32, 384+48, 192+32)
		self.scrollwidget = QtGui.QWidget(self.charscroller)
		self.charscroller.setWidget(self.scrollwidget)
		self.setGeometry(0, 384, 512, 640-384)
		
		"""
		self.charcombo = QtGui.QComboBox(self)
		self.charcombo.setGeometry(64, (640-384)/2-10, 192, 20)
		self.charconfirm = QtGui.QPushButton(self, text="Confirm")
		self.charconfirm.setGeometry(512-((self.charcombo.x()+self.charcombo.size().width())/2)-32, (640-384)/2-10, 64, 20)
		self.charconfirm.clicked.connect(self.confirmChar_clicked)
		"""
		
		self.disconnectbtn = QtGui.QPushButton(self, text="Disconnect")
		self.disconnectbtn.move(8, 8)
		self.disconnectbtn.clicked.connect(self.ao_app.stopGame)
	
	def showCharList(self, chars):
		pass
	
	def confirmChar_clicked(self):
		self.charClicked.emit(self.charcombo.currentIndex())