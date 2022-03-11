import socket, select, struct, os, time, zlib, ini

from PyQt4 import QtCore, QtGui
from ConfigParser import ConfigParser
from pybass import *

import AIOprotocol
from game_version import GAME_VERSION
from AIOMainWindow import AIOMainWindow
from packing import *


class AIOApplication(QtGui.QApplication):
	player_id = -1
	charlist, musiclist, zonelist = [], [], []
	defaultzone = ""
	motd = ""
	music = None
	sound = None
	GUIsound = None
	WTCEsound = None
	sndvol = 100
	musicvol = 100
	blipvol = 100
	fps = 30
	controls = {"up": [QtCore.Qt.Key_W, QtCore.Qt.Key_Up],
                "down": [QtCore.Qt.Key_S, QtCore.Qt.Key_Down],
                "left": [QtCore.Qt.Key_A, QtCore.Qt.Key_Left],
                "right": [QtCore.Qt.Key_D, QtCore.Qt.Key_Right],
                "run": [QtCore.Qt.Key_Shift, -1]}
    
	def __init__(self, argv=[]):
		super(AIOApplication, self).__init__(argv)

		self.tcpthread = ClientThread()
		self.udpthread = UDPThread()
		self.udpthread.start()

		self.musicvol = ini.read_ini_int("aaio.ini", "Audio", "Music volume", 100)
		self.sndvol = ini.read_ini_int("aaio.ini", "Audio", "Sound volume", 100)
		self.blipvol = ini.read_ini_int("aaio.ini", "Audio", "Blip volume", 100)
		self.fps = 60 if ini.read_ini_bool("aaio.ini", "General", "High FPS", True) else 30

		self.mainwindow = AIOMainWindow(self)
		self.mainwindow.show()
	
	def startGame(self, player_id, defaultzone, motd, charlist, musiclist, zonelist, evidencelist):
		self.player_id = player_id
		self.defaultzone = defaultzone
		for i in range(len(zonelist)):
			if zonelist[i][0] == defaultzone:
				self.defaultzoneid = i
		self.motd = motd
		self.charlist = charlist
		self.musiclist = musiclist
		self.zonelist = zonelist
		self.evidencelist = evidencelist
		self.mainwindow.startGame()
	
	def stopGame(self):
		self.stopMusic()
		self.tcpthread.disconnect()
		self.mainwindow.stopGame()
	
	def playMusic(self, file):
		self.stopMusic()
		
		if os.path.exists("data/sounds/music/"+file):
			filename, extension = os.path.splitext(file)
			extension = extension.lower()
			if extension == ".mod" or extension == ".xm" or extension == ".s3m" or extension == ".it":
				self.music = audio.loadmusic(False, "data/sounds/music/"+file)
			else:
				self.music = audio.loadhandle(False, "data/sounds/music/"+file, 0, 0, BASS_SAMPLE_LOOP)

		elif file.lower().startswith("http") or file.lower().startswith("ftp"): # stream from internet
			self.music = audio.loadURLhandle(file)

		if self.music:
			audio.sethandleattr(self.music, BASS_ATTRIB_VOL, self.musicvol / 100.0)
			audio.playhandle(self.music, True)
		
	def playSound(self, file):
		if self.sound:
			if audio.handleisactive(self.sound):
				audio.freehandle(self.sound)
		
		if os.path.exists(file):
			self.sound = audio.loadhandle(False, file, 0, 0, 0)
			audio.sethandleattr(self.sound, BASS_ATTRIB_VOL, self.sndvol / 100.0)
			audio.playhandle(self.sound, True)
	
	def playGUISound(self, file):
		if self.GUIsound:
			if audio.handleisactive(self.GUIsound):
				audio.freehandle(self.GUIsound)
		
		self.GUIsound = audio.loadhandle(False, file, 0, 0, 0)
		audio.sethandleattr(self.GUIsound, BASS_ATTRIB_VOL, self.sndvol / 100.0)
		audio.playhandle(self.GUIsound, True)

	def playWTCESound(self, file):
		if self.WTCEsound:
			if audio.handleisactive(self.WTCEsound):
				audio.freehandle(self.WTCEsound)
		
		self.WTCEsound = audio.loadhandle(False, file, 0, 0, 0)
		audio.sethandleattr(self.WTCEsound, BASS_ATTRIB_VOL, self.sndvol / 100.0)
		audio.playhandle(self.WTCEsound, True)
	
	def stopMusic(self):
		if self.music:
			if audio.handleisactive(self.music):
				audio.freehandle(self.music)
				audio.freemusic(self.music)
			self.music = None
	
	def connect(self, ip, port):
		self.tcpthread.disconnect()
		self.tcpthread.setAddress(ip, port)
		self.tcpthread.start()

