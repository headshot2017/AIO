import plugin

class TestPlugin(plugin.Plugin):
    def ooc_cmd_testplugin(self, server, client, consoleUser, args):
        """
Testing server plugins"""
        return "This is a test plugin A"
    
    
    def registerCommands(self, server):
        server.commands.register(self.ooc_cmd_testplugin)
    
    def onPluginStart(self, server):
        server.Print("[TestPlugin] PLUGIN START")
        self.registerCommands(server)
    
    def onPluginReload(self, server):
        server.Print("[TestPlugin] PLUGIN RELOAD")
        self.registerCommands(server)
    
    def onPluginStop(self, server, crash):
        server.Print("[TestPlugin] PLUGIN STOP")
    
    def onClientConnect(self, server, client, ip):
        server.Print("[TestPlugin] CLIENT CONNECT: %s %s" % (client, ip))
        return False # return true if client was kicked, or nothing/False if not
    
    def onClientDisconnect(self, server, clientid, ip):
        server.Print("[TestPlugin] CLIENT DISCONNECT: %d %s" % (clientid, ip))