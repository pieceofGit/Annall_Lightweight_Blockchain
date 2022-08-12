import json
import requests
from interfaces import verbose_print

class MembershipData:
    def __init__(self, id, conf_path, conf_file, api_path, bcdb, is_writer):
        self.id = id
        self.api_path = api_path
        self.full_conf_path = f"{conf_path}/{conf_file}"
        self.is_writer = is_writer
        self.writer_list = None    
        self.writer_list = None
        self.waiting_list = None
        self.bcdb = bcdb
        if id == 3:
            self.is_api = True
        else:
            self.is_api = False

        if self.is_api:
            with open(self.full_conf_path, "r") as f:
                self.conf = json.load(f)
                f.close()
        else:
            self.conf = self.get_remote_conf()     
   

    def set_lists(self):
        """ Updates the active sets """
        self.writer_list = self.conf["writer_list"]
        self.reader_list = self.conf["reader_list"]
        self.waiting_list = self.conf["waiting_list"]
            
    def get_remote_conf(self):
        """ Get conf if in an active set, else posts to be reader or writer """
        try:
            response = requests.get(self.api_path + "config", {})
            verbose_print("[CONFIG node API] Got config from node API")
            self.conf = response.json()
            self.set_lists()
            # If the node is not in any list, it posts to be reader or writer
            print(self.node_in_active_set(self.id))
            if not self.node_in_active_set(self.id):
                self.activate_node()
            return self.conf
        except Exception as e:
            verbose_print("[CONFIG LOCAL] Failed to get config from writer", e)
            with open(self.full_conf_path, "r") as f:
                return json.load(f)

    def set_conf(self):
        """ Sets changes to lists in conf """
        self.conf["writer_list"] = self.writer_list
        self.conf["reader_list"] = self.reader_list
        self.conf["waiting_list"] = self.waiting_list
        
    def _update_conf(self):
        if self.is_api:
            # Updates the configuration file
            # Might need a lock
            # set lists again
            self.set_conf()
            try:
                with open(self.full_conf_path, "w") as file:
                    json.dump(self.conf, file, indent=4)
            except Exception as e:
                print("failed to write to config file ", e)

    def activate_node(self):
        """ Adds node to waiting list """
        self.bcdb.get_missing_blocks()
        # TODO: The node should still be asking for the newest blockchain until it has connected to all active nodes
        # Add node to waiting list if up to date
        try:
            resp = requests.post(self.api_path + "activate_node", 
                data = json.dumps({"block": self.bcdb.get_latest_block(), "node": {"id": self.id, "is_writer": self.is_writer}}))
            if resp.status_code == 200: # has up to date config file
                pass
            elif resp.status_code == 201:
                self.conf = resp.json()  # Gets back new json
                self.set_lists()
                print('self.conf: ', self.conf)
            else:
                # Out of date blockchain, incorrect data, or service unavailable
                # Need to fetch blockchain again if failed and ask to be active writer.
                # Possibly the writer should be added to active list if fetching blockchain
                pass
        except:
            verbose_print("Could not post to node API to activate us as writer")

    def pop_from_waiting_list(self):
        try:
            id, is_writer = self.waiting_list.pop()
            if is_writer:
                self.writer_list.append(id)
            else:
                self.reader_list.append(id)
            if self.is_api:
                self._update_conf()
        except Exception as e:
            verbose_print("Failed to pop from waiting list ", e)

    def get_tuple_of_lists(self):
        return (self.writer_list, self.reader_list, self.waiting_list)

    def get_tcp_ip(self, id):
        return self.conf["node_set"][id -1]["hostname"]
    
    def get_tcp_port(self, id):
        return self.conf["node_set"][id -1]["client_port"]

    def waiting_list_not_equal(self, configs):
        """ Compare coordinator config to conf of all other nodes """
        # For simplicity, everone fetches a new config if someone's is not up to date
        if self.waiting_list == []:
            return False    # Nothing to add
        for conf in configs:
            try:    #Compares first item in waiting list
                print(conf[1][2][0], self.waiting_list[0])
                if conf[1][2][0] != self.waiting_list[0]:
                    return True    # First 
            except: # conf is empty but not waiting lists
                return True
        return False

    def add_to_config_by_key(self, key, value):
        try:
            self.conf[key].append(value)
            with open(self.full_conf_path, "w") as file:
                json.dump(self.conf, file, indent=4)
                file.close()
        except Exception as e:
            verbose_print("Failed to append to config by key ", e)
        
    def node_in_active_set(self, id):
        if (id in self.writer_list or
                id in self.reader_list or
                    any(id in row for row in self.waiting_list)):
            return True
        return False