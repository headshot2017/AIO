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
		self.stackwidget.setCurrentWidget(self.lobbywidget)
		self.setWindowTitle("Attorney Investigations Online")
		self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint)
		self.showServers()
	
	def startGame(self):
		self.gamewidget.startGame()
		self.stackwidget.setCurrentWidget(self.gamewidget)
		self.setFixedSize(1000, 512+20)
		self.center()
	
	def stopGame(self):
		self.gamewidget.stopGame()
		self.showServers()
	
	def showServers(self):
		self.lobbywidget.showServers()
		self.stackwidget.setCurrentWidget(self.lobbywidget)
		self.setFixedSize(800, 480)
		self.center()
	
	def center(self):
		frameGm = self.frameGeometry()
		centerPoint = QtGui.QDesktopWidget().availableGeometry().center()
		frameGm.moveCenter(centerPoint)
		self.move(frameGm.topLeft())
