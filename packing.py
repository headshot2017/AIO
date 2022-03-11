import struct
import zlib

def buffer_read(format, data):
    unpacked = struct.unpack_from(format, data)
    size = struct.calcsize(format)
    return data[size:], unpacked[0] # [size:] means skip ahead size amount of bytes

def readAIOHeader(data):
    packetsize, = struct.unpack("I", data[:3]+"\x00") # read first 3 bytes. this is the packet size
    compression, = struct.unpack("B", data[3]) # the last byte is the compression type. 0=none, 1=zlib
    return packetsize, compression # after that you do tcp.recv(packetsize) and check if decompression is needed

def makeAIOPacket(data, compression=0):
    if compression == 1:
        data = zlib.compress(data)
    finaldata = struct.pack("I", len(data))[:3] # strip the 4th byte off of it
    finaldata += struct.pack("B", compression) # compression type
    return finaldata + data

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
    patch = v[2] if len(v) > 2 else "0"
    
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