"""A local MongoDB database connection for the configuration files of a permissioned blockchain"""
# Idea for future work: Handle all blockchains in this single API. 

import json
from enum import unique
from hashlib import new
from xml.dom import NotFoundErr
from pymongo import MongoClient
import pymongo

class ConfigDB:
    def __init__(self, conf) -> None:
        self.client = MongoClient('localhost', 27017)
        self.db = self.client.blockchain_db
        self.configs = self.db.configs
        if not self.get_latest_config():
            self.update_config(conf)
        
    def get_latest_config(self):
        """Returns latest config version"""
        try:
            conf = self.configs.find().sort([('_id', -1)]).limit(1)
            return conf[0] 
        except:
            return
        
    def get_config_version(self, index: int):
        """Returns a config version by key and db"""
        config = self.configs.find_one({"_id": index})
        if config:
            return config
        else: 
            raise NotFoundErr
        
    def node_exists(self, id: int) -> bool:
        latest_conf =  self.get_latest_config()
        for node in latest_conf["node_set"]:
            if node["id"] == id:
                return True
        return False
    
    def activate_node(self, is_writer: bool, id: int) -> dict:
        if is_writer:
            return self._activate_writer(id)
        else:
            return self._activate_reader(id)

    def deactivate_node(self, is_writer: bool, id: int) -> dict:
        if is_writer:
            return self._deactivate_writer(id)
        else:
            return self._deactivate_reader(id)

    def _activate_writer(self, id: int) -> dict:
        """Adds writer to active set and creates an updated membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf and self.node_exists(id):
            if id in latest_conf["reader_list"]:
                latest_conf["reader_list"].remove(id)
            if id not in latest_conf["writer_list"]:
                latest_conf["writer_list"].append(id)
                return self.update_config(latest_conf)
            else:   # Node already in active set
                raise ValueError
        else:   # Node with id does not exist
            raise KeyError
            
    def _activate_reader(self, id: int) -> dict:
        """Adds reader to active set and creates an updated membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf and self.node_exists(id):
            if id in latest_conf["writer_list"]:
                latest_conf["writer_list"].remove(id)
            if id not in latest_conf["reader_list"]:
                latest_conf["reader_list"].append(id)
                return self.update_config(latest_conf)
            else:   # Node already in active set
                raise ValueError
        else:   # Node with id does not exist
            raise KeyError
                
    def _deactivate_writer(self, id: int) -> int:
        """Removes writer from active set and creates an updated membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf and self.node_exists(id):
            if id in latest_conf["writer_list"]:
                latest_conf["writer_list"].remove(id)
                self.update_config(latest_conf)
                return id
            else:   # Node not in active set
                raise ValueError
        else:   # Node with id does not exist
            raise KeyError
        
    def _deactivate_reader(self, id: int) -> int:
        """Removes reader from active set and creates an updated membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf and self.node_exists(id):
            if id in latest_conf["reader_list"]:
                latest_conf["reader_list"].remove(id)
                self.update_config(latest_conf)
                return id
            else:   # Node not in active set
                raise ValueError
        else:   # Node with id does not exist
            raise KeyError
    
    def remove_from_node_set(self, id: int) -> None:
        """Removes node from node set in config and updates membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf:
            for node in latest_conf["node_set"]:
                if node["id"] == id:
                    latest_conf["node_set"].remove(node)
                    self.update_config(latest_conf)
                    return id

    def add_to_node_set(self, node_details: dict) -> dict:
        """Adds node to node set in config and updates membership version"""
        latest_conf =  self.get_latest_config()
        # Check if node is already in node set
        if latest_conf:
            for node in latest_conf["node_set"]:
                if node["pub_key"] == node_details["pub_key"]:  # Perhaps the nodes should have the public key as the key in the config.
                    raise ValueError
            latest_conf["node_set"].append(node_details)
            return self.update_config(latest_conf)
    
    def update_node_details(self, id: int, node_details: dict) -> dict:
        """Updates node details and creates an updated membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf:
            for idx, x in enumerate(latest_conf["node_set"]):
                if x["id"] == id:
                    latest_conf["node_set"][idx] = node_details
                    return self.update_config(latest_conf)
    
    def update_config(self, new_conf: dict) -> dict:
        """Updates config with a new version number and returns the latest version"""
        latest_conf =  self.get_latest_config()
        if latest_conf:
            new_conf["_id"] = latest_conf["_id"] + 1
            new_conf["membership_version"] = new_conf["_id"]
            self.configs.insert_one(new_conf)
            return new_conf
        else:
            new_conf["_id"] = 1
            new_conf["membership_version"] = new_conf["_id"]
            self.configs.insert_one(new_conf)
            return new_conf
    
    def get_new_node_id(self):
        latest_conf =  self.get_latest_config()
        return len(latest_conf["node_set"])
            
TEST = False
if TEST:
    CONFIG_NAME = "configs/config-local-test.json"
    with open(f"{CONFIG_NAME}") as config_file:   # If in top directory for debug
        CONF = json.load(config_file)
    client = ConfigDB()
    client.update_config(CONF)
    print("FETCHING CONF Version 5", client.get_config_version(5))
    print(client.get_latest_config())
    # print(client.remove_from_node_set(1))
    client.deactivate_reader(0)
    print(client.activate_reader(3))
    client.deactivate_writer(0)
    client.deactivate_writer(1)
    print("ACTIVATE", client.activate_writer(1))
    print(client.deactivate_writer(1))
    print(client.deactivate_writer(2))
    print(client.deactivate_writer(2))
    client.activate_reader(1)
    client.activate_writer(1)
    client.activate_reader(1)
    print(client.get_latest_config())
    updated_node_1 = {
    "name": "dave",
    "id": 1,
    "hostname": "127.0.0.1",
    "protocol_port": 15003,
    "client_port": 5002,
    "pub_key": "6587849500818316161519508278916854824201302152793630979346725188602264462651268740217047928962253207403830618696453825975409521538077356628137373401104759"
    }
    print(client.update_node_details(updated_node_1["id"], updated_node_1))
    # Add a config to db

    # client = MongoClient()
    # client = MongoClient('localhost', 27017)
    # # A single instance of mongodb supports multiple independent databases.
    # db = client.test_database
    # # A collection is like a table in a relational database
    # collection = db.test_collection

    # import datetime
    # post = {"author": "Mike",
    #         "text": "My first blog post!",
    #         "tags": ["mongodb", "python", "pymongo"],
    #         "date": datetime.datetime.utcnow()}
    # posts = db.posts
    # post_id = posts.insert_one(post).inserted_id
    # print(db.list_collection_names())
    # print(posts.find_one())

