"""Gets json object for endpoint /activate_node and checks input"""
class CreateNodeInputModel:
    def __init__(self, request_obj) -> None:
        self.req_obj = request_obj
        self.error = False
        self.name = self.get_input("name", str)
        self.hostname = self.get_input("hostname", str)
        self.pub_key = str(self.get_input("pub_key", int))
        self.dict = {"name": self.name, "hostname": self.hostname, "pub_key": self.pub_key}
        
    def get_input(self, key, key_type):
        if key in self.req_obj.keys():
            if type(self.req_obj[key]) == key_type:
                return self.req_obj[key]
            else:
                self.error = True
                return f"'{key}' not of type {key_type.__name__}"
        else:
            self.error = True
        return f"Missing key '{key}' or missing value for key '{key}' in request object"    
    

            
    
    


