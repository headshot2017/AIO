import struct

# taken from AIO python server code, it'll make my life easier.
def string_unpack(buf):
	unpacked = buf.split("\0")[0]
	gay = list(buf)
	for l in range(len(unpacked+"\0")):
		del gay[0]
	return "".join(gay), unpacked

def buffer_read(format, buffer):
	if format != "S":
		unpacked = struct.unpack_from(format, buffer)
		size = struct.calcsize(format)
		liss = list(buffer)
		for l in range(size):
			del liss[0]
		returnbuffer = "".join(liss)
		return returnbuffer, unpacked[0]
	else:
		return string_unpack(buffer)

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
    data, l = struct.unpack_from("B", data)
    data, string = struct.unpack_from("%ds"%l, data)
    return data[struct.calcsize("B%ds"%l):], string[:l] # remove \x00 from unpacked string

def unpackString16(data):
    data, l = struct.unpack_from("H", data)
    data, string = struct.unpack_from("%ds"%l, data)
    return data[struct.calcsize("B%ds"%l):], string[:l] # remove \x00 from unpacked string

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