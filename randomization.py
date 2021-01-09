import os
import sys
import json
import random
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets
from pseudonimization import *
from byte_encoder import *
import base64

ps_deck = pseudonimization(["6:6","6:5","6:4","6:3","6:2","6:1","6:0","5:5","5:4","5:3","5:2","5:1","5:0","4:4","4:3","4:2","4:1","4:0","3:3","3:2","3:1","3:0","2:2","2:1","2:0","1:1","1:0","0:0"])

deck = ps_deck.pseudo_deck()
block_size_cbc = algorithms.AES.block_size // 8
key_map = dict()
new_deck = []
decrypted_deck = []
hand = []

def generate_symmetric_key():
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(hashes.SHA512(), 32, salt, 100000, default_backend())
    key = kdf.derive(os.urandom(16))
    return key

def encrypt():
    for tile in deck:
        msg = json.dumps(str(tile))
        key = generate_symmetric_key()
        IV = os.urandom(block_size_cbc)
        cipher = Cipher(algorithms.AES(key), modes.CBC(IV), default_backend())
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        encryptor = cipher.encryptor()
        c_text = b''
        t = str(tile)
        i = 0
        while i<len(t):
            #aux = encryptor.update(padder.update(tile[0]))
            aux = encryptor.update(padder.update(t[i:i+block_size_cbc].encode('utf-8')))
            c_text += aux
            i += block_size_cbc
        c_text += encryptor.update(padder.finalize())
        ciphertext = base64.b64encode(IV) + c_text

        # nonce = secrets.token_bytes(12)
        # ciphertext = nonce + AESGCM(key).encrypt(nonce, str(tile).encode('raw_unicode_escape'), b"")
        #print(ciphertext)
        key_map[(ciphertext)] = key
        new_deck.append(ciphertext)
        
    #random.shuffle(new_deck)

def decrypt():
    for ciphertext in new_deck:
        key = key_map[ciphertext]
        IV, c_text = base64.b64decode(ciphertext[:24]), ciphertext[24:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(IV), default_backend())
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        decryptor = cipher.decryptor()
        plaintext = b''
        i = 24
        while i<len(ciphertext):
            aux = unpadder.update(decryptor.update(ciphertext[i:i+block_size_cbc]))
            plaintext += aux
            i += block_size_cbc
        plaintext += unpadder.finalize()

        # plaintext = AESGCM(key).decrypt(tile[:12], tile[12:], b"")

        # cipher = Cipher(algorithms.AES(key_map[tile]), modes.CBC(IV), default_backend())
        # decryptor = cipher.decryptor()
        # u = padding.PKCS7(algorithms.AES.block_size).unpadder()
        # plaintext = decryptor.update(u.update(tile.encode())) + decryptor.finalize()
        decrypted_deck.append(base64.b64encode(plaintext).decode('utf-8'))

def pick_tile():
    if random.choice([i for i in range(100)]) > 5:
        return
    ids = [id for id in range(len(decrypted_deck))]
    choice = random.choice(ids)
    decrypted_deck.pop(decrypted_deck[choice])
    hand.append(decrypted_deck[choice])

encrypt()
decrypt()
string = dict()
string['msg'] = decrypted_deck
msg = json.dumps(string)
print(ps_deck.check(msg))