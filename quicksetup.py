import urllib2
import zipfile
import subprocess
import sys

def pip_install(package):
    subprocess.call([sys.executable, "-m", "pip", "install", package])

print "downloading pybass"
filedata = urllib2.urlopen('https://github.com/Wyliodrin/pybass/archive/master.zip')  
datatowrite = filedata.read()

with open('pybass.zip', 'wb') as f:  
    f.write(datatowrite)
    f.close()

print "downloading bass"
filedata = urllib2.urlopen('http://us.un4seen.com/files/bass24.zip')  
datatowrite = filedata.read()

with open('bass24.zip', 'wb') as f:  
    f.write(datatowrite)
    f.close()

print "extracting bass"
zip_ref = zipfile.ZipFile('bass24.zip', 'r')
zip_ref.extract('bass.dll')
zip_ref.close()

print "downloading pyqt4"
filedata = urllib2.urlopen('https://download.lfd.uci.edu/pythonlibs/u2hcgva4/PyQt4-4.11.4-cp27-cp27m-win32.whl')  
datatowrite = filedata.read()

with open('PyQt4-4.11.4-cp27-cp27m-win32.whl', 'wb') as f:  
    f.write(datatowrite)
    f.close()

print "installing pyqt4"
pip_install('PyQt4-4.11.4-cp27-cp27m-win32.whl')

print "done"
