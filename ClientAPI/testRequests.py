"""This is a test of requests in the annall client api."""
import unittest
import requests
import json
import time

class TestClientAPI(unittest.TestCase):
    """Tests client endpoints for Annáll blockchain"""
    def reset_blocks(self):
        response = requests.delete(writer_path + "blocks")
        if response.status_code == 204:
            return True
        return False

    def test_remove(self):
        """Chain deleted and GET should return empty chain"""
        self.assertTrue(self.reset_blocks(), "DELETE blocks status code")
        
    
    def test_post_block(self):
        """Adds block to chain and returns the block.
        New block should be the 0th block in get blocks"""
        response = requests.post(client_path+"blocks", payload_json)
        self.assertEqual(response.status_code, 201, "POST blocks status code")
        self.assertEqual(response.json(), payload_dict["payload"], "POST blocks, returned object")
    
    def test_get_blocks(self):
        """Should return the blockchain of length n list"""
        self.reset_blocks()
        response = requests.post(client_path+"blocks", payload_json)
        self.assertEqual(response.status_code, 201, "POST blocks status code, in GET blocks")
        time.sleep(1)
        response = requests.get(client_path+"blocks")
        self.assertEqual(response.status_code, 200, "GET blocks status code")
        latest_block = response.json()[0]["payload"]
        self.assertEqual(latest_block, payload_dict["payload"], "GET blocks, latest block")

    def test_get_by_hash(self):
        """Should return json of verified: true/false"""
        response = requests.post(client_path+"blocks", payload_json)
        self.assertEqual(response.status_code, 201, "GET blocks in POST blocks")
        response = requests.get(client_path+"blocks")
        time.sleep(1)   # Takes time to add block to blockchain
        self.assertEqual(response.status_code, 200, "GET blocks in GET blocks/<hash>/verified")
        # print("RESPONSE JSON", response.json())
        latest_block_hash = response.json()[0]["hash"]
        response = requests.get(client_path+"blocks/"+latest_block_hash+ "/verified")
        self.assertEqual(response.status_code, 200, "GET blocks/<hash>/verified status code")
        self.assertEqual(response.json(), {"verified": True}, "GET blocks/<hash>/verified object")

    def test_get_blocks_load(self):
        """Should always return the blockchain with a 200 status code"""
        for i in range(0,100):
            headers = {"User-Agent": "PostmanRuntime/7.29.2","Accept": "*/*", "Accept-Encoding": "gzip, deflate, br"}
            response = requests.get(client_path+"blocks", headers=headers)
            self.assertEqual(response.status_code, 200, f"Request {i}")
    
    def test_post_blocks_load(self):
        for i in range(0,100):
            response = requests.post(client_path+"blocks", payload_json)
            self.assertEqual(response.status_code, 201, f"Request {i}")

    def test_post_get_blocks_load(self):
        for i in range(0,100):
            response = requests.post(client_path+"blocks", payload_json)
            self.assertEqual(response.status_code, 201, f"Request {i}")
            response = requests.get(client_path+"blocks")
            self.assertEqual(response.status_code, 200, f"Request {i}")
                    
 
if __name__ == "__main__":
    client_path = "http://185.3.94.49:80/"
    writer_path = "http://176.58.116.107:70/"
    # client_path = "http://127.0.0.1:6000/"
    # writer_path = "http://127.0.0.1:8000/"
    payload_dict = {"payload": {"object": "value"}}
    payload_json = json.dumps({"payload": {"object": "value"}})
    unittest.main()