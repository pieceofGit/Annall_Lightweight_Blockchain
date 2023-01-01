"""Gets json object for endpoint /activate_node and checks input"""
class ActivateNodeInputModel:
    def __init__(self, request_obj) -> None:
        self.req_obj = request_obj
        self.error = False
        self.id = self.get_input("id", int)
        self.is_writer = self.get_input("is_writer", bool)
        self.dict = {"id": self.id, "is_writer": self.is_writer}
        
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
        
            
    
    


