# Test a workload for the blockchain.
# Answer how much data can be stored on the blockchain and how slow the data is fetched from the blockchain
# Test how much can be sent over the TCP sockets
# See how fast the blockchain works
# Need to have multiple instances of this workload running to test the blockchain and API in full

def get_data():
    """Get data to send to the blockchain"""
    ...
def send_requests():
    """Run a thread to send requests to the blockchain"""
    ...
def get_blockchain():
    """Returns the blockchain"""
    
def post_block():
    """Post block to blockchain"""

def setup_threads():
    """Sets up multiple threads to send data to the blockchain"""
    ...

if __name__ == "__main__":
    ...