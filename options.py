from PyQt4 import QtCore, QtGui
from ConfigParser import ConfigParser
from pybass import *
import os, ini, platform

class Options(QtGui.QWidget):
    fileSaved = QtCore.pyqtSignal()
    def __init__(self, ao_app):
        super(Options, self).__init__()
        self.ao_app = ao_app
        
        self.inifile = ConfigParser()
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 400)
        self.hide()
        
        main_layout = QtGui.QVBoxLayout(self)
        save_layout = QtGui.QHBoxLayout()
        
        self.tabs = QtGui.QTabWidget()
        self.tabs.resize(320-16, 480-40)
        self.tabs.move(8, 8)
        
        general_tab = QtGui.QWidget()
        controls_tab = QtGui.QWidget()
        audio_tab = QtGui.QWidget()
        advanced_tab = QtGui.QWidget()
        general_layout = QtGui.QVBoxLayout(general_tab)
        general_layout.setAlignment(QtCore.Qt.AlignTop)
        controls_layout = QtGui.QVBoxLayout(controls_tab)
        controls_layout.setAlignment(QtCore.Qt.AlignTop)
        audio_layout = QtGui.QFormLayout(audio_tab)
        audio_layout.setLabelAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        audio_layout.setFormAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        #audio_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout = QtGui.QVBoxLayout(advanced_tab)
        advanced_layout.setAlignment(QtCore.Qt.AlignTop)
        
        savebtn = QtGui.QPushButton()
        savebtn.setText("Save")
        savebtn.clicked.connect(self.onSaveClicked)
        cancelbtn = QtGui.QPushButton()
        cancelbtn.setText("Cancel")
        cancelbtn.clicked.connect(self.onCancelClicked)
        
        separators = []
        for i in range(2): # increase if needed
            separator = QtGui.QFrame()
            separator.setFixedSize(separator.size().width(), 16)
            separators.append(separator)
        
        ###### General tab ######
        defaultoocname_layout = QtGui.QHBoxLayout()
        defaultoocname_label = QtGui.QLabel("Default OOC name")
        self.defaultoocname = QtGui.QLineEdit()
        defaultoocname_layout.addWidget(defaultoocname_label)
        defaultoocname_layout.addWidget(self.defaultoocname)
        
        chatboximage_layout = QtGui.QHBoxLayout()
        chatboximage_label = QtGui.QLabel("Chatbox image")
        self.chatboximage_dropdown = QtGui.QComboBox()
        self.chatboximage_dropdown.currentIndexChanged.connect(self.onChangeChatbox)
        chatboximage_layout.addWidget(chatboximage_label)
        chatboximage_layout.addWidget(self.chatboximage_dropdown)
        
        self.chatboximage = QtGui.QLabel()
        
        for file in os.listdir("data/misc/"):
            if file.lower().startswith("chatbox_") and file.lower().endswith(".png"):
                self.chatboximage_dropdown.addItem(file)
        
        #savechangeswarn = QtGui.QLabel()
        #savechangeswarn.setText("* Change takes effect upon restarting the client")
        
        general_layout.addLayout(defaultoocname_layout)
        general_layout.addWidget(separators[0])
        general_layout.addLayout(chatboximage_layout)
        general_layout.addWidget(self.chatboximage, 0, QtCore.Qt.AlignCenter)
        #general_layout.addWidget(savechangeswarn, 50, QtCore.Qt.AlignBottom)
        
        ###### Controls tab ######
        
        ###### Audio tab ######
        device_label = QtGui.QLabel("Audio device")
        self.device_list = QtGui.QComboBox()
        audio_layout.setWidget(0, QtGui.QFormLayout.LabelRole, device_label)
        audio_layout.setWidget(0, QtGui.QFormLayout.FieldRole, self.device_list)
        
        audio_layout.setWidget(1, QtGui.QFormLayout.FieldRole, separators[1])
        
        volumelabel = QtGui.QLabel("Sound volume")
        musiclabel = QtGui.QLabel("Music")
        soundlabel = QtGui.QLabel("Sounds")
        bliplabel = QtGui.QLabel("Blips")
        self.musicslider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.soundslider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.blipslider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
        self.musicslider.setRange(0, 100)
        self.soundslider.setRange(0, 100)
        self.blipslider.setRange(0, 100)
        audio_layout.setWidget(2, QtGui.QFormLayout.LabelRole, musiclabel)
        audio_layout.setWidget(2, QtGui.QFormLayout.FieldRole, self.musicslider)
        audio_layout.setWidget(3, QtGui.QFormLayout.LabelRole, soundlabel)
        audio_layout.setWidget(3, QtGui.QFormLayout.FieldRole, self.soundslider)
        audio_layout.setWidget(4, QtGui.QFormLayout.LabelRole, bliplabel)
        audio_layout.setWidget(4, QtGui.QFormLayout.FieldRole, self.blipslider)

        info = BASS_DEVICEINFO()
        ind = 0
        while BASS_GetDeviceInfo(ind, info):
            self.device_list.addItem(info.name)
            ind += 1

        ###### Advanced tab ######
        ms_layout = QtGui.QHBoxLayout()
        ms_label = QtGui.QLabel("MasterServer IP")
        self.ms_lineedit = QtGui.QLineEdit()

        ms_layout.addWidget(ms_label)
        ms_layout.addWidget(self.ms_lineedit)

        advanced_layout.addLayout(ms_layout)


        self.tabs.addTab(general_tab, "General")
        self.tabs.addTab(controls_tab, "Controls")
        self.tabs.addTab(audio_tab, "Audio")
        self.tabs.addTab(advanced_tab, "Advanced")

        save_layout.addWidget(savebtn, 100, QtCore.Qt.AlignRight)
        save_layout.addWidget(cancelbtn, 0, QtCore.Qt.AlignRight)
        main_layout.addWidget(self.tabs)
        main_layout.addLayout(save_layout)
    
    def onChangeChatbox(self, ind):
        self.chatboximage.setPixmap(QtGui.QPixmap("data/misc/"+self.chatboximage_dropdown.itemText(ind)))
    
    def showSettings(self):
        self.show()
        
        if os.path.exists("aaio.ini"):
            self.inifile.read("aaio.ini")
            try:
                self.defaultoocname.setText(ini.read_ini("aaio.ini", "General", "OOC name").decode("utf-8"))
            except:
                self.defaultoocname.setText(ini.read_ini("aaio.ini", "General", "OOC name"))
            
            chatbox_ind = self.chatboximage_dropdown.findText(ini.read_ini("aaio.ini", "General", "Chatbox image"))
            if chatbox_ind > 0:
                self.chatboximage_dropdown.setCurrentIndex(chatbox_ind)
            
            self.ms_lineedit.setText(ini.read_ini("aaio.ini", "MasterServer", "IP"))
            self.device_list.setCurrentIndex(ini.read_ini_int("aaio.ini", "Audio", "Device", BASS_GetDevice()))
            self.musicslider.setValue(ini.read_ini_int("aaio.ini", "Audio", "Music volume", 100))
            self.soundslider.setValue(ini.read_ini_int("aaio.ini", "Audio", "Sound volume", 100))
            self.blipslider.setValue(ini.read_ini_int("aaio.ini", "Audio", "Blip volume", 100))
        else:
            self.defaultoocname.setText("")
            self.chatbox_dropdown.setCurrentIndex(0)
            self.ms_lineedit.setText("aaio-ms.aceattorneyonline.com:27011")
            self.device_list.setCurrentIndex(BASS_GetDevice())
            self.musicslider.setValue(100)
            self.soundslider.setValue(100)
            self.blipslider.setValue(100)
        
        self.tabs.setCurrentIndex(0)
        self.show()
    
    def onSaveClicked(self):
        if not self.inifile.has_section("General"): self.inifile.add_section("General")
        if not self.inifile.has_section("Audio"): self.inifile.add_section("Audio")
        if not self.inifile.has_section("MasterServer"): self.inifile.add_section("MasterServer")
        self.inifile.set("General", "OOC name", self.defaultoocname.text().toUtf8())
        self.inifile.set("General", "Chatbox image", self.chatboximage_dropdown.currentText())
        self.inifile.set("Audio", "Device", self.device_list.currentIndex())
        self.inifile.set("Audio", "Music volume", self.musicslider.value())
        self.inifile.set("Audio", "Sound volume", self.soundslider.value())
        self.inifile.set("Audio", "Blip volume", self.blipslider.value())
        self.inifile.set("MasterServer", "IP", self.ms_lineedit.text())
        self.inifile.write(open("aaio.ini", "w"))
        self.fileSaved.emit()
        
        self.hide()
    
    def onCancelClicked(self):
        self.hide()
