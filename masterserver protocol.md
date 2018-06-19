# AIO masterserver protocol

this document tries to explain how AIO client & server communicate with masterserver and vice versa

the very first thing that's read/sent is an uint (8),
these are the following uint (8)'s that can be read/sent:

uint8 "1" (CONNECT)

uint8 "12" (ASKFORSERVERS)

uint8 "13" (PUBLISH)

here's what they mean.

# uint8 "1" (CONNECT)
the client/server receives this from the masterserver when they connect to it.
next up, an uint (32) is read, which contains the ID assigned to the client

# uint8 "12" (ASKFORSERVERS)
the client sends this to ask for the server list (no it's not like AO1.7.5's askforservers#% which 
sends servers one by one). the masterserver responds by sending the same uint (8), and 
then the following done by a for loop (or whatever you think will work) which loops through a 
list containing all servers published:

uint16: server index

string: server name

string: server desc

string: server ip

uintv ("uint variable-size" (or just try "uint")): server port

if no servers are published it sends this:

uint16: 0

string: "No servers currently online :pepe:" (name)

string: "There are currently no available servers... Maybe host your own or wait later?:O"  (description)

string: "127.0.0.1" (ip)

uintv: 27010 (port)

# uint8 "13" (PUBLISH)
now on to the server, it sends this to publish a server to the list. the masterserver will 
automatically remove it when the "server" disconnects from the masterserver.
the server sends the following in this order:

string: server name

string: description

string: ip address (retrieved from ipv4bot.whatismyipaddress.com or icanhazip.com)

uintv: server port

the reason why you have to put an ip address is well... think about it: you want to
publish your server to YOUR masterserver for all to play... but what if it published it with
the IP 127.0.0.1? that spells disaster. that's why i put ip address there:O

here's an example of client<->MS communication interpreted in the AO protocol style:
MS is the masterserver and C is the client, as follows
(remember the uint8's from the beginning)

C: <connect>

MS: 1#0#% (1 = CONNECT uint8, 0 = ID uint32)

C: 12#% (12 = ASKFORSERVERS uint8)

let's assume there are 2 servers published and...

MS: 12#0#official AIO v0.2 test server#welcome to the official AIO v0.2 test server :O do whatever you like and have fun#190.123.69.69#27010#1#unnamed AIO server#this is an unnamed server#37.192.51.67#27010#%

the client will read all that in the order as explained above

let's go over server<->MS communication...
this time, C becomes S

S: <connect>

MS: 1#5#% (we assume the CID of the server connected to the MS is 5)

S: 13#best AIO server#please no non-vanilla content pls#185.12.59.68#27010#%

then the MS adds that to the list of servers published... if that makes any sense.
heck, if even ANY of this made any sense... at least, i hope it did- i tried my best to simplify this.
