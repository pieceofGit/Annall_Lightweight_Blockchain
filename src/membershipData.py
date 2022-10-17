import json
import requests
from interfaces import verbose_print

class MembershipData:
    def __init__(self, id, prepend_path, conf_file, api_path, bcdb):
        self.id = id
        self.prepend_path = prepend_path
        self.conf_file_name = conf_file
        self.writer_list = None
        self.reader_list = None
        self.conf = None
        self.api_path = api_path
        self.bcdb = bcdb
        with open(self.prepend_path + self.conf_file_name, "r") as conf_file:
            self.conf = json.load(conf_file)
            if id == 1: # API sends local requests to writer API
                self.is_api = True
            else:
                self.is_api = False
                self.get_remote_conf()
        self.set_lists()
        self.update_number = 0

    def set_lists(self):
        """ Updates the active sets """
        print(self.conf)
        self.writer_list = self.conf["writer_list"]
        self.reader_list = self.conf["reader_list"]
            
    def get_remote_conf(self):
        """ Get conf if in an active set, else posts to be reader or writer """
        try:
            response = requests.get(self.api_path + "config", {})
            self.conf = response.json()
            verbose_print("[CONFIG node API] Got config from node API")
        except Exception as e:
            verbose_print("[CONFIG LOCAL] Failed to get config from writer", e)
    
    def check_delete_blocks(self):
        if self.is_api:
            with open(self.prepend_path + "config-writer-api-update.json", "r") as writer_conf:
                response = json.load(writer_conf)
        else:
            # Remote request for update
            response = requests.get(self.api_path + "update", {}).json()
        if response["update_number"] > self.update_number:
            self.update_number = response["update_number"]
            return True
        return False

    def get_tcp_ip(self, id):
        return self.conf["node_set"][id -1]["hostname"]
    
    def get_tcp_port(self, id):
        return self.conf["node_set"][id -1]["client_port"]