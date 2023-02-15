import json

class Message:
    def __init__(self, msg_obj) -> None:
        self.error = None
        self.msg_obj = json.loads(msg_obj)
        self.round = self.get_input("round", int)
        self.type = self.get_input("type", str)
        self.payload = self.get_payload("payload")
        self.from_id = self.get_input("from_id", int)
        self.version = self.get_input("version", int)
        
    @classmethod
    def create_msg(self, round, from_id, message, type, version):
        return json.dumps({"round": round, "from_id": from_id, "payload": message, "type": type, "version": version})
    
    @classmethod
    def from_json(self, json_msg):
        try:
            msg = Message(json_msg)
            if not msg.error:
                return msg
            else:
                return False
        except:
            return
        
    def get_payload(self, key):
        if key in self.msg_obj.keys():
            return self.msg_obj[key]
        else:
            self.error = True
        return f"Missing key '{key}' or missing value for key '{key}' in request object"    


    # def get_payload_type(self):
    #     if self.type == "request":
    #         return int  # Round
    #     elif self.type == "reply":
    #         return int  # OTP
    #     elif self.type == "announce":
    #         return list
    #     else:
    #         return typing.Any
        
    def get_input(self, key, key_type):
        if key in self.msg_obj.keys():
            if type(self.msg_obj[key]) == key_type:
                return self.msg_obj[key]
            else:
                self.error = True
                return f"'{key}' not of type {key_type.__name__}"
        else:
            self.error = True
        return f"Missing key '{key}' or missing value for key '{key}' in request object"    

    
        