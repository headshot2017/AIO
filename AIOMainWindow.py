from PyQt4 import QtCore, QtGui

import lobby, game

class AIOMainWindow(QtGui.QMainWindow):
	ao_app = None
	def __init__(self, _ao_app):
		super(AIOMainWindow, self).__init__()
		self.ao_app = _ao_app
		
		self.stackwidget = QtGui.QStackedWidget(self)
		self.lobbywidget = lobby.lobby(_ao_app)
		self.lobbywidget.themeSize = self.lobbywidget.size()
		self.gamewidget = game.GameWidget(_ao_app)
		self.gamewidget.themeSize = self.gamewidget.size()

		self.setCentralWidget(self.stackwidget)
		self.stackwidget.addWidget(self.lobbywidget)
		self.stackwidget.addWidget(self.gamewidget)
		self.setWindowTitle("Attorney Investigations Online")
		self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint)
		self.showServers()
	
	def startGame(self):
		size = self.gamewidget.themeSize
		self.gamewidget.startGame()
		self.stackwidget.setCurrentWidget(self.gamewidget)
		self.setFixedSize(size)
		# without this the game becomes lobby sized for whatever reason
		self.gamewidget.resize(size)
		self.center()
	
	def stopGame(self):
		self.gamewidget.stopGame()
		self.showServers()
	
	def showServers(self):
		size = self.lobbywidget.themeSize
		self.setFixedSize(size)
		# without this the lobby stays game sized
		self.lobbywidget.resize(size)
		self.lobbywidget.showServers()
		self.stackwidget.setCurrentWidget(self.lobbywidget)
		self.center()

	# reloads the lobby and replaces the game with a new widget
	# essentialy soft restarting the game when a theme is changed.
	def reloadLobby(self):
		old_game = self.gamewidget
		old_game.stopGame()
		self.stackwidget.removeWidget(old_game)
		old_game.deleteLater()
		self.gamewidget = game.GameWidget(self.ao_app)
		self.gamewidget.themeSize = self.gamewidget.size()
		self.stackwidget.addWidget(self.gamewidget)

		old_lobby = self.lobbywidget
		old_lobby.shutdown()
		self.stackwidget.removeWidget(old_lobby)
		old_lobby.deleteLater()

		self.lobbywidget = lobby.lobby(self.ao_app)
		self.lobbywidget.themeSize = self.lobbywidget.size()
		self.stackwidget.insertWidget(0, self.lobbywidget)
		self.showServers()
	
	def center(self):
		frameGm = self.frameGeometry()
		centerPoint = QtGui.QDesktopWidget().availableGeometry().center()
		frameGm.moveCenter(centerPoint)
		self.move(frameGm.topLeft())
