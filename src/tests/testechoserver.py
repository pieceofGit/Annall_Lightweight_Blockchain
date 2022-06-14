import sys
import socket
import threading #from threading import Thread, active_count
import time
import json 


BUFFER_SIZE = 1024

ClientNames = [
    "orange",
    "apple",
    "pear",
    "banana",
    "kiwi",
    "apple",
    "banana",
    "lemon",
    "plum",
    "peach",
    "lime",
]


class ClientHandler(threading.Thread):
    # noinspection PyPep8Naming
    def __init__(self, threadID, _name, connection):
        threading.Thread.__init__(self, name=_name)
        self.threadID = threadID
        #self.name = name
        self.connection = connection
        self.delay = 3
        self.terminate = False

    def run(self):
        # Where the actual service of the client request takes place
        print("Starting Client:", self.threadID)
       
        # initial handshake with client
        msg = json.dumps({'Server': "Hello", 'Name': ClientNames[self.threadID]})
        print("To Client  :", msg)
        self.connection.send(msg.encode())

        data = self.connection.recv(BUFFER_SIZE)
        msg = data.decode()
        print("From client: ", msg) # Should be: {'Client': "Hello", 'Name': name}
        d = json.loads(msg)
        self.name = d['Name']

        # Service client requests until client terminates
        while not self.terminate:
            msg = json.dumps({"Server Echo": self.name, "Request": "Whatever"})
            try:
                self.connection.send(msg.encode())
                data = self.connection.recv(BUFFER_SIZE)
            except Exception as e:  # should really be more specific
                print("exception", type(e), e)
                self.terminate = True
                break

            msg = data.decode()
            print("Event Received (recv): ", msg, " ", data)
            time.sleep(self.delay)

        print("Exiting run " + self.name)

    def __del__(self):
        print("Thread ", self.name, "closing connection")
        self.connection.close()


# noinspection PyPep8Naming
class TCP_Server:
    NumConnections = 0
    threads = []
    ServerTerminate = False

    # noinspection PyPep8Naming
    def __init__(self, name, IPv4_addr, port, max_listeners):
        self.name = name
        self.max_listeners = max_listeners

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.s.bind((IPv4_addr, port))
            self.s.listen(5)
        except:
            raise

        print('Server started - listening at', TCP_IP, ':', TCP_PORT)

    def accept(self):
        try: 
            conn, addr = self.s.accept()
        except KeyboardInterrupt:
            TCP_Server.ServerTerminate = True
            print("Terminating server")
        else:     
            TCP_Server.NumConnections += 1
            #print('Connection number:', TCP_Server.NumConnections, 'address:', addr)
            self.handle_client(TCP_Server.NumConnections, conn, addr)
            
    def cleanup_terminated_threads(self, _all=False):
        live_threads = []
        for t in TCP_Server.threads:
            if not _all and t.is_alive():
                print("Thread: ", t.name, "is alive and running")
                live_threads.append(t)
            else:
                if not t.is_alive(): 
                    print("Thread: ", t.name, "has terminated")
                t.join()
        TCP_Server.threads = live_threads

    def handle_client(self, connections, connection, addr):
        # cleanup terminated threads
        self.cleanup_terminated_threads()

        print("Handle Client", connections, "total threads", threading.active_count())  
        try:          
            thread = ClientHandler(connections, None, connection)
            TCP_Server.threads.append(thread)
            thread.start()
            if connections > 10:
                raise Exception("H;tta")
        except KeyboardInterrupt:
            ServerTerminate = True

    def __del__(self):
        # Wait for all threads to complete
        #for t in TCP_Server.threads:
        #    t.join()
        self.cleanup_terminated_threads(True)
        if not self.s._closed:                    # closing listen socket
            self.s.close()

##

if __name__ == "__main__":

    TCP_IP = '127.0.0.1'
    TCP_PORT = 5006

    if len(sys.argv) > 1:
        TCP_PORT = int(sys.argv[1])

    EchoServer = TCP_Server("EchoServerTest", TCP_IP, TCP_PORT, 20)
    while not EchoServer.ServerTerminate:
        EchoServer.accept()
