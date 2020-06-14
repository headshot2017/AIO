import sys
from server_vars import plural

def mod_only():
    import functools
    def decorator(func):
        @functools.wraps(func)
        def wrapper_mod_only(server, client, consoleUser, args):
            if consoleUser == 0 and not server.clients[client].is_authed:
                print "[chat][OOC]", "%d,%d,%s was denied from running mod-only command" % (client, server.clients[client].zone, server.clients[client].OOCname)
                return "Permission denied."
            return func(server, client, consoleUser, args)
        return wrapper_mod_only
    return decorator

def _help(cmd=None):
    all = []
    nonhidden = []
    
    for allcmds in dir(sys.modules["_commands"]):
        if allcmds.startswith("ooc_cmd_") or allcmds.startswith("ooc_hiddencmd_"):
            name = allcmds.split("_", 2)[-1]
            all.append(name)
            if not allcmds.startswith("ooc_hiddencmd_"): nonhidden.append(name)

    if not cmd:
        return "Available commands:\n" + (", ".join(nonhidden)) + "\nType /help [name] to get information about a command."

    else:
        hidden = "hidden" if (cmd not in nonhidden and cmd in all) else ""

        if cmd in all:
            ind = all.index(cmd)
            return getattr(sys.modules["_commands"], "ooc_"+hidden+"cmd_"+cmd).__doc__
        else:
            return '"'+cmd+'" is not a valid command.'

def register(callback):
    setattr(sys.modules[__name__], callback.func_name, callback)

def ooc_cmd_help(server, client, consoleUser, args):
    """
Lists all commands available, or get help about a command.
Usage: /help [name]
"""
    return _help(args and args[0].lower())

def ooc_cmd_cmdlist(server, client, consoleUser, args):
    """
Lists all commands available.
Usage: /cmdlist
"""
    return _help()

@mod_only()
def ooc_cmd_reload(server, client, consoleUser, args):
    """
Reloads all commands and plugins.
Usage: /reload
"""

    # delete old
    for cmd in dir(sys.modules[__name__]):
        if (cmd.startswith("ooc_cmd_") or cmd.startswith("ooc_hiddencmd_")) and not cmd.endswith("help") and not cmd.endswith("cmdlist") and not cmd.endswith("reload"):
            delattr(sys.modules[__name__], cmd)
    for attr in dir(sys.modules[__name__].allCommands):
        if attr != "__name__" and attr != "__file__": delattr(sys.modules[__name__].allCommands, attr)
    
    # apply new
    allCommands = reload(sys.modules[__name__].allCommands)
    all = []
    for cmd in dir(allCommands):
        if cmd.startswith("ooc_cmd_") or cmd.startswith("ooc_hiddencmd_"):
            all.append(cmd)
            setattr(sys.modules[__name__], cmd, getattr(allCommands, cmd))
    
    server.reloadPlugins()

    server.sendOOC(server.ServerOOCName, "%d %s and %d %s loaded." % (len(all), plural("command", len(all)), len(server.plugins), plural("plugin", len(server.plugins))), client)

from allCommands import *