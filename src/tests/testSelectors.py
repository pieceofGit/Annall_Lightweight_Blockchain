import selectors
import socket

sel = selectors.DefaultSelector()

def accept(sock, mask):
    conn, addr = sock.accept()  # Should be ready
    print('accepted', conn, 'from', addr)
    conn.setblocking(False)
    skey = sel.register(conn, selectors.EVENT_READ, read)
    print(skey)

def read(conn, mask):
    data = conn.recv(1000)  # Should be ready
    if data:
        print('echoing', repr(data), 'to', conn)
        conn.send(data)  # Hope it won't block
    else:
        print('closing', conn)
        sel.unregister(conn)
        conn.close()

sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('localhost', 50015))
sock.listen(100)
sock.setblocking(False)
skey = sel.register(sock, selectors.EVENT_READ, accept)
print(skey)

while True:
    print("entering select")
    try:
        events = sel.select(timeout=5) 
    except Exception as e:
        print("Error: Timeout - remote end hung up")  #, type(e), e.args)
        break
    
    for key, mask in events:
        callback = key.data
        callback(key.fileobj, mask)
    
print("exiting gracefully")
sel.close()
