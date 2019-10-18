import requests
import json

Flags = {
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

    def read(self, count):
        ret = ""
        for i in self.text[self.position:self.position+count]:
            if ord(i) != 0:
                ret += "{:02x}".format(ord(i))

        self.position += count
        if len(ret) == 0:
            return 0

        return int(ret, 16)

    def readString(self):
        len = self.read(1)
        ret = ""

        for item in range(len):
            ch = self.read(1)
            # print ch, chr(ch)
            if ch == 34:
                ret += ""
            elif ch == 92:
                ret += "/"
            elif ch == 9:
                ret += ""
            elif ch == 10:
                ret += ""
            else:
                ret += chr(ch)

        return ret
    
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

def parse_server(buffer, servers):

    count = buffer.read(4)

    while buffer.step(6):
        server = Server()

        # Ip adress
        ip_pieces = []
        for x in range(4):
            ip = buffer.read(1)
            ip_pieces.append(str(ip))
        
        ip_pieces.reverse()
        server.ip = '.'.join(ip_pieces)

        server.port = buffer.read(2)

        servers.append(server)

def parse_server_v2(buffer, servers):
    flags = buffer.read(4)
    sequenceNumber = buffer.read(4)
    count = buffer.read(4)

    while buffer.step(6):
        server = Server()

        startPos = buffer.tell()

        # Length
        len = buffer.read(2)

        # Ip adress
        ip_pieces = []
        for x in range(4):
            ip = buffer.read(1)
            ip_pieces.append(str(ip))
        
        ip_pieces.reverse()
        server.ip = '.'.join(ip_pieces)

        server.port = buffer.read(2)
 
        if (flags & Flags["ASE_PLAYER_COUNT"]) != 0:
            server.playersCount = buffer.read(2)

        if (flags & Flags["ASE_MAX_PLAYER_COUNT"]) != 0:
            server.maxPlayersCount = buffer.read(2)

        if (flags & Flags["ASE_GAME_NAME"]) != 0:
            server.gameName = buffer.readString()

        if (flags & Flags["ASE_SERVER_NAME"]) != 0:
            server.serverName = buffer.readString()

        if (flags & Flags["ASE_GAME_MODE"]) != 0:
            server.modeName = buffer.readString()

        if (flags & Flags["ASE_MAP_NAME"]) != 0:
            server.mapName = buffer.readString()

        if (flags & Flags["ASE_SERVER_VER"]) != 0:
            server.verName = buffer.readString()
            
        if (flags & Flags["ASE_PASSWORDED"]) != 0:
            server.passworded = buffer.read(1)

        if (flags & Flags["ASE_SERIALS"]) != 0:
            server.serials = buffer.read(1)

        if (flags & Flags["ASE_PLAYER_LIST"]) != 0:
            listSize = buffer.read(2)

            for i in range(listSize):
                playerNick = buffer.readString()
                server.players.append(playerNick)
        
        # Only used for MTA, we don't care
        noResponse = 0
        if (flags & Flags["ASE_RESPONDING"]) != 0:
            noResponse = buffer.read(1)

        # Only used for MTA, we don't care
        restriction = 0
        if (flags & Flags["ASE_RESTRICTION"]) != 0:
            restriction = buffer.read(4)
        
        # Only used for MTA, we don't care
        if (flags & Flags["ASE_SEARCH_IGNORE_SECTIONS"]) != 0:
            numItems = buffer.read(1)

            # Skip
            buffer.seek(buffer.tell() + 2*numItems)

        # Only used for MTA, we don't care
        if (flags & Flags["ASE_KEEP_FLAG"]) != 0:
            keepFlag = buffer.read(1)

        if (flags & Flags["ASE_HTTP_PORT"]) != 0:
            server.httpPort = buffer.read(2)

        specialFlags = 0
        if (flags & Flags["ASE_SPECIAL"]) != 0:
            specialFlags = buffer.read(1)

        buffer.seek(startPos + len)

        servers.append(server)

def main():    
    # We get the data from the official server
    r = requests.get('https://master.multitheftauto.com/ase/mta/').content
    buffer = Buffer(r)

    # Initialize servers set
    servers = []
    
    count = buffer.read(2)
    ver = 0
    if count == 0:
        ver = buffer.read(2)

    if ver == 0:
        parse_server(buffer, servers)
    if ver == 2:
        parse_server_v2(buffer, servers)

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


    print(string)

if __name__ == "__main__":
    main()