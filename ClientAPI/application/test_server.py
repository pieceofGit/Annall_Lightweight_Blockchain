# import socket

# # create a socket object
# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# # get local machine name
# host = socket.gethostname()

# port = 12346

# # bind to the port
# s.bind((host, port))

# # queue up to 5 requests
# s.listen(1)

# while True:
#     # establish a connection
#     client_socket, addr = s.accept()
#     print(f"Got a connection from {addr}")

#     # receive data using a file-like object
#     file_like_object = client_socket.makefile(mode='rb')
#     data = file_like_object.read()
#     print(data)

#     # send data using a file-like object
#     file_like_object = client_socket.makefile(mode='wb')
#     file_like_object.write(b'Thank you for sending the data')
#     file_like_object.flush()

#     client_socket.close()

# s.close()
import socket

soc = socket.socket()
soc.bind(('',8081))
soc.listen(1)

print('waiting for connection...')
with soc:
    con,addr = soc.accept()
    print('server connected to',addr)
    with con:
        filename = "data/new_bcdb_2.json"
        with open(filename, 'r') as file:
            import json
            sendfile = json.load(file)
        print(sendfile)
        con.sendall(bytes(json.dumps(sendfile), "utf-8"))
        print('file sent')
filename = "data/bcdb.json"
with open(filename, 'r') as file:
    import json
    sendfile = json.load(file)
    print(sendfile[0]["payload"])