class ClientThread(QtCore.QThread):
	disconnected = QtCore.pyqtSignal()
	connectionError = QtCore.pyqtSignal(str)
	gotWelcome = QtCore.pyqtSignal(list)
	gotCharacters = QtCore.pyqtSignal(list)
	gotMusic = QtCore.pyqtSignal(list)
	gotZones = QtCore.pyqtSignal(list)
	gotEvidence = QtCore.pyqtSignal(list)
	evidenceChanged = QtCore.pyqtSignal(list)
	kicked = QtCore.pyqtSignal(str)
	serverWarning = QtCore.pyqtSignal(str)
	movementPacket = QtCore.pyqtSignal(list)
	examinePacket = QtCore.pyqtSignal(list)
	playerCreate = QtCore.pyqtSignal(list)
	playerDestroy = QtCore.pyqtSignal(int)
	musicChange = QtCore.pyqtSignal(list)
	emoteSound = QtCore.pyqtSignal(list)
	OOCMessage = QtCore.pyqtSignal(list)
	ICMessage = QtCore.pyqtSignal(list)
	broadcastMessage = QtCore.pyqtSignal(str)
	chatBubble = QtCore.pyqtSignal(list)
	zoneChange = QtCore.pyqtSignal(list)
	charChange = QtCore.pyqtSignal(list)
	penaltyBar = QtCore.pyqtSignal(list)
	WTCEMessage = QtCore.pyqtSignal(int)
	gotPing = QtCore.pyqtSignal(int)
	
	def __init__(self):
		super(ClientThread, self).__init__()
		self.connected = False
		self.tcp = None
		self.ip = "0"
		self.port = 0
		
	def __del__(self):
		self.disconnect()
		self.wait()
	
	def setAddress(self, ip, port):
		self.ip = ip
		self.port = port
	
	def forceDisconnect(self, error=False):
		self.tcp.close()
		self.connected = False
	
	def disconnect(self, error=False):
		if self.connected:
			self.forceDisconnect(error)
	
	def sendBuffer(self, buf):
		self.tcp.sendall(makeAIOPacket(buf))
	
	def sendWelcome(self):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.CONNECT)
			buf += packString8(GAME_VERSION)
			self.sendBuffer(buf)
	
	def sendRequest(self, type):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.REQUEST)
			buf += struct.pack("B", type)
			self.sendBuffer(buf)
	
	def sendIC(self, chatmsg, blip, color, realization, evidence, showname, message_id):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.MSCHAT)
			buf += packString8(chatmsg)
			buf += packString8(blip)
			buf += struct.pack("I", color)
			buf += struct.pack("B", realization)
			buf += struct.pack("B", evidence)
			buf += packString8(showname)
			buf += struct.pack("I", message_id)
			self.sendBuffer(buf)
	
	def sendOOC(self, name, chatmsg):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.OOC)
			buf += packString8(name)
			buf += packString16(chatmsg)
			self.sendBuffer(buf)
	
	def sendMusicChange(self, filename, showname):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.MUSIC)
			buf += packString16(filename)
			buf += packString8(showname)
			self.sendBuffer(buf)
	
	def sendExamine(self, x, y, showname):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.EXAMINE)
			buf += struct.pack("f", x)
			buf += struct.pack("f", y)
			buf += packString8(showname)
			self.sendBuffer(buf)
	
	def sendChatBubble(self, on):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.CHATBUBBLE)
			buf += struct.pack("B", on)
			self.sendBuffer(buf)
	
	def sendEmoteSound(self, soundname, delay):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.EMOTESOUND)
			buf += packString8(soundname)
			buf += struct.pack("I", delay)
			self.sendBuffer(buf)
	
	def setZone(self, zone):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.SETZONE)
			buf += struct.pack("H", zone)
			self.sendBuffer(buf)
	
	def setChar(self, char):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.SETCHAR)
			buf += struct.pack("h", char)
			self.sendBuffer(buf)
	
	def sendEvidence(self, type, *args):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.EVIDENCE)
			buf += struct.pack("B", type)
			if type == AIOprotocol.EV_ADD:
				name, desc, image = args
				buf += packString8(name)
				buf += packString16(desc)
				buf += packString8(image)
			elif type == AIOprotocol.EV_EDIT:
				ind, name, desc, image = args
				buf += struct.pack("B", ind)
				buf += packString8(name)
				buf += packString16(desc)
				buf += packString8(image)
			elif type == AIOprotocol.EV_DELETE:
				ind, = args
				buf += struct.pack("B", ind)
			else:
				return False
			
			self.sendBuffer(buf)
	
	def sendPenaltyBar(self, bar, health):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.BARS)
			buf += struct.pack("B", bar)
			buf += struct.pack("B", health)
			self.sendBuffer(buf)

	def sendWTCE(self, wtcetype):
		if self.connected:
			buf = struct.pack("B", AIOprotocol.WTCE)
			buf += struct.pack("B", wtcetype)
			self.sendBuffer(buf)
	
	def sendMovement(self, x, y, hspeed, vspeed, sprite, emoting, dir_nr, currentemote):
		if self.connected:
			self.lastSendTime = time.time()
			buf = struct.pack("B", AIOprotocol.MOVE)
			buf += struct.pack("f", x)
			buf += struct.pack("f", y)
			buf += struct.pack("h", hspeed)
			buf += struct.pack("h", vspeed)
			buf += packString16(sprite)
			buf += struct.pack("B", emoting)
			buf += struct.pack("B", dir_nr)
			buf += struct.pack("B", currentemote+1)
			self.sendBuffer(buf)
	
	def sendPing(self):
		if self.connected:
			self.pingbefore = time.time()

			buf = struct.pack("B", AIOprotocol.PING)
			self.sendBuffer(buf)
	
	def run(self):
		tempdata = ""
		connection_phase = 0
		self.pingbefore = 0
		self.lastSendTime = time.time()
		self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.tcp.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
		
		try:
			self.tcp.connect((self.ip, self.port))
		except socket.error as err:
			self.connectionError.emit("Unable to connect to the selected server.\nAdditional information: %s" % err)
			self.forceDisconnect()
			return
		
		self.connected = True
		self.tcp.setblocking(False)
		self.sendWelcome()
		
		while self.connected and self.tcp:
			ready = select.select([self.tcp], [], [], 3)
			if not ready[0]:
				continue

			try:
				data = ready[0][0].recv(4)
			except socket.error, err:
				if err.errno in (10035, 11) or err.args[0] == "timed out":
					continue
				else:
					if self.connected:
						self.connectionError.emit("The connection to the server has been lost.\nAdditional information: %s" % err)
						self.disconnect()
						break

			if len(data) < 4: # we need these 4 bytes to read the packet length
				continue

			bufflength = 0
			compression = 0
			try:
				bufflength, compression = readAIOHeader(data)
				data = ""
				while len(data) < bufflength:
					ready = select.select([self.tcp], [], [], 3)
					if not ready[0]:
						continue
					recvd = ready[0][0].recv(bufflength)
					data += recvd
			except socket.error as err:
				if err.errno in (10035, 11) or err.args[0] == "timed out":
					continue
				else:
					if self.connected:
						self.connectionError.emit("The connection to the server has been lost.\nAdditional information: %s" % err)
						self.disconnect()
						break
			except (MemoryError, OverflowError, struct.error):
				continue

			if compression == 1:
				data = zlib.decompress(data)

			while data:
				data, header = buffer_read("B", data)
				#for a in dir(AIOprotocol):
					#if getattr(AIOprotocol, a) == header and not "EV_" in a and not a in ("SOUTH", "SOUTHWEST", "SOUTHEAST", "EAST", "NORTH", "NORTHWEST", "NORTHEAST", "WEST"): print repr(a), repr(data)
				
				if header == AIOprotocol.CONNECT and connection_phase == 0: #server default zone, maximum characters, MOTD...
					data, player_id = buffer_read("I", data)
					data, maxchars = buffer_read("I", data)
					data, defaultzone = unpackString8(data)
					data, maxmusic = buffer_read("I", data)
					data, maxzones = buffer_read("I", data)
					data, motd = unpackString16(data)

					self.gotWelcome.emit([player_id, maxchars, defaultzone, maxmusic, maxzones, motd.replace("#", "\n").replace("\\#", "#")])
					connection_phase += 1
					self.sendRequest(0)
				
				elif header == AIOprotocol.REQUEST and connection_phase < 5:
					data, type = buffer_read("B", data)
					
					if type == 0: #characters
						charlist = []
						for i in range(maxchars):
							data, char = unpackString16(data)
							charlist.append(char)
						if connection_phase == 1:
							connection_phase += 1
							self.gotCharacters.emit(charlist)
							self.sendRequest(1)
					
					elif type == 1: #music
						musiclist = []
						for i in range(maxmusic):
							data, music = unpackString16(data)
							musiclist.append(music)
						if connection_phase == 2:
							connection_phase += 1
							self.gotMusic.emit(musiclist)
							self.sendRequest(2)
					
					elif type == 2: #zones
						zonelist = []
						for i in range(maxzones):
							data, zone = unpackString8(data)
							data, zonename = unpackString16(data)
							zonelist.append([zone, zonename])
						if connection_phase == 3:
							connection_phase += 1
							self.gotZones.emit(zonelist)
							self.sendRequest(3)
					
					elif type == 3: #evidence for spawn zone
						data, length = buffer_read("B", data)
						evidencelist = []
						for i in range(length):
							data, name = unpackString8(data)
							data, desc = unpackString16(data)
							data, image = unpackString8(data)
							evidencelist.append([name.decode("utf-8"), desc.decode("utf-8"), image.decode("utf-8")])
						if connection_phase == 4:
							connection_phase += 1
							self.gotEvidence.emit(evidencelist)
						
				elif header == AIOprotocol.KICK: #kicked.
					data, reason = unpackString16(data)
					self.kicked.emit(reason.replace("#", "\n").replace("\\#", "#")) #AIO was made in Game Maker 8, so it used hashes as newlines
					self.disconnect()
				
				elif header == AIOprotocol.MUSIC: #music change
					data, filename = unpackString16(data)
					data, char_id = buffer_read("I", data)
					data, showname = unpackString8(data)
					
					self.musicChange.emit([filename, char_id, showname])
					
				elif header == AIOprotocol.CREATE: #a player joins
					data, otherplayer = buffer_read("I", data)
					data, charid = buffer_read("h", data)
					data, zone = buffer_read("H", data)
					if otherplayer == player_id:
						continue
					
					self.playerCreate.emit([otherplayer, charid, zone])
				
				elif header == AIOprotocol.DESTROY: #a player leaves
					try:
						data, otherplayer = buffer_read("I", data)
					except struct.error: continue

					if otherplayer == player_id:
						continue
					
					self.playerDestroy.emit(otherplayer)
				
				elif header == AIOprotocol.EMOTESOUND:
					data, client_id = buffer_read("I", data)
					data, filename = unpackString8(data)
					data, sfx_delay = buffer_read("I", data)
					
					self.emoteSound.emit([client_id, filename, sfx_delay])
				
				elif header == AIOprotocol.MOVE: #player movements
					movepacket = []
					data, clients = buffer_read("H", data)
					for i in range(clients):
						data, client = buffer_read("I", data)
						data, x = buffer_read("f", data)
						data, y = buffer_read("f", data)
						data, hspeed = buffer_read("h", data)
						data, vspeed = buffer_read("h", data)
						data, sprite = unpackString16(data)
						data, emoting = buffer_read("B", data)
						data, dir_nr = buffer_read("B", data)
						data, currentemote = buffer_read("B", data)
						#print "client %d: %.2f %.2f %d %d %r %d %d %d" % (client, x, y, hspeed, vspeed, sprite, emoting, dir_nr, currentemote-1)
						movepacket.append([client, x, y, hspeed, vspeed, sprite, emoting, dir_nr, currentemote-1])
					self.movementPacket.emit(movepacket)
			
				elif header == AIOprotocol.SETZONE:
					data, client = buffer_read("H", data)
					data, zone = buffer_read("H", data)
					self.zoneChange.emit([client, zone])
				
				elif header == AIOprotocol.SETCHAR:
					data, client = buffer_read("H", data)
					data, charid = buffer_read("h", data)
					self.charChange.emit([client, charid])
				
				elif header == AIOprotocol.EXAMINE:
					data, char_id = buffer_read("H", data)
					data, zone = buffer_read("H", data)
					data, x = buffer_read("f", data)
					data, y = buffer_read("f", data)
					data, showname = unpackString8(data)
					self.examinePacket.emit([char_id, zone, x, y, showname])
				
				elif header == AIOprotocol.OOC:
					data, name = unpackString8(data)
					data, message = unpackString16(data)
					self.OOCMessage.emit([name.decode("utf-8"), message.decode("utf-8")])
				
				elif header == AIOprotocol.MSCHAT:
					data, name = unpackString8(data)
					data, chatmsg = unpackString8(data)
					data, blip = unpackString8(data)
					data, zone = buffer_read("I", data)
					data, color = buffer_read("I", data)
					data, realization = buffer_read("B", data)
					data, clientid = buffer_read("I", data)
					data, evidence = buffer_read("B", data)
					
					self.ICMessage.emit([name, chatmsg, blip, zone, color, realization, clientid, evidence])
				
				elif header == AIOprotocol.BROADCAST:
					data, message = unpackString16(data)
					self.broadcastMessage.emit(message)
				
				elif header == AIOprotocol.CHATBUBBLE:
					data, cid = buffer_read("I", data)
					data, on = buffer_read("B", data)
					self.chatBubble.emit([cid, on])
				
				elif header == AIOprotocol.EVIDENCE:
					data, type = buffer_read("B", data)
					data, zone = buffer_read("B", data)
					ev_msg = [type, zone]
					
					if type == AIOprotocol.EV_ADD:
						data, name = unpackString8(data)
						data, desc = unpackString16(data)
						data, image = unpackString8(data)
						ev_msg.extend([name.decode("utf-8"), desc.decode("utf-8"), image.decode("utf-8")])
					elif type == AIOprotocol.EV_EDIT:
						data, ind = buffer_read("B", data)
						data, name = unpackString8(data)
						data, desc = unpackString16(data)
						data, image = unpackString8(data)
						ev_msg.extend([ind, name.decode("utf-8"), desc.decode("utf-8"), image.decode("utf-8")])
					elif type == AIOprotocol.EV_DELETE:
						data, ind = buffer_read("B", data)
						ev_msg.append(ind)
					elif type == AIOprotocol.EV_FULL_LIST:
						data, length = buffer_read("B", data)
						for i in range(length):
							data, name = unpackString8(data)
							data, desc = unpackString16(data)
							data, image = unpackString8(data)
							ev_msg.append([name.decode("utf-8"), desc.decode("utf-8"), image.decode("utf-8")])
					
					self.evidenceChanged.emit(ev_msg)
				
				elif header == AIOprotocol.WARN:
					data, message = unpackString16(data)
					self.serverWarning.emit(message.decode("utf-8"))
				
				elif header == AIOprotocol.BARS:
					data, bar = buffer_read("B", data)
					data, health = buffer_read("B", data)
					self.penaltyBar.emit([bar, health])

				elif header == AIOprotocol.WTCE:
					data, wtcetype = buffer_read("B", data)
					self.WTCEMessage.emit(wtcetype)
				
				elif header == AIOprotocol.PING:
					pingafter = time.time()
					self.gotPing.emit(int((pingafter - self.pingbefore)* 1000))
				
				if data:
					if data[0] == "\r":
						data = data[1:]


