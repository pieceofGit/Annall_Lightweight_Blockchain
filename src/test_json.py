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

