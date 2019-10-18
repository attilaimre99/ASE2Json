import requests

LENGTH_OF_INT = 4
LENGTH_OF_SHORT = 2
LENGTH_OF_CHAR = 1

FLAGS = {
    "ASE_PLAYER_COUNT": 0x0004,
    "ASE_MAX_PLAYER_COUNT": 0x0008,
    "ASE_GAME_NAME": 0x0010,
    "ASE_SERVER_NAME": 0x0020,
    "ASE_GAME_MODE": 0x0040,
    "ASE_MAP_NAME": 0x0080,
    "ASE_SERVER_VER": 0x0100,
    "ASE_PASSWORDED": 0x0200,
    "ASE_SERIALS": 0x0400,
    "ASE_PLAYER_LIST": 0x0800,
    "ASE_RESPONDING": 0x1000,
    "ASE_RESTRICTION": 0x2000,
    "ASE_SEARCH_IGNORE_SECTIONS": 0x4000,
    "ASE_KEEP_FLAG": 0x8000,
    "ASE_HTTP_PORT": 0x080000,
    "ASE_SPECIAL": 0x100000
}


class Buffer:
    def __init__(self, text):
        self.text = text
        self.position = 0

    def format(self, byte):
        return "{:02x}".format(ord(byte))

    # We use this function to read the next COUNT "bytes" from the text, then move the "cursor" after the read postion
    def read(self, count):
        ret = ""
        for i in self.text[self.position : self.position + count]:
            if ord(i) != 0:
                ret += self.format(i)

        self.position += count

        # Because we removed every 0-length byte we have to take care of the case when everything is 00, meaning 0 in decimal.
        if len(ret) == 0:
            return 0

        return int(ret, 16)

    def readString(self):
        len = self.read(1)
        ret = ""

        for item in range(len):
            ch = self.read(1)
            # We have a special case for some terminating characters and new-line etc.
            if ch == 34 or ch == 92 or ch == 9 or ch == 10:
                ret += ""
            else:
                ret += chr(ch)

        return ret
    
    # Check if there are characters where we want to go next
    def step(self, count):
        return self.position + count <= len(self.text)

    def tell(self):
        return self.position

    def seek(self, pos):
        if(pos < len(self.text)):
            self.position = pos

class Server:
    def __init__(self):
        self.ip = ""
        self.port = 0
        self.playersCount = 0
        self.maxPlayersCount = 0
        self.gameName = ""
        self.serverName = ""
        self.modeName = ""
        self.mapName = ""
        self.verName = ""
        self.passworded = 0
        self.players = []
        self.httpPort = 0
        self.serials = 0

def parse_server(buffer):

    servers = []

    count = buffer.read(LENGTH_OF_INT)

    while buffer.step(6):
        server = Server()

        # Ip address
        ip_pieces = []
        for x in range(4):
            ip = buffer.read(LENGTH_OF_CHAR)
            ip_pieces.append(str(ip))
        
        ip_pieces.reverse()
        server.ip = '.'.join(ip_pieces)

        server.port = buffer.read(LENGTH_OF_SHORT)

        servers.append(server)

    return servers

