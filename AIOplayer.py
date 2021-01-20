import thread, time, random, math
from iniconfig import IniConfig
import AIOprotocol

class AIOplayer(object):
    CharID = -1
    ClientVersion = "???"
    zone = 0
    sock = None
    ip = "0"
    id = -1
    is_authed = False
    ratelimits = [] # [music, emotesound, examine, ooc, wtce]
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
    mustSend = False
    OOCname = ""
    loginfails = 0
    close = False
    first_picked = False
    use_adverts = True
    use_global = True
    pingpong = 0

    def __init__(self, sock, ip, id=-1):
        self.ratelimits = [0, 0, 0, 0, 0]
        self.sock = sock
        self.ip = ip
        self.id = id
    
    def __del__(self):
        self.close = True
    
    def player_thread(self):
        for i in range(len(self.ratelimits)):
            if self.ratelimits[i] > 0: self.ratelimits[i] -= 1
        if self.pingpong > 0: self.pingpong -= 1
    
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
    wandertick = 0
    blip = ""
    type = "idle"
    interact = None
    def __init__(self, charid, charname, x=0.0, y=0.0, zone=0):
        super(AIObot, self).__init__(None, "BOT")
        self.x = x
        self.y = y
        self.zone = zone
        self.ready = True
        self.CharID = charid
        self.charname = charname
        self.sprite = charname+"/spin.gif"
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
        return math.sqrt(pow(x2-x1, 2) + pow(y2-y1, 2))
    
    def player_thread(self):
        time.sleep(1./30)
        if not self.interact:
            return
            
        if self.type == "follow":
            dist = self.point_distance(self.x, self.y, self.interact.x, self.interact.y)
            if dist < 64:
                self.setMovement(False)
            else:
                run = int(dist >= 128)
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
            if self.wandertick:
                self.wandertick -= 1
            else:
                
                if self.isMoving():
                    self.wandertick = random.randint(10, 25)
                else:
                    self.wandertick = random.randint(60, 120)
                
                self.setMovement(not self.isMoving(), random.randint(0, 7), 0)
        
        else:
            self.setMovement(False)
        
        self.x += self.hspeed
        self.y += self.vspeed
        
    def setMovement(self, move, dir_nr=0, run=0):
        if not move:
            self.hspeed = 0
            self.vspeed = 0
            self.sprite = self.charname+"/spin.gif"
            return
        
        self.dir_nr = dir_nr
        self.run = run
        if not run:
            spd = 4.2
            ind = 0
        else:
            spd = 8.4
            ind = self.runanim
            
        if dir_nr == 0: #south
            self.hspeed = 0
            self.vspeed = spd
            self.sprite = self.charname+"/"+self.walkanims[ind]+"south.gif"
        if dir_nr == 1: #southwest
            self.hspeed = -spd
            self.vspeed = spd
            self.sprite = self.charname+"/"+self.walkanims[ind]+"southwest.gif"
        if dir_nr == 2: #west
            self.hspeed = -spd
            self.vspeed = 0
            self.sprite = self.charname+"/"+self.walkanims[ind]+"west.gif"
        if dir_nr == 3: #northwest
            self.hspeed = -spd
            self.vspeed = -spd
            self.sprite = self.charname+"/"+self.walkanims[ind]+"northwest.gif"
        if dir_nr == 4: #north
            self.hspeed = 0
            self.vspeed = -spd
            self.sprite = self.charname+"/"+self.walkanims[ind]+"north.gif"
        if dir_nr == 5: #northeast
            self.hspeed = spd
            self.vspeed = -spd
            self.sprite = self.charname+"/"+self.walkanims[ind]+"northeast.gif"
        if dir_nr == 6: #east
            self.hspeed = spd
            self.vspeed = 0
            self.sprite = self.charname+"/"+self.walkanims[ind]+"east.gif"
        if dir_nr == 7: #southeast
            self.hspeed = spd
            self.vspeed = spd
            self.sprite = self.charname+"/"+self.walkanims[ind]+"southeast.gif"
