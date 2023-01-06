"""A local MongoDB database connection for the configuration files of a permissioned blockchain"""
# Idea for future work: Handle all blockchains in this single API. 

import json
from enum import unique
from hashlib import new
from pymongo import MongoClient
import pymongo
class ConfigDB:
    def __init__(self) -> None:
        self.client = MongoClient('localhost', 27017)
        self.db = self.client.blockchain_db
        self.configs = self.db.configs
        self.configs.create_index([('membership_version', pymongo.ASCENDING)], unique=True)
        
    def get_latest_config(self):
        """Returns latest config version"""
        conf = self.configs.find().sort([('membership_version', -1)]).limit(1)
        try:
            return conf[0]
        except:
            return
        
    def get_config_version(self, index):
        """Returns a config version by key and db"""
        try:
            self.configs.find_one({"membership_version": index})
        except:
            return
    
    def activate_writer(self, id):
        """Adds writer to active set and creates an updated membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf:
            if id in latest_conf["reader_list"]:
                latest_conf["reader_list"].remove(id)
            if id not in latest_conf["writer_list"]:
                latest_conf["writer_list"].append(id)
                return self.update_config(latest_conf)
            
    def activate_reader(self, id):
        """Adds reader to active set and creates an updated membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf:
            if id in latest_conf["writer_list"]:
                latest_conf["writer_list"].remove(id)
            if id not in latest_conf["reader_list"]:
                latest_conf["reader_list"].append(id)
                return self.update_config(latest_conf)
        
    def deactivate_writer(self, id):
        """Removes writer from active set and creates an updated membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf:
            if id in latest_conf["writer_list"]:
                latest_conf.remove(id)
                self.update_config(latest_conf)
        
    def deactivate_reader(self, id):
        """Removes reader from active set and creates an updated membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf:
            if id in latest_conf["reader_list"]:
                latest_conf.remove(id)
    
    def remove_from_node_set(self, id):
        """Removes node from node set in config and updates membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf:
            for node in latest_conf["node_set"]:
                if node["id"] == id:
                    latest_conf["node_set"].remove(node)
                    return self.update_config(latest_conf)

    def add_to_node_set(self, node_details):
        """Adds node to node set in config and updates membership version"""
        latest_conf =  self.get_latest_config()
        # Check if node is already in node set
        if latest_conf:
            for node in latest_conf["node_set"]:
                if node["public_key"] == node_details["public_key"]:
                    return
            latest_conf["node_set"].append(node_details)
            return self.update_config(latest_conf)
    
    def update_node_details(self, id, node_details):
        """Updates node details and creates an updated membership version"""
        latest_conf =  self.get_latest_config()
        if latest_conf:
            for idx, x in enumerate(latest_conf["node_set"]):
                if idx["id"] == id:
                    latest_conf["node_set"][x] = node_details
                    return self.update_config(latest_conf)
    
    def update_config(self, new_conf):
        """Updates config with a new version number and returns the latest version"""
        latest_conf =  self.get_latest_config()
        if latest_conf:
            new_conf["membership_version"] = latest_conf["membership_version"] + 1
            self.configs.insert_one(new_conf)
            return new_conf

CONFIG_NAME = "src/WriterAPI/application/configs/config-local-test.json"
with open(f"{CONFIG_NAME}") as config_file:   # If in top directory for debug
    CONF = json.load(config_file)
client = ConfigDB()
client.create_conf(CONF)
print(client.get_config_version(1))
print(client.get_latest_config())

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

