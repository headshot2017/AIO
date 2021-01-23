import socket, thread, os, sys, struct, urllib, time, traceback, zlib

import iniconfig

import AIOprotocol
from AIOplayer import *
sys.path.append("./server/")
sys.path.append("./server/plugins")
from plugin import Plugin, PluginError
import _commands as Commands
from server_vars import *
from packing import *

class AIOserver(object):
    running = False
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    plugins = []
    readbuffer = ""
    econTemp = ""
    clients = {}
    econ_clients = {}
    musiclist = []
    charlist = []
    zonelist = []
    evidencelist = []
    banlist = []
    last_messages = [] # message IDs, 15 messages
    defaultzone = 0
    maxplayers = 1
    MSstate = -1
    MStick = -1
    ic_finished = True
    logfile = None
    
    
    ServerOOCName = "$SERVER" # the ooc name that the server will use to respond to OOC commands and the like
    
    
    def __init__(self):
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
                f.write("rcon=theadminpassword\n")
                f.write("maxplayers=100\n")
                f.write("evidence_limit=255\n")
                f.write("log=1\n")
                f.write("\n")
                f.write(";you cannot set the evidence limit higher than 255. it's the max.\n")
                f.write(";you can set \"maxplayers\" to 0 to use the total number of characters\n")
                f.write(";defined in the scene's init.ini file.\n")
                f.write("\n")
                f.write("[MasterServer]\n")
                f.write("ip=aaio-ms.aceattorneyonline.com:27011\n")
                f.write("[ECON]\n")
                f.write("port=27000\n")
                f.write("password=consolepassword\n")
                f.write("\n")
                f.write(";ECON is for advanced users. it allows you to control the server\n")
                f.write(";through the command line. leave the password empty to disable.\n")
                f.write("\n")
                f.write("[Advanced]\n")
                f.write("MaxMultiClients=4\n")
                f.write("ServerOOCName = $SERVER\n")
                f.write("AllowBots=0\n")

        self.commands = Commands

        ini = iniconfig.IniConfig("server/base.ini")
        self.servername = ini.get("Server", "name", "unnamed server")
        self.serverdesc = ini.get("Server", "desc", "automatically generated base.ini file")
        self.port = ini.get("Server", "port", 27010, int)
        self.scene = ini.get("Server", "scene", "default")
        self.motd = ini.get("Server", "motd", "Welcome to my server!##Overview of in-game controls:#Arrow keys or WASD keys - move#Shift - run#ESC or close button - quit#Spacebar - show emotes bar#T key - IC chat (Check the options menu to change this)##Musiclist controls:#Arrow keys - select song#Enter - play selected song##Have fun!")
        self.publish = ini.get("Server", "publish", 1, int)
        self.evidence_limit = ini.get("Server", "evidence_limit", 255, int)
        if self.evidence_limit > 255:
            self.Print("warning", "evidence_limit is higher than 255, changing to the limit")
            self.evidence_limit = 255
        self.ms_addr = ini.get("MasterServer", "ip", "aaio-ms.aceattorneyonline.com:27011").split(":")
        if len(self.ms_addr) == 1:
            self.ms_addr.append("27011")
        try:
            self.ms_addr[1] = int(self.ms_addr[1])
        except:
            self.ms_addr[1] = 27011
        self.rcon = ini.get("Server", "rcon", "")

        if ini.get("Server", "log", "1") == "1":
            local = time.localtime()
            timestamp = "%d-%.2d-%.2d %.2d-%.2d-%.2d" % (local[0], local[1], local[2], local[3], local[4], local[5])

            if not os.path.exists("server/logs"): os.makedirs("server/logs")
            self.logfile = open("server/logs/server_log_"+timestamp+".txt", "w")

        self.econ_port = ini.get("ECON", "port", 27000, int)
        self.econ_password = ini.get("ECON", "password", "")
        self.econ_tcp = None
        
        self.max_clients_per_ip = ini.get("Advanced", "MaxMultiClients", 4, int)
        self.ServerOOCName = ini.get("Advanced", "ServerOOCName", "$SERVER")
        self.allow_bots = ini.get("Advanced", "AllowBots", "0") == "1"
        if self.allow_bots and not os.path.exists("data/characters"):
            self.allow_bots = False
            self.Print("warning", "bots are enabled but 'data/characters' folder doesn't exist. disabling")
    
        if not os.path.exists("server/scene/"+self.scene) or not os.path.exists("server/scene/"+self.scene+"/init.ini"):
            self.Print("warning", "scene %s does not exist, switching to 'default'" % self.scene)
            self.scene = "default"
            if not os.path.exists("server/scene/"+self.scene) or not os.path.exists("server/scene/"+self.scene+"/init.ini"):
                self.Print("error", "scene 'default' does not exist, cannot continue loading!")
                sys.exit()
        
        scene_ini = iniconfig.IniConfig("server/scene/"+self.scene+"/init.ini")
        
        self.maxplayers = ini.get("Server", "maxplayers", -1, int)
        if self.maxplayers < 0:
            self.maxplayers = scene_ini.get("chars", "total", 3, int)
        self.maxchars = scene_ini.get("chars", "total", 3, int)
        
        zonelength = scene_ini.get("background", "total", 1, int)
        self.charlist = [scene_ini.get("chars", str(char), "Edgeworth") for char in range(1, self.maxchars+1)]
        self.zonelist = [[scene_ini.get("background", str(zone), "gk1hallway"), scene_ini.get("background", str(zone)+"_name", "Prosecutor's Office hallway"), 10, 10] for zone in range(1, zonelength+1)]
        for i in range(len(self.zonelist)):
            self.evidencelist.append([])
        
        self.defaultzone = scene_ini.get("background", "default", 1, int)-1
        if not os.path.exists("server/musiclist.txt"):
            self.musiclist = ["musiclist.txt not found"]
        else:
            self.musiclist = [music.rstrip() for music in open("server/musiclist.txt")]
        
        # server bans
        if os.path.exists("server/banlist.txt"):
            with open("server/banlist.txt") as f:
                self.banlist = [ban.rstrip().split(":") for ban in f]
        
        for ban in self.banlist:
            ban[1] = int(ban[1]) #time left in minutes

        # plugins
        import importlib
        if not os.path.exists("./server/plugins"): os.makedirs("./server/plugins")
        for file in os.listdir("./server/plugins"):
            if file.lower().endswith(".py"):
                try:
                    pluginModule = importlib.import_module(file[:-3])
                    pluginObj = getattr(pluginModule, file[:-3])
                    self.plugins.append([pluginObj, pluginObj(), file[:-3], pluginModule])

                    # plugin table explained: [plugin class object, plugin object instance, plugin name, imported plugin module]

                except:
                    print "Error occurred while trying to import plugin \"%s\":" % file[:-3]
                    print traceback.format_exc()
    
    def getPlugin(self, plugin_name, min_version=None, max_version=None):
        for plug in self.plugins:
            this_plugin = plug[2]
            if plugin_name == this_plugin:
                version = versionToInt(plug[3].version)
                
                if min_version:
                    min_version_int = versionToInt(min_version)
                    if version < min_version_int:
                        raise PluginError('Plugin "%s" is too old (%s), must be at least %s' % (plugin_name, plug[3].version, min_version))

                if max_version:
                    max_version_int = versionToInt(max_version)
                    if version > max_version_int:
                        raise PluginError('Plugin "%s" is too new (%s), maximum allowed is %s' % (plugin_name, plug[3].version, max_version))

                return plug[1]

        return False

    def reloadPlugins(self):
        for i in range(len(self.plugins)):
            plug = self.plugins[i]
            
            if plug[1].running:
                super(plug[0], plug[1]).onPluginStop(server, False)
                if hasattr(plug[1], "onPluginStop"):
                    plug[1].onPluginStop(self, False)

                pluginModule = reload(plug[3])
                pluginObj = getattr(plug[3], plug[2])
                pluginInst = pluginObj()
                self.plugins[i] = [pluginObj, pluginInst, plug[2], pluginModule]

                super(pluginObj, pluginInst).onPluginStart(server)
                if hasattr(pluginInst, "onPluginStart"):
                    pluginInst.onPluginStart(self)
    
    def getCharName(self, charid):
        if charid != -1:
            return self.charlist[charid]
        return "CHAR_SELECT"
    
    def acceptClient(self):
        try:
            client, ipaddr = self.tcp.accept()
        except socket.error:
            return
        
        for i in range(self.maxplayers):
            if not self.clients.has_key(i):
                self.Print("server", "incoming connection from %s (%d)" % (ipaddr[0], i))
                self.clients[i] = AIOplayer(client, ipaddr[0], i)
                
                for bans in self.banlist:
                    if bans[0] == ipaddr[0]:
                        if bans[1] > 0:
                            min = abs(time.time() - bans[1]) / 60
                            mintext = plural("minute", int(min+1))
                            self.kick(i, "You have been banned for %d %s: %s\nYour ban ID is %d." % (min+1, mintext, bans[2], self.banlist.index(bans)))
                        else:
                            self.kick(i, "You have been banned for life: %s\nYour ban ID is %d." % (bans[2], self.banlist.index(bans)))
                        return
                
                # multiclients
                ip_count = 1
                for multiclient in self.clients.keys():
                    if multiclient != i and self.clients[multiclient].ip == ipaddr[0]:
                        ip_count += 1
                if ip_count > self.max_clients_per_ip:
                    self.kick(i, "Only %d players with the same IP are allowed" % self.max_clients_per_ip)
                    return
                
                for plug in self.plugins:
                    if plug[1].running and hasattr(plug[1], "onClientConnect"):
                        wasNotKicked = plug[1].onClientConnect(self, self.clients[i], ipaddr[0])
                        if not wasNotKicked: return
                
                client.settimeout(0.1)
                self.clients[i].is_authed = ipaddr[0].startswith("127.") # automatically make localhost an admin
                #self.sendToMasterServer("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys()))+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%")
                self.clients[i].pingpong = ClientPingTime * 20 # tickspeed
                thread.start_new_thread(self.clientLoop, (i,))
                return
        
        self.kick(client, "Server is full.")
    
    def sendBuffer(self, clientID, buffer):
        try:
            if isinstance(clientID, AIOplayer):
                return clientID.sock.sendall(buffer+"\r")
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
        buffer += struct.pack("I", self.maxchars)
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
        
        printname = name if clientid >= self.maxplayers else self.getCharName(self.clients[clientid].CharID)
        self.Print("chat", "%d,%d,%s: %s" % (clientid,zone, printname, chatmsg))
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
            self.Print("OOC", chatmsg, dest=econID)
            return
        
        if self.econ_password and ClientID == -2:
            aClient = -1
            for i in self.clients.keys():
                if self.clients[i].OOCname == name:
                    aClient = i
            self.Print("OOC", "%d,%d,%s: %s" % (aClient, zone, name, chatmsg))
        
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
    
    def kick(self, ClientID, reason="No reason given", printMsg=True, noUpdate=False):
        if not self.running:
            print "[error]", "tried to use kick() without server running"
            return
        
        buffer = ""
        buffer += struct.pack("B", AIOprotocol.KICK)
        buffer += reason+"\0"
        buff = struct.pack("I", len(buffer)+1)
        buff += buffer
        
        if isinstance(ClientID, socket.socket):
            ClientID.sendall(buffer+"\r")
            if printMsg:
                self.Print("server", "kicked client %s: %s" % (ClientID.getpeername()[0], reason))
        else:
            player = self.clients[ClientID]
            del self.clients[ClientID]

            self.sendBuffer(player, buffer)
            
            if player.ready:
                self.sendDestroy(ClientID)
            
            if printMsg:
                self.Print("server", "kicked client %d (%s): %s" % (ClientID, self.getCharName(player.CharID), reason))
            
            if not noUpdate:
                pass
                #self.sendToMasterServer("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys())-1)+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%")

    
    def ban(self, ClientID, length, reason):
        if not self.running:
            print "[error]", "tried to use ban() without server running"
            return
        
        if time.time() > length and length > 0:
            return
        
        if length > 0:
            min = abs(time.time() - length) / 60+1
        else:
            min = 0
        mintext = plural("minute", int(min))

        if type(ClientID) == str:
            if "." in ClientID: # if it's an ip address
                for i in self.clients.keys(): # kick all players that match this IP
                    if self.clients[i].ip == ClientID: # found a player
                        if length > 0:
                            self.kick(i, "You have been banned for %d %s: %s\nYour ban ID is %d." % (min, mintext, reason, len(self.banlist)))
                        else:
                            self.kick(i, "You have been banned for life: %s\nYour ban ID is %d." % (reason, len(self.banlist)))
                self.banlist.append([ClientID, length, reason])
        
        else: # if it isn't an ip...
            self.banlist.append([self.clients[ClientID].ip, length, reason])
            for i in self.clients.keys(): # kick all players that match the banned ID
                if self.clients[i].ip == self.clients[ClientID].ip: # found a player
                    if length > 0:
                        self.kick(i, "You have been banned for %d %s: %s\nYour ban ID is %d." % (min, mintext, reason, len(self.banlist)-1))
                    else:
                        self.kick(i, "You have been banned for life: %s\nYour ban ID is %d." % (reason, len(self.banlist)-1))
        
        self.Print("bans", "banned %s for %s (%s)" % (self.banlist[-1][0], "%d min" % (min) if length > 0 else "life", reason))
        self.writeBanList()
        return len(self.banlist)-1
        
    def sendPenaltyBar(self, bar, health, zone, ClientID=-1):
        if not self.running:
            print "[error]", "tried to use sendPenaltyBar() without server running"
            return

        buffer = ""
        buffer += struct.pack("B", AIOprotocol.BARS)
        buffer += struct.pack("B", bar)
        buffer += struct.pack("B", health)
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
                    print "[warning]", "tried to perform sendPenaltyBar() on zone %d, to client %d but that client is in zone %d" % (zone, ClientID, self.clients[ClientID].zone)
                else:
                    return self.sendBuffer(ClientID, buffer)

    def sendWTCE(self, wtcetype, zone, ClientID=-1):
        if not self.running:
            print "[error]", "tried to use sendWTCE() without server running"
            return

        buffer = ""
        buffer += struct.pack("B", AIOprotocol.WTCE)
        buffer += struct.pack("B", wtcetype)
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
                    print "[warning]", "tried to perform sendWTCE() on zone %d, to client %d but that client is in zone %d" % (zone, ClientID, self.clients[ClientID].zone)
                else:
                    return self.sendBuffer(ClientID, buffer)

    def changeMusic(self, filename, charid, showname, zone=-1, ClientID=-1):
        if not self.running:
            print "[error]", "tried to use changeMusic() without server running"
            return
        
        buffer = ""
        buffer += struct.pack("B", AIOprotocol.MUSIC)
        buffer += filename+"\0"
        buffer += struct.pack("I", charid)
        buffer += showname+"\0"
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
        
        for plug in self.plugins:
            if plug[1].running and hasattr(plug[1], "onClientSetZone"):
                plug[1].onClientSetZone(self, self.clients[ClientID], zone)
        
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
        
        for plug in self.plugins:
            if plug[1].running and hasattr(plug[1], "onClientSetChar"):
                plug[1].onClientSetZone(self, self.clients[ClientID], charid)

        for client in self.clients.keys():
            if self.clients[client].ready and not self.clients[client].isBot():
                self.sendBuffer(client, buffer)
    
    def sendExamine(self, charid, zone, x, y, showname, ClientID=-1):
        if not self.running:
            print "[error]", "tried to use sendExamine() without server running"
            return
        
        buffer = struct.pack("B", AIOprotocol.EXAMINE)
        buffer += struct.pack("H", charid)
        buffer += struct.pack("H", zone)
        buffer += struct.pack("f", x)
        buffer += struct.pack("f", y)
        buffer += showname+"\0"
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
                if client == ClientID or not self.clients[client].ready or not self.clients[client].first_picked or not self.clients[client].sprite or not self.clients[client].mustSend:
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
    
    def sendPong(self, ClientID):
        if not self.running:
            print "[error]", "tried to use sendPong() without server running"
            return
        
        buffer = struct.pack("B", AIOprotocol.PING)
        self.sendBuffer(ClientID, buffer)
    
    def startMasterServerAdverter(self):
        self.Print("masterserver", "connecting to %s:%d..." % (self.ms_addr[0], self.ms_addr[1]))
        self.ms_tcp = None
        try:
            self.ms_tcp = socket.create_connection((self.ms_addr[0], self.ms_addr[1]))
        except socket.error as e:
            self.Print("masterserver", "failed to connect to masterserver. %s" % e)
            return False
        
        self.ms_tcp.setblocking(False)

        #self.ms_tcp.send("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys()))+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%\n")
        self.MSstate = MASTER_WAITINGSUCCESS
        return True
    
    def sendToMasterServer(self, msg):
        try:
            self.ms_tcp.send(struct.pack("I", len(msg)) + msg)
        except:
            pass
    
    def masterServerTick(self):
        try:
            data = self.ms_tcp.recv(4)
        except (socket.error, socket.timeout) as e:
            if e.args[0] == 10035 or e.errno == 11 or e.args[0] == "timed out":
                return True
            else:
                self.Print("masterserver", "connection to master server lost, retrying.")
                return False
        
        if not data:
            self.Print("masterserver", "no data from master server (connection lost), retrying.")
            return False

        if len(data) < 4: # we need these 4 bytes to read the packet length
            return True

        try:
            data, bufflength = buffer_read("I", data)
            data = self.ms_tcp.recv(bufflength+1)
        except socket.error as e:
            if e.args[0] == 10035 or e.errno == 11 or e.args[0] == "timed out":
                return True
            else:
                self.Print("masterserver", "connection to master server lost, retrying.")
                return False
        except (MemoryError, OverflowError, struct.error):
            return True

        data = zlib.decompress(data)
        data, header = buffer_read("B", data)

        if header == AIOprotocol.MS_CONNECTED:
            resp = struct.pack("B", AIOprotocol.MS_PUBLISH)
            resp += struct.pack("H", self.port)
            self.sendToMasterServer(resp)

        elif header == AIOprotocol.MS_PUBLISH: # success
            if self.MSstate == MASTER_WAITINGSUCCESS:
                self.MSstate = MASTER_PUBLISHED
                self.MStick = 200
                self.Print("masterserver", "server published.")

        elif header == AIOprotocol.MS_KEEPALIVE:
            self.MStick = 200
        
        return True
    
    def MSkeepAlive(self):
        self.sendToMasterServer(struct.pack("B", AIOprotocol.MS_KEEPALIVE))
    
    def ic_tick_thread(self, msg):
        self.ic_finished = False
        pos = 0
        progress = ""
        while msg != progress and not self.ic_finished:
            progress += msg[pos]
            pos += 1
            time.sleep(1./30)
        self.ic_finished = True

    def writeBanList(self):
        with open("server/banlist.txt", "w") as f:
            for ban in self.banlist:
                f.write("%s:%d:%s\n" % (ban[0], ban[1], ban[2]))

    def clientLoop(self, client):
        try:
            while True:
                if not self.clients.has_key(client): #if that CID suddendly disappeared possibly due to '/bot remove' or some other reason
                    return

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
                        self.Print("server", "client %d (%s) disconnected." % (client, self.clients[client].ip))
                        for plug in self.plugins:
                            if plug[1].running and hasattr(plug[1], "onClientDisconnect"):
                                plug[1].onClientDisconnect(self, client, self.clients[client].ip)
                        self.sendToMasterServer("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys())-1)+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%")
                        self.clients[client].close = True
                        del self.clients[client]
                        try: sock.close()
                        except: pass
                        break
                
                if not self.readbuffer or self.clients[client].pingpong <= 0:
                    if self.clients[client].ready:
                        self.sendDestroy(client)
                    self.Print("server", "client %d (%s) disconnected." % (client, self.clients[client].ip))
                    for plug in self.plugins:
                        if plug[1].running and hasattr(plug[1], "onClientDisconnect"):
                            plug[1].onClientDisconnect(self, client, self.clients[client].ip)
                    self.sendToMasterServer("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys())-1)+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%")
                    self.clients[client].close = True
                    del self.clients[client]
                    try: sock.close()
                    except: pass
                    break
                
                if len(self.readbuffer) < 4: # we need these 4 bytes to read the packet length
                    continue
                    
                try:
                    self.readbuffer, bufflength = buffer_read("I", self.readbuffer)
                    self.readbuffer = sock.recv(bufflength+1)
                except socket.error as e:
                    if e.args[0] == 10035 or e.errno == 11 or e.args[0] == "timed out":
                        continue
                    else:
                        if self.clients[client].ready:
                            self.sendDestroy(client)
                        try: sock.close()
                        except: pass
                        self.Print("server", "client %d (%s) disconnected." % (client, self.clients[client].ip))
                        for plug in self.plugins:
                            if plug[1].running and hasattr(plug[1], "onClientDisconnect"):
                                plug[1].onClientDisconnect(self, client, self.clients[client].ip)
                        self.sendToMasterServer("13#"+self.servername.replace("#", "<num>")+" ["+str(len(self.clients.keys())-1)+"/"+str(self.maxplayers)+"]#"+self.serverdesc.replace("#", "<num>")+"#"+str(self.port)+"#%")
                        self.clients[client].close = True
                        del self.clients[client]
                        break
                except (MemoryError, OverflowError, struct.error):
                    continue
                
                while self.readbuffer:
                    if self.readbuffer.endswith("\r"):
                        self.readbuffer = self.readbuffer.rstrip("\r")
                    if self.readbuffer.startswith("\r"):
                        temp = list(self.readbuffer)
                        del temp[0]
                        self.readbuffer = "".join(temp)
                        del temp
                    
                    try:
                        self.readbuffer, header = buffer_read("B", self.readbuffer)
                    except struct.error: # wtf?
                        continue
                    #print repr(header), repr(self.readbuffer)

                    # commence fun... <sigh>
                    if header == AIOprotocol.CONNECT and self.clients[client].ClientVersion == "???": # client sends version
                        mismatch = False
                        
                        try:
                            self.readbuffer, version = buffer_read("S", self.readbuffer)
                        except struct.error:
                            continue
                            
                        text = "client %d using version %s" % (client, version)
                        if version != GameVersion:
                            text += " (mismatch!)"
                            mismatch = True
                        self.Print("server", text)
                        self.clients[client].ClientVersion = version
                        if mismatch and not AllowVersionMismatch:
                            self.kick(client, "your client version (%s) doesn't match the server's (%s).#make sure you got the latest AIO update at tiny.cc/updateaio, or the server's custom client." % (version, GameVersion))
                            break
                        
                        self.clients[client].can_send_request = True
                        self.sendWelcome(client)
                    
                    elif header == AIOprotocol.REQUEST and not self.clients[client].ready: #get character, music and zone lists
                        if not self.clients[client].can_send_request:
                            self.kick(client, "your client tried to send a character/music/zone list request first before sending the client version to the server")
                            break
                            
                        try:
                            self.readbuffer, req = buffer_read("B", self.readbuffer)
                        except struct.error:
                            continue

                        if req == 0: #characters
                            self.sendCharList(client)
                        elif req == 1: #music
                            self.sendMusicList(client)
                        elif req == 2: #zones
                            self.sendZoneList(client)
                        elif req == 3: #evidence and penalty bars for current zone
                            self.sendEvidenceRequest(client)

                            self.sendPenaltyBar(0, self.zonelist[self.defaultzone][2], self.defaultzone, client)
                            self.sendPenaltyBar(1, self.zonelist[self.defaultzone][3], self.defaultzone, client)
                            self.clients[client].ready = True
                            self.Print("server", "player is ready. id=%d addr=%s" % (client, self.clients[client].ip))
                            self.sendCreate(client)
                            
                            for plug in self.plugins:
                                if plug[1].running and hasattr(plug[1], "onClientReady"):
                                    plug[1].onClientReady(self, self.clients[client])

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

                        old_x = self.clients[client].x
                        old_y = self.clients[client].y
                        old_hspeed = self.clients[client].hspeed
                        old_vspeed = self.clients[client].vspeed
                        old_sprite = self.clients[client].sprite
                        old_emoting = self.clients[client].emoting
                        old_dir_nr = self.clients[client].dir_nr

                        self.clients[client].x = x
                        self.clients[client].y = y
                        self.clients[client].hspeed = hspeed
                        self.clients[client].vspeed = vspeed
                        self.clients[client].sprite = sprite
                        self.clients[client].emoting = emoting
                        self.clients[client].dir_nr = dir_nr

                        if old_x != x or old_y != y or old_hspeed != hspeed or old_vspeed != vspeed or old_emoting != emoting or old_dir_nr != dir_nr or old_sprite != sprite:
                            self.clients[client].mustSend = True

                        for plug in self.plugins:
                            if plug[1].running and hasattr(plug[1], "onClientMovement"):
                                plug[1].onClientMovement(self, self.clients[client], x, y, hspeed,vspeed, sprite, emoting, dir_nr)

                    elif header == AIOprotocol.SETZONE: # change player zone
                        try:
                            self.readbuffer, zone = buffer_read("H", self.readbuffer)
                        except struct.error:
                            continue
                        
                        if not self.clients[client].ready or zone >= len(self.zonelist):
                            continue
                        
                        self.setPlayerZone(client, zone)
                        self.sendEvidenceList(client, zone)
                        self.sendPenaltyBar(0, self.zonelist[zone][2], zone, client)
                        self.sendPenaltyBar(1, self.zonelist[zone][3], zone, client)

                    elif header == AIOprotocol.SETCHAR:
                        try:
                            self.readbuffer, charid = buffer_read("h", self.readbuffer)
                        except struct.error:
                            continue
                        if not self.clients[client].ready or charid >= len(self.charlist): continue
                        
                        if not self.clients[client].first_picked:
                            if self.clients[client].ClientVersion != GameVersion and AllowVersionMismatch:
                                self.sendWarning(client, "Your client version (%s) does not match the server's version (%s).\nAbnormalities might happen during gameplay." % (self.clients[client].ClientVersion, GameVersion))
                        self.clients[client].first_picked = True
                        self.setPlayerChar(client, charid)
                    
                    elif header == AIOprotocol.MSCHAT: #IC chat.
                        try:
                            self.readbuffer, chatmsg = buffer_read("S", self.readbuffer)
                            self.readbuffer, blip = buffer_read("S", self.readbuffer)
                            self.readbuffer, color = buffer_read("I", self.readbuffer)
                            self.readbuffer, realization = buffer_read("B", self.readbuffer)
                            self.readbuffer, evidence = buffer_read("B", self.readbuffer)
                            self.readbuffer, showname = buffer_read("S", self.readbuffer)
                        except struct.error:
                            continue

                        # for old client compatibility
                        try: self.readbuffer, message_id = buffer_read("I", self.readbuffer)
                        except: message_id = 0
                        
                        if self.rcon and self.rcon in chatmsg: continue # NO LEAK PASSWORD
                        elif not self.clients[client].ready or self.clients[client].CharID == -1 or realization > 2 or (not self.ic_finished and not self.clients[client].is_authed) or ([message_id, client] in self.last_messages):
                            continue
                        self.ic_finished = True
                        
                        if message_id != 0:
                            self.last_messages.append([message_id, client])
                            if len(self.last_messages) > 15: # clear one message after another
                                del self.last_messages[0]

                        if color == 4294901760 and not self.clients[client].is_authed: #that color number is the exact red color (of course, you can get a similar one, but still.)
                            color = 4294967295 #set to exactly white

                        showname = showname[:ShowNameLength]
                        if not showname or self.ServerOOCName in showname or "ECON USER" in showname: # fuck fakers
                            showname = self.getCharName(self.clients[client].CharID)

                        self.sendChat(showname, chatmsg[:255], blip, self.clients[client].zone, color, realization, client, evidence)
                        for plug in self.plugins:
                            if plug[1].running and hasattr(plug[1], "onClientChat"):
                                plug[1].onClientChat(self, self.clients[client], chatmsg, showname, color, realization, evidence)
                    
                    elif header == AIOprotocol.OOC:
                        try:
                            self.readbuffer, name = buffer_read("S", self.readbuffer)
                            self.readbuffer, chatmsg = buffer_read("S", self.readbuffer)
                        except struct.error:
                            continue
                        
                        if not self.clients[client].ready or self.clients[client].CharID == -1 or not chatmsg:
                            continue
                        if self.clients[client].ratelimits[3] > 0: #ooc anti-spam
                            continue

                        fail = False
                        if not name or name.lower().endswith(self.ServerOOCName.lower()) or name.lower().startswith(self.ServerOOCName.lower()):
                            fail = True
                        for client2 in self.clients.values():
                            if client2 == self.clients[client]:
                                continue
                            if (client2.OOCname.lower() == name.lower() or name.lower().startswith(client2.OOCname.lower()) or name.lower().endswith(client2.OOCname.lower())) and client2.OOCname:
                                fail = True
                        
                        if not fail:
                            self.clients[client].OOCname = name
                        
                        if not self.clients[client].OOCname:
                            self.sendOOC(self.ServerOOCName, "you must enter a name with at least one character, and make sure it doesn't conflict with someone else's name.", client)
                        else:
                            self.clients[client].ratelimits[3] = OOCRateLimit * 20 # tickspeed
                            if chatmsg[0] != "/": # normal chat
                                if self.rcon and self.rcon in chatmsg: continue # NO LEAK PASSWORD

                                self.sendOOC(self.clients[client].OOCname, chatmsg, zone=self.clients[client].zone)
                                for plug in self.plugins:
                                    if plug[1].running and hasattr(plug[1], "onClientChatOOC"):
                                        plug[1].onClientChatOOC(self, self.clients[client], name, chatmsg)

                            else: #commands.
                                cmdargs = chatmsg.split(" ")
                                cmd = cmdargs.pop(0).lower().replace("/", "", 1)
                                self.Print("OOC", "%d,%d,%s used command '%s'" % (client, self.clients[client].zone, self.clients[client].OOCname, chatmsg))
                                self.parseOOCcommand(client, cmd, cmdargs)
                                
                    elif header == AIOprotocol.EXAMINE: #AA-like "Examine" functionality
                        try:
                            self.readbuffer, x = buffer_read("f", self.readbuffer)
                            self.readbuffer, y = buffer_read("f", self.readbuffer)
                            self.readbuffer, showname = buffer_read("S", self.readbuffer)
                        except struct.error:
                            continue
                        
                        if not self.clients[client].ready or self.clients[client].CharID == -1:
                            continue
                        if self.clients[client].ratelimits[2] > 0:
                            #print "[game]", "ratelimited Examine on client %d (%s, %s)" % (client, self.clients[client].ip, self.getCharName(self.clients[client].CharID))
                            continue

                        showname = showname[:ShowNameLength]
                        if self.ServerOOCName in showname or "ECON USER" in showname: # fuck fakers
                            showname = self.getCharName(self.clients[client].CharID)

                        self.sendExamine(self.clients[client].CharID, self.clients[client].zone, x, y, showname)
                        self.clients[client].ratelimits[2] = ExamineRateLimit * 20 # tickspeed

                        for plug in self.plugins:
                            if plug[1].running and hasattr(plug[1], "onClientExamine"):
                                plug[1].onClientExamine(self, self.clients[client], x, y, showname)
                    
                    elif header == AIOprotocol.MUSIC: #music change
                        try:
                            self.readbuffer, songname = buffer_read("S", self.readbuffer)
                            self.readbuffer, showname = buffer_read("S", self.readbuffer)
                        except:
                            continue

                        if not self.clients[client].ready or self.clients[client].CharID == -1:
                            continue
                        
                        if self.clients[client].ratelimits[0] > 0:
                            #print "[game]", "ratelimited music on client %d (%s, %s)" % (client, self.clients[client].ip, self.getCharName(self.clients[client].CharID))
                            continue
                        
                        change = False
                        for song in self.musiclist:
                            if songname.lower() == song.lower():
                                change = True

                        showname = showname[:ShowNameLength]
                        if self.ServerOOCName in showname or "ECON USER" in showname: # fuck fakers
                            showname = self.getCharName(self.clients[client].CharID)

                        message = "%s id=%d addr=%s zone=%d" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone)
                        if change:
                            self.changeMusic(songname, self.clients[client].CharID, showname, self.clients[client].zone)
                            self.Print("game", "%s changed the music to %s" % (message, songname))
                            
                            for plug in self.plugins:
                                if plug[1].running and hasattr(plug[1], "onClientMusic"):
                                    plug[1].onClientMusic(self, self.clients[client], songname, showname, True)
                        else:
                            self.Print("game", "%s failed to change the music to %s" % (message, songname))
                            
                            for plug in self.plugins:
                                if plug[1].running and hasattr(plug[1], "onClientMusic"):
                                    plug[1].onClientMusic(self, self.clients[client], songname, showname, False)

                        self.clients[client].ratelimits[0] = MusicRateLimit * 20 # tickspeed
                    
                    elif header == AIOprotocol.CHATBUBBLE: #chat bubble above the player's head to indicate if they're typing
                        try:
                            self.readbuffer, on = buffer_read("B", self.readbuffer)
                        except struct.error: continue
                        
                        if not self.clients[client].ready or self.clients[client].CharID == -1:
                            continue
                        
                        self.setChatBubble(client, on)
                        for plug in self.plugins:
                            if plug[1].running and hasattr(plug[1], "onClientChatBubble"):
                                plug[1].onClientChatBubble(self, self.clients[client], on)
                    
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
                        self.clients[client].ratelimits[1] = EmoteSoundRateLimit * 20 # tickspeed
                        
                        for plug in self.plugins:
                            if plug[1].running and hasattr(plug[1], "onClientEmoteSound"):
                                plug[1].onClientEmoteSound(self, self.clients[client], soundname, delay)
                    
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
                                self.Print("evidence", "%s id=%d addr=%s zone=%d tried to add a piece of evidence but exceeded the limit" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone))
                                self.sendWarning(client, "You cannot add more than %d pieces of evidence at a time." % self.evidence_limit)
                                continue
                            
                            self.Print("evidence", "%s id=%d addr=%s zone=%d added a piece of evidence: %s" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone, name))
                            self.addEvidence(self.clients[client].zone, name, desc, image)
                            
                            for plug in self.plugins:
                                if plug[1].running and hasattr(plug[1], "onClientEvidenceAdd"):
                                    plug[1].onClientEvidenceAdd(self, self.clients[client], self.clients[client].zone, name, desc, image)

                        elif type == AIOprotocol.EV_EDIT:
                            self.Print("evidence", "%s id=%d addr=%s zone=%d edited piece of evidence %d" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone, ind))
                            self.editEvidence(self.clients[client].zone, ind, name, desc, image)

                            for plug in self.plugins:
                                if plug[1].running and hasattr(plug[1], "onClientEvidenceEdit"):
                                    plug[1].onClientEvidenceEdit(self, self.clients[client], self.clients[client].zone, ind, name, desc, image)

                        elif type == AIOprotocol.EV_DELETE:
                            self.Print("evidence", "%s id=%d addr=%s zone=%d deleted piece of evidence %d" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone, ind))
                            self.deleteEvidence(self.clients[client].zone, ind)
                            
                            for plug in self.plugins:
                                if plug[1].running and hasattr(plug[1], "onClientEvidenceDelete"):
                                    plug[1].onClientEvidenceDelete(self, self.clients[client], self.clients[client].zone, ind)
                    
                    elif header == AIOprotocol.BARS: # penalty bars (AIO 0.4)
                        try:
                            self.readbuffer, bar = buffer_read("B", self.readbuffer)
                            self.readbuffer, health = buffer_read("B", self.readbuffer)
                        except struct.error: continue
                        
                        if bar > 1: # must be 0 or 1
                            self.Print("game", "%s id=%d addr=%s zone=%d tried to change penalty bar (%d)" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone, bar))
                            continue
                        if health > 10: # must be 0 or 10
                            self.Print("game", "%s id=%d addr=%s zone=%d broke the penalty machine %d (%d)" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone, bar, health))
                            continue
                        
                        self.Print("game", "%s id=%d addr=%s zone=%d changed penalty bar %d to %d" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone, bar, health))
                        self.zonelist[self.clients[client].zone][bar+2] = health
                        self.sendPenaltyBar(bar, health, self.clients[client].zone)
                        
                        for plug in self.plugins:
                            if plug[1].running and hasattr(plug[1], "onClientHealthBar"):
                                plug[1].onClientHealthBar(self, self.clients[client], self.clients[client].zone, bar, health)

                    elif header == AIOprotocol.WTCE: # testimony buttons (AIO 0.4)
                        try:
                            self.readbuffer, wtcetype = buffer_read("B", self.readbuffer)
                        except struct.error: continue

                        if wtcetype > 3: # must be between 0 and 3
                            self.Print("game", "%s id=%d addr=%s zone=%d tried to use WT/CE %d" % (self.getCharName(self.clients[client].CharID), client, self.clients[client].ip, self.clients[client].zone, wtcetype))
                            continue
                        if self.clients[client].ratelimits[4] > 0: # WTCE ratelimit
                            continue

                        self.clients[client].ratelimits[4] = WTCERateLimit * 20 # tickspeed
                        self.sendWTCE(wtcetype, self.clients[client].zone)
                        
                        for plug in self.plugins:
                            if plug[1].running and hasattr(plug[1], "onClientWTCE"):
                                plug[1].onClientWTCE(self, self.clients[client], self.clients[client].zone, wtcetype)

                    elif header == AIOprotocol.PING: #pong
                        self.clients[client].pingpong = ClientPingTime * 20 # tickspeed
                        self.sendPong(client)
        
        except Exception as e: # an error occurred on this client
            if client in self.clients:
                tracebackmsg = traceback.format_exc(e)
                self.Print("error", "Client %d crash:\n%s" % (client, tracebackmsg), False)
                server.kick(client, "\n\n=== CLIENT THREAD CRASH ===\n%s\nTry rejoining. If this message persists, report the problem." % tracebackmsg, False, True)
    
    def run(self): #main loop
        if self.running:
            print "[warning]", "tried to run server when it is already running"
            return
        
        self.running = True

        for plug in self.plugins:
            server.Print("plugins", "starting '%s' version %s" % (plug[2], plug[3].version))
            super(plug[0], plug[1]).onPluginStart(self)
            if hasattr(plug[1], "onPluginStart"):
                success = plug[1].onPluginStart(self)
                if success == False: # it would not be logical to do "if not success" because what if the plugin func doesn't return
                    self.Print("plugins", "Plugin '%s' failed to start." % plug[2])
                    super(plug[0], plug[1]).onPluginStop(self, False)
                    plug[1].onPluginStop(self, False)

        self.tcp.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.tcp.bind(("", self.port))
        self.tcp.listen(5)
        self.udp.bind(("", self.port))
        self.Print("server", "AIO server started on port %d" % self.port)
        
        self.tcp.setblocking(False)
        self.udp.settimeout(0.1)
        
        if self.econ_password:
            self.econ_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.econ_tcp.bind(("", self.econ_port))
            self.econ_tcp.listen(5)
            self.econ_tcp.setblocking(False)
            self.Print("econ", "external admin console started on port %d" % self.econ_port)

        if AllowVersionMismatch: self.Print("warning", "AllowVersionMismatch is enabled, players with different client versions can join. This can cause problems.")

        if self.publish:
            loopMS = self.startMasterServerAdverter()
            MSretryTick = 0

        if "noinput" not in sys.argv:
            thread.start_new_thread(self.chatThread, ())

        thread.start_new_thread(self.tickThread, ())

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

            if self.MSstate == MASTER_PUBLISHED:
                if self.MStick > 0:
                    self.MStick -= 1
                    if not self.MStick:
                        self.MSkeepAlive()

            if self.econ_password:
                self.econTick()

            for i in range(len(self.banlist)):
                ban = self.banlist[i]
                if ban[1] > 0 and time.time() > ban[1]:
                    self.Print("bans", "%s expired (%s)" % (ban[0], ban[2]))
                    del self.banlist[i]
                    self.writeBanList()
                    if not self.banlist:
                        break
                    i -= 1
                    continue

            self.acceptClient()
            self.udpLoop()

    def udpLoop(self):
        data = ""
        try:
            data, addr = self.udp.recvfrom(65535)
        except socket.error as e:
            if e.args[0] == 10035 or e.errno == 11 or e.args[0] == "timed out":
                return

        try:
            data, header = buffer_read("B", data)
        except struct.error: # wtf?
            return

        self.Print("udp", "message from %s: %d" % (addr, header))

        if header == AIOprotocol.UDP_REQUEST:
            response = struct.pack("B", header)
            response += self.servername+"\0" + self.serverdesc+"\0"
            response += struct.pack("IIH", len(self.clients), self.maxplayers, versionToInt(GameVersion))

        self.udp.sendto(zlib.compress(response), addr)

    def parseOOCcommand(self, client, cmd, cmdargs):
        isConsole = client == -1
        isEcon = client >= 10000
        
        consoleUser = isConsole and 1 or isEcon and 2 or 0
        
        func = None
        if hasattr(Commands, "ooc_cmd_"+cmd):
            func = getattr(Commands, "ooc_cmd_"+cmd)
        elif hasattr(Commands, "ooc_hiddencmd_"+cmd):
            func = getattr(Commands, "ooc_hiddencmd_"+cmd)
        else:
            self.sendOOC(self.ServerOOCName, "Unknown command '%s'. Try /help" % cmd, client)
            return

        try:
            message = func(self, client-10000 if isEcon else client, consoleUser, cmdargs)
        except:
            message = traceback.format_exc()+"\nAn error occurred while executing command /%s. See above." % cmd

        if message: self.sendOOC(server.ServerOOCName, message, client)
    
    def econTick(self):
        try:
            client, ipaddr = self.econ_tcp.accept()
            client.setblocking(False)
            self.Print("econ", "%s connected." % ipaddr[0], False)
            client.send("Enter password:\r\n> ")
            for i in range(500):
                if not self.econ_clients.has_key(i):
                    self.econ_clients[i] = [client, ipaddr[0], ECONSTATE_CONNECTED, ECONCLIENT_LF, 0]
                    break
        except:
            pass
        
        for i in self.econ_clients.keys():
            try:
                client = self.econ_clients[i]
            except:
                continue
            
            try:
                data = client[0].recv(4096)
            except (socket.error, socket.timeout) as e:
                if e.args[0] == 10035 or e.args[0] == "timed out" or e.errno == 11:
                    continue
                else:
                    self.Print("econ", "%s disconnected." % client[1], False)
                    del self.econ_clients[i]
                    continue
            
            if not data:
                self.Print("econ", "%s disconnected." % client[1], False)
                try:
                    client[0].close()
                except:
                    pass
                del self.econ_clients[i]
                continue
            
            if not data.endswith("\n"): #windows telnet client identification. on enter key, it sends "\r\n".
                if data != "\b":
                    self.econTemp += data
                else:
                    self.econTemp = self.econTemp[:-1]
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
                    self.Print("econ", "%s is now logged in." % client[1], False)
                
                else:
                    client[4] += 1
                    if client[4] >= MaxLoginFails:
                        self.Print("econ", "%s was kicked due to entering the wrong password." % client[1], False)
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
                    self.Print("econ", "%s used command '%s'" % (client[1], var), False)
                    try:
                        self.parseOOCcommand(i+10000, cmd.replace("/", "", 1), cmdargs)
                    except Exception as e:
                        self.Print("econ", "an error occurred while executing command %s from %s: %s" % (cmd, client[1], e.args), False)
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
                    self.sendChat("ECON USER %d" % i, txt, "male", var, 4294901760, 0, self.maxplayers+1, 0)
    
    def Print(self, element, text, sendToEcon=True, dest=-1):
        local = time.localtime()
        timestamp = "[%d-%.2d-%.2d %.2d:%.2d:%.2d]" % (local[0], local[1], local[2], local[3], local[4], local[5])
        finaltext = "%s[%s]: %s" % (timestamp, element, text)
        print finaltext
        sys.stdout.flush()

        if self.logfile:
            self.logfile.write(finaltext+"\n")

        if sendToEcon:
            if dest == -1:
                for client in self.econ_clients.values():
                    if client[2] == ECONSTATE_AUTHED:
                        send = text.replace("\n", "\r\n")+"\r\n" if client[3] == ECONCLIENT_CRLF else text+"\n"
                        try:
                            client[0].send(send)
                        except:
                            pass
            else:
                if self.econ_clients.has_key(dest):
                    send = text.replace("\n", "\r\n")+"\r\n" if self.econ_clients[dest][3] == ECONCLIENT_CRLF else text+"\n"
                    try:
                        self.econ_clients[dest][0].send(send)
                    except:
                        pass

    def tickThread(self):
        ticks = 0
        while True:
            time.sleep(1./60)
            ticks += 1
            if ticks % 20 == 0:
                for client in self.clients.keys():
                    self.clients[client].player_thread()

                    if self.clients[client].ready and len(self.clients) > 1:
                        if self.clients[client].isBot():
                            self.sendBotMovement(client)
                        else:
                            self.sendMovement(client)

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
                #print "[chat][IC] -1,%d,%s: %s" % (var, self.ServerOOCName, txt)
                self.sendChat(self.ServerOOCName, txt, "male", var, 4294901760, 0, self.maxplayers, 0)
            
