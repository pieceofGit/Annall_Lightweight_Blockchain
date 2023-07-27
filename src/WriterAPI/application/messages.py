from queue import Queue

from interfaces import vverbose_print, verbose_print
from . import pMsg

# Stores and fetches all messages for the protocol engine
class Messages:
    def __init__(self, protocol_engine, protocom) -> None:
        self.protocom = protocom
        self.pcomm = protocol_engine
        self.protocol_msg_queue= Queue()
        self.cancel_msg_queue = Queue()
        # View change should be a list of messages
        self.view_msg_queue = Queue()
    
def send_msg_to_remote_end(self, rem_id, message, send_to_readers): 
    # Send message to single remote end
    if not send_to_readers and not self.peers[rem_id].is_writer:    
        return  # Message is not for reader
    data = pMsg.data_msg(self.id, rem_id, message)
    vverbose_print(">", "Sending: ", data, " to id: ", rem_id)
    vverbose_print(">", "Connection:", self.peers[rem_id])
    self.pcomm.peers[rem_id].send_bytes(data)

def send_msg(self, message: str, send_to: int = None, send_to_readers: bool = None) -> list:
    """ Send message\n
        Does nothing if specified send_to id is not connected\n
        If send_to is None the message is broadcast to all connected writers\n
        @returns list of ids to which the message was succesfully sent

        Send procedure
        1. Send a single message with type Data
        2. Wait for data acknowledge
        3. confirm successful send
        """
    if send_to is None: # Broadcast message
            
        id_list = []
        for rem_id in self.pcomm.peers:
            if self.pcomm.peers[rem_id].is_active:
                try:
                    self.send_msg_to_remote_end(rem_id, message, send_to_readers)
                    id_list.append(rem_id)
                except Exception as e:
                    verbose_print(">!!", "Failed to send to id: ", rem_id, "With exception: ", type(e), e)
                    continue
            vverbose_print("Sent message to", id_list, "with message:", message, "is_active: ", self.peers[rem_id].is_active)
        return id_list
    else:
        if self.pcomm.peers[send_to].is_active:
            try:
                data = pMsg.data_msg(self.id, send_to, message)
                self.pcomm.peers[send_to].send_bytes(data)
                return [send_to]
            except Exception as e:
                verbose_print(">!!", "Failed to send to id: ", send_to)
        return [] # TODO: should this not be [sent_to]
 
def recv_msg(self, recv_from: int = None) -> list:
    """ returns a list of tuples of ([id]: int, [msg]: string) """
    # return all messages
    if recv_from is None:
        with self.pcomm.msg_lock:
            tmpl = self.pcomm.msg_queue.copy()
            self.pcomm.msg_queue.clear()
        return tmpl
    else:
        # search through msg_queue and return what fits with recv_from
        with self.pcomm.msg_lock:
            rl = [(i, m) for i, m in self.msg_queue if i == recv_from]
            for m in rl:
                self.msg_queue.remove(m)
        return rl

    