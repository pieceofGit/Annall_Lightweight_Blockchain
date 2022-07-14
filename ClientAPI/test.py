# Here would be the backend of the life insurance asking for data
import requests
import json
BASE = "http://127.0.0.1:5000/"

response = requests.get(BASE + "blocks", {})
print(response.json())
response = requests.post(BASE + "block", json.dumps({"body":"blockisamerica"}))
print(response.json())
