import os
import json
import base64
import pickle
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

class pseudonimization:
    def __init__(self, deck):
        self.deck = deck
        self.ps_deck = []
        self.pi = dict()

    def pseudo_deck(self):
        for i in range(len(self.deck)):
            ki = os.urandom(32)
            digest = hashes.Hash(hashes.SHA256(), default_backend())
            digest.update(self.deck[i].encode('utf-8'))
            digest.update(ki)
            digest.update(bytes(i))
            
            res = digest.finalize()
            self.pi[res] = [ki, i]
            self.ps_deck.append((res, i))
        string = dict()
        string.update({'msg':self.ps_deck})
        return pickle.dumps(string)

    def check(self, msg):
        c_deck = pickle.loads(msg)['msg']
        r_deck = []
        for i in c_deck:
            r_deck.append(base64.b64decode(i).decode('utf-8'))
        tmp = []
        for i in self.ps_deck:
            tmp.append(str(i))
        c_deck = r_deck
        for i in tmp:
            if i in r_deck:
                r_deck.remove(i)
            else:
                return False
        return r_deck == []