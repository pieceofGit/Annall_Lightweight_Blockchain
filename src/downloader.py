"""Handles fetching most of the blockchain before a node can be activated"""
import requests
import json
from models.block import Block
from interfaces import verbose_print
class Downloader:
    def __init__(self, mem_data, bcdb) -> None:
        self.mem_data = mem_data
        self.bcdb = bcdb
        
    def get_client_address(self, num):
        return "http://"+self.mem_data.conf["node_set"][num]["hostname"]+self.mem_data.conf["node_set"][num]["client_port"]+"/"

    def verify_latest_block(self):
        """Check if node latest block is verified by at least 51% of network. If not, drop our db"""
        latest_block = self.bcdb.get_latest_block()
        trusted_nodes = []
        reader_and_writer_list = self.self.mem_data.conf["writer_list"] + self.mem_data.conf["reader_list"]
        for node in reader_and_writer_list:
            response = requests.get(self.get_client_address(node)+"blocks"+latest_block["hash"]+"/verified", timeout=2).json()
            if response["verified"]:
                trusted_nodes.append(node)
        if (len(reader_and_writer_list) / (len(trusted_nodes) + len(reader_and_writer_list))) > 0.5:
            return latest_block, trusted_nodes  # TODO: Should be randomized list
        else:
            # Node has the wrong data. Drop db
            self.bcdb.truncate_table()
            return None, None
    
    def download_db(self):
        """Fetches all blocks, stores in db, and compares, then activates node and quits"""
        # Handle if partially stored, if data does not match, and if others not in agreement
        # Trust 51%
        try:
            # Check if node has the same data
            latest_block, trusted_nodes_list  = self.verify_latest_block()    
            in_sync = False
            # In sync if got data from a node and new latest block is verified by at least 51% of other nodes in network.
            node_num = 0
            node_list = trusted_nodes_list if trusted_nodes_list else self.mem_data.conf["writer_list"] + self.mem_data.conf["reader_list"]
            while not in_sync and node_num < len(node_list):   # Attempt to get data from a trusted node
                node_address = self.get_client_address(node_list[node_num])
                if latest_block:    # Only get missing blocks
                    # Get missing blocks
                    try:
                        response = requests.get(self.get_client_address()+"missing_blocks", json.dumps({"hash": latest_block.hash, "round": latest_block.round}), timeout=2).json()
                    except:
                        verbose_print("Failed to get missing blocks from node")
                    # Returns empty list or missing blocks
                    if len(response) > 1:
                        if response[0].prev_hash == latest_block.prev_hash: # If not equal, get from another node
                            for block in response[1:]:
                                self.bcdb.insert_block(block.round, Block.from_dict(block))
                            in_sync = True
                    else:
                        # Node is up to date
                        in_sync = True
                else:
                    # Get all blocks
                    response = requests.get(self.get_client_address()+"blocks", {}, timeout=2).json()
                    if len(response):
                        for block in response:
                            self.bcdb.insert_block(block.round, Block.from_dict(block))
                        in_sync = True
            # Activates node
            self.mem_data.activate_node()
            # All nodes should have a client api on the same computer as the node running the consensus. It should perhaps not be a thread in the program. 
        except Exception as e:
            print(e)
            
        
        