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

ps_deck = pseudonimization(["6:6","6:5","6:4","6:3","6:2","6:1","6:0","5:5","5:4","5:3","5:2","5:1","5:0","4:4","4:3","4:2","4:1","4:0","3:3","3:2","3:1","3:0","2:2","2:1","2:0","1:1","1:0","0:0"])

deck = ps_deck.pseudo_deck()

key_map = dict()
new_deck = []
decrypted_deck = []
IV = os.urandom(algorithms.AES.block_size // 8)
cipher = []
padder = []
unpadder = []

def generate_symmetric_key():
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(hashes.SHA512(), 32, salt, 100000, default_backend())
    key = kdf.derive(os.urandom(16))
    return key

def encrypt():
    for tile in deck:
        key = generate_symmetric_key()
        nonce = secrets.token_bytes(12)
        ciphertext = nonce + AESGCM(key).encrypt(nonce, str(tile).encode('raw_unicode_escape'), b"")
        key_map[str(ciphertext)] = key

        new_deck.append(ciphertext)
        # c = Cipher(algorithms.AES(key), modes.CBC(IV), default_backend())
        # p = padding.PKCS7(algorithms.AES.block_size).padder()
        # encryptor = c.encryptor()

        # plaintext = str(tile)
        # ciphertext = b""
        # for text in [plaintext[i:i+16] for i in range(0, len(plaintext), 16)]:
        #     if len(text) < 16:
        #         ciphertext += encryptor.update(p.update(text.encode())) + encryptor.update(p.finalize())
        #     else:
        #         ciphertext += encryptor.update(p.update(text.encode()))
    #random.shuffle(new_deck)

def decrypt():
    for tile in new_deck:
        key = key_map[str(tile)]
        plaintext = AESGCM(key).decrypt(tile[:12], tile[12:], b"")


        # cipher = Cipher(algorithms.AES(key_map[tile]), modes.CBC(IV), default_backend())
        # decryptor = cipher.decryptor()
        # u = padding.PKCS7(algorithms.AES.block_size).unpadder()
        # plaintext = decryptor.update(u.update(tile.encode())) + decryptor.finalize()
        decrypted_deck.append(plaintext)

encrypt()
decrypt()
json_c = json.dumps(key_map, cls=MyEncoder)
cenas = json.loads(json_c)
tmp = []
tmp2 = []
for key, value in key_map.items():
    tmp.append(value)
for key, value in cenas.items():
    tmp2.append(value)
# for j in range(len(tmp)):
#     print(tmp[j])
#     x = tmp2[j].encode('raw_unicode_escape')
#     print(x)
#     if tmp[j] == x:
#         print(True)
#     print()
res = json.dumps(decrypted_deck, cls=MyEncoder)
print(ps_deck.check(res))
print(ps_deck.check_deck(decrypted_deck))
