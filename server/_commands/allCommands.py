from __init__ import mod_only, _help
from server_vars import *
import time

def ooc_cmd_login(server, client, consoleUser, args):
    """
Log in as an administrator.
Usage: /login <password>"""

    if consoleUser > 0: return "You can't use /login from a console."
    elif server.clients[client].is_authed: return "You're already logged in."
    elif not server.rcon: return "Admin access is not configured on this server. To set it, open 'server/base.ini' and add the line 'rcon=adminpass'"
    elif not args: return "You must enter the password."
        
    password = " ".join(args)
    if password == server.rcon:
        server.clients[client].is_authed = True
        return "Logged in."
    else:
        server.clients[client].loginfails += 1
        if server.clients[client].loginfails >= MaxLoginFails:
            server.ban(client, time.time()+(60 * 5), "Too many wrong login attempts") # 5 min ban
            return
            
        return "Wrong password %d/%d." % (server.clients[client].loginfails, MaxLoginFails)

def ooc_cmd_logout(server, client, consoleUser, args):
    """
Log out from administrator.
Usage: /logout"""
    if consoleUser > 0: return "You can't use /logout from a console."
    elif not server.clients[client].is_authed: return "You're not logged in."

    server.clients[client].is_authed = False
    return "Logged out."

@mod_only()
def ooc_cmd_setzone(server, client, consoleUser, args):
    """
Forcefully move a player to a different zone.
Usage: /setzone <client_id> <zone_id>
Zone IDs can be seen on the Move button."""
    if len(args) < 2: return _help("setzone")
    
    try:
        id = int(args[0])
    except:
        return "Invalid client ID "+args[0]+"."
    
    try:
        zone = int(args[1])
    except:
        return "Invalid zone ID "+args[1]+"."
    
    if not server.clients.has_key(id): return "Client %d doesn't exist." % id
    elif zone < 0 or zone >= len(server.zonelist): return "Zone ID %d out of bounds." % zone
    
    server.setPlayerZone(id, zone)
    return "Moved client %d to zone %d (%s)." % (id, zone, server.zonelist[zone][1])

@mod_only()
def ooc_cmd_switch(server, client, consoleUser, args):
    """
Forcefully switch a player's character to another.
To move them to the character selection screen, use "-1" for the <character_name>.
Usage: /switch <client_id> <character_name>"""
    if len(args) < 2: return _help("switch")

    try:
        id = int(args[0])
    except:
        return "Invalid client ID "+args[0]+"."
    
    charname = " ".join(args[1:])
    
    if not server.clients.has_key(id): return "Client %d doesn't exist." % id
    
    if charname != "-1":
        for char in server.charlist:
            if charname.lower() == char.lower():
                server.setPlayerChar(id, server.charlist.index(char))
                return "Client %d is now \"%s\"." % (id, char)
    else:
        server.setPlayerChar(id, -1)
        return "Moved client %d to the character selection screen." % id

    return "The character \"%s\" doesn't exist. The character list is as follows:\n%s" % (charname, ", ".join(server.charlist))

@mod_only()
def ooc_cmd_warn(server, client, consoleUser, args):
    """
Warn a player.
Usage: /warn <client_id> <message>"""
    if len(args) < 2: return _help("warn")
    
    try:
        id = int(args[0])
    except:
        return "Invalid client ID "+args[0]+"."
    
    warnmsg = " ".join(args[1:])
    
    if not server.clients.has_key(id): return "Client %d doesn't exist." % id
    elif server.clients[id].isBot(): return "You can't warn bots."
    
    server.sendWarning(id, warnmsg)
    return "Warned user %d (%s)" % (id, server.getCharName(server.clients[id].CharID))

