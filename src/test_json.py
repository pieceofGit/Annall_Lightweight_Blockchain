import time
from datetime import datetime
import json
the_dict = {"hello":"john"}
if type(the_dict) == dict:
    print("IS DICT")
print(the_dict)
json_dict = json.dumps(the_dict) # Dict to json
print(json.dumps(json_dict))
print(f"{json_dict}")
print(json_dict)
# dict_json = json.loads(json_dict)
# print(dict_json)    # json to dict
# print(json_dict)
# json_dict = json.dumps(json_dict)
# print(json_dict)
# print(json.dumps(json_dict))

ts = time.gmtime()
insert_time = time.strftime("%Y:%m:%d %H:%M:%S", ts)

print(insert_time)
print(type(insert_time))
def getTimeStamp(date):
    return datetime.timestamp(date)
print(getTimeStamp(datetime.now()))