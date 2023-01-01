from flask import request
class LatestBlockInputModel:
    def __init__(self, request_obj) -> None:
        self.req_obj = request_obj
        self.error = False
        self.hash = self.get_input("hash", str)
        self.round = self.get_input("round", int)
        self.dict = {"hash": self.hash, "round": self.round}
        
    def get_input(self, key, key_type):
        if key in self.req_obj.keys():
            if type(self.req_obj[key]) == key_type:
                return self.req_obj[key]
            else:
                self.error = True
                return f"'{key}' not an integer value"
        else:
            self.error = True
        return f"Missing key '{key}' or missing value for key '{key}' in request object"    
                
                    
    


