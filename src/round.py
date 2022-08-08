import requests

from interfaces import verbose_print

class Round:
    def __init__(self, api_path, is_writer_api, round=0):
        self.writer_api_path = api_path
        self.is_writer_api = is_writer_api
        # if not round and not is_writer_api:
        #     self.num = self.get_round()
        # else:
        self.num = round
        print(self.is_writer_api)
    # def set_round(self, round: int):
    #     isinstance(round, int)
    #     self.round = round

    def get_round(self):
        self.set_round()
        return self.num

    def set_round(self):
        """ Fetches the current round from the API"""
        if not self.is_writer_api:  
            try:
                self.num = requests.get(self.writer_api_path + "round").json()
            except Exception as e:
                verbose_print("Could not fetch latest round  ", e)
