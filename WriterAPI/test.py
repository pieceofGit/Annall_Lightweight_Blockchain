# Here would be the backend of the life insurance asking for data
import requests
import json
BASE = "http://127.0.0.1:5000/"

response = requests.get(BASE + "config", {})
print(response.json())
new_writer = {
  "name": "writer_1",
  "hostname": "127.0.0.1",
  "pub_key": 6587849500818316161519508278916854824201302152793630979346725188602264462651268740217047928962253207403830618696453825975409521538077356628137373401104759
},
response = requests.post(BASE + "config", json.dumps({
  "name": "writer_1",
  "hostname": "127.0.0.1",
  "pub_key": 6587849500818316161519508278916854824201302152793630979346725188602264462651268740217047928962253207403830618696453825975409521538077356628137373401104759
}))
# response = requests.post(BASE + "block", json.dumps({"body":"blockisamerica"}))
print(response.json())
