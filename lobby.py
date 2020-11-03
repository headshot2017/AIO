from PyQt4 import QtCore, QtGui
from game_version import LOBBY_VERSION
import os, socket, buttons, options, ini

class ConnectingStatus(QtGui.QWidget):
	ao_app = None
	def __init__(self, parent, _ao_app):
		super(ConnectingStatus, self).__init__(parent)
		self.ao_app = _ao_app
		
		self.resize(800, 480)
		self.connectingmsg = QtGui.QLabel(self, text="Connecting...")
		self.connectingmsg.resize(800, 320)
		self.connectingmsg.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignCenter)
		self.connectingmsg.setFont(QtGui.QFont("Arial", 12))
		self.connectingmsg.setStyleSheet("color: white")
		
		self.ao_app.tcpthread.gotWelcome.connect(self.readWelcome)
		self.ao_app.tcpthread.gotCharacters.connect(self.readCharacters)
		self.ao_app.tcpthread.gotMusic.connect(self.readMusic)
		self.ao_app.tcpthread.gotZones.connect(self.readZones)
		self.ao_app.tcpthread.gotEvidence.connect(self.readEvidence)
		self.ao_app.tcpthread.kicked.connect(self.kicked)
		self.ao_app.tcpthread.serverWarning.connect(self.serverWarning)
		self.ao_app.tcpthread.connectionError.connect(self.connectionError)
		self.ao_app.tcpthread.disconnected.connect(self.disconnected)
	
	def readWelcome(self, welcome):
		self.player_id = welcome[0]
		self.maxchars = welcome[1]
		self.defaultzone = welcome[2]
		self.maxmusic = welcome[3]
		self.maxzones = welcome[4]
		self.motd = welcome[5]
		
		self.connectingmsg.setText("Retrieving character list... (%d)" % self.maxchars)
	
	def readCharacters(self, charlist):
		self.charlist = charlist
		self.connectingmsg.setText("Retrieving music list... (%d)" % self.maxmusic)
	
	def readMusic(self, musiclist):
		self.musiclist = musiclist
		self.connectingmsg.setText("Retrieving zone list... (%d)" % self.maxzones)
	
	def readZones(self, zonelist):
		self.zonelist = zonelist
		self.connectingmsg.setText("Getting evidence for zone \"%s\"..." % self.defaultzone)
	
	def readEvidence(self, evlist):
		self.evidencelist = evlist
		self.ao_app.startGame(self.player_id, self.defaultzone, self.motd, self.charlist, self.musiclist, self.zonelist, self.evidencelist)
	
	def showServers(self):
		self.hide()
		self.connectingmsg.setText("Connecting...")
	
	def connectionError(self, reason):
		QtGui.QMessageBox.critical(self, "Connection error", reason)
		self.disconnected()
	
	def disconnected(self):
		self.showServers()
		self.ao_app.stopGame()
	
	def kicked(self, reason):
		QtGui.QMessageBox.critical(self, "Kicked", "You were kicked off the server.\nReason: %s" % reason)
		self.showServers()
		self.ao_app.stopGame()
	
	def serverWarning(self, reason):
		QtGui.QMessageBox.warning(self, "Warning from server", reason)
	
	def paintEvent(self, event):
		painter = QtGui.QPainter(self)
		painter.fillRect(0, 0, 800, 480, QtGui.QColor(0, 0, 0, 128))

