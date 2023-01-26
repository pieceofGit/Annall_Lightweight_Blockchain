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
        return f'http://{self.mem_data.conf["node_set"][num]["hostname"]}:{self.mem_data.conf["node_set"][num]["client_port"]}/'

    def verify_latest_block(self):
        """Check if node latest block is verified by at least 51% of network. If not, drop our db and fetch correct data"""
        latest_block = self.bcdb.get_latest_block()
        trusted_nodes = []  # List of node id's that verify node latest block
        reader_and_writer_list = self.mem_data.writer_list + self.mem_data.reader_list
        if self.mem_data.id in reader_and_writer_list:
            reader_and_writer_list.remove(self.mem_data.id)
        responding_nodes = 0
        for node in reader_and_writer_list:
            try:
                response = requests.get(self.get_client_address(node)+"blocks/"+latest_block["hash"]+"/verified", timeout=2).json()
                if response["verified"]:
                    trusted_nodes.append(node)
                responding_nodes += 1
            except:
                verbose_print("Node did not respond with verification of latest block")
                
        if ((len(trusted_nodes) / len(reader_and_writer_list))) > 0.5:
            return latest_block, trusted_nodes, True  # TODO: Should be randomized list, from which node we fetch the data
        else:
            # Majority did not validate our latest block hash
            if responding_nodes:
                self.bcdb.truncate_table()
                return None, None, True
            else:
                # No other node online. Startup on our own
                return None, None, False
    
    def download_db(self):  # run function for thread
        """Fetches all blocks, stores in db, and compares, then activates node and quits"""
        # Handle if partially stored, if data does not match, and if others not in agreement
        # Trust 51%
        # Should ask for data from a random running node
        try:
            # Check if node at least has the same chain as others on the network
            latest_block, trusted_node_list, online_nodes  = self.verify_latest_block()                    
            in_sync = False
            if not online_nodes:    # No other nodes up and running. Activate node.
                in_sync = True
            # In sync if got data from a node and new latest block is verified by at least 51% of other nodes in network.
            node_num = 0
            node_list = trusted_node_list if trusted_node_list else self.mem_data.writer_list + self.mem_data.reader_list
            while not in_sync and node_num < len(node_list):   # Attempt to get data from an active node
                if latest_block:    # Only get missing blocks
                    # Get missing blocks
                    try:
                        missing_blocks = requests.get(self.get_client_address(node_list[node_num])+"missing_blocks", json.dumps({"hash": latest_block.hash, "round": latest_block.round}), timeout=2).json()
                    except:
                        verbose_print("Failed to get missing blocks from node")
                    # Returns empty list or missing blocks
                    if len(missing_blocks) > 1:
                        if missing_blocks[0].prev_hash == latest_block.prev_hash: # If not equal, get from another node
                            for block in missing_blocks[1:]:
                                self.bcdb.insert_block(block.round, Block.from_dict(block))
                            in_sync = True
                    else:
                        # Node is up to date
                        in_sync = True
                else:
                    # Get all blocks
                    try:
                        response = requests.get(self.get_client_address(node_list[node_num])+"blocks", {}, timeout=2).json()
                        if len(response):
                            for block in response:
                                self.bcdb.insert_block(block.round, Block.from_dict(block))
                            in_sync = True
                    except Exception as e:
                        print(e)
                        
            latest_block, trusted_node_list, online_nodes  = self.verify_latest_block()
            if trusted_node_list and online_nodes and not self.mem_data.node_activated:  # Fetched data is verified
                # Activates node for connecting to other 
                self.mem_data.activate_node()
            # All nodes should have a client api on the same computer as the node running the consensus. It should perhaps not be a thread in the program. 
        except Exception as e:
            print(e)
            
        
        