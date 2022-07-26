# Here would be the backend of the life insurance asking for data
import requests
import json
BASE = "http://127.0.0.1:8000/"
latest_block = {
    "hash":"0x913d716ccd5227e756a3b2eda00b56092e7e64ea60236f73ab79285b2b741657",
    "round": 7,
    "prev_hash": "0x902a956a1ad654bc8d371de7f41ec0e88b92da8765924116f43f2f8523b1eab8"
}

# response = requests.get(BASE + "blocks", data=json.dumps(latest_block))
# print(response)
# print(response.json())
the_false = json.dumps(False)
print(json.loads(the_false))
# print(response.json())
# new_writer = {
#   "name": "writer_1",
#   "hostname": "127.0.0.1",
#   "pub_key": 6587849500818316161519508278916854824201302152793630979346725188602264462651268740217047928962253207403830618696453825975409521538077356628137373401104759
# },
# response = requests.post(BASE + "config", json.dumps({
#   "name": "writer_1",
#   "hostname": "127.0.0.1",
#   "pub_key": 6587849500818316161519508278916854824201302152793630979346725188602264462651268740217047928962253207403830618696453825975409521538077356628137373401104759
# }))
# response = requests.post(BASE + "config", json.dumps({
#   "name": "writer_1",
#   "hostname": "127.0.0.1",
#   "pub_key": 6587849500818316161519508278916854824201302152793630979346725188602264462651268740217047928962253207403830618696453825975409521538077356628137373401104759
# }))
# response = requests.post(BASE + "config", json.dumps({
#   "name": "writer_1",
#   "hostname": "127.0.0.1",
#   "pub_key": 6587849500818316161519508278916854824201302152793630979346725188602264462651268740217047928962253207403830618696453825975409521538077356628137373401104759
# }))
# # response = requests.post(BASE + "block", json.dumps({"payload":"blockisamerica"}))
# print(response.json())
