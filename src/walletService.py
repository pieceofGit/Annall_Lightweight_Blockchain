import socket
import os
import sqlite3

from interfaces import (
    ProtocolCommunication,
    BlockChainEngine,
    ClientServer,
    ProtocolEngine,
)

PORT = 15005
HOST = "127.0.0.1"

NoneType = type(None)


"""class WalletNode:
    def __init__(self):
        self.address = "add"
        self.sock = None
        self.connect_to_server()

    def connect_to_server(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))

    def send_msg(self, message):
        self.sock.sendall(message)
        self.sock.close()
"""


"""TODO
    make it threaded so many txs can be performed
    add signature to transactions
"""


class WalletService:
    def __init__(self):
        dbpath = f"/src/db/blockchain5.db"
        self.mostRecentBlock = 0
        self.connection = sqlite3.connect(os.getcwd() + dbpath, check_same_thread=False)
        self.balances = {}
        self.init_balances()

    def read_blocks(self, begin=0, end=None, col="*"):
        """ Retrieve blocks with from and including start to end
            If end is None, retrieve only the one block
            Returns a list of blocks retrieved

            What if none satisfies?
            What type of exceptions
        """
        assert isinstance(begin, int)
        assert isinstance(end, (int, NoneType))
        if end is None:
            query = f"SELECT {col} FROM chain WHERE payload LIKE '%walletserv%' AND round >= {begin} ORDER BY round"
        else:
            query = f"SELECT {col} FROM chain WHERE payload LIKE '%walletserv%' AND round >= {begin} AND round <= {end} ORDER BY round"
        try:
            cursor = self.connection.cursor()
            retrived = cursor.execute(query)
        except Exception as e:
            print("Error retriving blocks from db")
            print(e)

        allBlocks = retrived.fetchall()
        self.mostRecentBlock = allBlocks[-1][0]
        return allBlocks

    def init_balances(self):
        txs = self.read_blocks()
        self.balances["none"] = 10000000
        for tx in txs:
            tx = tx[4].split(",")
            if tx[1] not in self.balances:
                self.balances[tx[1]] = 0

            if tx[2] not in self.balances:
                self.balances[tx[2]] = 0

            if tx[4] == "commit":
                self.balances[tx[1]] -= int(tx[3])
                self.balances[tx[2]] += int(tx[3])

    def makeTXS(self, fromm, too, amount):
        print(self.mostRecentBlock)

        """ Do init phase
            self.sendTXS(fromm, too, amount, init)
            while(no response):
                time.sleep(0.001)
            newBlocks = self.readblocks(start=self.mostRecentBlock)
            if not any(tx[1] == fromm for tx in newBlocks):
                self.sendTXS(fromm, too, amount, commit)
                self.updateBalances
                return 1
            else:
                return -1
        """
        if self.balances[fromm] < amount:
            return -1
        self.balances[fromm] -= amount
        self.balances[too] += amount
        return 1

    def getBalance(self, address):
        return self.balances[address]


class WalletApp:
    def __init__(self, address):
        self.serverConnection = WalletService()
        self.address = address
        self.balance = self.serverConnection.getBalance(self.address)

    def txs(self, receptor, amount):
        resp = self.serverConnection.makeTXS(self.address, receptor, amount)
        if resp < 0:
            print("Error, amount higher than balance")
        else:
            print("Success")

    def updateBalance(self):
        self.balance = self.serverConnection.getBalance(self.address)


if __name__ == "__main__":
    w = WalletApp("WALLET1")
    print(w.balance)
    w.txs("WALLET2", 20)
    print(w.balance)
    w.updateBalance()
    print(w.balance)
