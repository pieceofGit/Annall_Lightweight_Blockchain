"""Membership management.
1. On start-up, nodes are activated by posting to be in active reader or writer set
2. Coordinator fetches a new config and spreads info if new version in membership list """
import json
import requests
from interfaces import verbose_print, vverbose_print

class MembershipData:
    def __init__(self, id, prepend_path, conf_file, bcdb, is_writer):
        self.id = id
        self.prepend_path = prepend_path
        self.conf_file_name = conf_file 
        self.writer_list = None
        self.reader_list = None
        self.conf = None
        self.current_version = None
        self.proposed_version = None
        self.waiting_list = []
        self.disconnect_list = []
        self.bcdb = bcdb
        self.data_is_downloaded = False
        self.is_writer = is_writer
        self.reset_number = 0
        with open(self.prepend_path + self.conf_file_name, "r") as conf_file:
            self.conf = json.load(conf_file)
            self.api_path = f'http://{self.conf["writer_api"]["hostname"]}:{self.conf["writer_api"]["port"]}/'
        # Nodes post to be in active set
        self.get_remote_conf()
        self.set_lists()

    def set_lists(self):
        """ Updates the active sets """
        self.writer_list = self.conf["writer_list"]
        self.reader_list = self.conf["reader_list"]
            
    def get_remote_conf(self):
        """Running nodes ask for config and update proposed version"""
        try:
            response = requests.get(self.api_path + "config", {}, timeout=5)
            verbose_print("[CONFIG node API] Got config from node API")
            self.conf = response.json()
            if self.current_version and self.conf["membership_version"] > self.current_version:
                self.proposed_version = self.conf["membership_version"]
                self.requested_peer_changes(self.conf["writer_list"], self.conf["reader_list"])
            else:
                self.current_version = self.conf["membership_version"]
        except Exception as e:
            verbose_print("[CONFIG LOCAL] Failed to get config from writer", e)
    
    def activate_node(self):
        """Nodes activated on startup through external party config file"""
        # Nodes get conf with them included in active reader or writer set
        response = requests.post(self.api_path + "activate_node", json.dumps({ "id": self.id, "is_writer": self.is_writer }), timeout=2)
        self.conf = response.json()
        self.current_version = self.conf["membership_version"]
        self.set_lists()
        
    def update_version(self):
        """Updates active reader set and changes current version when changes have been applied"""
        self.set_lists()
        self.current_version = self.proposed_version
        self.waiting_list = []
        self.disconnect_list = []
            
    def requested_peer_changes(self, writer_list, reader_list):
        """Adds difference of active readers and writers to waiting list.
        Should remove connection to nodes not in active lists"""
        self.waiting_list.extend(list(set(writer_list)+set(reader_list)-set(self.writer_list)-set(self.reader_list)-set(self.waiting_list)))
        self.disconnect_list.extend(list(set(self.writer_list)+set(self.reader_list)-set(writer_list)-set(reader_list)-set(self.disconnect_list)))
        
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