@mod_only()
def ooc_cmd_evidence(server, client, consoleUser, args):
    """
Evidence admin command.
Available options: view, delete, nuke
Usage: /evidence <option> [values]"""

    if not args: return _help("evidence")
    ev_arg = args.pop(0).lower()
    
    if ev_arg == "view":
        if consoleUser == 0: return "This command is reserved for the server console and ECON.\nClick the \"Court Record\" button below instead."
        
        if not args: return "Usage: /evidence view <zone_id>"
        try:
            zone = int(args[0])
        except:
            return "Invalid zone ID "+args[0]+"."
        if zone < 0 or zone >= len(server.zonelist): return "Zone ID %d out of bounds." % zone

        evlist = "Listing evidence for zone %d (%s):" % (zone, server.zonelist[zone][1])
        for ev in server.evidencelist[zone]:
            evlist += "\n\n%d: === %s ===\n%s\nFile: %s" % (server.evidencelist[zone].index(ev), ev[0], ev[1], ev[2])
        evlist += "\n\nTotal: %d" % len(server.evidencelist[zone])
        return evlist
    
    elif ev_arg == "delete":
        if consoleUser == 0: return "This command is reserved for the server console and ECON.\nClick the \"Court Record\" button below instead."
        
        if len(args) < 2: return "Usage: /evidence delete <zone_id> <evidence_id>\nUse '/evidence view' to list all pieces of evidence on a zone."

        try:
            zone = int(args[0])
        except:
            return "Invalid zone ID "+args[0]+"."
        if zone < 0 or zone >= len(server.zonelist): return "Zone ID %d out of bounds." % zone

        try:
            evi = int(args[1])
        except:
            return "Invalid evidence ID "+args[1]+"."
        if evi < 0 or zone >= len(server.evidencelist[zone]): return "Evidence ID %d out of bounds. Use between 0-%d." % (evi, len(server.evidencelist[zone])-1)

        oldname = server.evidencelist[zone][evi][0]
        del server.evidencelist[zone][evi]
        for client2 in server.clients.keys():
            if not server.clients[client2].isBot() and server.clients[client2].zone == zone:
                server.sendEvidenceList(client2, zone)
        return "Deleted evidence %d (%s) on zone %d (%s)" % (evi, oldname, zone, server.zonelist[zone][1])
    
    elif ev_arg == "nuke":
        if not args:
            return "Usage: /evidence nuke <zone/all>\nIf you're absolutely sure you wish to nuke the evidence in any of the two options said above, you must type:\n/evidence nuke <choice> yes"
        
        type = args[0].lower()
        if len(args) == 1:
            try:
                msg = {"zone": "this zone", "all": "all zones"}[type]
            except:
                return "Unknown nuke option "+type
            return "Are you ABSOLUTELY sure you wish to nuke the evidence on %s?\nThis can not be undone! To confirm, enter the command:\n/evidence nuke %s yes" % (msg, type)
        
        confirm = args[1].lower()
        if confirm != "yes":
            return "You MUST type \"yes\" as a confirmation that you know what you're doing."

        if type == "zone":
            zone = 0
            if consoleUser > 0:
                if len(args) < 3: return "You must specify the zone ID."
                try:
                    zone = int(args[2])
                except:
                    return "Invalid zone ID "+args[2]+"."
                
                if zone < 0 or zone >= len(server.zonelist): return "Zone ID %d out of bounds." % zone
            else:
                zone = server.clients[client].zone

            server.evidencelist[zone] = []
            for client2 in server.clients.keys():
                if not server.clients[client2].isBot() and server.clients[client2].zone == zone:
                    server.sendEvidenceList(client2, zone)
            return "All the evidence on zone %d (%s) was nuked." % (zone, server.zonelist[zone][1])

        elif type == "all": #rip everything apart
            for i in range(len(server.evidencelist)):
                server.evidencelist[i] = []
            for client2 in server.clients.keys():
                if not server.clients[client2].isBot():
                    server.sendEvidenceList(client2, server.clients[client2].zone)
            return "All the evidence on every zone was nuked."

        return "Unknown nuke option "+type

@mod_only()
def ooc_cmd_kick(server, client, consoleUser, args):
    """
Kick a player from the server.
Usage: /kick <client_id> [reason]"""

    if not args: return _help("kick")
    
    try:
        id = int(args[0])
    except:
        return "Invalid client ID "+args[0]+"."

    reason = " ".join(args[1:]) or "No reason given"
    
    if not server.clients.has_key(id): return "Client %d doesn't exist." % id
    elif server.clients[id].isBot(): return "Use /bot remove %d instead." % id
    
    charname = server.getCharName(server.clients[id].CharID)
    ip = server.clients[id].ip
    server.kick(id, reason)
    return "Kicked player %d (%s) (%s)" % (id, charname, ip)

@mod_only()
def ooc_cmd_ban(server, client, consoleUser, args):
    """
Bans a player from the server.
Usage: /ban <id or ip> <ban length> [reason]
The ban length can be phrased in various ways:
"0" for lifeban
"1m" for 1 minute
or "24h" for 1 day.
If the letter is omitted, minutes are used by default."""

    if len(args) < 2: return _help("ban")
    
    id = args[0]
    banlength = args[1]
    bantype = banlength[-1].lower()

    if bantype.isdigit():
        bantype = "m"
        banlength = int(banlength)
    else:
        try:
            banlength = int(banlength[:-1])
        except:
            return "Invalid ban length argument."

    if bantype != "m" and bantype != "h" and bantype != "d":
        return "Invalid ban type '%s'. Valid: (m)inutes, (h)ours, (d)ays" % (bantype, client)

    reason = " ".join(args[2:]) or "No reason given"
    
    if not "." in id: #make sure it's not an ip
        try:
            id = int(id)
        except:
            return "Invalid client ID "+id+"."
            
        if not server.clients.has_key(id): return "Client %d doesn't exist." % id
        elif server.clients[id].isBot(): return "Use /bot remove %d instead." % id
        elif id == client: return "You can't ban yourself."
        elif server.clients[id].ip.startswith("127."): return "You can't ban the host."

    else: # could be an IP
        if len(id.split(".")) != 4:
            return "Invalid IP address '"+ip+"'"
        
        if id.beginswith("127.") or id == "localhost":
            return "You can't ban the host."

        for i in server.clients.keys():
            if server.clients[i].ip == server.clients[client].ip:
                return "You can't ban yourself."

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
    mintext = plural("minute", int(min+1))
    banid = server.ban(id, reallength, reason)

    if min > 0:
        return "User %s has been banned for %d %s (%s). Ban ID: %d" % (str(id), min+1, mintext, reason, banid)
    else:
        return "User %s has been banned for life (%s). Ban ID: %d" % (str(id), reason, banid)

