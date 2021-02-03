import os, socket, zlib, struct
from packing import *

from PyQt4 import QtCore, QtGui, uic

import AIOprotocol, buttons, ini, options
from game_version import LOBBY_VERSION


class ServerItem(QtGui.QTreeWidgetItem):
    def __lt__(self, other):
        column = self.treeWidget().sortColumn()
        key1 = self.text(column)
        key2 = other.text(column)
        try:
            if column == 1: # online player count
                return int(key1.split("/")[0]) < int(key2.split("/")[0])
            return float(key1) < float(key2)
        except ValueError:
            return key1.toLower() < key2.toLower()

class ConnectingStatus(QtGui.QWidget):
	ao_app = None
	def __init__(self, parent, _ao_app):
		super(ConnectingStatus, self).__init__(parent)
		self.ao_app = _ao_app
		
		self.resize(parent.size())
		self.connectingmsg = QtGui.QLabel(self, text="Connecting...")
		self.connectingmsg.resize(parent.size().width(), parent.size().height() / 1.5)
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
		painter.fillRect(0, 0, 960, 480, QtGui.QColor(0, 0, 0, 128))

class lobby(QtGui.QWidget):
	ao_app = None
	def __init__(self, _ao_app):
		super(lobby, self).__init__()
		self.ao_app = _ao_app

		theme = ini.read_ini("aaio.ini", "General", "Theme", "default")
		uic.loadUi("data/themes/"+theme+"/lobby.ui", self) # plant the bomb

		self.versiontext.setText("Attorney Investigations Online\nv"+str(LOBBY_VERSION))

		self.serverlistwidget.setHeaderItem(ServerItem(["Name", "Players", "Version", "Ping"]))
		self.serverlistwidget.header().resizeSection(0, 448)
		self.serverlistwidget.header().resizeSection(1, 64)
		self.serverlistwidget.header().resizeSection(2, 80)
		self.serverlistwidget.header().resizeSection(3, 64)
		self.serverlistwidget.itemClicked.connect(self.serverItemClicked)

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
		self.aboutbtn.clicked.connect(self.on_about_button)
		self.startserverbtn.clicked.connect(self.on_startserver_button)
		
		self.connectingstatus = ConnectingStatus(self, _ao_app)
		self.connectingstatus.hide()
		self.newswidget.hide()
		
		self.optionsgui = options.Options(_ao_app)
		#self.optionsgui.fileSaved.connect(self.onOptionsSave)
		
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
		self.msthread.error.connect(self.MSError)
		self.msthread.start()

		self.server_subprocess = None

		self.servers = []
		self.favorites = []
		self.pinged_list = [] # [name, players, version, ping, desc, ip, str(port)]
		self.ao_app.udpthread.gotInfoRequest.connect(self.gotUDPRequest)

		try:
			for line in open("data/serverlist.txt"):
				server = line.rstrip("\n").split(":")[:2]
				try: ip = socket.gethostbyname(server[0])
				except: ip = server[0]
				self.favorites.append([ip+":"+server[1], "", "", "pinging", "", ip, server[1]])

		except IOError:
			open("data/serverlist.txt", "w").write("localhost:27010\n")
			self.favorites = [["localhost:27010", "", "", "pinging", "", "localhost", "27010"]]

		self.serverselected = -1
		self.tab = 0

	def on_startserver_button(self):
		QtGui.QMessageBox.critical(None, "Start server", "This option does not work at this time.\nRun 'server.exe' in the game folder for the time being")

	def on_about_button(self):
		QtGui.QMessageBox.information(None, "About this game",
		"Attorney Investigations Online\nVersion %s\nCreated by Headshotnoby\n\nThis game is not affiliated with the original Attorney Online team.\n\nThanks to all the collaborators:\nstonedDiscord, X0men0X, Phoenix \"Nick\" Wright, Pyraq,\nand anyone else I may have forgotten." % LOBBY_VERSION)

	def MSError(self, msg):
		QtGui.QMessageBox.critical(None, "Error connecting to master", "Failed to connect to the master server.\nCheck your antivirus, internet connection or firewall?\n\nAdditional info:\n"+msg)

	""" so long, brother
	def paintEvent(self, event):
		painter = QtGui.QPainter(self)
		painterpath = QtGui.QPainterPath()
		
		painterpath.addRoundRect(960-160-64, 0, 960-(960-160-64), 480, 25, 10)
		
		painter.fillRect(0, 0, 960, 480, QtGui.QColor(255, 255, 255))
		painter.fillPath(painterpath, QtGui.QColor(64, 64, 64))
	"""

	def showServers(self):
		self.connectingstatus.showServers()

	def gotServerList(self, servers):
		self.servers = servers

		if self.tab == 0:
			self.pinged_list = list(servers)
			self.updateServerList(self.pinged_list)

			for server in servers:
				self.ao_app.udpthread.sendInfoRequest(tuple(server[-2:]))

	def gotUDPRequest(self, server):
		addr, name, desc, players, maxplayers, version, ping = server
		ip, port = addr
		version = versionToStr(str(version))

		if self.tab == 1:
			self.pinged_list.append([name, "%d/%d" % (players, maxplayers), version, ping, desc, ip, str(port)])
			self.updateServerList(self.pinged_list)
		elif self.tab == 2:
			if ["%s:%d" % (ip, port), "", "", "pinging", "", ip, str(port)] in self.favorites:
				ind = self.favorites.index(["%s:%d" % (ip, port), "", "", "pinging", "", ip, str(port)])
				self.pinged_list[ind] = [name, "%d/%d"%(players, maxplayers), str(version), ping, desc, ip, str(port)]
				self.updateServerList(self.pinged_list)
		elif self.tab == 0:
			if ["%s:%d" % (ip, port), "", "", "pinging", "", ip, str(port)] in self.servers:
				ind = self.servers.index(["%s:%d" % (ip, port), "", "", "pinging", "", ip, str(port)])
				self.pinged_list[ind] = [name, "%d/%d"%(players, maxplayers), str(version), ping, desc, ip, str(port)]
				self.updateServerList(self.pinged_list)

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
		self.pinged_list = []

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
		self.pinged_list = []

		for i in range(27010, 27020+1):
			self.ao_app.udpthread.sendInfoRequest(("<broadcast>", i))

	def refreshFavorites(self):
		self.pinged_list = list(self.favorites)

		for server in self.favorites:
			self.ao_app.udpthread.sendInfoRequest(tuple(server[-2:]))
	
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

		server = self.pinged_list[self.serverselected]

		ip = server[-2]
		port = int(server[-1])
		self.connectingstatus.show()
		self.ao_app.connect(ip, port)

	def updateServerList(self, servers):
		self.serverlistwidget.clear()
		self.serverselected = -1
		self.description.setText("")

		for server in servers:
			#item = QtGui.QListWidgetItem(server[0])
			item = ServerItem(server)
			self.serverlistwidget.addTopLevelItem(item)
	
	def serverItemClicked(self, item):
		i = self.serverlistwidget.indexOfTopLevelItem(item)
		for sv in self.pinged_list:
			if sv[0] == item.text(0):
				i = self.serverselected = self.pinged_list.index(sv)
				break

		self.description.setText(self.pinged_list[i][-3])

