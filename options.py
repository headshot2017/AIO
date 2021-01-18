from PyQt4 import QtCore, QtGui
from ConfigParser import ConfigParser
from pybass import *
from functools import partial
import os, ini, platform

def getControlName(ind):
    for c in dir(QtCore.Qt):
        if "Key_" in c and getattr(QtCore.Qt, c) == ind: return c

class HTMLDelegate(QtGui.QStyledItemDelegate): # https://stackoverflow.com/questions/53569768/how-to-display-partially-bold-text-in-qlistwidgetitem-with-qtcore-qt-userrole
    def __init__(self, parent=None):
        super(HTMLDelegate, self).__init__(parent)
        self.doc = QtGui.QTextDocument(self)

    def paint(self, painter, option, index):
        painter.save()
        options = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(options, index)
        self.doc.setHtml(options.text)
        text = options.text.toUtf8()
        options.text = ""
        style = QtGui.QApplication.style() if options.widget is None else options.widget.style()
        style.drawControl(QtGui.QStyle.CE_ItemViewItem, options, painter)

        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()
        if option.state & QtGui.QStyle.State_Selected:
            ctx.palette.setColor(QtGui.QPalette.Text, option.palette.color(
                QtGui.QPalette.Active, QtGui.QPalette.HighlightedText))
        else:
            ctx.palette.setColor(QtGui.QPalette.Text, option.palette.color(
                QtGui.QPalette.Active, QtGui.QPalette.Text))
        textRect = style.subElementRect(QtGui.QStyle.SE_ItemViewItemText, options, None)
        if index.column() != 0:
            textRect.adjust(5, 0, 0, 0)
        constant = 4
        print text.count("<br/>")
        margin = (option.rect.height() - options.fontMetrics.height()) // 2 - (text.count("<br/>") * options.fontMetrics.height() // 2)
        margin = margin - constant
        textRect.setTop(textRect.top() + margin)

        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        self.doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        return QtCore.QSize(self.doc.idealWidth(), 96)


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
        theme_tab = QtGui.QWidget()
        advanced_tab = QtGui.QWidget()
        general_layout = QtGui.QVBoxLayout(general_tab)
        general_layout.setAlignment(QtCore.Qt.AlignTop)
        controls_layout = QtGui.QVBoxLayout(controls_tab)
        controls_layout.setAlignment(QtCore.Qt.AlignTop)
        audio_layout = QtGui.QFormLayout(audio_tab)
        audio_layout.setLabelAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        audio_layout.setFormAlignment(QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        #audio_layout.setContentsMargins(0, 0, 0, 0)
        theme_layout = QtGui.QVBoxLayout(theme_tab)
        theme_layout.setAlignment(QtCore.Qt.AlignTop)
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

        ###### Theme tab ######
        themeview_layout = QtGui.QHBoxLayout()
        self.themeview = QtGui.QListWidget()
        #self.themeview.setViewMode(QtGui.QListWidget.IconMode)
        self.themeview.setIconSize(QtCore.QSize(96, 96))
        #self.themeview.setResizeMode(QtGui.QListWidget.Adjust)
        self.themeview.setMovement(QtGui.QListWidget.Static)
        self.themeview.setItemDelegate(HTMLDelegate(self.themeview))

        self.themes = []
        for theme in os.listdir("data/themes"):
            if not os.path.exists("data/themes/"+theme+"/theme.ini"): continue

            themename = ini.read_ini("data/themes/"+theme+"/theme.ini", "Theme", "name", "unknown theme")
            themedesc = ini.read_ini("data/themes/"+theme+"/theme.ini", "Theme", "description")
            themeauthor = ini.read_ini("data/themes/"+theme+"/theme.ini", "Theme", "author")

            thumbnail = "data/themes/"+theme+"/thumbnail.png"
            if not os.path.exists(thumbnail):
                thumbnail = "data/misc/unknown_theme.png"

            text = "<b>"+themename+"</b>"
            if themedesc or themeauthor: text += "<br/>"
            if themedesc:
                text += themedesc+"<br/>"
            if themeauthor:
                text += "Author: "+themeauthor

            item = QtGui.QListWidgetItem(QtGui.QIcon(thumbnail), text)
            self.themes.append([theme, themename])
            self.themeview.addItem(item)

        themeview_layout.addWidget(self.themeview)
        
        theme_layout.addLayout(themeview_layout)

        ###### Controls tab ######
        self.changingBind = [] # [pushbutton object, control name, control index]
        
        up_layout = QtGui.QHBoxLayout()
        down_layout = QtGui.QHBoxLayout()
        left_layout = QtGui.QHBoxLayout()
        right_layout = QtGui.QHBoxLayout()
        run_layout = QtGui.QHBoxLayout()
        up_label = QtGui.QLabel("Up")
        down_label = QtGui.QLabel("Down")
        left_label = QtGui.QLabel("Left")
        right_label = QtGui.QLabel("Right")
        run_label = QtGui.QLabel("Run")
        self.up_buttons = [QtGui.QPushButton(), QtGui.QPushButton()]
        self.down_buttons = [QtGui.QPushButton(), QtGui.QPushButton()]
        self.left_buttons = [QtGui.QPushButton(), QtGui.QPushButton()]
        self.right_buttons = [QtGui.QPushButton(), QtGui.QPushButton()]
        self.run_button = QtGui.QPushButton()
        
        for b in self.up_buttons: b.clicked.connect(partial(self.changeBind, b, "up", self.up_buttons.index(b)))
        for b in self.down_buttons: b.clicked.connect(partial(self.changeBind, b, "down", self.down_buttons.index(b)))
        for b in self.left_buttons: b.clicked.connect(partial(self.changeBind, b, "left", self.left_buttons.index(b)))
        for b in self.right_buttons: b.clicked.connect(partial(self.changeBind, b, "right", self.right_buttons.index(b)))
        self.run_button.clicked.connect(partial(self.changeBind, self.run_button, "run", 0))

        for i in range(len(self.up_buttons)): ao_app.controls["up"][i] = ini.read_ini_int("aaio.ini", "Controls", "up%d"%(i+1), ao_app.controls["up"][i])
        for i in range(len(self.down_buttons)): ao_app.controls["down"][i] = ini.read_ini_int("aaio.ini", "Controls", "down%d"%(i+1), ao_app.controls["down"][i])
        for i in range(len(self.left_buttons)): ao_app.controls["left"][i] = ini.read_ini_int("aaio.ini", "Controls", "left%d"%(i+1), ao_app.controls["left"][i])
        for i in range(len(self.right_buttons)): ao_app.controls["right"][i] = ini.read_ini_int("aaio.ini", "Controls", "right%d"%(i+1), ao_app.controls["right"][i])
        ao_app.controls["run"][0] = ini.read_ini_int("aaio.ini", "Controls", "run", ao_app.controls["run"][0])

        up_layout.addWidget(up_label)
        for b in self.up_buttons: up_layout.addWidget(b)
        down_layout.addWidget(down_label)
        for b in self.down_buttons: down_layout.addWidget(b)
        left_layout.addWidget(left_label)
        for b in self.left_buttons: left_layout.addWidget(b)
        right_layout.addWidget(right_label)
        for b in self.right_buttons: right_layout.addWidget(b)
        run_layout.addWidget(run_label)
        run_layout.addWidget(self.run_button)
        
        controls_layout.addLayout(up_layout)
        controls_layout.addLayout(down_layout)
        controls_layout.addLayout(left_layout)
        controls_layout.addLayout(right_layout)
        controls_layout.addLayout(run_layout)
        
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
        self.tabs.addTab(theme_tab, "Theme")
        self.tabs.addTab(controls_tab, "Controls")
        self.tabs.addTab(audio_tab, "Audio")
        self.tabs.addTab(advanced_tab, "Advanced")

        save_layout.addWidget(savebtn, 100, QtCore.Qt.AlignRight)
        save_layout.addWidget(cancelbtn, 0, QtCore.Qt.AlignRight)
        main_layout.addWidget(self.tabs)
        main_layout.addLayout(save_layout)
        
        ao_app.installEventFilter(self)
    
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

            selectedtheme = ini.read_ini("aaio.ini", "General", "Theme")
            for i in range(len(self.themes)):
                theme, themename = self.themes[i]

                if theme == selectedtheme:
                    self.themeview.setCurrentRow(i)
                    break

            chatbox_ind = self.chatboximage_dropdown.findText(ini.read_ini("aaio.ini", "General", "Chatbox image"))
            if chatbox_ind > 0:
                self.chatboximage_dropdown.setCurrentIndex(chatbox_ind)
            
            self.ms_lineedit.setText(ini.read_ini("aaio.ini", "MasterServer", "IP"))
            self.device_list.setCurrentIndex(ini.read_ini_int("aaio.ini", "Audio", "Device", BASS_GetDevice()))
            self.musicslider.setValue(ini.read_ini_int("aaio.ini", "Audio", "Music volume", 100))
            self.soundslider.setValue(ini.read_ini_int("aaio.ini", "Audio", "Sound volume", 100))
            self.blipslider.setValue(ini.read_ini_int("aaio.ini", "Audio", "Blip volume", 100))
            
            self.up_buttons[0].setText(getControlName(ini.read_ini_int("aaio.ini", "Controls", "up1", QtCore.Qt.Key_W)))
            self.up_buttons[1].setText(getControlName(ini.read_ini_int("aaio.ini", "Controls", "up2", QtCore.Qt.Key_Up)))
            self.down_buttons[0].setText(getControlName(ini.read_ini_int("aaio.ini", "Controls", "down1", QtCore.Qt.Key_S)))
            self.down_buttons[1].setText(getControlName(ini.read_ini_int("aaio.ini", "Controls", "down2", QtCore.Qt.Key_Down)))
            self.left_buttons[0].setText(getControlName(ini.read_ini_int("aaio.ini", "Controls", "left1", QtCore.Qt.Key_A)))
            self.left_buttons[1].setText(getControlName(ini.read_ini_int("aaio.ini", "Controls", "left2", QtCore.Qt.Key_Left)))
            self.right_buttons[0].setText(getControlName(ini.read_ini_int("aaio.ini", "Controls", "right1", QtCore.Qt.Key_D)))
            self.right_buttons[1].setText(getControlName(ini.read_ini_int("aaio.ini", "Controls", "right2", QtCore.Qt.Key_Right)))
            self.run_button.setText(getControlName(ini.read_ini_int("aaio.ini", "Controls", "run", QtCore.Qt.Key_Shift)))
            
        else:
            self.defaultoocname.setText("")

            for i in range(len(self.themes)):
                theme, themename = self.themes[i]

                if theme == "default":
                    self.themeview.setCurrentRow(i)
                    break

            self.chatboximage_dropdown.setCurrentIndex(0)
            self.ms_lineedit.setText("aaio-ms.aceattorneyonline.com:27011")
            self.device_list.setCurrentIndex(BASS_GetDevice())
            self.musicslider.setValue(100)
            self.soundslider.setValue(100)
            self.blipslider.setValue(100)
            
            self.up_buttons[0].setText("Key_W")
            self.up_buttons[1].setText("Key_Up")
            self.down_buttons[0].setText("Key_S")
            self.down_buttons[1].setText("Key_Down")
            self.left_buttons[0].setText("Key_A")
            self.left_buttons[1].setText("Key_Left")
            self.right_buttons[0].setText("Key_D")
            self.right_buttons[1].setText("Key_Right")
            self.run_button.setText("Key_Shift")
        
        self.tabs.setCurrentIndex(0)
        self.show()
    
    def onSaveClicked(self):
        if not self.inifile.has_section("General"): self.inifile.add_section("General")
        if not self.inifile.has_section("Controls"): self.inifile.add_section("Controls")
        if not self.inifile.has_section("Audio"): self.inifile.add_section("Audio")
        if not self.inifile.has_section("MasterServer"): self.inifile.add_section("MasterServer")
        self.inifile.set("General", "OOC name", self.defaultoocname.text().toUtf8())
        self.inifile.set("General", "Theme", self.themes[self.themeview.currentRow()][0])
        self.inifile.set("General", "Chatbox image", self.chatboximage_dropdown.currentText())
        for i in range(len(self.up_buttons)): self.inifile.set("Controls", "up%d" % (i+1), self.ao_app.controls["up"][i])
        for i in range(len(self.down_buttons)): self.inifile.set("Controls", "down%d" % (i+1), self.ao_app.controls["down"][i])
        for i in range(len(self.left_buttons)): self.inifile.set("Controls", "left%d" % (i+1), self.ao_app.controls["left"][i])
        for i in range(len(self.right_buttons)): self.inifile.set("Controls", "right%d" % (i+1), self.ao_app.controls["right"][i])
        self.inifile.set("Controls", "run", self.ao_app.controls["run"][0])
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
    
    def changeBind(self, button, name, ind):
        self.changingBind = [button, name, ind]
        button.setText("Press any key or ESC to cancel...")

    def eventFilter(self, source, event):
        if self.tabs.currentIndex() == 1 and self.changingBind and event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            if key != QtCore.Qt.Key_Escape:
                self.ao_app.controls[self.changingBind[1]][self.changingBind[2]] = key
                self.changingBind[0].setText(getControlName(key))
            else:
                self.changingBind[0].setText(getControlName(self.ao_app.controls[self.changingBind[1]][self.changingBind[2]]))
            self.changingBind = []
        return super(Options, self).eventFilter(source, event)