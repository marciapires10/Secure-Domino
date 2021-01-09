import os
import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from byte_encoder import *

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
            self.ps_deck.append([res, i])
        return self.ps_deck

    def check_deck(self, recieved_deck):
        tmp = []
        for elem in self.ps_deck:
            tmp.append(elem[0])
        t = recieved_deck   # make a mutable copy
        for i in range(len(recieved_deck)):
            if recieved_deck[i].decode('raw_unicode_escape') != str(self.ps_deck[i]):
                return False
        return True

    def check(self, msg):
        c_deck = json.loads(msg)['msg']
        r_deck = []
        for i in c_deck:
            r_deck.append(base64.b64decode(i.encode('utf-8')).decode('utf-8'))
        tmp = []
        for i in self.ps_deck:
            tmp.append(str(i))
        c_deck = r_deck
        for i in tmp:
            if i in r_deck:
                r_deck.remove(i)
            else:
                return False
        return r_deck==[]