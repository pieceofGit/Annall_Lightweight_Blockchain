import json
import requests
from interfaces import verbose_print, vverbose_print

class MembershipData:
    def __init__(self, id, prepend_path, conf_file, bcdb):
        self.id = id
        self.prepend_path = prepend_path
        self.conf_file_name = conf_file
        self.writer_list = None
        self.reader_list = None
        self.conf = None
        self.current_version = None
        self.proposed_version = None
        self.bcdb = bcdb
        with open(self.prepend_path + self.conf_file_name, "r") as conf_file:
            self.conf = json.load(conf_file)
            self.api_path = f'http://{self.conf["writer_api"]["hostname"]}:{self.conf["writer_api"]["port"]}/'
            self.get_remote_conf()
        self.set_lists()
        self.reset_number = 0

    def set_lists(self):
        """ Updates the active sets """
        self.writer_list = self.conf["writer_list"]
        self.reader_list = self.conf["reader_list"]
            
    def get_remote_conf(self):
        """ Get conf if in an active set, else posts to be reader or writer """
        try:
            response = requests.get(self.api_path + "config", {}, timeout=5)
            verbose_print("[CONFIG node API] Got config from node API")
            self.conf = response.json()
            # 
            if self.current_version and self.conf["membership_version"] > self.current_version:
                self.proposed_version = self.conf["membership_version"]
            else:
                self.current_version = self.conf["membership_version"]
        except Exception as e:
            verbose_print("[CONFIG LOCAL] Failed to get config from writer", e)
            
    def check_delete_blocks(self):
        # Remote request for update
        try:
            response = requests.get(self.api_path + "update", {}, timeout=2).json()
            if response["reset_number"] > self.reset_number:
                self.reset_number = response["reset_number"]
                return True
        except:
            verbose_print("Failed to make request to remote writer API")
            return False
        
    def get_tcp_ip(self, id):
        return self.conf["node_set"][id -1]["hostname"]
    
    def get_tcp_port(self, id):
        return self.conf["node_set"][id -1]["client_port"]