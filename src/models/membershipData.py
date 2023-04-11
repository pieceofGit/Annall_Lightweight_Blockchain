"""Membership management.
1. On start-up, nodes are activated by posting to be in active reader or writer set
2. Coordinator fetches a new config and spreads info if new version in membership list """
import json
import requests
from interfaces import verbose_print, vverbose_print
from downloader import Downloader
from threading import Event

class MembershipData:
    def __init__(self, id, prepend_path, conf_file, bcdb, is_writer):
        self.id = id
        self.prepend_path = prepend_path
        self.conf_file_name = conf_file 
        self.ma_writer_list = None # As given by the membership authority (MA)
        self.ma_reader_list = None 
        self.round_writer_list = None # Changes based on penalty box
        self.round_reader_list = None 
        self.conf = None
        self.current_version = None
        self.proposed_version = 0
        self.waiting_list = []
        self.round_disconnect_list = []   # Resets every round
        self.bcdb = bcdb
        self.penalty_box = {}
        self.node_activated = False
        self.is_writer = is_writer
        self.reset_number = 0
        with open(self.prepend_path + self.conf_file_name, "r") as conf_file:
            self.conf = json.load(conf_file)
            self.api_path = f'http://{self.conf["writer_api"]["hostname"]}:{self.conf["writer_api"]["port"]}/'
        # Assumes e.g. node declares itself as writer if writer
        self.get_remote_conf()
        self.set_lists()
        self.stop_event = None
        self.is_genesis_node = self.id in self.ma_reader_list or self.id in self.ma_writer_list   # Genesis nodes start up without needing to fetch data
        if not self.is_genesis_node:    
            self.stop_event = Event()   # Stop downloading process after successful db download
            self.downloader = Downloader(self, bcdb, self.stop_event)
        else:
            verbose_print("NODE ACTIVATED")
            self.node_activated = True

    def set_lists(self):
        """Updates the active sets"""
        if self.node_activated:
            
            for writer in self.conf["writer_list"]:
                if writer not in self.ma_writer_list:
                    self.round_writer_list.append(writer)
            for reader in self.conf["reader_list"]:
                if writer not in self.ma_reader_list:
                    self.round_reader_list.append(reader)
        else:
            self.round_writer_list = self.conf["writer_list"]
            self.round_reader_list = self.conf["reader_list"]
        self.ma_writer_list = self.conf["writer_list"]
        self.ma_reader_list = self.conf["reader_list"]
        
    
    def waiting_node_get_conf(self, version = None):
        try:
            if version:
                response = requests.get(self.api_path + "config/" + version, {}, timeout=2)
            else:
                response = requests.get(self.api_path + "config", {}, timeout=2)
            self.conf = response.json()
            self.current_version = self.conf["membership_version"]
            self.set_lists()
        except Exception as e:
            verbose_print("[CONFIG LOCAL] Failed to get config from writer", e)
            self.current_version = 0
    
    def get_membership_version(self, version):
        try:
            response = requests.get(self.api_path + "config/" + str(version), {}, timeout=2)
            if response.status_code == 200:
                self.conf = response.json()
                self.proposed_version = self.conf["membership_version"]
                return True
            else:
                raise Exception
        except Exception as e:
            print(e)
            return False

    def get_remote_conf(self) -> int:
        """Running nodes ask for config and update proposed version"""
        try:
            response = requests.get(self.api_path + "config", {}, timeout=2)
            self.conf = response.json()
            if self.current_version and self.conf["membership_version"] > self.current_version: # New membership file
                self.proposed_version = self.conf["membership_version"]
                # self.add_to_waiting_and_disconnect_lists(self.conf["writer_list"], self.conf["reader_list"])
                return self.proposed_version
            else:
                self.current_version = self.conf["membership_version"]
                return self.current_version
        except Exception as e:
            verbose_print("[CONFIG LOCAL] Failed to get config from writer", e)
            self.current_version = 0

    def get_version(self):
        """Returns proposed or current version"""
        if self.proposed_version  > self.current_version:
            return self.proposed_version
        else:
            return self.current_version
    
    def deactivate_node(self):
        """"""
        try:
            response = requests.post(self.api_path + "deactivate_node", json.dumps({"id": self.id, "is_writer": self.is_writer}), timeout=2)
            # self.conf = response.json()
            return True;
        except Exception as e:
            verbose_print(f"Failed to get config from writer API: {e}")
            return False;
        
    def activate_node(self):
        """Nodes activated on startup through external party config file"""
        # Nodes get conf with them included in active reader or writer set
        # Post to activate if node is not in the active list. 
        try:
            response = requests.post(self.api_path + "activate_node", json.dumps({"id": self.id, "is_writer": self.is_writer}), timeout=2)
            self.conf = response.json()
            self.stop_event.set()
        except Exception as e:
            verbose_print(f"Failed to get config from writer API: {e}")
        self.current_version = self.conf["membership_version"]
        self.set_lists()
        self.node_activated = True  # Node joins consensus protocol
        
    def downloader_clean_up(self):
        """Clean up after successful download"""
        if self.stop_event:
            self.stop_event.set()
            self.downloader.thread.join()

        
        
    def add_to_penalty_box(self, round):
        for node in self.round_disconnect_list:
            node_key = self.mem_data.conf[node]["pub_key"]
            if self.penalty_box.get(node_key, None):
                self.penalty_box[node_key]["counter"] += 1
                self.penalty_box[node_key]["in_penalty_box"] = True
                self.penalty_box[node_key]["round_added"] = round
            else:
                self.penalty_box[node_key] = {"id": node, "counter": 1, "in_penalty_box": True, "round_added": round}
       
    def set_round_lists(self):
        """Moves nodes from """
        for node in self.round_disconnect_list:
            # Remove from active node list
            if node in self.ma_writer_list:
                self.round_writer_list.remove(node)
            else:
                self.round_reader_list.remove(node)
        for key in self.penalty_box:
            if self.penalty_box[key]["in_penalty_box"]:
                if round > self.penalty_box[key]["round_added"] + 2 ** self.penalty_box[key]["counter"]:
                    # Node is no longer in penalty box
                    self.penalty_box[key]["in_penalty_box"] = False
                    # Add node back to round active node set
                    if self.penalty_box[key]["id"] in self.ma_writer_list:
                        self.round_writer_list.append(self.penalty_box[key]["id"])
                    else:
                        self.round_reader_list.append(self.penalty_box[key]["id"])
        self.round_reader_list.sort()
        self.round_writer_list.sort()
        
    def update_version(self):
        """Updates active reader set and changes current version when changes have been applied"""
        self.set_lists()
        self.current_version = self.proposed_version
        self.waiting_list = []
        self.round_disconnect_list = []
        
    def add_to_waiting_and_disconnect_lists(self, writer_list, reader_list):
        """Adds difference of active readers and writers to waiting list.
        Should remove connection to nodes not in active lists"""
        self.waiting_list.extend(list(set(writer_list)+set(reader_list)-set(self.ma_writer_list)-set(self.ma_reader_list)-set(self.waiting_list)))
        self.round_disconnect_list.extend(list(set(self.ma_writer_list)+set(self.ma_reader_list)-set(writer_list)-set(reader_list)-set(self.round_disconnect_list)))
        
    def check_reset_chain(self):
        # Remote request for update
        try:
            response = requests.get(self.api_path + "reset", {}, timeout=2).json()
            if response["reset_number"] > self.reset_number:
                self.reset_number = response["reset_number"]
                return True
        except Exception as e:
            verbose_print("Failed to make request to remote writer API ", e)
            return False
        
    def get_tcp_ip(self, id):
        return self.conf["node_set"][id -1]["hostname"]
    
    def get_tcp_port(self, id):
        return self.conf["node_set"][id -1]["client_port"]