if __name__ == "__main__":
    server = AIOserver()
    
    try:
        server.run()
        
    except KeyboardInterrupt: # manual interruption
        for i in server.clients.keys():
            if not server.clients[i].isBot():
                server.kick(i, "\n\n=== SERVER CLOSED ===", False, True)

        server.tcp.close()
        if server.econ_password and server.econ_tcp: server.econ_tcp.close()
        
        for plug in server.plugins:
            server.Print("plugins", "stopping '%s' version %s" % (plug[2], plug[3].version))
            super(plug[0], plug[1]).onPluginStop(server, False)
            if hasattr(plug[1], "onPluginStop"):
                plug[1].onPluginStop(server, False)
        
        server.Print("server", "Server stopped.")

        if server.logfile: server.logfile.close()
        
    except Exception as e: #server crashed
        tracebackmsg = traceback.format_exc(e)
        atime = time.localtime()
        print tracebackmsg
        
        with open("server/traceback_%d.%d.%d_%d-%d-%d.txt" % (atime[3], atime[4], atime[5], atime[2], atime[1], atime[0]), "w") as f:
            f.write(tracebackmsg)
        
        for i in server.clients.keys():
            if not server.clients[i].isBot():
                server.kick(i, "\n\n=== SERVER CRASHED ===\n" + tracebackmsg.rstrip(), False, True)
        
        server.tcp.close()
        if server.econ_password and server.econ_tcp: server.econ_tcp.close()
        
        for plug in server.plugins:
            server.Print("plugins", "stopping '%s' version %s" % (plug[2], plug[3].version))
            super(plug[0], plug[1]).onPluginStop(server, True)
            if hasattr(plug[1], "onPluginStop"):
                plug[1].onPluginStop(server, True)
        
        server.Print("server", "Server stopped due to a crash.")

        if server.logfile: server.logfile.close()
