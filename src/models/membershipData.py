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
        self.ma_reader_list = None # As given by the membership authority (MA)
        self.round_writer_list = None # Changes based on the penalty box
        self.round_reader_list = None # Changes based on the penalty box
        self.conf = None    # Current config
        self.current_version = None # Current version of config
        self.proposed_version = 0   # Proposed version of config
        self.waiting_list = []  # Nodes waiting to be added to round_writer_list or round_reader_list
        self.round_disconnect_list = []   # Nodes voted to be set in penalty box in next round
        self.disconnected_nodes = []    # Nodes disconnected from in current round
        self.bcdb = bcdb    # Blockchain database object
        self.penalty_box = {}   # Stores state for nodes in penalty box   
        self.node_activated = False
        self.is_writer = is_writer
        self.reset_number = 0   # Reset number for blockchain from MA
        with open(self.prepend_path + self.conf_file_name, "r") as conf_file:
            self.conf = json.load(conf_file)
            self.api_path = f'http://{self.conf["writer_api"]["hostname"]}:{self.conf["writer_api"]["port"]}/'
        # Assumes e.g. node declares itself as writer if writer
        self.get_remote_conf()
        self.update_lists()
        self.stop_event = None
        # This logic does not work if a joined node crashes.
        # Also, do nodes share the penalty box anywhere for new nodes?
        self.is_genesis_node = self.id in self.ma_reader_list or self.id in self.ma_writer_list   
        if not self.is_genesis_node:    # Non-genesis nodes start up by fetching the blockchain db
            self.stop_event = Event()   # Stop downloading process after successful db download
            self.downloader = Downloader(self, bcdb, self.stop_event)
        else:
            verbose_print("NODE ACTIVATED")
            self.node_activated = True


    def update_lists(self):
        """Updates the active sets for an activated node."""
        #TODO: crashed nodes should be able to join again?? If a node crashes, it should startup differently. Perhaps simpler just to deactivate it.
        if self.node_activated:
            remove_list = [id for id in self.round_writer_list + self.round_reader_list if id not in self.conf["writer_list"] + self.conf["reader_list"]]
            for id in remove_list:  # Removes a deactivated node from all lists
                if id in self.round_writer_list:
                    self.round_writer_list.remove(id)
                if id in self.round_reader_list:
                    self.round_reader_list.remove(id)
                if id in self.round_disconnect_list:
                    self.round_disconnect_list.remove(id)
                if id in self.waiting_list:
                    self.waiting_list.remove(id)
                if id in self.penalty_box:
                    self.penalty_box.remove(id)
            # Only add new nodes, not nodes currently in penalty box.
            for writer in self.conf["writer_list"]:
                if writer not in self.ma_writer_list:
                    self.round_writer_list.append(writer)
            for reader in self.conf["reader_list"]:
                if writer not in self.ma_reader_list:
                    self.round_reader_list.append(reader)
        else:
            self.round_writer_list = self.conf["writer_list"].copy()
            self.round_reader_list = self.conf["reader_list"].copy()
        
        self.ma_writer_list = self.conf["writer_list"].copy()
        self.ma_reader_list = self.conf["reader_list"].copy()
        self.initiate_penalty_box()
        
    def initiate_penalty_box(self):
        """Initiates the penalty box for an activated node."""
        self.ma_active_node_list = self.ma_writer_list + self.ma_reader_list
        for node_id in self.ma_active_node_list:
            if not self.penalty_box.get(self.get_pub_key_by_id(node_id), None):
                self.penalty_box[self.get_pub_key_by_id(node_id)] = {"id": node_id, "counter": 1, "in_penalty_box": False, "curr_counter": 0, "honesty_counter": 0, "is_active": False}

    def update_penalty_box(self):
        """Updates the penalty box dynamic variables and sets node as active if their timer is at zero."""
        for node_key in self.penalty_box:
            if self.penalty_box[node_key]["in_penalty_box"]:
                self.penalty_box[node_key]["curr_counter"] -= 1
                if self.penalty_box[node_key]["curr_counter"] <= 0:
                    self.penalty_box[node_key]["in_penalty_box"] = False
                    self.penalty_box[node_key]["honesty_counter"] = 0
                    if self.penalty_box[node_key]["id"] in self.ma_writer_list:
                        self.round_writer_list.append(self.penalty_box[node_key]["id"])
                    elif self.penalty_box[node_key]["id"] in self.ma_reader_list:
                        self.round_reader_list.append(self.penalty_box[node_key]["id"])
            else:
                self.penalty_box[node_key]["honesty_counter"] += 1
        self.add_to_penalty_box(round)
    
    def waiting_node_get_conf(self, version = None):
        try:
            if version:
                response = requests.get(self.api_path + "config/" + version, {}, timeout=2)
            else:
                response = requests.get(self.api_path + "config", {}, timeout=2)
            self.conf = response.json()
            self.current_version = self.conf["membership_version"]
            self.update_lists()
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
                return self.proposed_version
            else:
                self.current_version = self.conf["membership_version"]
                return self.current_version
        except Exception as e:
            verbose_print("[CONFIG LOCAL] Failed to get config from writer", e)
            self.current_version = 0

    def get_version(self):
        """Returns proposed or current version. Sent with each message in protocol."""
        if self.proposed_version  > self.current_version:
            return self.proposed_version
        else:
            return self.current_version
    
    def deactivate_node(self):
        """Node calls MA to deactivate itself."""
        try:
            response = requests.post(self.api_path + "deactivate_node", json.dumps({"id": self.id, "is_writer": self.is_writer}), timeout=2)
            # self.conf = response.json()
            return True;
        except Exception as e:
            verbose_print(f"Failed to get config from writer API: {e}")
            return False;
        
    def activate_node(self):
        """Node activated on startup through MA API."""
        try:
            response = requests.post(self.api_path + "activate_node", json.dumps({"id": self.id, "is_writer": self.is_writer}), timeout=2)
            self.conf = response.json()
            self.stop_event.set()
        except Exception as e:
            verbose_print(f"Failed to get config from writer API: {e}")
        self.current_version = self.conf["membership_version"]
        self.update_lists()
        self.node_activated = True  # Node joins consensus protocol
        
    def downloader_clean_up(self):
        """Clean up after successful download"""
        if self.stop_event:
            self.stop_event.set()
            self.downloader.thread.join()
        
    def get_pub_key_by_id(self, id):
        return self.conf["node_set"][id-1]["pub_key"]
        
    def add_to_penalty_box(self, round):
        """Adds nodes from round_disconnect_list to penalty box."""
        for node_id in self.round_disconnect_list:
            node_key = self.conf["node_set"][node_id-1]["pub_key"]
            self.penalty_box[node_key]["counter"] += 1
            self.penalty_box[node_key]["in_penalty_box"] = True
            self.penalty_box[node_key]["curr_counter"] = 2**self.penalty_box[node_key]["counter"]
            self.penalty_box[node_key]["honesty_counter"] = 0
       
    def set_round_lists(self, round):
        """Updates per-round active sets."""
        for node in self.round_disconnect_list:
            # Remove from active node list
            if node in self.ma_writer_list and node in self.round_writer_list:
                self.round_writer_list.remove(node)
            elif node in self.ma_reader_list and node in self.round_reader_list:
                self.round_reader_list.remove(node)
        self.update_penalty_box()  # Update penalty box variables
        self.add_to_penalty_box(round)  # Add nodes to penalty box from disconnect list
        self.round_reader_list.sort()
        self.round_writer_list.sort()
        self.disconnected_nodes = []
        self.round_disconnect_list = []
    
    def decrease_penalty_box_counters(self):
        for key in self.penalty_box:
            if self.penalty_box[key]["in_penalty_box"]:
                self.penalty_box[key]["curr_counter"] -= 1
                
        
    def update_version(self):
        """Updates active reader set and changes current version when changes have been applied"""
        self.update_lists()
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
