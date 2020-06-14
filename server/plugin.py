# core plugin object

class Plugin(object):
    running = False
    
    def onPluginStart(self, server):
        self.running = True
    
    def onPluginStop(self, server, crash):
        self.running = False