class lobby(QtGui.QWidget):
	ao_app = None
	def __init__(self, _ao_app):
		super(lobby, self).__init__()
		self.ao_app = _ao_app
		
		self.font = QtGui.QFont("Arial", 12)
		
		self.text = QtGui.QLabel(self, text="Attorney Investigations Online\nv"+str(LOBBY_VERSION))
		self.text.setFont(self.font)
		self.text.move(8, 8)
		
		self.serverlistwidget = QtGui.QListWidget(self)
		self.serverlistwidget.setGeometry(64, 64, 512-64, 240)
		self.serverlistwidget.itemClicked.connect(self.serverItemClicked)
		
		desc_x, desc_y, desc_w, desc_h = 640-64+8, 16, 256-48, 480-128
		
		self.connectingstatus = ConnectingStatus(self, _ao_app)
		self.connectingstatus.hide()
		
		self.addtofav = buttons.AIOButton(self)
		self.connectbtn = buttons.AIOButton(self)
		self.refreshbtn = buttons.AIOButton(self)
		self.newsbtn = buttons.AIOButton(self)
		self.allservers = buttons.AIOButton(self)
		self.LANbtn = buttons.AIOButton(self)
		self.favoritesbtn = buttons.AIOButton(self)
		self.joinipaddress = buttons.AIOButton(self)
		self.optionsbtn = buttons.AIOButton(self)
		
		self.addtofav.setPixmap(QtGui.QPixmap("data/misc/add_to_favorites.png"))
		self.addtofav.move(640-16, desc_y+desc_h+4)
		self.connectbtn.setPixmap(QtGui.QPixmap("data/misc/connect_button.png"))
		self.connectbtn.move(640-16, desc_y+desc_h+4+48)
		self.refreshbtn.setPixmap(QtGui.QPixmap("data/misc/refresh.png"))
		self.refreshbtn.move((self.serverlistwidget.x()+self.serverlistwidget.size().width())/2 - 32, self.serverlistwidget.y()+self.serverlistwidget.size().height()+16)
		self.allservers.setPixmap(QtGui.QPixmap("data/misc/all_servers.png"))
		self.allservers.move(self.refreshbtn.x() - 128 - 8, self.refreshbtn.y() + 64)
		self.favoritesbtn.setPixmap(QtGui.QPixmap("data/misc/favorites.png"))
		self.favoritesbtn.move(self.refreshbtn.x() + 128 + 8, self.refreshbtn.y() + 64)
		self.LANbtn.setPixmap(QtGui.QPixmap("data/misc/lan.png"))
		self.LANbtn.move(self.refreshbtn.x(), self.refreshbtn.y() + 64)
		self.newsbtn.setPixmap(QtGui.QPixmap("data/misc/news_button.png"))
		self.newsbtn.move(self.refreshbtn.x() - (self.newsbtn.pixmap().size().width())/2, self.favoritesbtn.y() + 32)
		self.joinipaddress.setPixmap(QtGui.QPixmap("data/misc/joinip_button.png"))
		self.joinipaddress.move(self.newsbtn.x() + self.newsbtn.pixmap().size().width() + 8, self.newsbtn.y())
		self.optionsbtn.setPixmap(QtGui.QPixmap("data/misc/options_button.png"))
		self.optionsbtn.move(8, self.size().height()-40)
		
		self.description = QtGui.QTextEdit(self)
		self.description.setFont(self.font)
		self.description.setGeometry(desc_x, desc_y, desc_w, desc_h)
		self.description.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
		self.description.setFrameStyle(QtGui.QFrame.NoFrame)
		self.description.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.description.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
		self.description.setReadOnly(True)
		self.description.setStyleSheet("background-color: rgba(0, 0, 0, 0);"
														"color: white")
		
		self.newstext = QtGui.QTextEdit(self)
		self.newstext.setFont(self.font)
		self.newstext.setGeometry(64, 64, 512-64, 240)
		self.newstext.setReadOnly(True)
		self.newslabel = QtGui.QLabel(self)
		self.newslabel.setFont(self.font)
		self.newslabel.setText("News")
		self.newslabel.move(self.newstext.x(), self.newstext.y() - 20)
		self.newstext.hide()
		self.newslabel.hide()

		if os.path.exists("data/aaio_news.txt"):
			self.newstext.setText(open("data/aaio_news.txt").read())
		
		self.addtofav.clicked.connect(self.add_to_favorites)
		self.connectbtn.clicked.connect(self.connectClicked)
		self.refreshbtn.clicked.connect(self.refresh)
		self.allservers.clicked.connect(self.on_public_servers)
		self.LANbtn.clicked.connect(self.on_lan_servers)
		self.favoritesbtn.clicked.connect(self.on_favorites_list)
		self.newsbtn.clicked.connect(self.on_news_tab)
		self.joinipaddress.clicked.connect(self.join_ip_address)
		self.optionsbtn.clicked.connect(self.on_settings_button)
		self.addtofav.show()
		self.connectbtn.show()
		self.refreshbtn.show()
		self.allservers.show()
		self.LANbtn.show()
		self.favoritesbtn.show()
		self.newsbtn.show()
		self.joinipaddress.show()
		
		self.connectingstatus.raise_()
		
		self.optionsgui = options.Options(_ao_app)
		self.optionsgui.fileSaved.connect(self.onOptionsSave)
		
		a = ini.read_ini("aaio.ini", "MasterServer", "IP", "aaio-ms.aceattorneyonline.com:27011").split(":")
		ip = a[0]
		try:
			port = int(a[1])
		except:
			port = 27011

		self.newPackets = ini.read_ini("aaio.ini", "Advanced", "0.5 packets", "0") == "1"

		self.msthread = MasterServerThread(ip, port, self.newPackets)
		self.msthread.gotServers.connect(self.gotServerList)
		self.msthread.gotNews.connect(self.gotNews)
		self.msthread.start()

		self.servers = []
		self.favorites = []
		self.lanservers = []
		self.ao_app.udpthread.gotInfoRequest.connect(self.gotUDPRequest)

		try:
			for line in open("data/serverlist.txt"):
				server = line.rstrip("\n").split(":")[:2]
				self.favorites.append([server[0]+":"+server[1], "", server[0], int(server[1])])

		except IOError:
			open("data/serverlist.txt", "w").write("localhost:27010\n")
			self.favorites = [["localhost", 27010]]

		self.pinged_favorites = list(self.favorites) # a copy
		self.serverselected = -1
		self.tab = 0
	
	def onOptionsSave(self):
		self.ao_app.mainwindow.gamewidget.chatbox.setPixmap(QtGui.QPixmap("data/misc/"+ini.read_ini("aaio.ini", "General", "Chatbox image")))
		
	def paintEvent(self, event):
		painter = QtGui.QPainter(self)
		painterpath = QtGui.QPainterPath()
		
		painterpath.addRoundRect(640-64, 0, 800-(640-64), 480, 25, 10)
		
		painter.fillRect(0, 0, 800, 480, QtGui.QColor(255, 255, 255))
		painter.fillPath(painterpath, QtGui.QColor(64, 64, 64))

	def showServers(self):
		self.connectingstatus.showServers()

	def gotServerList(self, servers):
		self.servers = list(servers)
		if self.tab == 0:
			self.updateServerList(servers)

	def gotUDPRequest(self, server):
		addr, name, desc, players, maxplayers, version = server
		ip, port = addr

		if self.tab == 1:
			self.lanservers.append([name, desc, ip, port, players, maxplayers, version])
			self.updateServerList(self.lanservers)
		elif self.tab == 2:
			if ["%s:%d" % (ip, port), "", ip, port] in self.favorites:
				ind = self.favorites.index(["%s:%d" % (ip, port), "", ip, port])
				self.pinged_favorites[ind] = [name, desc, ip, port]
				self.updateServerList(self.pinged_favorites)

	def gotNews(self, news):
		self.newstext.setText(news)
		if not os.path.exists("data/aaio_news.txt"):
			open("data/aaio_news.txt", "w").close()
		
		with open("data/aaio_news.txt") as f:
			if f.read() != news:
				f.close()
				f = open("data/aaio_news.txt", "w")
				f.write(news)
				f.close()
				self.on_news_tab()
	
	def on_public_servers(self):
		if self.tab == 0:
			return
		
		self.tab = 0
		self.newstext.hide()
		self.newslabel.hide()
		self.refresh()

	def on_lan_servers(self):
		if self.tab == 1:
			return
		
		self.tab = 1
		self.newstext.hide()
		self.newslabel.hide()
		self.refresh()
	
	def on_favorites_list(self):
		if self.tab == 2:
			return
		
		self.tab = 2
		self.newstext.hide()
		self.newslabel.hide()
		self.refresh()
	
	def on_news_tab(self):
		if self.tab == 3:
			return
		
		self.tab = 3
		self.refreshbtn.show()
		self.newstext.show()
		self.newslabel.show()
	
	def on_settings_button(self):
		self.optionsgui.showSettings()
	
	def add_to_favorites(self):
		if self.tab in (2, 3): # can't add in favs tab or news tab
			return self.description.setText("You can't do that.")
		if self.serverselected == -1:
			return self.description.setText("Select a server first you nobo")
		
		server = self.servers[self.serverselected]
		
		for fav in self.favorites:
			if server[2] in fav and server[3] in fav:
				return QtGui.QMessageBox.information(self, "uh", "That server already exists in your favorites, named \"%s\"" % fav[2])
		
		self.favorites.append([server[2], server[3], server[0], server[1]])
		with open("data/serverlist.txt", "a") as file:
			file.write(server[2]+":"+str(server[3])+":"+server[0]+":"+server[1]+"\n")
	
	def refresh(self):
		if self.tab == 0: # public
			self.updateServerList([])
			self.msthread.sendRefresh()
		elif self.tab == 1: # LAN
			self.updateServerList([])
			self.refreshLAN()
		elif self.tab == 2: # favorites
			self.updateServerList(self.favorites)
			self.refreshFavorites()
		else:
			self.msthread.getNews()

	def refreshLAN(self):
		self.lanservers = []

		for i in range(27010, 27020+1):
			self.ao_app.udpthread.sendInfoRequest(("<broadcast>", i))

	def refreshFavorites(self):
		self.pinged_favorites = list(self.favorites)

		for server in self.favorites:
			self.ao_app.udpthread.sendInfoRequest(tuple(server[2:]))
	
	def join_ip_address(self):
		addr, ok = QtGui.QInputDialog.getText(self, "Join IP address...", "Enter the IP address of the server you wish to join.\nIt must have the format \"ip:port\"\nExample: 127.0.0.1:27010")
		
		if ok and addr:
			ip = addr.split(":")
			if len(ip) == 1:
				ip.append("27010")
			else:
				if not ip[1]:
					ip[1] = "27010"
			port = int(ip[1])
			
			self.connectingstatus.show()
			self.ao_app.connect(ip[0], port)
	
	def connectClicked(self):
		if self.serverselected == -1:
			return self.description.setText("Lmao you need to pick a server from the list")
		
		if self.tab == 0:
			server = self.servers[self.serverselected]
		elif self.tab == 2:
			server = self.favorites[self.serverselected]
		else:
			server = self.lanservers[self.serverselected]

		ip = server[2]
		port = server[3]
		self.connectingstatus.show()
		self.ao_app.connect(ip, port)

	def updateServerList(self, servers):
		self.serverlistwidget.clear()
		self.serverselected = -1
		self.description.setText("")

		for server in servers:
			item = QtGui.QListWidgetItem(server[0])
			item.setFont(self.font)
			self.serverlistwidget.addItem(item)
	
	def serverItemClicked(self, current):
		for i in range(self.serverlistwidget.count()):
			if self.serverlistwidget.item(i) == current:
				if self.tab == 0:
					self.description.setText(self.servers[i][1])
				elif self.tab == 1:
					self.description.setText(self.lanservers[i][1])
				elif self.tab == 2:
					self.description.setText(self.pinged_favorites[i][1])
				self.serverselected = i

