import urllib2
import zipfile
import subprocess
import sys
import os

def pip_install(package):
    subprocess.call([sys.executable, "-m", "pip", "install", package])

print "installing pyinstaller"
pip_install('pyinstaller==3.6')

print "installing ini"
pip_install('ini')

print "installing requests"
pip_install('requests')
import requests

print "done"
