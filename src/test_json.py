# import time
# from datetime import datetime
# import json
# the_dict = {"hello":"john"}
# if type(the_dict) == dict:
#     print("IS DICT")
# print(the_dict)
# json_dict = json.dumps(the_dict) # Dict to json
# print(json.dumps(json_dict))
# print(f"{json_dict}")
# print(json_dict)
# # dict_json = json.loads(json_dict)
# # print(dict_json)    # json to dict
# # print(json_dict)
# # json_dict = json.dumps(json_dict)
# # print(json_dict)
# # print(json.dumps(json_dict))

# ts = time.gmtime()
# insert_time = time.strftime("%Y:%m:%d %H:%M:%S", ts)

# print(insert_time)
# print(type(insert_time))
# def getTimeStamp(date):
#     return datetime.timestamp(date)
# print(getTimeStamp(datetime.now()))
# print("False" == 'False')

# config = {
#   "no_active_writers": 2,
#   "no_permitted_writers": 5,
#   "writer_set": [
#     {
#       "name": "writer_1",
#       "id": 1,
#       "hostname": "127.0.0.1",
#       "protocol_port": 15000,
#       "client_port": 5001,
#       "pub_key": 6587849500818316161519508278916854824201302152793630979346725188602264462651268740217047928962253207403830618696453825975409521538077356628137373401104759
#     },
#     {
#       "name": "writer_2",
#       "id": 2,
#       "hostname": "127.0.0.1",
#       "client_port": 5002,
#       "protocol_port": 15001,
#       "pub_key": 7072596007751013276115763365334775647526935641452954422401179425814232240581993553233465219898765669312968657349941019520385494775696600800706705707268499
#     },
#     {
#       "name": "writer_3",
#       "id": 3,
#       "hostname": "127.0.0.1",
#       "client_port": 5003,
#       "protocol_port": 15002,
#       "pub_key": 3941527843193072839219651612561714850139179779664018649490166460942660103172749505534375311748933530214486514570162310956887591134812030523316666781462193
#     },
#     {
#       "name": "writer_4",
#       "id": 4,
#       "hostname": "127.0.0.1",
#       "protocol_port": 15003,
#       "client_port": 5004,
#       "pub_key": 5387372810488782308044565870417288547290919556026436556779644681752625312225750236098258788755163135162601938868830524137732540777797185856220997353773341
#     },
#     {
#       "name": "writer_5",
#       "id": 5,
#       "hostname": "127.0.0.1",
#       "protocol_port": 15004,
#       "client_port": 5005,
#       "pub_key": 5201436109692264160381491489256447438599177742267677213582409586036574854460390077866591556888766373006402781686515565938838507128202395078557421943547813
#     }
#   ],
#   "NO_coord": 1,
#   "modulus": 65537,
#   "version": "1.0"
# }

# new_writer = {
#   "name": "writaaaafFROMTHASIDEE",
#   "id": 5,
#   "hostname": "127.0.0.1",
#   "protocol_port": 15004,
#   "client_port": 5005,
#   "pub_key": 5201436109692264160381491489256447438599177742267677213582409586036574854460390077866591556888766373006402781686515565938838507128202395078557421943547813
# }
import ast

# from aem import app
# config["writer_set"].append(new_writer)
# print(config)
some = "False"
other = "heehaaa"
# print(bool(some))
# print(bool(some))
message = "3-2-100-block-False"
parsed_message = message.split("-")
# print(ast.literal_eval(parsed_message[2]))
# print(ast.literal_eval(parsed_message[3]))
# print(ast.literal_eval(parsed_message[4]))

import os
import struct
# payload = ast.literal_eval("False")
# payload = ast.literal_eval("Johnny")
# def generate_pad():
#     ''' Generates a number '''
#     # TODO: This needs to be changed to use an already generated pad
#     x = os.urandom(8)
#     number = struct.unpack("Q", x)[0]
#     return number % 10000
# otps = []
# for i in range(1000000):
#     otps.append(generate_pad())
# for j in otps:
#     if j <= 0:
#         print(j)
#     print(j) 

# print(-1000 % 9)
# print(-1000 % 6)
# print(-5%4)
# print(-5%-4)
# print(5%-4)
# # Python modulo operator always return the remainder having the same sign as the divisor.
# # 4 is the divisor and thus is 

# some_list = [1,2]
# if ast.literal_eval("1") in some_list:
#     print("YES")

# from .src.WriterAPI.annallWriterAPI import app
# from .WriterAPI.annallWriterAPI import app
# from ..WriterAPI.annallWriterAPI import add_new_writer

# annallWriterAPI.app.run()

# a_list = ["some"]
# print(ast.literal_eval(a_list))
# some = ("yes", "no")
# print(some[0])

# other = [0]
# print([other])

# no = []
# if not no:
#     print("YES")
# print(len(no))

# print(1%100)
import time
# import timeit
# max_latency = 2
# wait = time.perf_counter()
# max_wait = max_latency + wait
# while True:
#     print(f"wait {time.perf_counter()} and max_wait {max_wait}")
#     if time.perf_counter() > wait + 2:
#         print("HELLO")
#         break
#     else:
#         print("STILL WAITING")
# for i in range(0):
#     print("hello")

# for i in range(1):
#     print("helllo")

# if None == False:
#     print("YESSS")

# def func():
#     pass

# if func() == False:
#     print("OHHH")

# print(func())

# print(time.perf_counter())
# time.sleep(2)
# print(time.perf_counter())
# print(time.perf_counter())
# time.sleep(2)
# print(time.perf_counter())


def get_timer(wait):
    time.sleep(2)
    if time.perf_counter() > wait + 2:
        print("Time was more")


wait = time.perf_counter()
get_timer(wait)

a_list = [1,2,3]
other_list = a_list

other_list.pop(1)
print(a_list)


