# import socket

# # create a socket object
# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# host = socket.gethostname()

# port = 12346

# # connect to the server
# s.connect((host, port))

# # send data using a file-like object
# file_like_object = s.makefile(mode='wb')
# file_like_object.write(b'Hello, this is the data')
# file_like_object.flush()

# # receive data using a file-like object
# file_like_object = s.makefile(mode='rb')
# data = file_like_object.read()
# print(data)

# s.close()
import socket

soc = socket.socket()
soc.connect(('localhost',8081))
savefilename = "data/new_bcdb_3.json"
with soc,open(savefilename,'wb') as file:
    while True:
        recvfile = soc.recv(4096)
        if not recvfile: break
        import json
        file.write(recvfile)
print("File has been received.")