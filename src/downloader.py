"""Handles fetching most of the blockchain before a node can be activated"""
import requests
import json
from models.block import Block
class Downloader:
    def __init__(self, mem_data, bcdb) -> None:
        self.mem_data = mem_data
        self.bcdb = bcdb
    
    def download_db(self):
        """Fetches all blocks, stores in db, and compares, then notifies mem_data and quits"""
        # Handle if partially stored, if data does not match, and if others not in agreement
        # Trust 51%
        try:
            # Check if node has the same data
            address = "http://"+self.mem_data.conf["node_set"][0]["hostname"]+self.mem_data.conf["node_set"][0]["client_port"]+"/"
            latest_block = self.bcdb.get_latest_block()
            if latest_block:
                response = requests.get(address+"blocks"+latest_block["hash"]+"/verified").json()
                if response["verified"]:
                    # Get missing blocks
                    response = requests.get(address+"missing_blocks", json.dumps({"hash": latest_block.hash, "round": latest_block.round})).json()
                    # Returns empty list or missing blocks
                    if len(response):
                        # Verify blocks and add to database
                        for block in response:
                            self.bcdb.insert_block(block.round, Block.from_dict(block))
                        # Activates node
                        self.mem_data.activate_node()
        except Exception as e:
            print(e)
            
        
        