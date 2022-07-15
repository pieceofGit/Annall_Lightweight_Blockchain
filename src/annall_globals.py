

""" 
Config and global variables, implemented as a dataclass

"""

from dataclasses import dataclass
import json


@dataclass
class Writer:
    name : str
    id : int
    ip_host : str
    ip_protocol_port : int
    ip_client_port : int
    ip_admin_port : int
    pub_key : str
    

@dataclass
class Global_Config:
    name : str 
    admin_ip_host : str
    admin_ip_port : int
    total_members : int
    permitted_writers : int
    list_of_writers = dict()  ## Dictionary of <id, ChainWriter>

@dataclass
class MyDetails:
    id : int
    me : Writer
    private_key : str

##Two global variables 
gMasterConfig = Global_Config(
        "Annáll - Permitted Blockchain", "127.0.0.1", 3000, 5, 5)

gMyDetails = MyDetails(None,None,None) ## unitialized



def init_config(myID : int, config_file : str = "src/config-local.json"):
    # Read config and other init stuff
    with open(f"{config_file}", "r") as f:
        data = json.load(f)

    #MasterConfig = PermittedChainConfig(
    #    "Annáll - Permitted Blockchain", "127.0.0.1", 3000, 
    #    int(data["no_active_writers"]), int(data["no_active_writers"]))
    #    #,dict())
    gMasterConfig.permitted_writers = int(data["no_active_writers"])
    gMasterConfig.total_members = gMasterConfig.permitted_writers

    writer_list = data["writer_set"]
    for w in writer_list:
        cw = Writer(
            name = w["name"],
            id = int(w["id"]),
            ip_host = w["hostname"],
            ip_protocol_port = int(w["protocol_port"]),
            ip_client_port = int(w["client_port"]),
            ip_admin_port = None,
            pub_key = w["pub_key"]
        )
        gMasterConfig.list_of_writers[cw.id] = cw
        print(f"Added node: name={cw.name}, id={cw.id}, ip_host={cw.ip_host}")

    gMasterConfig.total_members = len(gMasterConfig.list_of_writers)
    gMyDetails.id = myID
    gMyDetails.me = gMasterConfig.list_of_writers[myID]
    
 
if __name__ == "__main__":
    
    init_config(3)

    print(" ")

    print(gMasterConfig)
    print(gMasterConfig.list_of_writers)
    print(gMyDetails)


 