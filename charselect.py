from PyQt4 import QtCore, QtGui
import buttons

class CharSelect(QtGui.QWidget):
	charClicked = QtCore.pyqtSignal(int)
	charHover = QtCore.pyqtSignal(int)
	
	def __init__(self, parent, ao_app):
		super(CharSelect, self).__init__(parent)
		self.ao_app = ao_app
		self.charbuttons = []
		
		self.charscroller = QtGui.QScrollArea(self)
		self.charscroller.setGeometry(16, 32, 384+96, 192+32)
		self.scrollwidget = QtGui.QWidget(self.charscroller)
		self.scrollwidget.resize(384+96-20, 384)
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
		all = range(len(self.charbuttons))
		for i in all:
			del self.charbuttons[0]
		self.charbuttons.append(buttons.AIOCharButton(self.scrollwidget, self.ao_app, 0))
		self.charbuttons[0].move(8, 8)
		self.charbuttons[0].mouseEnter.connect(self.charHovered)
	
	def charHovered(self, ind):
		print ind
	
	def confirmChar_clicked(self, ind):
		self.charClicked.emit(ind)