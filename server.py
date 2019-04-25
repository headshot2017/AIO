import socket, thread, iniconfig, os, sys, struct, urllib, time
import AIOprotocol
from AIOplayer import AIOplayer, AIObot

################################
GameVersion = "0.3.1" # you can modify this so that it matches the version you want to make your server compatible with
AllowVersionMismatch = False # change this to 'True' (case-sensitive) to allow clients with a different version than your server to join (could raise problems)
ServerOOCName = "$SERVER" # the ooc name that the server will use to respond to OOC commands and the like
MaxLoginFails = 3 # this amount of consecutive fails on the /login command or ECON password will kick the user
EmoteSoundRateLimit = 1 #amount of ticks to wait before allowing to use emotes with sound again
MusicRateLimit = 3 #same as above, to prevent spam, but for music
ExamineRateLimit = 2 #same as above, but for Examine

AllowBot = True # set this to True to allow usage of the /bot command (NOTE: to use these bots you MUST have the client data on the server so that it can get the character data)
################################

############CONSTANTS#############
ECONSTATE_CONNECTED = 0
ECONSTATE_AUTHED = 1
ECONCLIENT_CRLF = 0
ECONCLIENT_LF = 1
MASTER_WAITINGSUCCESS = 0
################################

def plural(text, value):
	return text+"s" if value != 1 else text

def isNumber(text):
	try:
		int(text)
		return True
	except:
		return False

def string_unpack(buf):
	unpacked = buf.split("\0")[0]
	gay = list(buf)
	for l in range(len(unpacked+"\0")):
		try:
			del gay[0]
		except:
			break
	return "".join(gay), unpacked

def buffer_read(format, buffer):
	if format != "S":
		unpacked = struct.unpack_from(format, buffer)
		size = struct.calcsize(format)
		liss = list(buffer)
		for l in range(size):
			del liss[0]
		returnbuffer = "".join(liss)
		return returnbuffer, unpacked[0]
	else:
		return string_unpack(buffer)

def versionToInt(ver):
	v = ver.split(".")
	major = v[0]
	minor = v[1]
	if len(v) > 2:
		patch = v[2]
	else:
		patch = "0"
	
	try:
		return int(minor+major+patch)
	except:
		return int(major+minor+"0")

def versionToStr(ver):
	major = ver[1]
	minor = ver[0]
	if len(ver) > 2:
		patch = ver[2]
	else:
		return major+"."+minor
	
	return  major+"."+minor+"."+patch

