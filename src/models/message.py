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
        self.cancel_round = self.get_input("cancel_number", int)
        self.view = self.get_input("view", int)
        
    @classmethod
    def create_msg(self, round, from_id, message, type, version, cancel_round, view=0):
        return json.dumps({"round": round, "from_id": from_id, "payload": message, "type": type, "version": version, "cancel_number": cancel_round, "view": view})
    
    def __str__(self) -> str:
        return f"Message(round={self.round}, type={self.type}, payload={self.payload}, from_id={self.from_id}, version={self.version})"
    
    @classmethod
    def from_json(self, json_msg):
        msg = Message(json_msg)
        if not msg.error:
            return msg
        else:
            print("Error in message object: ", msg.error)
            return False
    
    def get_payload(self, key):
        if key in self.msg_obj.keys():
            return self.msg_obj[key]
        else:
            self.error = True
        return f"Missing key '{key}' or missing value for key '{key}' in request object"    

        
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

    
        