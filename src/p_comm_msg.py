# Message classes for communication

VERBOSE = False


class pMsgTyp:
    c_request = "C-REQUEST"
    c_reply = "C-REPLY"
    c_ack = "C-ACK"
    echo_request = "ECHO-REQUEST"
    echo_reply = "ECHO-REPLY"
    data = "DATA"
    data_ack = "DATA-ACK"
    type_set = {c_request, c_reply, c_ack, echo_request, echo_reply, data, data_ack}

    @staticmethod
    def valid_type(t):
        if t in pMsgTyp.type_set:
            return True
        else:
            return False


class pMsg:
    sep = "#"

    @staticmethod
    def make_msg(mtype, self_id, rem_id, data=None):
        msg = f"{mtype}{pMsg.sep}{self_id}{pMsg.sep}{rem_id}{pMsg.sep}"
        if data is not None:
            msg = msg + data
        return msg

    @staticmethod
    def valid_msg(msg: str) -> bool:
        if pMsg.sep in msg:
            tokens = msg.split(pMsg.sep)
            if len(tokens) >= 3:
                if pMsgTyp.valid_type(tokens[0]):
                    return True
        return False

    @staticmethod
    def format_msg(msg: str) -> bytes:
        """ Format message to be sent over socket """
        # print(">>>", "Length: ", len(msg), "Message: ", msg)
        b = len(msg).to_bytes(4, "big", signed=False) + bytes(msg, "utf-8")
        # print(">>>", "Message in bytes: ", b)
        return b

    @staticmethod
    def con_requ_msg(self_id: int, rem_id: int, secret="Geheimnis") -> bytes:
        """ Connection request message
            @returns bytes """
        m = pMsg.make_msg(pMsgTyp.c_request, self_id, rem_id, str(secret))
        return pMsg.format_msg(m)

    @staticmethod
    def con_repl_msg(
        self_id: int, rem_id: int, peers: list = [], secret="Geheimnis"
    ) -> bytes:
        """ Connection reply message
            @returns bytes """
        data = str(secret)
        if len(peers) > 0:
            peers = list(map(str, peers))
            data += pMsg.sep + "peers: " + ", ".join(peers)
        m = pMsg.make_msg(pMsgTyp.c_reply, self_id, rem_id, data)
        return pMsg.format_msg(m)

    @staticmethod
    def con_ack_msg(self_id: int, rem_id: int, peers: list) -> bytes:
        """ Connection ack message
            @returns bytes """
        data = ""
        if len(peers) > 0:
            peers = list(map(str, peers))
            data += "connected peers: " + ", ".join(peers)
        m = pMsg.make_msg(pMsgTyp.c_ack, self_id, rem_id, data)
        return pMsg.format_msg(m)

    @staticmethod
    def data_msg(self_id: int, rem_id: int, data: str) -> bytes:
        """ Data ack message
            maybe send back length of message received or add some message counter
            @returns bytes """
        m = pMsg.make_msg(pMsgTyp.data, self_id, rem_id, data)
        return pMsg.format_msg(m)

    @staticmethod
    def data_ack_msg(self_id: int, rem_id: int) -> bytes:
        """ Data ack message
            maybe send back length of message received or add some message counter
            @returns bytes """
        m = pMsg.make_msg(pMsgTyp.data_ack, self_id, rem_id)
        return pMsg.format_msg(m)

    @staticmethod
    def echo_requ_msg(self_id: int, rem_id: int, data: str = None) -> bytes:
        """ ECHO request message
            maybe send back length of message received or add some message counter
            @returns bytes """
        m = pMsg.make_msg(pMsgTyp.echo_request, self_id, rem_id, data)
        return pMsg.format_msg(m)

    @staticmethod
    def echo_repl_msg(self_id: int, rem_id: int, data: str = None) -> bytes:
        """ ECHO reply message
            maybe send back length of message received or add some message counter
            @returns bytes """
        m = pMsg.make_msg(pMsgTyp.echo_reply, self_id, rem_id, data)
        return pMsg.format_msg(m)

    @staticmethod
    def verify_con_msg(
        tokens: list, self_id, rem_id: int = None, secret="Geheimnis"
    ) -> bool:
        """ Verify incoming verification message """
        if VERBOSE:
            print("Verifying message")
            print("lenght is:", len(tokens))
        if len(tokens) != 3:
            return False
        if VERBOSE:
            print("Remote id is:", tokens[0], "and should be:", rem_id)
            print("Self id is:", tokens[1], "and should be:", self_id)
            print("Secret is:", tokens[2], "and should be:", secret)
        if rem_id is not None and tokens[0] != str(rem_id):
            return False
        if tokens[1] != str(self_id):
            return False
        # if secret does not exist in config then it defaults
        if tokens[2] != str(secret):
            return False
        return True