class UDPThread(QtCore.QThread):
	gotInfoRequest = QtCore.pyqtSignal(list)

	def __init__(self):
		super(UDPThread, self).__init__()
		self.udp = None
		self.end = False
		self.pings = {}

	def __del__(self):
		self.end = True
		self.wait()

	def sendBuffer(self, buf, addr):
		port = addr[1]
		if type(port) != int:
			port = int(port)
		self.udp.sendto(buf, (addr[0], port))

	def sendInfoRequest(self, addr):
		addr = (addr[0], int(addr[1]))
		self.pings[addr] = time.time()

		data = struct.pack("B", AIOprotocol.UDP_REQUEST)
		self.sendBuffer(data, addr)

	def run(self):
		self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.udp.settimeout(0.1)
		self.end = False

		while not self.end and self.udp:
			try:
				data, addr = self.udp.recvfrom(65535)
			except socket.error, err:
				if err.errno in (10035, 10054, 11) or err.args[0] == "timed out":
					continue
				print err.errno

			data = zlib.decompress(data)
			data, header = buffer_read("B", data)

			if header == AIOprotocol.UDP_REQUEST:
				data, name = unpackString16(data)
				data, desc = unpackString16(data)
				data, players = buffer_read("I", data)
				data, maxplayers = buffer_read("I", data)
				data, version = buffer_read("H", data)

				ping = "999"
				sentPing = addr in self.pings
				isLAN = False
				for sv in self.pings:
					if sv[0] == "<broadcast>" and sv[1] == addr[1]:
						sentPing = isLAN = True
						break

				addrKey = addr if not isLAN else ("<broadcast>", addr[1])

				if sentPing:
					pingbefore = self.pings[addrKey]
					pingafter = time.time()
					ping = "%d" % ((pingafter - pingbefore)* 1000)
					del self.pings[addrKey]

				self.gotInfoRequest.emit([addr, name, desc, players, maxplayers, version, ping])