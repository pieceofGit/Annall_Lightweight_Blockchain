# Here would be the backend of the life insurance asking for data
import requests

BASE = "http://127.0.0.1:5000/"

response = requests.get(BASE + "block/" + "1", {})
print(response.json())
response = requests.post(BASE + "block", {})
print(response.json())
