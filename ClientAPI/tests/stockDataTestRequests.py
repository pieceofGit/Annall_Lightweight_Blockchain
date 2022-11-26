# Polygon.io API key
# PK = 3oKQphVvYKHKNwfddN23RZCTBboFpk73
import requests
from polygon import RESTClient
import time
from typing import cast
from urllib3 import HTTPResponse
import json
from dates import get_yesterday, get_date_by_delta

def post_stock_data(stock_dict):
    ''' This function sends stock data to Annall in order to test the blockchain'''
    block = json.dumps({"request_type": "block", "payload": stock_dict['payload']})
    resp_obj = requests.post('http://185.3.94.49:80/blocks', block)
    if resp_obj.status_code == 201:
        print("Transaction added to the blockcahin")
    else:
        print("Not added to  blockchain")
        print("Code ", resp_obj.status_code)

def get_stock_data():
    ''' This function generates stock data for annall'''
    client = RESTClient('3oKQphVvYKHKNwfddN23RZCTBboFpk73')
    while True:
        for ticker in client.list_tickers(active = True, limit = 1000):
            from datetime import date
            today = date.today()
            from_date = get_date_by_delta(time_delta=2)
            to_date = get_date_by_delta(time_delta=1)
            count = 0
            guard = False
            while True:     
                if count >= 1:
                    break
                count +=1
                try:
                    print("Tryign ticker ", ticker.ticker)
                    print("From date ", from_date)
                    print("To date ", to_date)
                    stock = client.get_aggs(ticker.ticker, 1, "day", from_date, to_date)
                    
                    guard = True
                    break
                except:
                    print("Couldn't get stock agg")
                    time.sleep(2)
            
            if guard:
                stock = stock[0]
                stock_dict = {
                "ticker" : ticker.ticker,
                "name" : ticker.name,
                "currency" : ticker.currency_name,
                "primary_exchange" : ticker.primary_exchange,
                "open": stock.open,
                "high" : stock.high,
                "low" : stock.low,
                "close": stock.close,
                "volume" : stock.volume,
                "vwap" : stock.vwap,
                "timestamp" : stock.timestamp,
                "transactions" : stock.transactions,
                "date_from" : from_date,
                "to_date" : to_date, 
            }
                print("The stock to add ", stock_dict)
                # post_stock_data(stock_dict = stock_dict)
                time.sleep(15)
get_stock_data()