import os
import json
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
            digest.update(self.deck[i].encode())
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
            # print(recieved_deck[i].decode('raw_unicode_escape'))
            # print(self.ps_deck[i])
            if recieved_deck[i].decode('raw_unicode_escape') != str(self.ps_deck[i]):
                return False
        return True

    def check(self, r_json):
        r_deck = json.loads(r_json)
        tmp = []
        for i in self.ps_deck:
            tmp.append(str(i))
        for i in r_deck:
            if i in tmp:
                r_deck.remove(i)
            else:
                return False
        return True