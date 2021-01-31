import random
import os
import json
import pickle
import base64
from cryptography.hazmat.primitives import hashes, serialization, padding, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding as as_padd


class Player:
    def __init__(self, name,socket,pieces_per_player=None):
        self.name = name
        self.socket = socket
        self.hand = []
        self.all_hand = []
        self.start_hand = []
        self.num_pieces = 0
        self.score = 0
        self.host=False
        self.pieces_per_player=pieces_per_player
        self.ready_to_play = False
        self.in_table = []
        self.nopiece = False
        self.deck = []
        #-------added-------------
        self.n_pieces = 0
        self.hand2 = []
        self.d_hand = []
        self.ciphered_deck = []
        self.deciphered_deck = []
        self.key_map = dict()
        self.bitcommit = None
        self.r1 = None
        self.r2 = None
        self.indexes = []
        self.index_map = dict()
        self.tmp_piece = None

    def __str__(self):
        return str(self.toJson())

    def toJson(self):
        return {"name": self.name, "hand": self.hand, "score": self.score}

    def isHost(self):
        return self.host

    def pickPiece(self):
        if not self.ready_to_play and self.num_pieces==self.pieces_per_player:
            self.ready_to_play = True
        self.tmp_piece = self.deck.pop()
        #self.insertInHand(piece)
        return {"action": "get_piece", "deck": self.deck, "piece": self.tmp_piece}

    def updatePieces(self,i):
        self.num_pieces+=i

    def canPick(self):
        return self.num_pieces<self.pieces_per_player

    def insertInHand(self,piece):
        print("picked piece: " + str(piece))
        self.num_pieces += 1
        self.hand.append(piece)
        self.all_hand.append(piece)
        #self.hand.sort(key=lambda p : int(p.values[0].value)+int(p.values[1].value))
        return

    def checkifWin(self):
        print("Winner ",self.num_pieces == 0)
        return self.num_pieces == 0

    def play(self, is_cheating):
        res = {}
        self.score += 1
        if self.in_table == []:
            print("Empty table")
            piece = self.hand.pop()
            self.updatePieces(-1)
            res = {"action": "play_piece","piece":piece,"edge":0,"win":False, "score": self.score}
        else:
            edges = self.in_table[0].split(":")[0], self.in_table[len(self.in_table) - 1].split(":")[1]
            #edges = self.in_table[0].values[0].value, self.in_table[len(self.in_table) - 1].values[1].value
            max = 0
            index = 0
            edge = None
            flip = False
            #get if possible the best piece to play and the correspondent assigned edge
            for i, piece in enumerate(self.hand):
                aux = int(piece.split(":")[0]) + int(piece.split(":")[1])
                if aux > max:
                    if int(piece.split(":")[0]) == int(edges[0]):
                            max = aux
                            index = i
                            flip = True
                            edge = 0
                    elif int(piece.split(":")[1]) == int(edges[0]):
                            max = aux
                            index = i
                            flip = False
                            edge = 0
                    elif int(piece.split(":")[0]) == int(edges[1]):
                            max = aux
                            index = i
                            flip = False
                            edge = 1
                    elif int(piece.split(":")[1]) == int(edges[1]):
                            max = aux
                            index = i
                            flip = True
                            edge = 1
            #if there is a piece to play, remove the piece from the hand and check if the orientation is the correct
            if edge is not None:
                if not is_cheating:
                    piece = self.hand.pop(index)
                else:
                    # Try Cheat
                    piece = self.cheat()
                if flip:
                    piece = piece.split(":")[1]+":"+piece.split(":")[0]
                    #piece.flip()
                self.updatePieces(-1)
                res = {"action": "play_piece", "piece": piece,"edge":edge,"win":self.checkifWin(), "score": self.score}
            # if there is no piece to play try to pick a piece, if there is no piece to pick pass
            else:
                if len(self.deck)>0:
                    res = self.pickPiece()
                else:
                    res = {"action": "pass_play", "piece": None, "edge": edge,"win":self.checkifWin(), "score": self.score}
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

    # def decipher_tiles_first(self, tiles):
    #     k_map = dict()
    #     for ciphertext in tiles:
    #         c = base64.b64decode(ciphertext)
    #         key = self.key_map[ciphertext]
    #         IV, c_text = c[:16], c[16:]
    #         cipher = Cipher(algorithms.AES(key), modes.CBC(IV), default_backend())
    #         unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    #         decryptor = cipher.decryptor()
    #         plaintext = b''
    #         plaintext = unpadder.update(decryptor.update(c_text)) + unpadder.finalize()
    #         k_map[ciphertext] = key
    #     return k_map

    def decipher_tiles(self, tiles, k_map_arr):
        t = tiles
        aux = []
        for k_map in k_map_arr:
            for ciphertext in t:
                if ciphertext in k_map:
                    plaintext = self.decipher(ciphertext, k_map)
                    aux.append(base64.b64encode(plaintext))
            if aux != []:
                t = aux
                aux = []
        k_map = dict()
        for ciphertext in t:
            if ciphertext in self.key_map:
                plaintext = self.decipher(ciphertext, self.key_map)
                k_map[ciphertext] = self.key_map[ciphertext]
        return k_map

    def decipher_all(self, tiles, k_map_arr):
        t = tiles
        aux = []
        last = len(k_map_arr)
        count = 0
        for k_map in k_map_arr:
            count += 1
            for ciphertext in t:
                if ciphertext in k_map:
                    plaintext = self.decipher(ciphertext, k_map)
                    if count == last:
                        aux.append(plaintext)
                    else:
                        aux.append(base64.b64encode(plaintext))
            if aux != []:
                t = aux
                aux = []
        for i in t:
            self.indexes.append(tuple(map(str, i.decode("utf-8")[1:-1].split(', ')))[-1])

    def decipher(self, ciphertext, k_map):
        c = base64.b64decode(ciphertext)
        key = k_map[ciphertext]
        IV, c_text = c[:16], c[16:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(IV), default_backend())
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        decryptor = cipher.decryptor()
        plaintext = b''
        plaintext = unpadder.update(decryptor.update(c_text)) + unpadder.finalize()
        return plaintext

    def pick_tile(self, tiles):
        if random.choice([i for i in range(100)]) > 99 or len(self.hand2) == self.pieces_per_player:
            if random.choice([i for i in range(100)]) >= 50:
                ids = [id for id in range(len(tiles))]
                choice = tiles.pop(random.choice(ids))
                ids = [id for id in range(len(self.hand2))]
                tiles.append(self.hand2.pop(random.choice(ids)))
                self.hand2.append(choice)
            return tiles
        else:
            ids = [id for id in range(len(tiles))]
            choice = tiles.pop(random.choice(ids))
            self.hand2.append(choice)
        return tiles

    def bitcommitment(self):
        self.r1 = os.urandom(128)
        self.r2 = os.urandom(128)
        digest = hashes.Hash(hashes.SHA256(), default_backend())
        digest.update(str(self.hand2).encode('utf-8'))
        digest.update(self.r1)
        digest.update(self.r2)
        self.bitcommit = digest.finalize()

    def fill_array(self, array):
        arr = array
        if random.choice([i for i in range(100)]) < 99 and self.indexes != []:
            ids = [id for id in range(len(self.indexes))]
            choice = self.indexes.pop(random.choice(ids))
            for i in range(len(arr)):
                if arr[i][0] == str(choice):
                    priv, pub = self.genrate_rsa_key_pair()
                    arr[i][1] = pub
                    self.index_map[choice] = priv
        return arr

    def genrate_rsa_key_pair(self):
        priv_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        pub_key = priv_key.public_key()
        return (priv_key, self.rsa_serialize_key(pub_key))
    
    def rsa_serialize_key(self, public_key):
        pub_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pub_pem

    def reveal_tiles(self, array):
        for i in range(len(array)):
            if array[i][0] in self.index_map.keys():
                tile = self.rsa_decrypt(array[i][1], self.index_map[array[i][0]])
                self.hand.append(tile.decode('utf-8'))
                self.all_hand.append(tile.decode('utf-8'))               
        print(self.hand)
    
    def rsa_decrypt(self, ciphertext, privkey):
        plaintext = privkey.decrypt(ciphertext, as_padd.OAEP(
                mgf=as_padd.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext

    def cheat(self):
        pieces_slots = []
        with open('pieces', 'r') as file:
            file.seek(0)
            pieces = file.read()
        for piece in pieces.split(","):
            piece = piece.replace(" ", "").split("-")
            pieces_slots.append(Piece(piece[0], piece[1]))
        pieces_to_play =  [p for p in pieces_slots if p not in self.all_hand and Piece(str(p).split(":")[1],str(p).split(":")[0]) not in self.all_hand]
        random.shuffle(pieces_to_play)
        self.hand.pop()
        piece = str(pieces_to_play.pop())

        return piece

    def get_otherside_piece(self, p):
        piece = p.split(":")[1] + ":" + p.split(":")[0]

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
    idx = []

    def __init__(self,pieces_per_player=5):
        with open('pieces', 'r') as file:
            pieces = file.read()
        for piece in pieces.rstrip().split(","):
            piece = piece.replace(" ", "").split("-")
            p = Piece(piece[0], piece[1]) #added
            self.deck2.append(p.__str__()) #added
            self.deck.append(p) #altered
        # random.shuffle(self.deck2) #added
        self.pseudo_deck() #added
        self.npieces = len(self.deck)
        self.pieces_per_player = pieces_per_player
        self.in_table = []
    #--------------------------------added-------------------------------
    def pseudo_deck(self):
        for i in range(len(self.deck2)):
            ki = os.urandom(128)
            digest = hashes.Hash(hashes.SHA256(), default_backend())
            digest.update(self.deck2[i].encode('utf-8'))
            digest.update(ki)
            digest.update(bytes(i))
            res = digest.finalize()
            self.pseudonym_map.update({res: [ki, i]})
            self.ps_deck.append((res, i))

    def check(self, msg):
        r_deck = [i.decode('utf-8') for i in msg]
        tmp2 = r_deck
        tmp = [str(i) for i in self.ps_deck]
        for i in r_deck:
            if i in tmp:
                tmp.remove(i)
            else:
                return False
        return True

    def decipher_all(self, p_tiles, k_map_arr):
        t = p_tiles
        aux = []
        last = len(k_map_arr)
        count = 0
        for k_map in k_map_arr:
            count += 1
            for ciphertext in t:
                if ciphertext in k_map:
                    plaintext = self.decipher(ciphertext, k_map)
                    if count == last:
                        aux.append(plaintext)
                    else:
                        aux.append(base64.b64encode(plaintext))
            if aux != []:
                t = aux
                aux = []
        for i in t:
            self.idx.append([tuple(map(str, i.decode("utf-8")[1:-1].split(', ')))[-1], None])

    def decipher_all_return(self, p_tiles, k_map_arr):
        hand_decoded = []
        t = p_tiles
        aux = []
        last = len(k_map_arr)
        count = 0
        for k_map in k_map_arr:
            count += 1
            for ciphertext in t:
                if ciphertext in k_map:
                    plaintext = self.decipher(ciphertext, k_map)
                    if count == last:
                        aux.append(plaintext)
                    else:
                        aux.append(base64.b64encode(plaintext))
            if aux != []:
                t = aux
                aux = []
        for i in t:
            hand_decoded.append([tuple(map(str, i.decode("utf-8")[1:-1].split(', ')))[-1], None])
        return hand_decoded
        
        
    def decipher(self, ciphertext, k_map):
        c = base64.b64decode(ciphertext)
        key = k_map[ciphertext]
        IV, c_text = c[:16], c[16:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(IV), default_backend())
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        decryptor = cipher.decryptor()
        plaintext = b''
        plaintext = unpadder.update(decryptor.update(c_text)) + unpadder.finalize()
        return plaintext

    def de_anonimyze(self):
        for i in range(len(self.idx)):
            ciphertext = self.rsa_encrypt(self.deck2[int(self.idx[i][0])].encode('utf-8'), self.idx[i][1])
            self.idx[i][1] = ciphertext
    
    def rsa_encrypt(self, msg, pubkey):
        pub = serialization.load_pem_public_key(pubkey, backend=default_backend())
        ciphertext = pub.encrypt(msg,as_padd.OAEP(
                mgf=as_padd.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext
    #--------------------------------------------------------------------

    def __str__(self):
        a = ""
        for piece in self.deck:
            a+=str(piece)
        return a

    def toJson(self):
        return {"npieces": self.npieces, "pieces_per_player": self.pieces_per_player, "in_table": self.in_table,"deck":self.deck}

