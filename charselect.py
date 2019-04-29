from PyQt4 import QtCore, QtGui

class CharSelect(QtGui.QWidget):
	charClicked = QtCore.pyqtSignal(int)
	
	def __init__(self, parent, ao_app):
		super(CharSelect, self).__init__(parent)
		self.ao_app = ao_app
		
		self.setGeometry(0, 384, 512, 640-384)
		self.charcombo = QtGui.QComboBox(self)
		self.charcombo.setGeometry(64, (640-384)/2-10, 192, 20)
		self.charconfirm = QtGui.QPushButton(self, text="Confirm")
		self.charconfirm.setGeometry(512-((self.charcombo.x()+self.charcombo.size().width())/2)-32, (640-384)/2-10, 64, 20)
		self.charconfirm.clicked.connect(self.confirmChar_clicked)
		self.disconnectbtn = QtGui.QPushButton(self, text="Disconnect")
		self.disconnectbtn.move(8, 8)
		self.disconnectbtn.clicked.connect(self.ao_app.stopGame)
	
	def showCharList(self, chars):
		self.charcombo.clear()
		self.charcombo.addItems(chars)
	
	def confirmChar_clicked(self):
		self.charClicked.emit(self.charcombo.currentIndex())