import urllib2
import zipfile
import subprocess
import sys
import os
import platform

def pip_install(package):
    subprocess.call([sys.executable, "-m", "pip", "install", package])

print "installing pyinstaller"
pip_install('pyinstaller==3.6')

print "installing ini"
pip_install('ini')

print "installing requests"
pip_install('requests')
import requests

print "downloading pybass"
filedata = urllib2.urlopen('http://master.dl.sourceforge.net/project/pybass/pybass_055.zip')
datatowrite = filedata.read()

with open('pybass_055.zip', 'wb') as f:  
    f.write(datatowrite)
    f.close()

print "extracting pybass"
zip_ref = zipfile.ZipFile('pybass_055.zip', 'r')
zip_ref.extractall()
zip_ref.close()

print "renaming pybass.py"
if os.path.exists("pybass/__init__.py"): os.remove('pybass/__init__.py')
os.rename('pybass/pybass.py', 'pybass/__init__.py')

BASSZIP = "bass24.zip"
BASSDLL = "bass.dll"
BASSOPUSZIP = "bassopus24.zip"
BASSOPUSDLL = "bassopus.dll"
if platform.system() == "Darwin":
    BASSZIP = "bass24-osx.zip"
    BASSDLL = "libbass.dylib"
    BASSOPUSZIP = "bassopus24-osx.zip"
    BASSOPUSDLL = "libbassopus.dylib"
elif platform.system() == "Linux":
    BASSZIP = "bass24-linux.zip"
    BASSDLL = "libbass.so"
    BASSOPUSZIP = "bassopus24-linux.zip"
    BASSOPUSDLL = "libbassopus.so"

print "downloading", BASSZIP
filedata = urllib2.urlopen('http://us.un4seen.com/files/'+BASSZIP)
datatowrite = filedata.read()

with open(BASSZIP, 'wb') as f:  
    f.write(datatowrite)
    f.close()

print "extracting "+BASSDLL+" from "+BASSZIP
zip_ref = zipfile.ZipFile(BASSZIP, 'r')
zip_ref.extract(BASSDLL)
zip_ref.close()

print "downloading", BASSOPUSZIP
filedata = urllib2.urlopen('http://us.un4seen.com/files/'+BASSOPUSZIP)
datatowrite = filedata.read()

with open(BASSOPUSZIP, 'wb') as f:
    f.write(datatowrite)
    f.close()

print "extracting "+BASSOPUSDLL+" from "+BASSOPUSZIP
zip_ref = zipfile.ZipFile(BASSOPUSZIP, 'r')
zip_ref.extract(BASSOPUSDLL)
zip_ref.close()

print "installing apng"
pip_install("apng")

try:
    from PIL import Image
    if Image.__version__ != "5.3.0":
        jm = raw_input("Pillow version 5.3.0 is recommended; You have version %s\nReplace with version 5.3.0? (Y/N) > " % Image.__version__).lower()
        if jm == "y":
            print "installing Pillow 5.3.0"
            pip_install("Pillow==5.3.0")
    else:
        print "Pillow 5.3.0 already exists, skipping"

except ImportError:
    print "installing Pillow 5.3.0"
    pip_install("Pillow==5.3.0")

if os.name == 'nt':
    print "downloading pyqt4"
    filedata = requests.get('https://pypi.anaconda.org/ales-erjavec/simple/pyqt4/4.11.4/PyQt4-4.11.4-cp27-none-win32.whl')
    datatowrite = filedata.content

    with open('PyQt4-4.11.4-cp27-none-win32.whl', 'wb') as f:  
        f.write(datatowrite)
        f.close()
    

    print "installing pyqt4"
    pip_install('PyQt4-4.11.4-cp27-none-win32.whl')

else:
    print "downloading sip"
    filedata = urllib2.urlopen('http://www.riverbankcomputing.com/static/Downloads/sip/4.19.15/sip-4.19.15.tar.gz')  
    datatowrite = filedata.read()

    with open('sip.tar.gz', 'wb') as f:  
        f.write(datatowrite)
        f.close()
        
    print "downloading pyqt4"
    filedata = urllib2.urlopen('http://sourceforge.net/projects/pyqt/files/PyQt4/PyQt-4.12.3/PyQt4_gpl_x11-4.12.3.tar.gz')  
    datatowrite = filedata.read()

    with open('pyqt4.tar.gz', 'wb') as f:  
        f.write(datatowrite)
        f.close()
    print "on linux you will have to build first sip and then pyqt4 yourself..."
    print "to do that, extract the sip.tar.gz and pyqt4.tar.gz and run 'python2 configure.py' then 'make' and lastly 'make install' in both folders"

print "done"