class MasterServerThread(QtCore.QThread):
	gotServers = QtCore.pyqtSignal(list)
	gotNews = QtCore.pyqtSignal(str)
	error = QtCore.pyqtSignal(str)

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

	def sendBuffer(self, data):
		data = struct.pack("I", len(data)) + data
		self.tcp.send(data)

	def sendRefresh(self):
		if not self.newPackets:
			self.tcp.send("12#%\n")
		else:
			self.sendBuffer(struct.pack("B", AIOprotocol.MS_LIST))
	
	def getNews(self):
		if not self.newPackets:
			self.tcp.send("NEWS#%\n")
		else:
			self.sendBuffer(struct.pack("B", AIOprotocol.MS_NEWS))

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
					#servers.append([network[i+2], network[i+3]])

				self.gotServers.emit(servers)

				if not self.got_news:
					self.getNews() #get news tab
					self.got_news = True

			elif header == "NEWS": #news tab
				self.gotNews.emit(network[0].replace("<num>", "#").replace("<percent>", "%"))

	def newPacketLoop(self, data):
		if len(data) < 4:
			return

		data, length = buffer_read("I", data)
		data = zlib.decompress(self.tcp.recv(length+1))

		data, header = buffer_read("B", data)

		if header == AIOprotocol.MS_CONNECTED:
			self.sendRefresh()

		elif header == AIOprotocol.MS_LIST: # server list
			servers = []
			while data:
				data, ip = buffer_read("S", data)
				data, port = buffer_read("H", data)

				servers.append(["%s:%d"%(ip,port), "", "", "pinging", "", ip, str(port)])

			self.gotServers.emit(servers)

			if not self.got_news:
				self.getNews()
				self.got_news = True

		elif header == AIOprotocol.MS_NEWS:
			data, big_wall_of_text = buffer_read("S", data)
			self.gotNews.emit(big_wall_of_text)

	def run(self):
		self.got_news = False
		
		try:
			self.tcp.connect((self.ip, self.port))
		except socket.error as err:
			#self.gotServers.emit((("Error connecting to master server. Click for details", str(err), "127.0.0.1", 27010),))
			self.error.emit(str(err))
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


			try:
				if not self.newPackets:
					self.oldPacketLoop(data)
				else:
					self.newPacketLoop(data)
			except:
				continue