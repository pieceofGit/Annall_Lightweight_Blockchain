"""Handles fetching most of the blockchain before a node can be activated"""
import requests
import json
from models.block import Block
from interfaces import verbose_print
from threading import Thread


class Downloader:
    def __init__(self, mem_data, bcdb, stop_event=None) -> None:
        self.mem_data = mem_data
        self.bcdb = bcdb
        self.stop_event = stop_event
        if stop_event:
            self.thread = Thread(target=self.download_helper, name="DownloadThread")
            self.thread.start()
    
    def get_client_address(self, id):
        return f'http://{self.mem_data.conf["node_set"][id-1]["hostname"]}:{self.mem_data.conf["node_set"][id-1]["api_port"]}/'

    def verify_latest_block(self, latest_block):
        """Check if node latest block is verified by at least 51% of network. If not, drop our db and fetch correct data"""
        trusted_nodes = []  # List of node id's that verify node latest block
        reader_and_ma_writer_list = self.mem_data.ma_writer_list + self.mem_data.ma_reader_list
        if self.mem_data.id in reader_and_ma_writer_list:
            reader_and_ma_writer_list.remove(self.mem_data.id)
        responding_nodes = 0
        for node in reader_and_ma_writer_list:
            try:
                response = requests.get(self.get_client_address(node)+"blocks/"+latest_block["hash"]+"/verified", timeout=2).json()
                if response["verified"]:
                    trusted_nodes.append(node)
                responding_nodes += 1
            except:
                verbose_print("Node did not respond with verification of latest block")
                
        if ((len(trusted_nodes) / len(reader_and_ma_writer_list))) > 0.5:
            return trusted_nodes, True  # TODO: Should be randomized list, from which node we fetch the data
        else:
            # Majority did not validate our latest block hash
            if responding_nodes:
                self.bcdb.truncate_table()
                return None, True
            else:
                # No other node online. Startup on our own
                return None, False
    
    def download_helper(self):
        while not self.stop_event.is_set():
            self.download_db()
    
    def download_db(self):  # run function for thread
        """Fetches all blocks, stores in db, and compares, then activates node and quits"""
        # Handle if partially stored, if data does not match, and if others not in agreement
        # Trust 51%
        # Should ask for data from a random running node
        try:
            # Check if node at least has the same chain as others on the network
            latest_block = self.bcdb.get_latest_block()
            in_sync = False
            node_num = 0
            node_list = self.mem_data.ma_writer_list + self.mem_data.ma_reader_list
            if self.mem_data.id in node_list:
                node_list.remove(self.mem_data.id)
            while not in_sync and node_num < len(node_list):   # Attempt to get data from an active node
                if latest_block:    # Only get missing blocks
                    # Get missing blocks
                    try:
                        print({"hash": type(latest_block["hash"]), "round": type(latest_block["round"])})
                        print(self.get_client_address(node_list[node_num])+"missing_blocks")
                        request_obj = {"hash": latest_block["hash"], "round": latest_block["round"]}
                        response = requests.get(self.get_client_address(node_list[node_num])+"missing_blocks", data=json.dumps(request_obj))
                    except Exception as e:
                        verbose_print("Failed to get missing blocks from node: ", e)
                    # Returns latest block or missing blocks
                    if response.status_code == 200:
                        missing_blocks = response.json()    
                        if len(missing_blocks) > 1:
                            if missing_blocks[0]["prevHash"] == latest_block["prevHash"]: # If not equal, get from another node
                                for block in missing_blocks[1:]:
                                    self.bcdb.insert_block(block["round"], Block.from_dict(block))
                                in_sync = True
                        else:
                            # Node is up to date
                            in_sync = True
                        node_num += 1   # Try next node if node down
                else:
                    # Node had no blocks, fetch all blocks from any peer in network
                    try:
                        blocks_to_insert = requests.get(self.get_client_address(node_list[node_num])+"blocks", {}, timeout=2).json()
                        if len(blocks_to_insert):
                            blocks_to_insert.reverse()
                            for block in blocks_to_insert:
                                insert_block = Block.from_dict(block)
                                self.bcdb.insert_block(insert_block.round, insert_block)
                            in_sync = True  # TODO: Check if all blocks are verified by 51% of network
                    except Exception as e:
                        print(e)
                node_num += 1
            # Node has latest blocks. Activate node        
            if  not self.mem_data.node_activated:
                # Activates node for connecting to other 
                # print("ACTIVATED")
                self.mem_data.activate_node()
            # All nodes should have a client api on the same computer as the node running the consensus. It should perhaps not be a thread in the program. 
        except Exception as e:
            print(e, "FAILED HERE")
            
        
if __name__ == "__main__":
    from models.blockchainDB import BlockchainDB
    from models.membershipData import MembershipData
    import argparse, os
    CWD = os.getcwd()
    CONFIG_PATH = f"{CWD}/"
    PRIV_KEY_PATH = f"{CWD}/"

if __name__ == "__main__":
    print("MAIN STARTED")
    ap = argparse.ArgumentParser()
    ap.add_argument("-myID", default=3, type=int,
                    help="ID fyrir skrifara, mandatory")
    ap.add_argument("-r", default=0, type=int, help="number of rounds")
    ap.add_argument("-conf", default="configs/config-local.json", type=str, help="config file for writers")
    ap.add_argument("-privKey", default="priv_key.json", type=str, help="private key file for writer under /src")
    ap.add_argument("-db", default=None, type=str, help="Set if shared db in docker")
    ap.add_argument("-isWriter", default=True, type=bool, help="Set if shared db in docker")
    a = ap.parse_args()
    id = a.myID
    rounds = a.r
    config_file = a.conf
    priv_key = a.privKey
    db_path = a.db
    is_writer = a.isWriter
    verbose_print("[ID]", id, " [ROUNDS]", rounds)
     # Initialize the local database connection
    #   -- this is the local copy of the blockchain
    if not db_path:
        db_path = f"testNodes/test_node_{id}/blockchain.db"
    print("::> Starting up Blockchain DB = using ", db_path)
    bce = BlockchainDB(db_path)
    print("Local block chain database successfully initialized")
    mem_data = MembershipData(id, CONFIG_PATH, config_file, bce, is_writer)