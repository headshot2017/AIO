from PyQt4 import QtCore, QtGui
import lobby, game

class AIOMainWindow(QtGui.QMainWindow):
	ao_app = None
	def __init__(self, _ao_app):
		super(AIOMainWindow, self).__init__()
		self.ao_app = _ao_app
		
		self.stackwidget = QtGui.QStackedWidget(self)
		self.lobbywidget = lobby.lobby(_ao_app)
		self.gamewidget = game.GameWidget(_ao_app)

		self.setCentralWidget(self.stackwidget)
		self.stackwidget.addWidget(self.lobbywidget)
		self.stackwidget.addWidget(self.gamewidget)
		self.setWindowTitle("Attorney Investigations Online")
		self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint)
		self.showServers()
	
	def startGame(self):
		size = self.gamewidget.size()
		self.gamewidget.startGame()
		self.stackwidget.setCurrentWidget(self.gamewidget)
		self.setFixedSize(size)
		self.center()
	
	def stopGame(self):
		self.gamewidget.stopGame()
		self.showServers()
	
	def showServers(self):
		size = self.lobbywidget.size()
		self.lobbywidget.showServers()
		self.stackwidget.setCurrentWidget(self.lobbywidget)
		self.setFixedSize(size)
		self.center()
	
	def center(self):
		frameGm = self.frameGeometry()
		centerPoint = QtGui.QDesktopWidget().availableGeometry().center()
		frameGm.moveCenter(centerPoint)
		self.move(frameGm.topLeft())
