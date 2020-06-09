################################
GameVersion = "0.4" # you can modify this so that it matches the version you want to make your server compatible with
AllowVersionMismatch = False # change this to 'True' (case-sensitive) to allow clients with a different version than your server to join (could raise problems)
MaxLoginFails = 3 # this amount of consecutive fails on the /login command or ECON password will kick the user
EmoteSoundRateLimit = 1 #amount of seconds to wait before allowing to use emotes with sound again
MusicRateLimit = 3 #same as above, to prevent spam, but for music
ExamineRateLimit = 2 #same as above, but for Examine
OOCRateLimit = 1 # amount of seconds to wait before allowing another OOC message (anti spam)
WTCERateLimit = 10 # amount of seconds to wait before allowing another testimony button (anti spam)
ClientPingTime = 30 # amount of seconds to wait before kicking a player that hasn't sent the ping packet
ShowNameLength = 16 # maximum amount of characters (or letters if you're computer illiterate) a showname can have, it is trimmed down if exceeded

AllowBot = False # set this to True to allow usage of the /bot command (NOTE: to use these bots you MUST have the client data on the server so that it can get the character data)
################################

############CONSTANTS#############
ECONSTATE_CONNECTED = 0
ECONSTATE_AUTHED = 1
ECONCLIENT_CRLF = 0
ECONCLIENT_LF = 1
MASTER_WAITINGSUCCESS = 0
MASTER_PUBLISHED = 1
################################

def plural(text, value):
    print text, value
    return text+"s" if value != 1 else text