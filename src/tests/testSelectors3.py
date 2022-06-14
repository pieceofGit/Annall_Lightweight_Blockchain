import selectors
import socket
import sys
import json
import time 
import random
import argparse

verbose = True
vverbose = False


def verbose_print(*s):
    if verbose:
        print(s)

def vverbose_print(*s):
    if vverbose:
        print(s)

ctrl_msg = {"C-Request"   : "-{_to}-{_from}-", # "-{data}", #data is listening address
            "C-Reply"     : "-{_to}-{_from}-", # -{data}",
            "ECHOrequest" : "-{_to}-{_from}-", # -{data}",
            "ECHOreply"   : "-{_to}-{_from}-", # -{data}"
            "Data"        : "-{_to}-{_from}-"  # -{data}"
}


def create_msg(mtype:str, _to:int, _from:int, data:str=None):
    # 
    # optional data to be appended to the message
    ctrl_msg = {"C-Request"   : "-{_to}-{_from}-", # "-{data}", #data is listening address
                "C-Reply"     : "-{_to}-{_from}-", # -{data}",
                "ECHOrequest" : "-{_to}-{_from}-", # -{data}",
                "ECHOreply"   : "-{_to}-{_from}-", # -{data}"
                "Data"        : "-{_to}-{_from}-"  # -{data}"
    }
    try:
        msg = ctrl_msg[mtype].format(_to=_to,_from=_from)
        if data is not None:
            msg = msg + data
    except KeyError as e:
        print("Invalid Message")
        raise
   
    return msg.encode()

def msg_2_tuple(msg:bytes):
    print("before decode")

    # msg = b'\x00\x00\x00\xa8C-REQUEST#1#2#6587849500818316161519508278916854824201302152793630979346725188602264462651268740217047928962253207403830618696453825975409521538077356628137373401104759'

    t = msg.decode().split(b"-", maxsplit=3)
    print(msg.decode())
    t = msg.split(b"-", maxsplit=3)
    print(t)
    print("after decode")
    try:
        msg = ctrl_msg[t[0]]
    except KeyError as e:
        print("Invalid Message")
        raise
    


class PeerNode:
    def __init__(self, address, id):
        # connection, address are as returned by accept
        self.remote_listener = address  # format: (host, port)
        self.remote_id = id
        self.connection = None
        self._is_connected = False  # shall be true if me is connected to the remote peer
        self._lastActive = None

    def __del__(self):
        #self.connection.close()  
        pass


class Peers:
    list_of_peers = {}
    initialized = False
    me = -1

    def __init__(self):
        pass
    
    def initilize(self, me:int, peers):
        # 
        Peers.me = me
        if Peers.initialized:
            raise "Error: only one instance of Peers allowed"
        elif peers is  None:
            raise "Error: peers is none"
        else:
            for peer_id, peer_address in peers.items():
                if peer_id == me:
                    verbose_print("Error: Local is not a peer : ignored")
                else:
                    self.list_of_peers[peer_id] = PeerNode(peer_address,peer_id)
                    Peers.initialized = True
        if not Peers.initialized:
            raise "Error: peers is empty"

    def lookup_peer(self, addr):
        # lookup addr in list of peers - return me if 
        pass

    def add_connection(self, conn, pid):
        self.list_of_peers[pid].connection = conn
        self.list_of_peers[pid]._is_connected = True
        self.list_of_peers[pid]._lastActive = time.time()


    '''def accept(self, conn, addr):
        print("Inside  Peers:accept", self, " ", conn)
        #initiate handshake - receive identification from remote host
        data = conn.recv(4096)
        tmsg = msg_2_tuple(data)
        if (hello == "Hello") and (int(l_id) == Peers.me):
            pnode = self.list_of_peers[int(r_id)]
            if not pnode._is_connected:
                h, p = pnode.address
                if (h == r_host and p == p_host):
                    msg = create_msg("C-Reply", r_id, Peers.me)
                    conn.sendall(msg)
                    self.add_connection(conn, int(r_id))
                else:
                    print("Error host:port mismatch in connect request from peer", 
                            r_id, " ", h, ":", p, "  ", r_host, ":", r_port)
                    return False
            else:
                print("Error: Remote peer already connected")
                return False
        else:
            print("Error: Hello message format error")
            return  False

        return True
    '''

    def accept(self, conn, addr):
        print("Inside  Peers:accept", self, " ", conn)
        #initiate handshake - receive identification from remote host
        data = conn.recv(4096)
        # Verify handshake message
        try:
            print()
            print()
            print(data)
            print()
            print()
            # (mtype, l_id, r_id, address) = msg_2_tuple(data)
            print("before msg_2_tuple")
            d = msg_2_tuple(data)
            print("after msg_2_tuple")
            print("what is this")
            print(d)
        except Exception as e:
            print("Error: Message format", type(e), e.args)
            raise     
        if (int(l_id) != Peers.me):
            raise f"Remote peer ({r_id}) does not recognize me {l_id}"
        try:
            pnode = self.list_of_peers[int(r_id)]
        except Exception as e:
            print("ERROR: Unknown peer ", r_id)
        if pnode._is_connected:
            raise f"Error: Remote peer ({r_id}) is already connected"
        if pnode.address[0] != address[0] or pnode.address[1] != address[1]:
            raise f"Error host:port: Peer reports ({address}). Expected {pnode.address}"

        # Handshake from remote peer accepted
        # Complete the handshake with a connection reply
        msg = create_msg("C-Reply", r_id, Peers.me)
        try:
            conn.sendall(msg)
        except Exception as e:
            print("Error: Message format", type(e), e.args)
            raise 
        self.add_connection(conn, int(r_id))

    def is_fully_connected(self):
        for peer_id, pNode in list_of_peers:
            if not pNode._is_connected:
                return False
        return True

    def connect_to_all(self):
        pass

    
        

