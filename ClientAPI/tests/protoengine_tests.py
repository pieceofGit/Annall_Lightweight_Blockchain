
global_list = []


def verify_chain(chain):
    correct_hash_chain = True
    for index in range(len(chain)):
        if index != 0:
            if chain[index][1] != chain[index - 1][7]:
                print("Incorrect part in chain 1/2" , chain[index][1])
                print("Incorrect part in chain 2/2" , chain[index - 1][7])
                correct_hash_chain = False

    same_writer_coord = not any(block[2] == block[3] for block in chain[1:])

    correctly_hashed = all(hash_block(block[1:]) == block[7] for block in chain[1:])

    return correct_hash_chain and same_writer_coord and correctly_hashed


def test_engine(id: int, rounds: int, no_writers: int):
    with open("./src/config-l2.json", "r") as f:
        data = json.load(f)


    # bce, blockchain writer to db
    CWD = os.getcwd()
    dbpath = f"/src/db/blockchain{id}.db"
    dbpath = CWD + dbpath
    print(f"[DIRECTORY PATH] {dbpath}")
    bce = BlockchainDB(dbpath)

    # p2p network
    pcomm = ProtoCom(id, data)
    pcomm.daemon = True
    pcomm.start()

    # client server thread
    if id == 1:
        TCP_IP = data["node_set"][id - 1]["hostname"]
        TCP_PORT = 15005
        print("::> Starting up ClientServer thread")
        clients = TCP_Server("the server", TCP_IP, TCP_PORT, ClientHandler, bce)
        cthread = Thread(target=clients.run, name="ClientServerThread")
        cthread.daemon = True
        cthread.start()
        print("ClientServer up and running as:", cthread.name)
    else:
        clients = ClientServer()

    keys = data["node_set"][id - 1]["priv_key"]

    # run the protocol engine, with all the stuff
    w = ProtoEngine(id, tuple(keys), pcomm, bce, clients,)
    w.set_rounds(rounds)
    w.set_conf(data)

    wlist = []
    for i in range(no_writers):
        if (i + 1) != id:
            wlist.append(i + 1)
    w.set_writers(wlist)
    w.run()
    time.sleep(id)
    global_list.append(w.bcdb.read_blocks(0, 10))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-w", default=5, type=int, help="number of writers")
    ap.add_argument(
        "-r", default=10, type=int, help="number of rounds, 0 = run forever"
    )
    a = ap.parse_args()
    print(sys.argv[0], a.w, a.r)
    no_writers = a.w
    rounds = a.r
    threads = []

    for i in range(no_writers):
        thread = Thread(target=test_engine, args=[i + 1, rounds, no_writers])
        threads.append(thread)

    for t in threads:
        t.start()

    for t in threads:
        t.join()
    # Here we verify if the chain is stil lintact
    correctness = all(verify_chain(chain) for chain in global_list)
    if correctness:
        print("THE CHAIN IS INTACT")
    else:
        print("The chain failed somewhere")
        for chain in global_list:
            print(chain)