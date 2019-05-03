from PyQt4 import QtCore, QtGui
import buttons

class CharSelect(QtGui.QWidget):
	charClicked = QtCore.pyqtSignal(int)
	
	def __init__(self, parent, ao_app):
		super(CharSelect, self).__init__(parent)
		self.ao_app = ao_app
		self.charbuttons = []
		
		self.charscroller = QtGui.QScrollArea(self)
		self.charscroller.setGeometry(8, 32, 512-8, 192+32)
		self.scrollwidget = QtGui.QWidget(self.charscroller)
		self.scrollwidget.resize(512-28, 384)
		self.charscroller.setWidget(self.scrollwidget)
		self.setGeometry(0, 384, 512, 640-384)
		
		for i in range(750):
			self.charbuttons.append(buttons.AIOCharButton(self.scrollwidget, self.ao_app, i))
		
		self.disconnectbtn = QtGui.QPushButton(self, text="Disconnect")
		self.disconnectbtn.move(8, 8)
		self.disconnectbtn.clicked.connect(self.ao_app.stopGame)
		
		self.charnameimg = QtGui.QLabel(self)
		self.charnameimg.setPixmap(QtGui.QPixmap("data/misc/evidence_name.png"))
		self.charnameimg.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
		self.charnameimg.move(256 - (self.charnameimg.pixmap().size().width()/2), 4)
		self.charname = QtGui.QLabel(self.charnameimg)
		self.charname.setAlignment(QtCore.Qt.AlignCenter)
		self.charname.setStyleSheet("background-color: rgba(0, 0, 0, 0);\ncolor: "+QtGui.QColor(255, 165, 0).name())
		self.charname.resize(self.charnameimg.pixmap().size().width(), self.charnameimg.size().height())
	
	def showCharList(self, chars):
		self.charname.setText("Select your character...")
		
		"""
		all = range(len(self.charbuttons))
		for i in all:
			del self.charbuttons[0]
		"""
		
		#since it's a scrollbar system, we don't need height variables. infinite height
		spacing = 2
		x_mod_count = y_mod_count = 0
		left, top = (12, 8)
		width = self.scrollwidget.size().width()
		columns = (width - 64) / (spacing + 64) + 1
		for i in range(750):
			if i < len(chars):
				x_pos = (64 + spacing) * x_mod_count
				y_pos = (64 + spacing) * y_mod_count
				self.charbuttons[i].showChar()
				self.charbuttons[i].move(left+x_pos, top+y_pos)
				self.charbuttons[i].mouseEnter.connect(self.charHovered)
				self.charbuttons[i].clicked.connect(self.confirmChar_clicked)
				x_mod_count += 1
				if x_mod_count == columns:
					x_mod_count = 0
					y_mod_count += 1
			else:
				self.charbuttons[i].hide()
		
		self.scrollwidget.resize(self.scrollwidget.size().width(), top+y_pos+64)
	
	def charHovered(self, ind):
		self.charname.setText(self.ao_app.charlist[ind])
		self.ao_app.playGUISound("data\\sounds\\general\\sfx-selectblip.wav")
	
	def confirmChar_clicked(self, ind):
		self.charClicked.emit(ind)