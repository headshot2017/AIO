import os

def getThemeFile(theme, file):
    if os.path.exists("data/themes/%s/%s" % (theme, file)): return "data/themes/%s/%s" % (theme, file)
    return "data/themes/default/%s" % file

def getImage(file):
    exts = (".png", ".gif")
    for ext in exts:
        os.path.exists(file + ext): return file + ext
    raise Exception("Image file '%s' in %s file formats not found" % (file, exts))

def getAnimatedImage(file):
    exts = (".apng", ".webp", ".gif", ".png")
    for ext in exts:
        os.path.exists(file + ext): return file + ext
    raise Exception("Animated image file '%s' in %s file formats not found" % (file, exts))
