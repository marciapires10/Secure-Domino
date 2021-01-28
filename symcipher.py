import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.backends import default_backend
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import random

### First we generate a shared secret using DH, after that we apply KDF that will result in a shared key.
### Then we use that shared key in AES.


####### Diffie Hellman Key Exchange Algorithm #######

class DiffieHellman:
    prime = 103079
    generator = 7

    def __init__(self):
        self.secret_value = random.randint(1,100)
        self.public_value = self.generate_pk()

    def generate_pk(self):
        public_value = (self.generator ** self.secret_value) % self.prime
        return public_value

    def generate_ss(self, secret_value, other_key):
        shared_secret = (other_key ** self.secret_value) % self.prime
        return shared_secret

### test ###
alice = DiffieHellman()
bob = DiffieHellman()

alice_ss = alice.generate_ss(alice.secret_value, bob.public_value)
print(alice_ss)
bob_ss = bob.generate_ss(bob.secret_value, alice.public_value)
print(bob_ss)


########### Key Derivation (KDF) ############

def keyDerivation(key):

    salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        hashes.SHA512(), 32, salt, 10000, default_backend()
    )
    key = kdf.derive(bytes(key))

    return key


### test ###

key_derivation = keyDerivation(alice_ss)
print(key_derivation)

########### Cifra simétrica ############
### Note to self: this class needs to be fixed


class SymmetricCipher:

    def encrypt_message(message, key):

        IV = os.urandom(algorithms.AES.block_size // 8)
        cipher = Cipher(
            algorithms.AES(key), 
            modes.CBC(IV), 
            default_backend()
        )
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(algorithms.AES.block_size).padder()

        padded = padder.update(message) + padder.finalize()
        ciphertext = encryptor.update(padded) + encryptor.finalize()

        return IV + ciphertext

    def decrypt_message(ciphertext, key):

        IV, ciphertext_text = ciphertext[:algorithms.AES.block_size//8], ciphertext[algorithms.AES.block_size//8:]
        cipher = Cipher(
            algorithms.AES(key), 
            modes.CBC(IV), 
            default_backend()
        )
        decryptor = cipher.decryptor()
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

        pt = decryptor.update(ciphertext_text) + decryptor.finalize()
        plaintext = unpadder.update(pt) + unpadder.finalize()

        return plaintext

    ### test ###
    key = keyDerivation(alice_ss)
    original_msg = b'2]f\xb9a\xdf\x99\xc8\xd4'
    print("Mensagem original:", original_msg)
    ciphertext = encrypt_message(original_msg, key)
    print("Ciphertext:", ciphertext) 

    msg_result = decrypt_message(ciphertext, key)
    print("Mensagem resultante:", msg_result)


