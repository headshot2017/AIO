from PyQt4 import QtCore, QtGui, uic

import ini, buttons

class CharSelect(QtGui.QWidget):
	charClicked = QtCore.pyqtSignal(int)
	
	def __init__(self):
		super(CharSelect, self).__init__()
		self.charbuttons = []

	def setupUi(self, parent, ao_app):
		self.ao_app = ao_app
		self.parent = parent
		self.charname = parent.charnamelabel
		self.charscroller = parent.charscroller
		self.scrollwidget = parent.charscrollwidget

	def showCharList(self, chars):
		self.charname.setText("Select your character")
		
		all = range(len(self.charbuttons))
		for i in all:
			del self.charbuttons[0]
		
		#since it's a scrollbar system, we don't need height variables. infinite height
		spacing = 2
		x_mod_count = y_mod_count = 0
		left, top = (8, 8)
		width = self.scrollwidget.size().width()
		columns = (width - 64) / (spacing + 64) + 1
		for i in range(len(chars)):
			x_pos = (64 + spacing) * x_mod_count
			y_pos = (64 + spacing) * y_mod_count
			self.charbuttons.append(buttons.AIOCharButton(self.scrollwidget, self.ao_app, i))
			self.charbuttons[i].move(left+x_pos, top+y_pos)
			self.charbuttons[i].mouseEnter.connect(self.charHovered)
			self.charbuttons[i].clicked.connect(self.confirmChar_clicked)
			x_mod_count += 1
			if x_mod_count == columns:
				x_mod_count = 0
				y_mod_count += 1

		self.scrollwidget.setMinimumSize(self.scrollwidget.size().width(), top+y_pos+64)
	
	def charHovered(self, ind):
		self.charname.setText(self.ao_app.charlist[ind])
		self.ao_app.playGUISound("data/sounds/general/sfx-selectblip.wav")
	
	def confirmChar_clicked(self, ind):
		self.charClicked.emit(ind)
