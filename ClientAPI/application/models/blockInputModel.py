from flask import request
class BlockInputModel:
    def __init__(self, request_obj) -> None:
        self.error = False
        self.name = self.get_name()
        self.payload = self.get_payload(request_obj)
        self.dict = {"request_type": "block", "name": self.name, "payload": self.payload, "payload_id": 1}
        if self.error:
            self.dict = {"payload": self.payload}
    def get_name(self):
        return request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    
    def get_payload(self, request_obj):
        if "payload" in request_obj:
            return request_obj["payload"]
        else:
            self.error = True
            return "Missing key 'payload' in request object"
    
    
    


