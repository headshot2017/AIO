import struct

def buffer_read(format, data):
    unpacked = struct.unpack_from(format, data)
    size = struct.calcsize(format)
    return data[size:], unpacked[0] # [size:] means skip ahead size amount of bytes

def packString8(string):
    string = string[:255]
    l = len(string)
    buf = struct.pack("B%ds"%l, l, string)
    return buf

def packString16(string):
    string = string[:65535]
    l = len(string)
    buf = struct.pack("H%ds"%l, l, string)
    return buf

def unpackString8(data):
    l, = struct.unpack_from("B", data)
    string, = struct.unpack_from("%ds"%l, data[1:])
    return data[struct.calcsize("B%ds"%l):], string[:l]

def unpackString16(data):
    l, = struct.unpack_from("H", data)
    string, = struct.unpack_from("%ds"%l, data[2:])
    return data[struct.calcsize("H%ds"%l):], string[:l]

def versionToInt(ver):
    v = ver.split(".")
    major = v[0]
    minor = v[1]
    if len(v) > 2:
        patch = v[2]
    else:
        patch = "0"
    
    try:
        return int(major+minor+patch)
    except:
        return int(major+minor+"0")

def versionToStr(ver):
    major = ver[1]
    minor = ver[0]
    if len(ver) > 2:
        patch = ver[2]
    else:
        return major+"."+minor
    
    return  major+"."+minor+"."+patch