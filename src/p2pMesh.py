# Peer to peer fully connected mesh support and establishment
import interfaces
from threading import Thread
import threading
import socket
import sys
import json
import time 
import random
import argparse

    



class ListenSocket:
    def __init__(self, IPv4_addr, port:int, max_listeners=5):    
        ''' Constructor.
            Note: RequestHandlerClass is the class that handles request, and should be derived from Threads
        '''
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.bind((IPv4_addr, port))
            self.s.listen(max_listeners)
        except Exception as e:
            print("Error: Cannot setup socket - no point in continuing", type(e), e.args)
            raise
        else:
            print('Listening at', IPv4_addr, ":" ,port)

    def accept(self):
        try: 
            conn, addr = self.s.accept()
        except KeyboardInterrupt:
            #self.__server_terminate = True
            print("Terminating")
            raise
        else:     
            return (conn, addr)


class p2pMesh:

    def __init__(self, list_of_remote_hosts, me:int):
        ''' 
            list_of_remote_hosts is a list of {id, host, port}
            me is the id of this node
            attempts to connect to and maintain connectivity with all hosts on the list
        '''
        self.list_of_remotes = list_of_remote_hosts
        self.me = me
        self.peer_nodes = []
        for peer in list_of_remote_hosts:
            id = int(peer["id"])
            if id != me:
                self.peer_nodes.append(peerNode(peer["host"], int(peer["port"]), id))


    def run(self):
        pass


if __name__ == "__main__":
    
    ap = argparse.ArgumentParser()
    ap.add_argument('configfile', nargs='?', type=argparse.FileType('r'),
                    default="../testdata/config.writer", help='configuration file (default stdin)')
    ap.add_argument("-myID", default=1, type=int, help="ID fyrir skrifara, mandatory")
    a = ap.parse_args()
    print(sys.argv[0], "config: ", a.configfile, "MyID:", a.myID)
    print()

    read_data = a.configfile.read()
    config_list_of_hosts = json.loads(read_data)

    p2p_network = p2pMesh(config_list_of_hosts, a.myID)

    host = ''
    port = 0
    for peer in config_list_of_hosts:
        id = int(peer["id"])
        if id == a.myID:
            host = peer["host"] 
            port = int(peer["port"])
    
    listen_socket = ListenSocket(host, port, max_listeners=5)



    print("here")
    
