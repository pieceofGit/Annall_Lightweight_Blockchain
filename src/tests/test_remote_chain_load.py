from unittest import result
import requests, json, sys
with open("../configs/config-remote.json", "r") as f:
    conf = json.load(f)
post_block_path = f'http://{conf["client_api"]["hostname"]}:{conf["client_api"]["port"]}/blocks'

data_dict = {"total": 10000, "failed_post": 0, "failed_get": 0, "success_post": 0, "success_get": 0, "chain_info": [], "conf": conf}
print("CONF SIZE: ", sys.getsizeof(conf))
import time
for i in range(data_dict["total"]):
    try:
        start = time.time()
        resp = requests.post(post_block_path, json.dumps({"payload": conf}), timeout=2)
        
        end = time.time()
        request_time = end-start
        if resp.status_code != 201:
            data_dict["failed_post"]+= 1
        else:
            data_dict["success_post"] += 1
            try:
                resp = requests.get(post_block_path, timeout=2)
                if resp.status_code != 200:
                    data_dict["failed_get"] += 1    
                else:
                    data_dict["success_get"] += 1
                    data = resp.json()
                    data_dict["chain_info"].append((len(data), request_time, sys.getsizeof(data)))
            except Exception as e:
                print(e)
                data_dict["failed_get"] += 1
    except:
        data_dict["failed_post"] += 1
print(f"FAILED POST {data_dict['failed_post']/data_dict['total']*100}%")
print(f"SUCCESS POST {data_dict['success_post']/data_dict['total']*100}%")
print(f"FAILED GET {data_dict['failed_get']/data_dict['total']*100}%")
print(f"SUCCESS GET {data_dict['success_get']/data_dict['total']*100}%")
with open("results/test_chain_result.json", "r") as result_file:
    # Store percentages, totals, and chain info per request
    result_list = json.load(result_file)
    print(result_list)
result_list.append(data_dict)
with open("results/test_chain_result.json", "w") as result_file:
    json.dump(result_list, result_file, indent=4)

    