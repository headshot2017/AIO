import plugin

class TestPlugin(plugin.Plugin):
    def onPluginStart(self, server):
        server.Print("[TestPlugin] PLUGIN START")
    
    def onPluginStop(self, server, crash):
        server.Print("[TestPlugin] PLUGIN STOP")
    
    def onClientConnect(self, server, client, ip):
        server.Print("[TestPlugin] CLIENT CONNECT: %s %s" % (client, ip))
        return False # return true if client was kicked, or nothing/False if not
    
    def onClientDisconnect(self, server, clientid, ip):
        pass