@mod_only()
def ooc_cmd_unban(server, client, consoleUser, args):
    """
Unbans a player.
Usage: /unban <ban ID>"""
    if not args: return _help("unban")

    try:
        id = int(args[0])
    except:
        return "Invalid ban ID "+args[0]+"."

    if id < 0 or id >= len(server.banlist): return "Ban ID range out of bounds."

    min = abs(time.time() - server.banlist[id][1]) / 60
    mintext = plural("minute", int(min+1))

    msg = "Unbanned %s: %d %s (%s)" % (id, min+1, mintext, server.banlist[id][2])
    del server.banlist[id]
    return msg

@mod_only()
def ooc_cmd_play(server, client, consoleUser, args):
    """
Play a custom song.
Usage: /play <filename or http stream>
Usage in console: /play <zone id> <filename or http stream>
YouTube http streams are NOT supported."""
    if (consoleUser > 0 and len(args) < 2) or not args: return _help("play")

    try:
        zone = int(args.pop(0)) if consoleUser > 0 else server.clients[client].zone
    except:
        return "Invalid zone ID: %s" % zone

    filename = " ".join(args)
    print filename
    showname = server.ServerOOCName if consoleUser == 1 else "ECON USER %d"%client if consoleUser == 2 else ""
    charID = consoleUser == 0 and server.clients[client].CharID or 0
    server.changeMusic(filename, charID, showname, zone)

@mod_only()
def ooc_cmd_status(server, client, consoleUser, args):
    """
List all connected players.
Usage: /status"""

    message = ""
    for client2 in server.clients.keys():
        message += "\n[%d][%s][%s][%s] version=%s zone=%d authed=%r" % (client2, server.clients[client2].ip, server.getCharName(server.clients[client2].CharID), server.clients[client2].OOCname, server.clients[client2].ClientVersion, server.clients[client2].zone, server.clients[client2].is_authed)
    return message

def ooc_cmd_g(server, client, consoleUser, args):
    """
Send a message globally to all players.
Usage: /g <message>"""

    globalmsg = " ".join(args)
    name = server.ServerOOCName if consoleUser == 1 else "ECON USER %d"%client if consoleUser == 2 else server.getCharName(server.clients[client].CharID)
    zone = server.clients[client].zone if consoleUser == 0 else -1
    server.sendOOC("$G[%s][%d]" % (name, zone), globalmsg)

@mod_only()
def ooc_cmd_gm(server, client, consoleUser, args):
    """
Send a message globally to all players with a moderator tag.
Usage: /gm <message>"""

    globalmsg = " ".join(args)
    name = server.ServerOOCName if consoleUser == 1 else "ECON USER %d"%client if consoleUser == 2 else server.getCharName(server.clients[client].CharID)
    zone = server.clients[client].zone if consoleUser == 0 else -1
    server.sendOOC("$G[%s][%d][M]" % (name, zone), globalmsg)

@mod_only()
def ooc_cmd_need(server, client, consoleUser, args):
    """
Send an advert globally to all players specifying what you need.
Usage: /need <message>"""

    globalmsg = " ".join(args)
    name = server.ServerOOCName if consoleUser == 1 else "ECON USER %d"%client if consoleUser == 2 else server.getCharName(server.clients[client].CharID)
    zone = server.clients[client].zone if consoleUser == 0 else -1
    server.sendOOC(server.ServerOOCName, "=== ATTENTION ===\n%s at zone %d needs %s" % (name, zone, globalmsg))
    server.sendBroadcast("%s at zone %d needs %s" % (name, zone, globalmsg))

@mod_only()
def ooc_cmd_announce(server, client, consoleUser, args):
    """
Send a server-wide announcement.
Usage: /announce <message>"""

    globalmsg = " ".join(args)
    server.sendOOC(server.ServerOOCName, "=== ANNOUNCEMENT ===\n%s" % globalmsg)
    server.sendBroadcast("Announcement: %s" % globalmsg)

@mod_only()
def ooc_cmd_bot(server, client, consoleUser, args):
    """
Manage server-side player bots.
Usage: /bot <add/remove/type>"""

    if not AllowBot: return "Bots are disabled on this server."
    return "To be implemented in a future version."