class AIOserver(object):
	running = False
	tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	readbuffer = ""
	econTemp = ""
	clients = {}
	econ_clients = {}
	musiclist = []
	charlist = []
	zonelist = []
	evidencelist = []
	banlist = []
	defaultzone = 0
	maxplayers = 1
	MSstate = -1
	ic_finished = True
	def __init__(self):
		global AllowBot
		if AllowBot and not os.path.exists("data/characters"):
			AllowBot = False
		
		if not os.path.exists("server/base.ini"):
			print "[warning]", "server/base.ini not found, creating file..."
			with open("server/base.ini", "w") as f:
				f.write("[Server]\n")
				f.write("name=unnamed server\n")
				f.write("desc=automatically generated base.ini file\n")
				f.write("port=27010\n")
				f.write("scene=default\n")
				f.write("motd=Welcome to my server!##Overview of in-game controls:#WASD keys - move#Shift - run##Have fun!\n")
				f.write("publish=1\n")
				f.write("evidence_limit=255\n")
				f.write("rcon=theadminpassword")
				
		ini = iniconfig.IniConfig("server/base.ini")
		self.servername = ini.get("Server", "name", "unnamed server")
		self.serverdesc = ini.get("Server", "desc", "automatically generated base.ini file")
		self.port = int(ini.get("Server", "port", "27010"))
		self.scene = ini.get("Server", "scene", "default")
		self.motd = ini.get("Server", "motd", "Welcome to my server!##Overview of in-game controls:#Arrow keys or WASD keys - move#Shift - run#ESC or close button - quit#Spacebar - show emotes bar#T key - IC chat (Check the options menu to change this)##Musiclist controls:#Arrow keys - select song#Enter - play selected song##Have fun!")
		self.publish = int(ini.get("Server", "publish", "1"))
		self.evidence_limit = int(ini.get("Server", "evidence_limit", "255"))
		self.ms_addr = ini.get("MasterServer", "ip", "headshot.iminecraft.se:27011").split(":")
		if len(self.ms_addr) == 1:
			self.ms_addr.append("27011")
		try:
			self.ms_addr[1] = int(self.ms_addr[1])
		except:
			self.ms_addr[1] = 27011
		self.rcon = ini.get("Server", "rcon", "")
		self.econ_port = int(ini.get("ECON", "port", "27000"))
		self.econ_password = ini.get("ECON", "password", "")
	
		if not os.path.exists("server/scene/"+self.scene) or not os.path.exists("server/scene/"+self.scene+"/init.ini"):
			print "[warning]", "scene %s does not exist, switching to 'default'" % self.scene
			self.scene = "default"
			if not os.path.exists("server/scene/"+self.scene) or not os.path.exists("server/scene/"+self.scene+"/init.ini"):
				print "[error]", "scene 'default' does not exist, cannot continue loading!"
				sys.exit()
		
		scene_ini = iniconfig.IniConfig("server/scene/"+self.scene+"/init.ini")
		self.maxplayers = int(scene_ini.get("chars", "total", 14))
		zonelength = int(scene_ini.get("background", "total", 1))
		self.charlist = [scene_ini.get("chars", str(char), "Edgeworth") for char in range(1, self.maxplayers+1)]
		self.zonelist = [[scene_ini.get("background", str(zone), "gk1hallway"), scene_ini.get("background", str(zone)+"_name", "Prosecutor's Office hallway")] for zone in range(1, zonelength+1)]
		for i in range(len(self.zonelist)):
			self.evidencelist.append([])
		
		self.defaultzone = int(scene_ini.get("background", "default", 1))-1
		if not os.path.exists("server/musiclist.txt"):
			self.musiclist = ["musiclist.txt not found", "could not add music"]
		else:
			self.musiclist = [music.rstrip() for music in open("server/musiclist.txt")]
		
		if os.path.exists("server/banlist.txt"):
			with open("server/banlist.txt") as f:
				self.banlist = [ban.rstrip().split(":") for ban in f]
		
		for ban in self.banlist:
			ban[1] = int(ban[1]) #time left in minutes
	
	def getCharName(self, charid):
		if charid != -1:
			return self.charlist[charid]
		else:
			return "CHAR_SELECT"
	
	def acceptClient(self):
		try:
			client, ipaddr = self.tcp.accept()
		except socket.error:
			return
			
		for i in range(self.maxplayers):
			if not self.clients.has_key(i):
				self.econPrint("[game] incoming connection from %s (%d)" % (ipaddr[0], i))
				self.clients[i] = AIOplayer(client, ipaddr[0])
				
				for bans in self.banlist:
					if bans[0] == ipaddr[0]:
						if bans[1] > 0:
							min = abs(time.time() - bans[1]) / 60
							mintext = plural("minute", min+1)
							self.kick(i, "You have been banned for %d %s: %s" % (min+1, mintext, bans[2]))
						else:
							self.kick(i, "You have been banned for life: %s" % bans[2])
						return
				
				if ipaddr[0].startswith("127."): #localhost
					self.clients[i].is_authed = True
				self.sendToMasterServer("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys()))+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%")
				return
		
		self.kick(client, "Server is full.")
	
	def sendBuffer(self, clientID, buffer):
		try:
			return self.clients[clientID].sock.sendall(buffer+"\r")
		except (socket.error, socket.timeout) as e:
			#print "socket error %d" % e.args[0]
			return 0
		
	def sendWelcome(self, ClientID):
		if not self.running:
			print "[error]", "tried to use sendWelcome() without server running"
			return
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.CONNECT)
		buffer += struct.pack("I", ClientID)
		buffer += struct.pack("I", self.maxplayers)
		buffer += self.zonelist[self.defaultzone][0]+"\0"
		buffer += struct.pack("I", len(self.musiclist))
		buffer += struct.pack("I", len(self.zonelist))
		buffer += self.motd+"\0"
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		return self.sendBuffer(ClientID, buffer)
	
	def sendChat(self, name, chatmsg, blip, zone, color, realization, clientid, evidence, ClientID=-1):
		if not self.running:
			print "[error]", "tried to use sendChat() without server running"
			return
		
		self.econPrint("[chat][IC] %d,%d,%s: %s" % (clientid,zone,name, chatmsg))
		thread.start_new_thread(self.ic_tick_thread, (chatmsg,))
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.MSCHAT)
		buffer += name+"\0"
		buffer += chatmsg+"\0"
		buffer += blip+"\0"
		buffer += struct.pack("I", zone)
		buffer += struct.pack("I", color)
		buffer += struct.pack("B", realization)
		buffer += struct.pack("I", clientid)
		buffer += struct.pack("B", evidence)
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		if ClientID == -1:
			for client in self.clients.keys():
				if self.clients[client].isBot() or self.clients[client].zone != zone:
					continue
				self.sendBuffer(client, buffer)
		else:
			return self.sendBuffer(ClientID, buffer)
	
	def sendCreate(self, ClientID):
		if not self.running:
			print "[error]", "tried to use sendCreate() without server running"
			return
		
		for client in self.clients.keys():
			if client == ClientID:
				continue
			
			if not self.clients[client].isBot():
				buffer = ""
				buffer += struct.pack("B", AIOprotocol.CREATE)
				buffer += struct.pack("I", ClientID)
				buffer += struct.pack("h", self.clients[ClientID].CharID)
				buffer += struct.pack("H", self.clients[ClientID].zone)
				buff = struct.pack("I", len(buffer)+1)
				buff += buffer
				self.sendBuffer(client, buffer)
			
			if not self.clients[ClientID].isBot():
				buffer = ""
				buffer += struct.pack("B", AIOprotocol.CREATE)
				buffer += struct.pack("I", client)
				buffer += struct.pack("h", self.clients[client].CharID)
				buffer += struct.pack("H", self.clients[client].zone)
				buff = struct.pack("I", len(buffer)+1)
				buff += buffer
				self.sendBuffer(ClientID, buffer)
	
	def sendDestroy(self, ClientID):
		if not self.running:
			print "[error]", "tried to use sendDestroy() without server running"
			return
		
		for client in self.clients.keys():
			if client == ClientID:
				continue
			
			if not self.clients[client].isBot():
				buffer = ""
				buffer += struct.pack("B", AIOprotocol.DESTROY)
				buffer += struct.pack("I", ClientID)
				buff = struct.pack("I", len(buffer)+1)
				buff += buffer
				self.sendBuffer(client, buffer)
			
			"""
			if not self.clients[ClientID].isBot():
				buffer = ""
				buffer += struct.pack("B", AIOprotocol.DESTROY)
				buffer += struct.pack("I", client)
				buff = struct.pack("I", len(buffer)+1)
				buff += buffer
				self.clients[ClientID].sock.sendall(buffer+"\r")
			"""
	
	def sendCharList(self, ClientID):
		if not self.running:
			print "[error]", "tried to use sendCharList() without server running"
			return
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.REQUEST)
		buffer += struct.pack("B", 0)
		for char in self.charlist:
			buffer += char+"\0"
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		self.sendBuffer(ClientID, buffer)
	
	def sendMusicList(self, ClientID):
		if not self.running:
			print "[error]", "tried to use sendMusicList() without server running"
			return
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.REQUEST)
		buffer += struct.pack("B", 1)
		for song in self.musiclist:
			buffer += song+"\0"
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		self.sendBuffer(ClientID, buffer)
	
	def sendZoneList(self, ClientID):
		if not self.running:
			print "[error]", "tried to use sendZoneList() without server running"
			return
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.REQUEST)
		buffer += struct.pack("B", 2)
		for zone in self.zonelist:
			buffer += zone[0]+"\0"
			buffer += zone[1]+"\0"
		buffer += struct.pack("H", self.defaultzone)
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		self.sendBuffer(ClientID, buffer)
	
	def sendEvidenceRequest(self, ClientID):
		if not self.running:
			print "[error]", "tried to use sendEvidenceRequest() without server running"
			return
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.REQUEST)
		buffer += struct.pack("B", 3)
		buffer += struct.pack("B", len(self.evidencelist[self.defaultzone]))
		for evidence in self.evidencelist[self.defaultzone]:
			buffer += evidence[0]+"\0"
			buffer += evidence[1]+"\0"
			buffer += evidence[2]+"\0"
		
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		self.sendBuffer(ClientID, buffer)
	
	def sendEvidenceList(self, ClientID, zone):
		if not self.running:
			print "[error]", "tried to use sendEvidenceList() without server running"
			return
		
		buffer = struct.pack("B", AIOprotocol.EVIDENCE)
		buffer += struct.pack("B", AIOprotocol.EV_FULL_LIST)
		buffer += struct.pack("B", zone)
		buffer += struct.pack("B", len(self.evidencelist[zone]))
		for evidence in self.evidencelist[zone]:
			buffer += evidence[0]+"\0"
			buffer += evidence[1]+"\0"
			buffer += evidence[2]+"\0"
		
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		self.sendBuffer(ClientID, buffer)
	
	def addEvidence(self, zone, name, desc, image):
		if not self.running:
			print "[error]", "tried to use addEvidence() without server running"
			return
		
		self.evidencelist[zone].append([name, desc, image])
		
		buffer = struct.pack("B", AIOprotocol.EVIDENCE)
		buffer += struct.pack("B", AIOprotocol.EV_ADD)
		buffer += struct.pack("B", zone)
		buffer += name+"\0"
		buffer += desc+"\0"
		buffer += image+"\0"
		
		for client in self.clients:
			if self.clients[client].isBot() or self.clients[client].zone != zone:
				continue
			self.sendBuffer(client, buffer)
	
	def editEvidence(self, zone, ind, name, desc, image):
		if not self.running:
			print "[error]", "tried to use editEvidence() without server running"
			return
		
		try:
			self.evidencelist[zone][ind] = [name, desc, image]
		except:
			print "[error]", "tried to edit evidence %d on zone %d but failed" % (ind, zone)
			return
		
		buffer = struct.pack("B", AIOprotocol.EVIDENCE)
		buffer += struct.pack("B", AIOprotocol.EV_EDIT)
		buffer += struct.pack("B", zone)
		buffer += struct.pack("B", ind)
		buffer += name+"\0"
		buffer += desc+"\0"
		buffer += image+"\0"
		
		for client in self.clients:
			if self.clients[client].isBot() or self.clients[client].zone != zone:
				continue
			self.sendBuffer(client, buffer)
	
	def deleteEvidence(self, zone, ind):
		if not self.running:
			print "[error]", "tried to use deleteEvidence() without server running"
			return
		
		try:
			del self.evidencelist[zone][ind]
		except:
			print "[error]", "tried to delete evidence %d on zone %d but failed" % (ind, zone)
			return
		
		buffer = struct.pack("B", AIOprotocol.EVIDENCE)
		buffer += struct.pack("B", AIOprotocol.EV_DELETE)
		buffer += struct.pack("B", zone)
		buffer += struct.pack("B", ind)
		
		for client in self.clients:
			if self.clients[client].isBot() or self.clients[client].zone != zone:
				continue
			self.sendBuffer(client, buffer)
	
	def sendEmoteSound(self, charid, filename, delay, zone, ClientID=-1):
		if not self.running:
			print "[error]", "tried to use sendEmoteSound() without server running"
			return
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.EMOTESOUND)
		buffer += struct.pack("i", charid)
		buffer += filename+"\0"
		buffer += struct.pack("I", delay)
		buffer += struct.pack("H", zone)
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		if ClientID == -1:
			for client in self.clients:
				if self.clients[client].isBot():
					continue
				self.sendBuffer(client, buffer)
		else:
			return self.sendBuffer(ClientID, buffer)
	
	def sendEmoteSoundOwner(self, charid, filename, delay, zone, owner):
		if not self.running:
			print "[error]", "tried to use sendEmoteSoundOwner() without server running"
			return
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.EMOTESOUND)
		buffer += struct.pack("i", charid)
		buffer += filename+"\0"
		buffer += struct.pack("I", delay)
		buffer += struct.pack("H", zone)
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		for client in self.clients:
			if self.clients[client].isBot() or owner == client:
				continue
			self.sendBuffer(client, buffer)

	def setChatBubble(self, ClientID, on):
		if not self.running:
			print "[error]", "tried to use setChatBubble() without server running"
			return
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.CHATBUBBLE)
		buffer += struct.pack("I", ClientID)
		buffer += struct.pack("B", on)
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		for client in self.clients:
			if self.clients[client].isBot():
				continue
			self.sendBuffer(client, buffer)
	
	def sendOOC(self, name, chatmsg, ClientID=-2, zone=-1):
		if not self.running:
			print "[error]", "tried to use sendOOC() without server running"
			return
		
		if ClientID == -1: #console input
			print chatmsg
			return
		
		elif ClientID >= 10000: #ECON input
			econID = ClientID - 10000
			self.econPrint(chatmsg, econID)
			return
		
		if self.econ_password and ClientID == -2:
			aClient = -1
			for i in self.clients.keys():
				if self.clients[i].OOCname == name:
					aClient = i
			self.econPrint("[chat][OOC] %d,%d,%s: %s" % (aClient, zone, name, chatmsg))
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.OOC)
		buffer += name+"\0"
		buffer += chatmsg+"\0"
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		if ClientID == -2:
			for client in self.clients:
				if self.clients[client].isBot() or (zone != self.clients[client].zone and zone >= 0):
					continue
				self.sendBuffer(client, buffer)
		else:
			return self.sendBuffer(ClientID, buffer)
	
	def sendWarning(self, client, reason):
		if not self.running:
			print "[error]", "tried to use sendWarning() without server running"
			return
		
		buffer = struct.pack("B", AIOprotocol.WARN)
		buffer += reason+"\0"
		
		self.sendBuffer(client, buffer)
		
	def sendBroadcast(self, message, zone=-1, ClientID=-1):
		if not self.running:
			print "[error]", "tried to use sendBroadcast() without server running"
			return
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.BROADCAST)
		buffer += struct.pack("h", zone)
		buffer += message+"\0"
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		if ClientID == -1:
			for client in self.clients:
				if self.clients[client].isBot():
					continue
				if zone == -1:
					self.sendBuffer(client, buffer)
				else:
					if self.clients[client].zone == zone:
						self.sendBuffer(client, buffer)
		else:
			if zone == -1:
				return self.sendBuffer(ClientID, buffer)
			else:
				if self.clients[ClientID].zone != zone:
					print "[warning]", "tried to perform sendBroadcast() on zone %d, to client %d but that client is in zone %d" % (zone, ClientID, self.clients[ClientID].zone)
				else:
					return self.sendBuffer(ClientID, buffer)
	
	def kick(self, ClientID, reason="No reason given"):
		if not self.running:
			print "[error]", "tried to use kick() without server running"
			return
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.KICK)
		buffer += reason+"\0"
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		if isinstance(ClientID, socket.socket):
			self.ClientID.sendall(buffer+"\r")
			self.econPrint("[game] kicked client %s: %s" % (ClientID.getpeername()[0], reason))
		else:
			self.sendBuffer(ClientID, buffer)
			self.econPrint("[game] kicked client %d (%s): %s" % (ClientID, self.getCharName(self.clients[ClientID].CharID), reason))
			self.sendToMasterServer("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys())-1)+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%")
			del self.clients[ClientID]
	
	def ban(self, ClientID, length, reason):
		if not self.running:
			print "[error]", "tried to use ban() without server running"
			return
		
		if time.time() > length and length > 0:
			return
		
		if length > 0:
			min = abs(time.time() - length) / 60
		else:
			min = 0
		mintext = plural("minute", min+1)
		
		if type(ClientID) == str:
			if "." in ClientID: # if it's an ip address
				for i in self.clients.keys(): #let's check if a player with that IP is playing here
					if self.clients[i].ip == ClientID: #lol bad hiding spot found
						if length > 0:
							self.kick(i, "You have been banned for %d %s: %s" % (min+1, mintext, reason))
						else:
							self.kick(i, "You have been banned for life: %s" % reason)
						break
				self.banlist.append([ClientID, length, reason])
		
		else: #if it isn't an ip...
			self.banlist.append([self.clients[ClientID].ip, length, reason])
			if length > 0:
				self.kick(ClientID, "You have been banned for %d %s: %s" % (min+1, mintext, reason))
			else:
				self.kick(ClientID, "You have been banned for life: %s" % reason)
		
		self.econPrint("[bans] banned %s for %d min (%s) " % (self.banlist[-1][0], min+1, reason))
		self.writeBanList()
		
	def changeMusic(self, filename, charid, zone=-1, ClientID=-1):
		if not self.running:
			print "[error]", "tried to use changeMusic() without server running"
			return
		
		buffer = ""
		buffer += struct.pack("B", AIOprotocol.MUSIC)
		buffer += filename+"\0"
		buffer += struct.pack("I", charid)
		buffer += struct.pack("H", zone)
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		if ClientID == -1:
			for client in self.clients:
				if self.clients[client].isBot():
					continue
				if zone == -1:
					self.sendBuffer(client, buffer)
				else:
					if self.clients[client].zone == zone:
						self.sendBuffer(client, buffer)
		else:
			if zone == -1:
				return self.sendBuffer(ClientID, buffer)
			else:
				if self.clients[ClientID].zone != zone:
					print "[warning]", "tried to perform changeMusic() on zone %d, to client %d but that client is in zone %d" % (zone, ClientID, self.clients[ClientID].zone)
				else:
					return self.sendBuffer(ClientID, buffer)
	
	def setPlayerZone(self, ClientID, zone):
		if not self.running:
			print "[error]", "tried to use setPlayerZone() without server running"
			return
			
		self.clients[ClientID].zone = zone
		buffer = struct.pack("B", AIOprotocol.SETZONE)
		buffer += struct.pack("H", ClientID)
		buffer += struct.pack("H", zone)
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		for client in self.clients.keys():
			if self.clients[client].ready and not self.clients[client].isBot():
				self.sendBuffer(client, buffer)
		
	def setPlayerChar(self, ClientID, charid):
		if not self.running:
			print "[error]", "tried to use setPlayerChar() without server running"
			return
		
		self.clients[ClientID].CharID = charid
		buffer = struct.pack("B", AIOprotocol.SETCHAR)
		buffer += struct.pack("H", ClientID)
		buffer += struct.pack("h", charid)
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		for client in self.clients.keys():
			if self.clients[client].ready and not self.clients[client].isBot():
				self.sendBuffer(client, buffer)
	
	def sendExamine(self, charid, zone, x, y, ClientID=-1):
		if not self.running:
			print "[error]", "tried to use sendExamine() without server running"
			return
		
		buffer = struct.pack("B", AIOprotocol.EXAMINE)
		buffer += struct.pack("H", charid)
		buffer += struct.pack("H", zone)
		buffer += struct.pack("f", x)
		buffer += struct.pack("f", y)
		buff = struct.pack("I", len(buffer)+1)
		buff += buffer
		
		if ClientID != -1:
			self.sendBuffer(ClientID, buffer)
		else:
			for client in self.clients:
				if self.clients[client].isBot():
					continue
				self.sendBuffer(client, buffer)
	
	def sendBotMovement(self, botID):
		buffer = struct.pack("B", AIOprotocol.MOVE)
		emptybuffer = buffer
		
		buffer += struct.pack("I", botID)
		buffer += struct.pack("f", self.clients[botID].x)
		buffer += struct.pack("f", self.clients[botID].y)
		buffer += struct.pack("h", self.clients[botID].hspeed)
		buffer += struct.pack("h", self.clients[botID].vspeed)
		buffer += self.clients[botID].sprite+"\0"
		buffer += struct.pack("B", self.clients[botID].emoting)
		buffer += struct.pack("B", self.clients[botID].dir_nr)
		
		if buffer == emptybuffer:
			return
		
		for client in self.clients.keys():
			if not self.clients[client].isBot() and self.clients[client].ready and client != botID:
				self.sendBuffer(client, buffer)
	
	def sendMovement(self, ClientID, sourceID=-1):
		buffer = struct.pack("B", AIOprotocol.MOVE)
		emptybuffer = buffer
		
		if sourceID == -1:
			for client in self.clients.keys():
				if client == ClientID or not self.clients[client].ready or not self.clients[client].first_picked or not self.clients[client].sprite:
					continue
				
				buffer += struct.pack("I", client)
				buffer += struct.pack("f", self.clients[client].x)
				buffer += struct.pack("f", self.clients[client].y)
				buffer += struct.pack("h", self.clients[client].hspeed)
				buffer += struct.pack("h", self.clients[client].vspeed)
				buffer += self.clients[client].sprite+"\0"
				buffer += struct.pack("B", self.clients[client].emoting)
				buffer += struct.pack("B", self.clients[client].dir_nr)
		
		else:
			if not self.clients.has_key(sourceID):
				print "[warning]", "tried to sendMovement() to client %d from source client %d, but the source client ID doesn't exist" % (ClientID, source)
				return
			
			buffer += struct.pack("I", sourceID)
			buffer += struct.pack("f", self.clients[sourceID].x)
			buffer += struct.pack("f", self.clients[sourceID].y)
			buffer += struct.pack("h", self.clients[sourceID].hspeed)
			buffer += struct.pack("h", self.clients[sourceID].vspeed)
			buffer += self.clients[sourceID].sprite+"\0"
			buffer += struct.pack("B", self.clients[sourceID].emoting)
			buffer += struct.pack("B", self.clients[sourceID].dir_nr)
		
		if buffer == emptybuffer:
			return
		
		self.sendBuffer(ClientID, buffer)
	
	def startMasterServerAdverter(self):
		print "[masterserver]", "connecting to %s:%d..." % (self.ms_addr[0], self.ms_addr[1])
		self.ms_tcp = None
		try:
			self.ms_tcp = socket.create_connection((self.ms_addr[0], self.ms_addr[1]))
		except socket.error as e:
			print "[masterserver]", "failed to connect to masterserver. %s" % e
			return False
		
		self.ms_tcp.setblocking(False)
		self.ms_tcp.send("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys()))+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%\n")
		self.MSstate = MASTER_WAITINGSUCCESS
		return True
	
	def sendToMasterServer(self, msg):
		try:
			self.ms_tcp.send(msg+"\n")
		except:
			pass
	
	def masterServerTick(self):
		try:
			data = self.ms_tcp.recv(4096)
		except (socket.error, socket.timeout) as e:
			if e.args[0] == 10035 or e.errno == 11 or e.args[0] == "timed out":
				return True
			else:
				print "[masterserver]", "connection to master server lost, retrying."
				return False
		
		if not data:
			print "[masterserver]", "no data from master server, retrying."
			return False
		
		t = data.split("%")
		for msg in t:
			network = msg.split("#")
			header = network.pop(0)
			if header == "SUCCESS":
				type = network[0]
				if type == "13":
					if self.MSstate == MASTER_WAITINGSUCCESS:
						self.MSstate = -1
						ip = self.ms_addr[0]
						if ip.startswith("127.") or ip == "localhost":
							try:
								url = urllib.urlopen("http://ipv4bot.whatismyipaddress.com")
							except:
								print "[masterserver]", "failed to get own IP address. make sure you have internet access."
								self.ms_tcp.close()
								return False
			
							ip = url.read().rstrip()
							self.ms_tcp.send("SET_IP#"+ip+"#%\n")
						else:
							print "[masterserver]", "server published."
					
				elif type == "SET_IP":
					print "[masterserver]", "server published."
		
		return True
	
	def ic_tick_thread(self, msg):
		self.ic_finished = False
		pos = 0
		progress = ""
		while msg != progress:
			progress += msg[pos]
			pos += 1
			time.sleep(1./30)
		self.ic_finished = True
	
	def writeBanList(self):
		with open("server/banlist.txt", "w") as f:
			for ban in self.banlist:
				f.write("%s:%d:%s\n" % (ban[0], ban[1], ban[2]))
	
	def run(self): #main loop
		if self.running:
			print "[warning]", "tried to run server when it is already running"
			return
		
		self.running = True
		
		self.tcp.bind(("", self.port))
		self.tcp.listen(5)
		print "[server]", "AIO server started on port %d" % self.port
		
		self.tcp.settimeout(0.1)
		
		if self.econ_password:
			self.econ_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.econ_tcp.bind(("", self.econ_port))
			self.econ_tcp.listen(5)
			self.econ_tcp.setblocking(False)
			print "[econ]", "external admin console started on port %d" % self.econ_port
		
		if self.publish:
			loopMS = self.startMasterServerAdverter()
			MSretryTick = 0
		
		thread.start_new_thread(self.chatThread, ())
		
		while True:
			if self.publish:
				if not MSretryTick:
					if loopMS:
						loopMS = self.masterServerTick()
					else:
						MSretryTick = 60
				else:
					MSretryTick -= 1
					if MSretryTick == 0:
						loopMS = self.startMasterServerAdverter()
			
			if self.econ_password:
				self.econTick()
			
			for i in range(len(self.banlist)):
				ban = self.banlist[i]
				if ban[1] > 0 and time.time() > ban[1]:
					self.econPrint("[bans] %s expired (%s)" % (ban[0], ban[2]))
					del self.banlist[i]
					self.writeBanList()
					if not self.banlist:
						break
					i -= 1
					continue
					
			self.acceptClient()
			
			for client in self.clients.keys():
				if not self.clients.has_key(client): #if that CID suddendly disappeared possibly due to '/bot remove' or some other reason
					continue
				
				if self.clients[client].ready and len(self.clients) > 1:
					if self.clients[client].isBot():
						self.sendBotMovement(client)
					else:
						self.sendMovement(client)
				
				if not self.clients.has_key(client) or self.clients[client].isBot(): #trust no one, not even myself.
					continue
				
				sock = self.clients[client].sock
				try:
					self.readbuffer = sock.recv(4)
				except socket.error as e:
					if e.args[0] == 10035 or e.errno == 11 or e.args[0] == "timed out":
						continue
					else:
						if self.clients[client].ready:
							self.sendDestroy(client)
						sock.close()
						print "[game]", "client %d (%s) disconnected." % (client, self.clients[client].ip)
						self.sendToMasterServer("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys())-1)+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%")
						self.clients[client].close = True
						del self.clients[client]
						break
				
				if not self.readbuffer:
					if self.clients[client].ready:
						self.sendDestroy(client)
					sock.close()
					print "[game]", "client %d (%s) disconnected." % (client, self.clients[client].ip)
					self.sendToMasterServer("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys())-1)+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%")
					self.clients[client].close = True
					del self.clients[client]
					break
				
				if len(self.readbuffer) < 4:
					continue
				self.readbuffer, bufflength = buffer_read("I", self.readbuffer)
				try:
					self.readbuffer = sock.recv(bufflength+1)
				except socket.error as e:
					if e.args[0] == 10035 or e.errno == 11 or e.args[0] == "timed out":
						continue
					else:
						if self.clients[client].ready:
							self.sendDestroy(client)
						sock.close()
						print "[game]", "client %d (%s) disconnected." % (client, self.clients[client].ip)
						self.sendToMasterServer("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys())-1)+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%")
						self.clients[client].close = True
						del self.clients[client]
						break
				except MemoryError, OverflowError:
					continue
				
				while self.readbuffer:
					if self.readbuffer.endswith("\r"):
						self.readbuffer = self.readbuffer.rstrip("\r")
					if self.readbuffer.startswith("\r"):
						temp = list(self.readbuffer)
						del temp[0]
						self.readbuffer = "".join(temp)
						del temp
					self.readbuffer, header = buffer_read("B", self.readbuffer)
					
					# commence fun... <sigh>
					if header == AIOprotocol.CONNECT: # client sends version
						mismatch = False
						self.readbuffer, version = buffer_read("S", self.readbuffer)
						text = "[game] client %d using version %s" % (client, version)
						if version != GameVersion:
							text += " (mismatch!)"
							mismatch = True
						self.econPrint(text)
						self.clients[client].ClientVersion = version
						if mismatch and not AllowVersionMismatch:
							self.kick(client, "your client version (%s) doesn't match the server's (%s).#make sure you got the latest AIO update at tiny.cc/updateaio, or the server's custom client." % (version, GameVersion))
							break
						
						self.clients[client].can_send_request = True
						self.sendWelcome(client)
					
					elif header == AIOprotocol.REQUEST: #get character, music and zone lists
						if not self.clients[client].can_send_request:
							self.kick(client, "your client tried to send a character/music/zone list request first before sending the client version to the server")
							break
							
						self.readbuffer, req = buffer_read("B", self.readbuffer)
						if req == 0: #characters
							self.sendCharList(client)
						elif req == 1: #music
							self.sendMusicList(client)
						elif req == 2: #zones
							self.sendZoneList(client)
						elif req == 3: #evidence for current zone
							self.sendEvidenceRequest(client)
							self.clients[client].ready = True
							self.econPrint("[game] player is ready. id=%d addr=%s" % (client, self.clients[client].ip))
							self.sendCreate(client)
					
					elif header == AIOprotocol.MOVE: #player movement.
						try:
							self.readbuffer, x = buffer_read("f", self.readbuffer)
							self.readbuffer, y = buffer_read("f", self.readbuffer)
							self.readbuffer, hspeed = buffer_read("h", self.readbuffer)
							self.readbuffer, vspeed = buffer_read("h", self.readbuffer)
							self.readbuffer, sprite = buffer_read("S", self.readbuffer)
							self.readbuffer, emoting = buffer_read("B", self.readbuffer)
							self.readbuffer, dir_nr = buffer_read("B", self.readbuffer)
						except struct.error:
							continue
						if not self.clients[client].ready:
							continue
						
						self.clients[client].x = x
						self.clients[client].y = y
						self.clients[client].hspeed = hspeed
						self.clients[client].vspeed = vspeed
						self.clients[client].sprite = sprite
						self.clients[client].emoting = emoting
						self.clients[client].dir_nr = dir_nr
					
					elif header == AIOprotocol.SETZONE:
						try:
							self.readbuffer, zone = buffer_read("H", self.readbuffer)
						except struct.error:
							continue
						
						if not self.clients[client].ready:
							continue
						
						self.setPlayerZone(client, zone)
						self.sendEvidenceList(client, zone)
					
					elif header == AIOprotocol.SETCHAR:
						self.readbuffer, charid = buffer_read("h", self.readbuffer)
						if not self.clients[client].ready:
							continue
						
						self.clients[client].first_picked = True
						self.setPlayerChar(client, charid)
					
					elif header == AIOprotocol.MSCHAT: #IC chat.
						try:
							self.readbuffer, chatmsg = buffer_read("S", self.readbuffer)
							self.readbuffer, blip = buffer_read("S", self.readbuffer)
							self.readbuffer, color = buffer_read("I", self.readbuffer)
							self.readbuffer, realization = buffer_read("B", self.readbuffer)
							self.readbuffer, evidence = buffer_read("B", self.readbuffer)
						except struct.error:
							continue
						
						if not self.clients[client].ready or self.clients[client].CharID == -1 or realization > 2 or not self.ic_finished:
							continue
						
						if color == 4294901760 and not self.clients[client].is_authed: #that color number is the exact red color (of course, you can get a similar one, but still.)
							color = 4294967295 #set to exactly white
						
						self.sendChat(self.getCharName(self.clients[client].CharID), chatmsg[:255], blip, self.clients[client].zone, color, realization, client, evidence)
						#print "[chat][IC]", "%d,%d,%s: %s" % (client, self.clients[client].zone, self.getCharName(self.clients[client].CharID), chatmsg)
					
					elif header == AIOprotocol.OOC:
						try:
							self.readbuffer, name = buffer_read("S", self.readbuffer)
							self.readbuffer, chatmsg = buffer_read("S", self.readbuffer)
						except struct.error:
							continue
						
						if not self.clients[client].ready or self.clients[client].CharID == -1 or not chatmsg:
							continue
							
						fail = False
						if not name or name.lower().endswith(ServerOOCName.lower()) or name.lower().startswith(ServerOOCName.lower()):
							fail = True
						for client2 in self.clients.values():
							if client2 == self.clients[client]:
								continue
							if (client2.OOCname.lower() == name.lower() or name.lower().startswith(client2.OOCname.lower()) or name.lower().endswith(client2.OOCname.lower())) and client2.OOCname:
								fail = True
						
						if not fail:
							self.clients[client].OOCname = name
						
						if not self.clients[client].OOCname:
							self.sendOOC(ServerOOCName, "you must enter a name with at least one character, and make sure it doesn't conflict with someone else's name.", client)
						else:
							if chatmsg[0] != "/":
								self.sendOOC(self.clients[client].OOCname, chatmsg, zone=self.clients[client].zone)
							else: #commands.
								cmdargs = chatmsg.split(" ")
								cmd = cmdargs.pop(0).lower().replace("/", "", 1)
								print "[chat][OOC]", "%d,%d,%s used command '%s'" % (client, self.clients[client].zone, self.clients[client].OOCname, chatmsg)
								self.parseOOCcommand(client, cmd, cmdargs)
								
					elif header == AIOprotocol.EXAMINE: #AA-like "Examine" functionality
						try:
							self.readbuffer, x = buffer_read("f", self.readbuffer)
							self.readbuffer, y = buffer_read("f", self.readbuffer)
						except struct.error:
							continue
						
						if not self.clients[client].ready or self.clients[client].CharID == -1:
							continue
						if self.clients[client].ratelimits[2] > 0:
							#print "[game]", "ratelimited Examine on client %d (%s, %s)" % (client, self.clients[client].ip, self.getCharName(self.clients[client].CharID))
							continue
						
						self.sendExamine(self.clients[client].CharID, self.clients[client].zone, x, y)
						self.clients[client].ratelimits[2] = ExamineRateLimit
					
					elif header == AIOprotocol.MUSIC: #music change
						self.readbuffer, songname = buffer_read("S", self.readbuffer)
						if not self.clients[client].ready or self.clients[client].CharID == -1:
							continue
						
						if self.clients[client].ratelimits[0] > 0:
							#print "[game]", "ratelimited music on client %d (%s, %s)" % (client, self.clients[client].ip, self.getCharName(self.clients[client].CharID))
							continue
						
						change = False
						for song in self.musiclist:
							if songname.lower() == song.lower():
								change = True
						
						message = "%s id=%d addr=%s zone=%d" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone)
						if change:
							self.changeMusic(songname, self.clients[client].CharID, self.clients[client].zone)
							print "[game]", message, "changed the music to "+songname
							
						else:
							print "[game]", message, "attempted to change the music to "+songname
						self.clients[client].ratelimits[0] = MusicRateLimit
					
					elif header == AIOprotocol.CHATBUBBLE: #chat bubble above the player's head to indicate if they're typing
						self.readbuffer, on = buffer_read("B", self.readbuffer)
						if not self.clients[client].ready or self.clients[client].CharID == -1:
							continue
						
						self.setChatBubble(client, on)
					
					elif header == AIOprotocol.EMOTESOUND:
						try:
							self.readbuffer, soundname = buffer_read("S", self.readbuffer)
							self.readbuffer, delay = buffer_read("I", self.readbuffer)
						except struct.error:
							continue
						
						if not self.clients[client].ready or self.clients[client].CharID == -1:
							continue
							
						if self.clients[client].ratelimits[1] > 0:
							#print "[game]", "ratelimited emotesound on client %d (%s, %s)" % (client, self.clients[client].ip, self.getCharName(self.clients[client].CharID))
							continue
						
						self.sendEmoteSoundOwner(self.clients[client].CharID, soundname, delay, self.clients[client].zone, client)
						self.clients[client].ratelimits[1] = EmoteSoundRateLimit
					
					elif header == AIOprotocol.EVIDENCE:
						try:
							self.readbuffer, type = buffer_read("B", self.readbuffer)
							if type == AIOprotocol.EV_ADD:
								self.readbuffer, name = buffer_read("S", self.readbuffer)
								self.readbuffer, desc = buffer_read("S", self.readbuffer)
								self.readbuffer, image = buffer_read("S", self.readbuffer)
							elif type == AIOprotocol.EV_EDIT:
								self.readbuffer, ind = buffer_read("B", self.readbuffer)
								self.readbuffer, name = buffer_read("S", self.readbuffer)
								self.readbuffer, desc = buffer_read("S", self.readbuffer)
								self.readbuffer, image = buffer_read("S", self.readbuffer)
							elif type == AIOprotocol.EV_DELETE:
								self.readbuffer, ind = buffer_read("B", self.readbuffer)
						except struct.error:
							continue
						
						if not self.clients[client].ready or self.clients[client].CharID == -1:
							continue
						
						if type == AIOprotocol.EV_ADD:
							if len(self.evidencelist[self.clients[client].zone]) == self.evidence_limit:
								print "[game]", "%s id=%d addr=%s zone=%d tried to add a piece of evidence but exceeded the limit"
								self.sendWarning(client, "You cannot add more than %d pieces of evidence at a time." % self.evidence_limit)
								continue
							
							print "[game]", "%s id=%d addr=%s zone=%d added a piece of evidence: %s" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone, name)
							self.addEvidence(self.clients[client].zone, name, desc, image)
						elif type == AIOprotocol.EV_EDIT:
							print "[game]", "%s id=%d addr=%s zone=%d edited piece of evidence %d" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone, ind)
							self.editEvidence(self.clients[client].zone, ind, name, desc, image)
						elif type == AIOprotocol.EV_DELETE:
							print "[game]", "%s id=%d addr=%s zone=%d deleted piece of evidence %d" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone, ind)
							self.deleteEvidence(self.clients[client].zone, ind)
	
	def parseOOCcommand(self, client, cmd, cmdargs):
		isConsole = client == -1
		isEcon = client >= 10000
		
		if cmd == "cmdlist":
			self.sendOOC(ServerOOCName, "announce, cmdlist, evidence, g, gm, kick, ban, unban, login, need, play, setzone, status, switch, warn", client)
		
		elif cmd == "setzone":
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /setzone <client_id> <zone_id>\nto find your target, type /status and search for the id.", client)
				return
			if not isConsole and not isEcon:
				if not self.clients[client].is_authed:
					self.sendOOC(ServerOOCName, "access denied: you're not logged in.", client)
					return
			
			try:
				id = int(cmdargs[0])
			except:
				self.sendOOC(ServerOOCName, "invalid ID "+cmdargs[0]+".", client)
				return
			
			if len(cmdargs) == 1:
				self.sendOOC(ServerOOCName, "missing zone_id argument. to find out the zone ID, click the \"Move\" button ingame.")
				return
			
			try:
				zone = int(cmdargs[1])
			except:
				self.sendOOC(ServerOOCName, "invalid zone ID "+cmdargs[1]+".", client)
				return
			
			if not self.clients.has_key(id):
				self.sendOOC(ServerOOCName, "that client doesn't exist", client)
				return
			if zone < 0 or zone >= len(self.zonelist):
				self.sendOOC(ServerOOCName, "zone ID %d out of bounds" % zone, client)
				return
			
			self.setPlayerZone(id, zone)
			self.sendOOC(ServerOOCName, "moved client %d to zone %d (%s)" % (id, zone, self.zonelist[zone][1]), client)
		
		elif cmd == "switch":
			if not isConsole and not isEcon:
				if not self.clients[client].is_authed:
					self.sendOOC(ServerOOCName, "access denied: you're not logged in.\nif you're trying to change your character ingame, just click the Switch button.", client)
					return
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /switch <client_id> <character_name>\nto find your target, type /status and search for the id.\nto move someone to the character selection screen, use \"-1\" as the character_name.", client)
				return
			
			try:
				id = int(cmdargs[0])
			except:
				self.sendOOC(ServerOOCName, "invalid ID "+cmdargs[0]+".", client)
				return
			
			if len(cmdargs) == 1:
				self.sendOOC(ServerOOCName, "missing character_name argument. the character list is as follows:\n"+str(self.charlist), client)
				return
			
			charname = ""
			for i in range(1, len(cmdargs)):
				charname += cmdargs[i]+" "
			charname = charname.rstrip()
			
			if not self.clients.has_key(id):
				self.sendOOC(ServerOOCName, "that client doesn't exist", client)
				return
			
			success = False
			if charname != "-1":
				for i in range(len(self.charlist)):
					if charname.lower() == self.charlist[i].lower():
						self.setPlayerChar(id, i)
						self.sendOOC(ServerOOCName, "client %d is now %s." % (id, self.charlist[i]), client)
						success = True
						break
			else:
				self.setPlayerChar(id, -1)
				self.sendOOC(ServerOOCName, "moved client %d to the character selection screen." % id, client)
				success = True
			
			if not success:
				self.sendOOC(ServerOOCName, "the character \"%s\" doesn't exist. the character list is as follows:\n%s" % (charname, str(self.charlist)), client)
			
		elif cmd == "warn":
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /warn <id> [message]\nto find your target, type /status and search for the id.", client)
				return
			if not isConsole and not isEcon:
				if not self.clients[client].is_authed:
					self.sendOOC(ServerOOCName, "access denied: you're not logged in.", client)
					return
			
			try:
				id = int(cmdargs[0])
			except:
				self.sendOOC(ServerOOCName, "invalid ID "+cmdargs[0]+".", client)
				return
			
			reason = ""
			if len(cmdargs) > 1:
				for i in range(1, len(cmdargs)):
					reason += cmdargs[i]+" "
				reason = reason.rstrip()
			else:
				self.sendOOC(ServerOOCName, "the warning message can not be left empty.", client)
				return
			
			if not self.clients.has_key(id):
				self.sendOOC(ServerOOCName, "that client doesn't exist lol", client)
				return
			if self.clients[id].isBot():
				self.sendOOC(ServerOOCName, "what's the point in warning a bot??", client)
				return
			
			self.sendWarning(id, reason)
		
		elif cmd == "evidence":
			if not isConsole and not isEcon:
				if not self.clients[client].is_authed:
					self.sendOOC(ServerOOCName, "access denied: you're not logged in.", client)
					return
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /evidence <option>\noptions available: nuke", client)
				return
			
			ev_arg = cmdargs.pop(0).lower()
			if ev_arg == "nuke":
				if not cmdargs:
					self.sendOOC(ServerOOCName, "usage: /evidence nuke <zone/all>\nif you're absolutely sure you wish to nuke the evidence in any of the two options said above, you must type:\n/evidence nuke (option) yes", client)
					return
				
				type = cmdargs[0].lower()
				if len(cmdargs) == 1:
					if type == "zone":
						msg = "this zone"
					elif type == "all":
						msg = "all zones"
					else:
						msg = "(unknown option %s)" % type
					self.sendOOC(ServerOOCName, "Are you ABSOLUTELY sure you wish to nuke the evidence on %s?\nThis can not be undone! To confirm, enter the command:\n/evidence nuke %s yes" % (msg, type), client)
					return
				
				confirm = cmdargs[1].lower()
				if confirm != "yes":
					self.sendOOC(ServerOOCName, "no! you must type EXACTLY \"yes\" to confirm that you're sure! you can't make mistakes here!", client)
					return
				else:
					if type == "zone":
						if isConsole or isEcon:
							self.sendOOC(ServerOOCName, "sorry, but you must be ingame to do this for the time being.", client)
							return
						self.evidencelist[self.clients[client].zone] = []
						self.sendOOC(ServerOOCName, "all the evidence on this zone was nuked off.", client)
						for client2 in self.clients.keys():
							if not self.clients[client2].isBot() and self.clients[client2].zone == self.clients[client].zone:
								self.sendEvidenceList(client2, zone)
					elif type == "all": #rip everything
						for i in range(len(self.evidencelist)):
							self.evidencelist[i] = []
						self.sendOOC(ServerOOCName, "every single piece of evidence has been nuked off.\ncan we get an F in the chat?")
						for client2 in self.clients.keys():
							if not self.clients[client2].isBot():
								self.sendEvidenceList(client2, zone)
					else:
						self.sendOOC(ServerOOCName, "unknown type %s, can not return." % type)
									
		elif cmd == "login":
			if isConsole or isEcon:
				self.sendOOC("", "lol what's the point of that here", client)
				return
			if self.clients[client].is_authed:
				self.sendOOC(ServerOOCName, "you're already logged in.", client)
				return
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /login <password>", client)
				return
			if not self.rcon:
				self.sendOOC(ServerOOCName, "the admin password is not set on this server. to set it, open 'server/base.ini' and add the line 'rcon=adminpass'", client)
				return
				
			password = cmdargs[0]
			if password == self.rcon:
				self.clients[client].is_authed = True
				self.sendOOC(ServerOOCName, "logged in.", client)
			else:
				self.clients[client].loginfails += 1
				if self.clients[client].loginfails >= MaxLoginFails:
					self.kick(client, "too many wrong login attempts")
					return
					
				self.sendOOC(ServerOOCName, "wrong password %d/%d." % (self.clients[client].loginfails, MaxLoginFails), client)
		
		elif cmd == "kick":
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /kick <id> [reason]\nto find your target, type /status and search for the id.", client)
				return
			if not isConsole and not isEcon:
				if not self.clients[client].is_authed:
					self.sendOOC(ServerOOCName, "access denied: you're not logged in.", client)
					return
			
			try:
				id = int(cmdargs[0])
			except:
				self.sendOOC(ServerOOCName, "invalid ID "+cmdargs[0]+".", client)
				return
			
			reason = ""
			if len(cmdargs) > 1:
				for i in range(1, len(cmdargs)):
					reason += cmdargs[i]+" "
				reason = reason.rstrip()
			else:
				reason = "No reason given"
			
			if not self.clients.has_key(id):
				self.sendOOC(ServerOOCName, "that client doesn't exist lol", client)
				return
			if self.clients[id].isBot():
				self.sendOOC(ServerOOCName, "you might want to use \"/bot remove\" for that, buddy", client)
				return
			
			self.kick(id, reason)
		
		elif cmd == "ban":
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /ban <id or ip> <time> [reason]\nthe \"time\" argument can be phrased like this:\n'0' for lifeban\n'1m' for 1 minute\n'24h' for 1 day\n'7d' for one week, and so on.\nif this letter is not specified, minutes are used by default.", client)
				return
			if not isConsole and not isEcon:
				if not self.clients[client].is_authed:
					self.sendOOC(ServerOOCName, "access denied: you're not logged in.", client)
					return
			
			try:
				id = cmdargs[0]
			except:
				self.sendOOC(ServerOOCName, "invalid ID "+cmdargs[0]+".", client)
				return
			
			if id.startswith("127.") or id.lower() == "localhost" or id.startswith("192."):
				self.sendOOC(ServerOOCName, "HOOOOLD UP fam you can't do that", client)
				return
			
			try:
				banlength = cmdargs[1]
			except:
				self.sendOOC(ServerOOCName, "missing/invalid ban length argument.", client)
				return	
			
			bantype = banlength[-1].lower()
			if isNumber(bantype):
				bantype = "m"
				banlength = int(banlength)
			else:
				banlength = int(banlength[:-1])
			if bantype != "m" and bantype != "h" and bantype != "d":
				self.sendOOC(ServerOOCName, "invalid ban type: %s" % bantype, client)
				return
			
			if (bantype == "d" and banlength >= 365) or (bantype == "h" and banlength >= 8760) or (bantype == "m" and banlength >= 525600):
				self.sendOOC(ServerOOCName, "woah, you can't ban people for a year, what's wrong with you?", client)
				return
			
			reason = ""
			if len(cmdargs) > 2:
				for i in range(2, len(cmdargs)):
					reason += cmdargs[i]+" "
				reason = reason.rstrip()
			else:
				reason = "No reason given"
			
			if not "." in id: #make sure it's not an ip
				try:
					id = int(id)
				except:
					self.sendOOC(ServerOOCName, "invalid ID.", client)
					return
					
				if not self.clients.has_key(id):
					self.sendOOC(ServerOOCName, "that client doesn't exist lol", client)
					return
				if self.clients[id].isBot():
					self.sendOOC(ServerOOCName, "you might want to use \"/bot remove\" for that, buddy", client)
					return
			else:
				if len(id.split(".")) != 4:
					self.sendOOC(ServerOOCName, "invalid IP address %s" % id, client)
					return
			
			if banlength > 0:
				reallength = int(time.time())
				if bantype == "m":
					reallength += banlength * 60
				elif bantype == "h":
					reallength += banlength * 3600
				elif bantype == "d":
					reallength += banlength * 86400
			else:
				reallength = 0
			
			min = abs(time.time() - reallength) / 60 if reallength > 0 else 0
			mintext = plural("minute", min+1)
			self.ban(id, reallength, reason)
			
			if not self.clients.has_key(client) and not isConsole and not isEcon:
				return
			
			if min > 0:
				self.sendOOC(ServerOOCName, "user %s has been banned for %d %s (%s)" % (str(id), min+1, mintext, reason), client)
			else:
				self.sendOOC(ServerOOCName, "user %s has been lifebanned (%s)" % (str(id), reason), client)
		
		elif cmd == "unban":
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /unban <ip>unban an IP address from the server.", client)
				return
			if not isConsole and not isEcon:
				if not self.clients[client].is_authed:
					self.sendOOC(ServerOOCName, "access denied: you're not logged in.", client)
					return
			
			try:
				ip = cmdargs[0]
			except:
				self.sendOOC(ServerOOCName, "invalid IP "+cmdargs[0]+".", client)
				return
			
			for i in range(len(self.banlist)):
				ban = self.banlist[i]
				if ban[0] == ip:
					self.sendOOC(ServerOOCName, "unbanned IP %s" % ip, client)
					del self.banlist[i]
					self.writeBanList()
					return
			
			self.sendOOC(ServerOOCName, "IP %s is not banned" % ip, client)
		
		elif cmd == "play":
			if not cmdargs:
				if not isConsole and not isEcon:
					self.sendOOC(ServerOOCName, "usage: /play <filename>", client)
				else:
					self.sendOOC(ServerOOCName, "usage: /play <zone ID> <filename>", client)
				return
			if not isConsole and not isEcon:
				if not self.clients[client].is_authed:
					self.sendOOC(ServerOOCName, "access denied: you're not logged in.", client)
					return
			
			if isConsole or isEcon:
				try:
					zone = int(cmdargs.pop(0))
				except:
					if isConsole:
						print "invalid zone ID."
					elif isEcon:
						self.econ_clients[client-10000][0].send("invalid zone ID.\n")
					return
			
			musicname = ""
			for name in cmdargs:
				musicname += name+" "
			musicname = musicname.rstrip()
			
			if not isConsole and not isEcon:
				self.changeMusic(musicname, self.clients[client].CharID, self.clients[client].zone)
			else:
				self.changeMusic(musicname, 0, zone)
				if isConsole:
					self.sendBroadcast(ServerOOCName+" played "+musicname, zone)
				elif isEcon:
					self.sendBroadcast("ECON USER "+str(client-10000)+" played "+musicname, zone)
		
		elif cmd == "status":
			if not isConsole and not isEcon:
				if not self.clients[client].is_authed:
					self.sendOOC(ServerOOCName, "access denied: you're not logged in.", client)
					return
			
			message = ""
			for client2 in self.clients.keys():
				message += "id=%d addr=%s version=%s zone=%d char=%s oocname=%s authed=%r\n" % (client2, self.clients[client2].ip, self.clients[client2].ClientVersion, self.clients[client2].zone, self.getCharName(self.clients[client2].CharID), self.clients[client2].OOCname, self.clients[client2].is_authed)
			message = message.rstrip("\n")
			
			self.sendOOC(ServerOOCName, message, client)
		
		elif cmd == "g":
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /g <text>", client)
				return
				
			globalmsg = ""
			for text in cmdargs:
				globalmsg += text+" "
			globalmsg = globalmsg.rstrip()
			
			if not isConsole and not isEcon:
				self.sendOOC("$G[%s][%d]" % (self.getCharName(self.clients[client].CharID), self.clients[client].zone), globalmsg)
			else:
				if isConsole:
					self.sendOOC("$G[%s][-1]" % ServerOOCName, globalmsg)
				elif isEcon:
					self.sendOOC("$G[%s][-1]" % ("ECON USER %d" % (client-10000)), globalmsg)
		
		elif cmd == "gm":
			if not isConsole and not isEcon:
				if not self.clients[client].is_authed:
					self.sendOOC(ServerOOCName, "access denied: you're not logged in.", client)
					return
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /gm <text>", client)
				return
				
			globalmsg = ""
			for text in cmdargs:
				globalmsg += text+" "
			globalmsg = globalmsg.rstrip()
			
			if not isConsole and not isEcon:
				self.sendOOC("$G[%s][%d][M]" % (self.getCharName(self.clients[client].CharID), self.clients[client].zone), globalmsg)
			else:
				if isConsole:
					self.sendOOC("$G[%s][-1][M]" % ServerOOCName, globalmsg)
				elif isEcon:
					self.sendOOC("$G[%s][-1][M]" % ("ECON USER %d" % (client-10000)), globalmsg)
		
		elif cmd == "need":
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /need <text>", client)
				return
				
			globalmsg = ""
			for text in cmdargs:
				globalmsg += text+" "
			globalmsg = globalmsg.rstrip()
			
			if not isConsole and not isEcon:
				self.sendOOC(ServerOOCName, "=== ATTENTION ===\n%s at zone %d needs %s" % (self.getCharName(self.clients[client].CharID), self.clients[client].zone, globalmsg))
				self.sendBroadcast("%s at zone %d needs %s" % (self.getCharName(self.clients[client].CharID), self.clients[client].zone, globalmsg))
			else:
				if isConsole:
					name = ServerOOCName
				else:
					name = "ECON USER %d" % (client-10000)
				self.sendOOC(ServerOOCName, "=== ATTENTION ===\n"+name+" at zone -1 needs %s" % globalmsg)
				self.sendBroadcast("%s at zone -1 needs %s" % (name, globalmsg))
		
		elif cmd == "announce":
			if not isConsole and not isEcon:
				if not self.clients[client].is_authed:
					self.sendOOC(ServerOOCName, "access denied: you're not logged in.", client)
					return
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /announce <text>", client)
				return
				
			globalmsg = ""
			for text in cmdargs:
				globalmsg += text+" "
			globalmsg = globalmsg.rstrip()
			
			self.sendOOC(ServerOOCName, "=== ANNOUNCEMENT ===\n"+globalmsg)
		
		elif cmd == "bot":
			if isConsole or isEcon:
				self.sendOOC("", "sorry. you must be ingame to use this command.", client)
				return
			if not self.clients[client].is_authed:
				self.sendOOC(ServerOOCName, "access denied: you're not logged in.", client)
				return
			if not AllowBot:
				self.sendOOC(ServerOOCName, "bots are disabled on this server.", client)
				return
			if not cmdargs:
				self.sendOOC(ServerOOCName, "usage: /bot <add/remove/type>", client)
				return
			
			bot_arg = cmdargs.pop(0)
			if bot_arg == "add":
				if not cmdargs:
					self.sendOOC(ServerOOCName, "usage: /bot add <charname>", client)
					return
					
				charname = cmdargs[0].lower()
				
				found = False
				charid = -1
				for i in range(len(self.charlist)):
					if self.charlist[i].lower() == charname:
						found = True
						charid = i
						break
				
				if not found:
					self.sendOOC(ServerOOCName, "character not found. the characters list is as follows:\n"+str(self.charlist), client)
					return
				
				idattempt = self.maxplayers
				while self.clients.has_key(idattempt):
					idattempt += 1
				
				self.clients[idattempt] = AIObot(charid, self.getCharName(charid), self.clients[client].x, self.clients[client].y, self.clients[client].zone)
				self.clients[idattempt].interact = self.clients[client]
				self.sendOOC(ServerOOCName, "bot added with client ID %d" % idattempt, client)
				self.sendCreate(idattempt)
				self.setPlayerChar(idattempt, charid)
				
			elif bot_arg == "remove":
				if not cmdargs:
					self.sendOOC(ServerOOCName, "usage: /bot remove <bot client ID>", client)
					return
				
				try:
					botid = int(cmdargs[0])
				except:
					self.sendOOC(ServerOOCName, "invalid client ID.", client)
					return
				
				if not self.clients.has_key(botid):
					self.sendOOC(ServerOOCName, "that client ID doesn't exist.", client)
					return
				
				if not self.clients[botid].isBot():
					self.sendOOC(ServerOOCName, "that's a human, not a bot you nobo", client)
					return
				
				self.sendDestroy(botid)
				del self.clients[botid]
				self.sendOOC(ServerOOCName, "bot deleted", client)
			
			elif bot_arg == "type":
				if not cmdargs:
					self.sendOOC(ServerOOCName, "usage: /bot type <botid> <idle/follow/wander>", client)
					return
				
				try:
					botid = int(cmdargs[0])
				except:
					self.sendOOC(ServerOOCName, "invalid client ID.", client)
					return
				
				if not self.clients.has_key(botid):
					self.sendOOC(ServerOOCName, "that client ID doesn't exist.", client)
					return
				
				if not self.clients[botid].isBot():
					self.sendOOC(ServerOOCName, "that's a human, not a bot you nobo", client)
					return
				
				if len(cmdargs) == 1:
					self.sendOOC(ServerOOCName, "bot %d's current type is '%s'" % (botid, self.clients[botid].type))
					return
				
				bottype = cmdargs[1].lower()
				self.clients[botid].type = bottype
				self.clients[botid].interact = self.clients[client]
				self.sendOOC(ServerOOCName, "bot type set to %s" % bottype, client)
		
		else:
			self.sendOOC(ServerOOCName, "unknown command \"%s\". try \"/cmdlist\" for a list of available commands." % cmd, client)
	
	def econTick(self):
		try:
			client, ipaddr = self.econ_tcp.accept()
			print "[econ]", "%s connected." % ipaddr[0]
			client.send("Enter password:\n> ")
			for i in range(500):
				if not self.econ_clients.has_key(i):
					self.econ_clients[i] = [client, ipaddr[0], ECONSTATE_CONNECTED, ECONCLIENT_LF, 0]
					break
		except:
			pass
		
		for i in range(len(self.econ_clients.keys())):
			try:
				client = self.econ_clients[i]
			except:
				continue
			
			try:
				data = client[0].recv(4096)
			except (socket.error, socket.timeout) as e:
				if e.args[0] == 10035 or e.args[0] == "timed out":
					continue
				else:
					print "[econ]", "%s disconnected." % client[1]
					del self.econ_clients[i]
					continue
			
			if not data:
				print "[econ]", "%s disconnected." % client[1]
				try:
					client[0].close()
				except:
					pass
				del self.econ_clients[i]
				continue
			
			if not data.endswith("\n"): #windows telnet client identification. on enter key, it sends "\r\n".
				self.econTemp += data
				continue
			elif data == "\r\n":
				client[3] = ECONCLIENT_CRLF
				data = self.econTemp
				self.econTemp = ""
			
			if data.endswith("\n") or data.endswith("\r"):
				data = data.rstrip()
			
			state = client[2]
			if state == ECONSTATE_CONNECTED: #need to type password.
				if data == self.econ_password:
					client[2] = ECONSTATE_AUTHED
					client[0].send("Access to server console granted.%s" % ("\r\n" if client[3] == ECONCLIENT_CRLF else "\n"))
					print "[econ]", "%s is now logged in." % client[1]
				
				else:
					client[4] += 1
					if client[4] >= MaxLoginFails:
						print "[econ]", "%s was kicked due to entering the wrong password." % client[1]
						try:
							client[0].close()
						except:
							pass
						del self.econ_clients[i]
						continue
					
					else:
						client[0].send("Wrong password %d/%d.%s> " % (client[4], MaxLoginFails, "\r\n" if client[3] == ECONCLIENT_CRLF else "\n"))
			
			elif state == ECONSTATE_AUTHED:
				var = data.split(" ")[0]
				if not var:
					client[0].send("formats: <zone id> <chat message>, or </command>\n")
					continue
				
				if var.startswith("/"):
					cmdargs = data.split(" ")
					cmd = cmdargs.pop(0).lower()
					print "[econ]", "%s used command '%s'" % (client[1], var)
					try:
						self.parseOOCcommand(i+10000, cmd.replace("/", "", 1), cmdargs)
					except Exception as e:
						print "[econ]", "an error occurred while executing command %s from %s: %s" % (cmd, client[1], e.args)
						client[0].send(str(e.args)+"%s" % ("\r\n" if client[3] == ECONCLIENT_CRLF else "\n"))
						continue
				else:
					try:
						var = int(var)
					except:
						client[0].send("invalid zone ID or command. hit enter for help.%s" % ("\r\n" if client[3] == ECONCLIENT_CRLF else "\n"))
						continue
					
					if var < 0 or var >= len(self.zonelist):
						client[0].send("invalid zone ID. hit enter for help.%s" % ("\r\n" if client[3] == ECONCLIENT_CRLF else "\n"))
						continue
					
					al = list(data)
					for i in range(len(str(var))):
						del al[0]
					if len(al) > 0:
						del al[0]
					else:
						al.append(" ")
					txt ="".join(al)
					#print "[chat][IC] -1,%d,%s: %s" % (var, "ECON USER %d" % i, txt)
					self.sendChat("ECON USER %d" % i, txt, "male", var, 4294901760, 0, 0, 0)
	
	def econPrint(self, text, dest=-1):
		print text
		if dest == -1:
			for client in self.econ_clients.values():
				if client[2] == ECONSTATE_AUTHED:
					send = text+"\r\n" if client[3] == ECONCLIENT_CRLF else text+"\n"
					try:
						client[0].send(send)
					except:
						pass
		else:
			if self.econ_clients.has_key(dest):
				send = text+"\r\n" if self.econ_clients[dest][3] == ECONCLIENT_CRLF else text+"\n"
				try:
					self.econ_clients[dest][0].send(send)
				except:
					pass
	
	def chatThread(self):
		while True:
			txt = raw_input()
			var = txt.split(" ")[0]
			if not var:
				print "formats: <zone id> <chat message>, or </command>"
				continue
			
			if var.startswith("/"):
				cmdargs = txt.split(" ")
				cmd = cmdargs.pop(0).lower()
				try:
					self.parseOOCcommand(-1, cmd.replace("/", "", 1), cmdargs)
				except Exception as e:
					print e.args
					continue
			else:
				try:
					var = int(var)
				except:
					print "invalid zone ID or command. hit enter for help."
					continue
				
				if var < 0 or var >= len(self.zonelist):
					print "invalid zone ID. hit enter for help."
					continue
				
				txt = txt.replace(str(var)+" ", "")
				#print "[chat][IC] -1,%d,%s: %s" % (var, ServerOOCName, txt)
				self.sendChat(ServerOOCName, txt, "male", var, 4294901760, 0, 0, 0)
			
if __name__ == "__main__":
	server = AIOserver()
	server.run()