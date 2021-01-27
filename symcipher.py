import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.backends import default_backend
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


####### Diffie Hellman Key Exchange Algorithm #######

# class DiffieHellman:
    
#     def __init__(self, pk1, pk2, private_key):
#         self.pk1 = pk1
#         self.pk2 = pk2
#         self.private_key = private_key
#         self.full_key = None

#     def generate_partial_key(self):
#         partial_key = self.pk1**self.pk2
#         partial_key = partial_key%self.pk2
#         return partial_key

#     def generate_full_key(self, partial_key_r):
#         full_key = partial_key_r**self.private_key
#         full_key = full_key%self.pk2
#         self.full_key = full_key
#         return full_key


########### Key Derivation (KDF) ############

def keyDerivation():

    salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        hashes.SHA512(), 32, salt, 10000, default_backend()
    )
    key = kdf.derive(os.urandom(16))

    return key

########### Cifra simétrica ############

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
    key = keyDerivation()
    original_msg = b'2]f\xb9a\xdf\x99\xc8\xd4'
    print("Mensagem original:", original_msg)
    ciphertext = encrypt_message(original_msg, key)
    print("Ciphertext:", ciphertext) 

    msg_result = decrypt_message(ciphertext, key)
    print("Mensagem resultante:", msg_result)


