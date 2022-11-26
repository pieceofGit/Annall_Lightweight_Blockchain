
def get_message_type_dict(pub_key_exp, message, signature,message_type='document'):
    ''' Returns the correct dictionary for the message type specified'''
    if message_type == 'document':
        dict_ret = {
                    "payload": {
                    "headers" : {
                        "type" : "document",
                        "pubKey" : pub_key_exp,
                        "message": message,
                        "signature" : signature
                    }, 
                    "payload": {
                        "userId" : 13,
                        "documentId" : 8
                        }
                    }
            }
        return dict_ret