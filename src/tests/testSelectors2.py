import selectors
import socket
import sys
import json
import time 
import random
import argparse

GLOBAL_config_list_of_peers = []



class PeerNode:
    def __init__(self, host, port, id):
        # connection, address are as returned by accept
        self.remote_listener = (host, port)
        self.remote_id = id
        self.connection = None
        self._is_connected = False  # shall be true if me is connected to the remote peer
        self._lastActive = None

    def __del__(self):
        #self.connection.close()  
        pass


class Peers:
    list_of_peers = {}
    def __init__(self, id):
        # 
        for peer in GLOBAL_config_list_of_peers:
            peer_id = int(peer["id"])
            if peer_id != me:
                host = peer["host"] 
                port = int(peer["port"])
                list_of_peers[peer_id] = PeerNode(host,port,peer_id)

    def accept(self, conn):
        pass

    def is_fully_connected(self):
        for peer_id, pNode in list_of_peers:
            if not pNode._is_connected:
                return False
        return True

    def connect_to_all(self):
        pass

    
        

class p2pMesh:
    sel = selectors.DefaultSelector()

    def __init__(self, me: int, listen_at):
        #  me is the id of this node
        self.me = me
        self.listen_address = listen_at
        try:
            self.listen_sock = socket.socket()
            self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_sock.bind(('localhost', 50015))
            self.listen_sock.listen(100)
            self.listen_sock.setblocking(False)
        except Exception as e:
            print("Error: Cannot setup socket - no point in continuing", type(e), e.args)
            raise
        
        try:
            skey = p2pMesh.sel.register(self.listen_sock, selectors.EVENT_READ, self.accept) 
        except Exception as e:
            print("Error: Cannot register accept listener - no point in continuing", type(e), e.args)
            raise  
        else:
            print(skey)
            print("p2pMesh created [",me,"] ", self.listen_sock) 

    @classmethod
    def accept(cls, sock, mask):
        conn, addr = sock.accept()  # Should be ready
        print('accepted', conn, 'from', addr)
        conn.setblocking(False)
        skey = p2pMesh.sel.register(conn, selectors.EVENT_READ, cls.read)
        print(skey)

    @classmethod
    def read(cls, conn, mask):
        data = conn.recv(1000)  # Should be ready
        if data:
            print('echoing', repr(data), 'to', conn)
            conn.send(data)  # Hope it won't block
        else:
            print('closing', conn)
            p2pMesh.sel.unregister(conn)
            conn.close()


    def run(self):
        while True:
            print("entering select")
            try:
                events = p2pMesh.sel.select(timeout=5) 
            except Exception as e:
                print("Error: Timeout - remote end hung up")  #, type(e), e.args)
                break
            
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
            
        print("exiting gracefully")
        p2pMesh.sel.close()


if __name__ == "__main__":
    
    ap = argparse.ArgumentParser()
    ap.add_argument('configfile', nargs='?', type=argparse.FileType('r'),
                    default="../testdata/config.writer", help='configuration file (default stdin)')
    ap.add_argument("-myID", default=1, type=int, help="ID fyrir skrifara, mandatory")
    a = ap.parse_args()
    print(sys.argv[0], "config: ", a.configfile, "MyID:", a.myID)
    print()

    read_data = a.configfile.read()
    config_list_of_peers = json.loads(read_data)

    print(config_list_of_peers)
    me = a.myID
    host = ''
    port = 0
    for peer in config_list_of_peers:
        id = int(peer["id"])
        if id == a.myID:
            host = peer["host"] 
            port = int(peer["port"])

    p2p = p2pMesh(me,(host, port))
    p2p.run()