class p2pMesh:
    sel = selectors.DefaultSelector()
    peers = Peers()

    def __init__(self, me: int, listen_at, peer_list):
        ''' Constructs a p2pMesh. Establishes a listening socket.
            Initializes the list of peers 
            Arguments:
                me: is the id of this node in the peer network
                listen_at: the address (host, port) of the listening 
                            port for other peers to connect to.
                peer_list: list of peer hosts, containing for each, id, peer address (host, port)
                
        '''
        self.me = me
        self.listen_address = listen_at
        try:
            self.listen_sock = socket.socket()
            self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_sock.bind(listen_at)
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
            vverbose_print(skey)
            verbose_print("p2pMesh created [",me,"] ", self.listen_sock) 

        p2pMesh.peers.initilize(me, list_of_peers)
        verbose_print("List of peers ", p2pMesh.peers.list_of_peers)

    @classmethod
    def accept(cls, sock, mask):
        ''' Accept handler, registered with selector
            socket (sock) is ready - ow selector would not have returned it
            This function always succeeds, as remote id is not known handshake
        '''
        conn, addr = sock.accept()  # Should be ready
        verbose_print('accepted', conn, 'from', addr)
        try:
            cls.peers.accept(conn, addr)
        except Exception as e:
            print('Rejecting connection', conn)
            conn.close()
        else:
            conn.setblocking(False)
            skey = p2pMesh.sel.register(conn, selectors.EVENT_READ, cls.read)
            vverbose_print(skey)            

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
    ap.add_argument("-v", default=True, type=bool, help="verbose")
    ap.add_argument("-vv", default=False, type=bool, help="Very verbose")
    a = ap.parse_args()
    print("Running")
    verbose_print(sys.argv[0], "config: ", a.configfile, "MyID:", a.myID, a.v, a.vv)
    verbose = a.v
    vverbose = a.vv
    verbose_print("")

    read_data = a.configfile.read()
    config_list_of_peers = json.loads(read_data)

    # Prints content stored in ./testdata/config.writer
    verbose_print(config_list_of_peers)
    me = a.myID
    host = ''
    port = 0
    list_of_peers = {}
    for peer in config_list_of_peers:
        id = int(peer["id"])
        if id == a.myID:
            host = peer["host"] 
            port = int(peer["port"])
        else:
            paddr = peer["host"], int(peer["port"])
            list_of_peers[id] = paddr

    verbose_print(list_of_peers)

    verbose_print("start")    
    p2p = p2pMesh(me,(host, port), list_of_peers)
    p2p.run()

