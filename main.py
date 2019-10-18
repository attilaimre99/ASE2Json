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
        # print self.position, self.position+count, ":".join("{:02x}".format(ord(c)) for c in self.text[self.position:self.position+count])

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
            if ch == 0x22:
                ret += "\\"
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
    def __init__(self, ip="", port=0, playersCount=0, maxPlayersCount=0, gameName="", serverName="", modeName="", mapName="", verName="", passworded=0, players=[], httpPort=0, serials=0):
        self.ip = ip
        self.port = port
        self.playersCount = playersCount
        self.maxPlayersCount = maxPlayersCount
        self.gameName = gameName
        self.serverName = serverName
        self.modeName = modeName
        self.mapName = mapName
        self.verName = verName
        self.passworded = passworded
        self.players = players
        self.httpPort = httpPort
        self.serials = serials
    
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

def pretty_print(clas, indent=0):
    print(' ' * indent +  type(clas).__name__ +  ':')
    indent += 4
    for k,v in clas.__dict__.items():
        if '__dict__' in dir(v):
            pretty_print(v,indent)
        else:
            print(' ' * indent +  k + ': ' + str(v))

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
        ip1 = buffer.read(1)
        ip2 = buffer.read(1)
        ip3 = buffer.read(1)
        ip4 = buffer.read(1)
        server.ip = '.'.join((str(ip4), str(ip3), str(ip2), str(ip1)))

        server.port = buffer.read(2)
 
        if (flags & Flags["ASE_PLAYER_COUNT"]) != 0:
            server.playersCount = buffer.read(2);

        if (flags & Flags["ASE_MAX_PLAYER_COUNT"]) != 0:
            server.maxPlayersCount = buffer.read(2);

        if (flags & Flags["ASE_GAME_NAME"]) != 0:
            server.gameName = buffer.readString();

        if (flags & Flags["ASE_SERVER_NAME"]) != 0:
            server.serverName = buffer.readString();

        if (flags & Flags["ASE_GAME_MODE"]) != 0:
            server.modeName = buffer.readString();

        if (flags & Flags["ASE_MAP_NAME"]) != 0:
            server.mapName = buffer.readString();

        if (flags & Flags["ASE_SERVER_VER"]) != 0:
            server.verName = buffer.readString();
            
        if (flags & Flags["ASE_PASSWORDED"]) != 0:
            server.passworded = buffer.read(1);

        if (flags & Flags["ASE_SERIALS"]) != 0:
            server.serials = buffer.read(1);

        if (flags & Flags["ASE_PLAYER_LIST"]) != 0:
            listSize = buffer.read(2);

            for i in range(listSize):
                playerNick = buffer.readString()
                server.players.append(playerNick)
        
        # Only used for MTA, we don't care
        noResponse = 0;
        if (flags & Flags["ASE_RESPONDING"]) != 0:
            noResponse = buffer.read(1);

        # Only used for MTA, we don't care
        restriction = 0;
        if (flags & Flags["ASE_RESTRICTION"]) != 0:
            restriction = buffer.read(4);
        
        # Only used for MTA, we don't care
        if (flags & Flags["ASE_SEARCH_IGNORE_SECTIONS"]) != 0:
            numItems = buffer.read(1);

            # Skip
            buffer.seek(buffer.tell() + 2*numItems)

        # Only used for MTA, we don't care
        if (flags & Flags["ASE_KEEP_FLAG"]) != 0:
            keepFlag = buffer.read(1);

        if (flags & Flags["ASE_HTTP_PORT"]) != 0:
            server.httpPort = buffer.read(2);

        specialFlags = 0;
        if (flags & Flags["ASE_SPECIAL"]) != 0:
            specialFlags = buffer.read(1);

        if startPos + len - buffer.tell() > 0:
            print startPos + len - buffer.tell()

        buffer.seek(startPos + len)

        servers.append(server)
        

def main():    
    # We get the data from the official server
    r = requests.get('https://master.multitheftauto.com/ase/mta/').content
    buffer = Buffer(r)

    # Initialize server buffer
    servers = []
        
    count = buffer.read(2)
    ver = 0
    if count == 0:
        ver = buffer.read(2)

    if ver == 0:
        parse_server(buffer, servers)
    if ver == 2:
        parse_server_v2(buffer, servers)

    def sortFunction(item):
        return item.playersCount

    for item in servers:
        print json.dumps(item)

if __name__ == "__main__":
    main()