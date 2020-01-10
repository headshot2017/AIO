import thread, time, random
from iniconfig import IniConfig
import AIOprotocol

class AIOplayer(object):
	CharID = -1
	ClientVersion = "???"
	zone = 0
	sock = None
	ip = "0"
	is_authed = False
	ratelimits = [0, 0, 0, 0] #index 0 = music, index 1 = emotesound, index 2 = examine, index 3 = ooc
	ready = False
	can_send_request = False
	x = 0.0
	y = 0.0
	hspeed = 0
	vspeed = 0
	dir_nr = 0
	sprite = ""
	emoting = 0
	currentemote = 0
	run = 0
	OOCname = ""
	loginfails = 0
	close = False
	first_picked = False
	pingpong = 0

	def __init__(self, sock, ip):
		self.sock = sock
		self.ip = ip
		athread = thread.start_new_thread(self.player_thread, ())
	
	def __del__(self):
		self.close = True
	
	def player_thread(self):
		while True:
			if self.close:
				thread.exit()

			for i in range(len(self.ratelimits)):
				if self.ratelimits[i] > 0: self.ratelimits[i] -= 0.1
			if self.pingpong > 0: self.pingpong -= 0.1
			if not self.isBot(): time.sleep(0.1)
	
	def isBot(self):
		return not bool(self.sock)
	
	def isMoving(self):
		return self.hspeed != 0 or self.vspeed != 0

class AIObot(AIOplayer):
	char_ini = None
	charname = ""
	imgprefix = ""
	walkanims = []
	runanim = 0
	blip = ""
	type = "wander"
	interact = None
	def __init__(self, charid, charname, x=0.0, y=0.0, zone=0):
		super(AIObot, self).__init__(None, random.choice(["ur mom gay", "go commit die", "beep boop", "i'm a bot", "69", "vali sucks"]))
		self.x = x
		self.y = y
		self.zone = zone
		self.ready = True
		self.CharID = charid
		self.charname = charname
		self.sprite = charname+"\\spin"
		self.char_ini = IniConfig("data/characters/"+charname+"/char.ini")
		self.imgprefix = self.char_ini.get("Options", "imgprefix", "")
		if self.imgprefix:
			self.imgprefix += "-"
		self.blip = self.char_ini.get("Options", "blip", "male")
		walkanimlen = int(self.char_ini.get("WalkAnims", "total", 1))
		self.walkanims = [self.char_ini.get("WalkAnims", str(i+1), "walk") for i in range(walkanimlen+1)]
		self.runanim = int(self.char_ini.get("WalkAnims", "runanim", 1))-1
		self.setMovement(False)
	
	def point_distance(self, x1, y1, x2, y2):
		return ((x1- x2) * (x1 - x2) + (y1 - y2) * (y1-y2))
	
	def player_thread(self):
		wandertick = 0
		while True:
			if self.close:
				thread.exit()
			
			if not self.interact:
				continue
				
			if self.type == "follow":
				dist = self.point_distance(self.x, self.y, self.interact.x, self.interact.y)
				if dist < 512:
					self.setMovement(False)
				else:
					run = int(dist >= 768)
					if self.x > self.interact.x and self.y > self.interact.y:
						dir_nr = AIOprotocol.NORTHWEST
					elif self.x < self.interact.x and self.y > self.interact.y:
						dir_nr = AIOprotocol.NORTHEAST
					elif self.x > self.interact.x and self.y < self.interact.y:
						dir_nr = AIOprotocol.SOUTHWEST
					elif self.x < self.interact.x and self.y < self.interact.y:
						dir_nr = AIOprotocol.SOUTHEAST
					elif self.x < self.interact.x:
						dir_nr = AIOprotocol.EAST
					elif self.x > self.interact.x:
						dir_nr = AIOprotocol.WEST
					elif self.y > self.interact.y:
						dir_nr = AIOprotocol.NORTH
					elif self.y < self.interact.y:
						dir_nr = AIOprotocol.SOUTH
					
					self.setMovement(True, dir_nr, run)
			
			elif self.type == "wander":
				if wandertick:
					wandertick -= 1
				else:
					
					if self.isMoving():
						wandertick = random.randint(10, 25)
					else:
						wandertick = random.randint(30, 60)
					
					self.setMovement(not self.isMoving(), random.randint(0, 7), 0)
			
			else:
				self.setMovement(False)
			
			self.x += self.hspeed
			self.y += self.vspeed
			time.sleep(1./30)
		
	def setMovement(self, move, dir_nr=0, run=0):
		if not move:
			self.hspeed = 0
			self.vspeed = 0
			self.sprite = self.charname+"\\spin"
			return
		
		self.dir_nr = dir_nr
		self.run = run
		if not run:
			spd = 3
			ind = 0
		else:
			spd = 6
			ind = self.runanim
			
		if dir_nr == 0: #south
			self.hspeed = 0
			self.vspeed = spd
			self.sprite = self.charname+"\\"+self.walkanims[ind]+"south"
		if dir_nr == 1: #southwest
			self.hspeed = -spd
			self.vspeed = spd
			self.sprite = self.charname+"\\"+self.walkanims[ind]+"southwest"
		if dir_nr == 2: #west
			self.hspeed = -spd
			self.vspeed = 0
			self.sprite = self.charname+"\\"+self.walkanims[ind]+"west"
		if dir_nr == 3: #northwest
			self.hspeed = -spd
			self.vspeed = -spd
			self.sprite = self.charname+"\\"+self.walkanims[ind]+"northwest"
		if dir_nr == 4: #north
			self.hspeed = 0
			self.vspeed = -spd
			self.sprite = self.charname+"\\"+self.walkanims[ind]+"north"
		if dir_nr == 5: #northeast
			self.hspeed = spd
			self.vspeed = -spd
			self.sprite = self.charname+"\\"+self.walkanims[ind]+"northeast"
		if dir_nr == 6: #east
			self.hspeed = spd
			self.vspeed = 0
			self.sprite = self.charname+"\\"+self.walkanims[ind]+"east"
		if dir_nr == 7: #southeast
			self.hspeed = spd
			self.vspeed = spd
			self.sprite = self.charname+"\\"+self.walkanims[ind]+"southeast"