class MasterServerThread(QtCore.QThread):
	gotServers = QtCore.pyqtSignal(tuple)
	gotNews = QtCore.pyqtSignal(str)

	def __init__(self, ip, port, newPackets=False):
		super(MasterServerThread, self).__init__()
		self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.ip = ip
		self.port = port
		self.newPackets = newPackets
	
	def __del__(self):
		self.closeConnection()
		self.wait()
	
	def closeConnection(self):
		self.tcp.close()
		self.terminate()
	
	def sendRefresh(self):
		self.tcp.send("12#%\n")
	
	def getNews(self):
		self.tcp.send("NEWS#%\n")

	def oldPacketLoop(self, data):
		if not data.endswith("%"):
			self.tempdata += data
			return
		else:
			if self.tempdata:
				data = self.tempdata+data
				self.tempdata = ""

		totals = data.split("%")
		for moredata in totals:
			network = moredata.split("#")
			header = network.pop(0)

			if header == "1": #connected, contains client ID (not that useful anyway)
				player_id = int(network[0])
				self.sendRefresh() #request servers

			elif header == "12": #server list
				total_servers = len(network) / 4
				if total_servers <= 0:
					print "warning: received server list packet, but total_servers is %d" % total_servers
					return

				servers = []
				for i in range(0, total_servers*4, 4):
					servers.append((network[i], network[i+1].replace("<num>", "\n"), network[i+2], int(network[i+3])))

				self.gotServers.emit(tuple(servers))

				if not self.got_news:
					self.getNews() #get news tab
					self.got_news = True

			elif header == "NEWS": #news tab
				self.gotNews.emit(network[0].replace("<num>", "#").replace("<percent>", "%"))

	def newPacketLoop(self, data):
		pass

	def run(self):
		self.got_news = False
		
		try:
			self.tcp.connect((self.ip, self.port))
		except socket.error as err:
			self.gotServers.emit((("Error connecting to master server. Click for details", str(err), "127.0.0.1", 27010),))
			self.closeConnection()
		
		self.tcp.settimeout(0.1)
		self.tempdata = ""
		
		while True:
			try:
				data = self.tcp.recv(8192 if not self.newPackets else 4)
				
			except socket.timeout, err:
				error = err.args[0]
				if error == "timed out":
					continue
				else:
					print err.args
					self.closeConnection()
			
			except socket.error, err:
				print err.args
				self.closeConnection()
			
			if not data:
				print "MS connection closed by server"
				self.closeConnection()


			if not self.newPackets:
				self.oldPacketLoop(data)
			else:
				self.newPacketLoop(data)