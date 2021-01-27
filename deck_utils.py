import random
import os
import json
import pickle
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class Player:
    def __init__(self, name,socket,pieces_per_player=None):
        self.name = name
        self.socket = socket
        self.hand = []
        self.num_pieces = 0
        self.n_pieces = 0 #added
        self.score = 0
        self.host=False
        self.pieces_per_player=pieces_per_player
        self.ready_to_play = False
        self.in_table = []
        self.nopiece = False
        #-------added-------------
        self.hand2 = []
        self.deck = []
        self.ciphered_deck = []
        self.deciphered_deck = []
        self.key_map = dict()


    def __str__(self):
        return str(self.toJson())

    def toJson(self):
        return {"name": self.name, "hand": self.hand, "score": self.score}

    def isHost(self):
        return self.host

    def pickPiece(self):
        if not self.ready_to_play and self.num_pieces==self.pieces_per_player:
            self.ready_to_play = True
        random.shuffle(self.deck)
        piece = self.deck.pop()
        self.insertInHand(piece)
        return {"action": "get_piece", "deck": self.deck}

    def updatePieces(self,i):
        self.num_pieces+=i

    def canPick(self):
        return self.num_pieces<self.pieces_per_player

    def insertInHand(self,piece):
        self.num_pieces += 1
        self.hand.append(piece)
        self.hand.sort(key=lambda p : int(p.values[0].value)+int(p.values[1].value))

    def checkifWin(self):
        print("Winner ",self.num_pieces == 0)
        return self.num_pieces == 0

    def play(self):
        res = {}
        self.score += 1
        if self.in_table == []:
            print("Empty table")
            piece = self.hand.pop()
            self.updatePieces(-1)
            res = {"action": "play_piece","piece":piece,"edge":0,"win":False, "score": self.score}
        else:
            edges = self.in_table[0].values[0].value, self.in_table[len(self.in_table) - 1].values[1].value
            print(str(edges[0])+" "+str(edges[1]))
            max = 0
            index = 0
            edge = None
            flip = False
            #get if possible the best piece to play and the correspondent assigned edge
            for i, piece in enumerate(self.hand):
                aux = int(piece.values[0].value) + int(piece.values[1].value)
                if aux > max:
                    if int(piece.values[0].value) == int(edges[0]):
                            max = aux
                            index = i
                            flip = True
                            edge = 0
                    elif int(piece.values[1].value) == int(edges[0]):
                            max = aux
                            index = i
                            flip = False
                            edge = 0
                    elif int(piece.values[0].value) == int(edges[1]):
                            max = aux
                            index = i
                            flip = False
                            edge = 1
                    elif int(piece.values[1].value) == int(edges[1]):
                            max = aux
                            index = i
                            flip = True
                            edge = 1
            #if there is a piece to play, remove the piece from the hand and check if the orientation is the correct
            if edge is not None:
                piece = self.hand.pop(index)
                if flip:
                    piece.flip()
                self.updatePieces(-1)
                res = {"action": "play_piece", "piece": piece,"edge":edge,"win":self.checkifWin(), "score": self.score}
            # if there is no piece to play try to pick a piece, if there is no piece to pick pass
            else:
                if len(self.deck)>0:
                    res = self.pickPiece()
                else:
                    res = {"action": "pass_play", "piece": None, "edge": edge,"win":self.checkifWin(), "score": self.score}
            # print("To play -> "+str(piece))
        print("Self score: " + str(self.score))
        return res

    #--------------------added----------------------------------------

    def generate_symmetric_key(self):
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(hashes.SHA512(), 32, salt, 100000, default_backend())
        key = kdf.derive(os.urandom(16))
        return key

    def cipher_tiles(self, tiles):
        for tile in tiles:
            check = True
            while check:
                key = self.generate_symmetric_key()
                IV = os.urandom(algorithms.AES.block_size // 8)
                cipher = Cipher(algorithms.AES(key), modes.CBC(IV), default_backend())
                padder = padding.PKCS7(algorithms.AES.block_size).padder()
                encryptor = cipher.encryptor()
                c_text = b''
                if self.host:
                    t = str(tile)
                else:
                    t = base64.b64decode(tile)
                i = 0
                while i<len(t):
                    if self.host:
                        aux = encryptor.update(padder.update(t[i:i+(algorithms.AES.block_size // 8)].encode('utf-8')))
                    else:
                        aux = encryptor.update(padder.update(t[i:i+(algorithms.AES.block_size // 8)]))
                    c_text += aux
                    i += algorithms.AES.block_size // 8
                c_text += encryptor.update(padder.finalize())
                ciphertext = base64.b64encode(IV + c_text)
                check = ciphertext in self.key_map
            self.key_map[ciphertext] = key
            self.ciphered_deck.append(ciphertext)
        random.shuffle(self.ciphered_deck)

    def decipher_tiles(self, tiles):
        for ciphertext in tiles:
            c = base64.b64decode(ciphertext)
            key = self.key_map[ciphertext]
            IV, c_text = c[:16], c[16:]
            cipher = Cipher(algorithms.AES(key), modes.CBC(IV), default_backend())
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            decryptor = cipher.decryptor()
            plaintext = b''
            i = 16
            plaintext = unpadder.update(decryptor.update(c_text)) + unpadder.finalize()
            self.deciphered_deck.append(base64.b64encode(plaintext))

    def pick_tile(self, tiles):
        if len(self.hand2) < self.pieces_per_player:
            if random.choice([i for i in range(100)]) > 99:
                if random.choice([i for i in range(100)]) >= 50:
                    ids = [id for id in range(len(tiles))]
                    choice = tiles.pop(random.choice(ids))
                    ids = [id for id in range(len(self.hand2))]
                    tiles.append(self.hand2.pop(random.choice(ids)))
                    self.hand2.append(choice)
                return tiles
            ids = [id for id in range(len(tiles))]
            choice = tiles.pop(random.choice(ids))
            self.hand2.append(choice)
        return tiles

class Piece:
    values = []

    def __init__(self, first, second):
        self.values = [SubPiece(first), SubPiece(second)]

    def __str__(self):
        return "{}:{}".format(str(self.values[0].value),str(self.values[1].value))

    def flip(self):
        self.values = [self.values[1], self.values[0]]

class SubPiece:
    value = None
    def __init__(self,value):
        self.value = value

    def __str__(self):
        return "\033[1;9{}m{}\033[0m".format(int(self.value)+1, self.value)

class Deck:

    deck = []
    deck2 = []
    ps_deck = []
    pseudonym_map = dict()

    def __init__(self,pieces_per_player=5):
        with open('pieces', 'r') as file:
            pieces = file.read()
        for piece in pieces.split(","):
            piece = piece.replace(" ", "").split("-")
            p = Piece(piece[0], piece[1]) #added
            self.deck2.append(p.__str__()) #added
            self.deck.append(p) #altered

        self.pseudo_deck() #added
        self.npieces = len(self.deck)
        self.pieces_per_player = pieces_per_player
        self.in_table = []
    #--------------------------------added-------------------------------
    def pseudo_deck(self):
        for i in range(len(self.deck2)):
            ki = os.urandom(32)
            digest = hashes.Hash(hashes.SHA256(), default_backend())
            digest.update(self.deck2[i].encode('utf-8'))
            digest.update(ki)
            digest.update(bytes(i))
            res = digest.finalize()
            self.pseudonym_map.update({res: [ki, i]})
            self.ps_deck.append((res, i))

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
    #--------------------------------------------------------------------

    def __str__(self):
        a = ""
        for piece in self.deck:
            a+=str(piece)
        return a

    def toJson(self):
        return {"npieces": self.npieces, "pieces_per_player": self.pieces_per_player, "in_table": self.in_table,"deck":self.deck}