def parse_server_v2(buffer):

    servers = []

    flags = buffer.read(LENGTH_OF_INT)
    sequenceNumber = buffer.read(LENGTH_OF_INT)
    count = buffer.read(LENGTH_OF_INT)

    while buffer.step(6):
        server = Server()

        startPos = buffer.tell()

        # Length
        len = buffer.read(LENGTH_OF_SHORT)

        # Ip address
        ip_pieces = []
        for x in range(LENGTH_OF_INT):
            ip = buffer.read(LENGTH_OF_CHAR)
            ip_pieces.append(str(ip))
        
        ip_pieces.reverse()
        server.ip = '.'.join(ip_pieces)

        server.port = buffer.read(LENGTH_OF_SHORT)
 
        if (flags & FLAGS["ASE_PLAYER_COUNT"]) != 0:
            server.playersCount = buffer.read(LENGTH_OF_SHORT)

        if (flags & FLAGS["ASE_MAX_PLAYER_COUNT"]) != 0:
            server.maxPlayersCount = buffer.read(LENGTH_OF_SHORT)

        if (flags & FLAGS["ASE_GAME_NAME"]) != 0:
            server.gameName = buffer.readString()

        if (flags & FLAGS["ASE_SERVER_NAME"]) != 0:
            server.serverName = buffer.readString()

        if (flags & FLAGS["ASE_GAME_MODE"]) != 0:
            server.modeName = buffer.readString()

        if (flags & FLAGS["ASE_MAP_NAME"]) != 0:
            server.mapName = buffer.readString()

        if (flags & FLAGS["ASE_SERVER_VER"]) != 0:
            server.verName = buffer.readString()
            
        if (flags & FLAGS["ASE_PASSWORDED"]) != 0:
            server.passworded = buffer.read(LENGTH_OF_CHAR)

        if (flags & FLAGS["ASE_SERIALS"]) != 0:
            server.serials = buffer.read(LENGTH_OF_CHAR)

        if (flags & FLAGS["ASE_PLAYER_LIST"]) != 0:
            listSize = buffer.read(LENGTH_OF_SHORT)

            for i in range(listSize):
                playerNick = buffer.readString()
                server.players.append(playerNick)
        
        # Only used for MTA, we don't care
        noResponse = 0
        if (flags & FLAGS["ASE_RESPONDING"]) != 0:
            noResponse = buffer.read(LENGTH_OF_CHAR)

        # Only used for MTA, we don't care
        restriction = 0
        if (flags & FLAGS["ASE_RESTRICTION"]) != 0:
            restriction = buffer.read(LENGTH_OF_INT)
        
        # Only used for MTA, we don't care
        if (flags & FLAGS["ASE_SEARCH_IGNORE_SECTIONS"]) != 0:
            numItems = buffer.read(LENGTH_OF_CHAR)

            # Skip
            buffer.seek(buffer.tell() + LENGTH_OF_SHORT*numItems)

        # Only used for MTA, we don't care
        if (flags & FLAGS["ASE_KEEP_FLAG"]) != 0:
            keepFlag = buffer.read(LENGTH_OF_CHAR)

        if (flags & FLAGS["ASE_HTTP_PORT"]) != 0:
            server.httpPort = buffer.read(LENGTH_OF_SHORT)

        specialFlags = 0
        if (flags & FLAGS["ASE_SPECIAL"]) != 0:
            specialFlags = buffer.read(LENGTH_OF_CHAR)

        # Jump to the next server
        buffer.seek(startPos + len)

        # Append the server to the set
        servers.append(server)

    return servers

def format_json(servers):
    string = "[\n"

    firstServer = True

    for server in servers:
        if firstServer == False:
            string += ",\n"

        string += "        { "
        string += "\"ip\": \"" + server.ip + "\", "
        string += "\"port\": " + str(server.port) + ", "
        string += "\"playersCount\": " + str(server.playersCount) + ", "
        string += "\"maxPlayersCount\": " + str(server.maxPlayersCount) + ", "
        string += "\"gameName\": \"" + server.gameName + "\", "
        string += "\"serverName\": \"" + server.serverName + "\", "
        string += "\"modeName\": \"" + server.modeName + "\", "
        string += "\"mapName\": \"" + server.mapName + "\", "
        string += "\"version\": \"" + server.verName + "\", "

        if server.passworded != 0:
            string += "\"passworded\": true, "
        else:
            string += "\"passworded\": false, "

        string += "\"players\": ["

        for playerName in server.players:
            string += "\"" + playerName + "\", "

        string += "], "
        string += "\"httpPort\": " + str(server.httpPort)

        firstServer = False

        string += " }"

    string += "\n    ]"

    return string

# We get the data from the official server
r = requests.get('https://master.multitheftauto.com/ase/mta/').content
buffer = Buffer(r)

# Check the first byte of the string
count = buffer.read(LENGTH_OF_SHORT)
ver = 0
if count == 0:
    # If the first byte is 0 that means that it uses the default version where there are lots of data about the servers
    ver = buffer.read(LENGTH_OF_SHORT)

servers = []
if ver == 0:
    servers = parse_server(buffer)
if ver == 2:
    servers = parse_server_v2(buffer)

print(format_json(servers))