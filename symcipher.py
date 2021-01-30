import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import dh
import secrets
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.backends import default_backend
import base64
#from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import random
import pickle

### First we generate a shared secret using DH, after that we apply KDF that will result in a shared key.
### Then we use that shared key in AES.

####### Diffie Hellman from cryptography.hazmat.primitives #######

class DiffieHellman:

    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.parameters = dh.generate_parameters(generator=2, key_size=2048, backend=default_backend())

    def getExchangeKeys(self):
        self.private_key = self.parameters.generate_private_key()
        self.public_key = self.private_key.public_key()

    def getSharedKey(self, peer_public_key):
        shared_key = self.private_key.exchange(peer_public_key)
        print(str(shared_key))

        # Key derivation
        derived_key = HKDF(algorithm=hashes.SHA256(),
                            length=32,
                            salt=None,
                            info=b'handshake data',
                            backend=default_backend()
                        ).derive(shared_key)

        return derived_key
        
####### Diffie Hellman Key Exchange Algorithm made by us #######

# class DiffieHellman:
#     prime = 103079
#     generator = 7

#     def __init__(self):
#         self.secret_value = random.randint(1,100)
#         self.public_value = self.generate_pk()

#     def generate_pk(self):
#         public_value = (self.generator ** self.secret_value) % self.prime
#         return public_value

#     def generate_ss(self, secret_value, other_key):
#         shared_secret = (other_key ** self.secret_value) % self.prime
#         return shared_secret

#     def __str__(self):
#         return "secret values is " + str(self.secret_value) + " and public value is " + str(self.public_value)

### test ###
# alice = DiffieHellman()
# bob = DiffieHellman()

# alice_ss = alice.generate_ss(alice.secret_value, bob.public_value)
# print(alice_ss)
# bob_ss = bob.generate_ss(bob.secret_value, alice.public_value)
# print(bob_ss)


########### Key Derivation (KDF) ############

def keyDerivation(key):


    kdf = PBKDF2HMAC(
        hashes.SHA512(), 32, bytes(5), 10000, default_backend()
    )
    key = kdf.derive(bytes(key))

    return key


### test ###

# key_derivation = keyDerivation(alice_ss)
# print(key_derivation)

########### Cifra simétrica ############
### Note to self: this class needs to be fixed


class SymmetricCipher:

    def encrypt_message(self, message, key):
        print(str(message).encode('utf-8'))
        
        # nonce = secrets.token_bytes(12)
        # print(type(nonce))
        # ciphertext = nonce + AESGCM(key).encrypt(nonce, str(message).encode('utf-8'), b"")

        nonce = secrets.token_bytes(12)
        ciphertext = nonce + AESGCM(key).encrypt(nonce, str(message).encode('utf-8'), b"")

        # encryptor = cipher.encryptor()
        # padder = padding.PKCS7(algorithms.AES.block_size).padder()

        # padded = padder.update(message) + padder.finalize()
        # ciphertext = encryptor.update(padded) + encryptor.finalize()

        return base64.b64encode(ciphertext).decode('utf-8')

    def decrypt_message(self, ciphertext, key):

        # IV, ciphertext_text = ciphertext[:algorithms.AES.block_size//8], ciphertext[algorithms.AES.block_size//8:]
        # cipher = Cipher(
        #     algorithms.AES(key), 
        #     modes.CBC(IV), 
        #     default_backend()
        # )
        # decryptor = cipher.decryptor()
        # unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

        # pt = decryptor.update(ciphertext_text) + decryptor.finalize()
        # plaintext = unpadder.update(pt) + unpadder.finalize()

        #plaintext = AESGCM(key).decrypt(ciphertext[:12], ciphertext[12:], b"")

        ciphertext = base64.b64decode(ciphertext.encode('utf-8'))

        plaintext = AESGCM(key).decrypt(ciphertext[:12], ciphertext[12:], b"")

        return plaintext

    ### test ###
    # key = keyDerivation(alice_ss)
    # print(key)

    # key = keyDerivation(bob_ss)
    # print(key)
    #original_msg = b'2]f\xb9a\xdf\x99\xc8\xd4'
    #print("Mensagem original:", original_msg)
    #ciphertext = encrypt_message(original_msg, key)
    #print("Ciphertext:", ciphertext) 

    #msg_result = decrypt_message(ciphertext, key)
    #print("Mensagem resultante:", msg_result)


