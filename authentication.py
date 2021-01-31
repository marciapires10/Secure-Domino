import pandas
from Crypto.Cipher import DES3, AES
from PyKCS11 import *
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.primitives.asymmetric import (padding ,rsa ,utils)

lib = '/usr/local/lib/libpteidpkcs11.so'


def authSerialNumber():
    serialNumber = ""
    try :

        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(lib)
        slots = pkcs11.getSlotList()

        for slot in slots :
            if 'CARTAO DE CIDADAO' in pkcs11.getTokenInfo(slot).label:
                
                session = pkcs11.openSession(slot)
                objects = session.findObjects()

                for obj in objects:
                    l = session.getAttributeValue(obj, [CKA_LABEL])[0]
                    if l == 'CITIZEN SIGNATURE CERTIFICATE':
                        serialNumber=session.getAttributeValue(obj, [CKA_SERIAL_NUMBER], True)[0]

                session.closeSession
        print("Authentication succeeded")
        SN = encryptSerialNumber(serialNumber)
        return SN
    except Exception as e:
        print(e)
        print("You didn\'t have the card inserted!")
        # sys.exit(0)


def encryptSerialNumber(serialNumber):
    ## Encrypt with DES
    key = b'Sixteen byte key'
    iv = b'\xd1\xd1\x10\x9e\xaeB\xc9u'
    plaintext = str(serialNumber)
    cipher = DES3.new(key, DES3.MODE_OFB, iv)
    pad_len = 8 - len(plaintext) % 8 # length of padding
    padding = chr(pad_len) * pad_len # PKCS5 padding content
    plaintext += padding
    msg = cipher.encrypt(plaintext)
    #print(msg)
    return msg


def dencryptSerialNumber(msg):
    ## Decrypt with DES
    key = b'Sixteen byte key'
    iv = b'\xd1\xd1\x10\x9e\xaeB\xc9u'
    cipher = DES3.new(key, DES3.MODE_OFB, iv)
    return cipher.decrypt(msg).decode()


def writeCSV(msg, score):
    olderMember = False
    df = pandas.read_csv('data.csv')
    count = 0
    for r in df.values:
        if r[1] == str(msg):  #if the person already exist in our DB
            olderMember = True
            df.loc[count,'POINTS'] = df.loc[count,'POINTS']+score
            print("\nDF: " + str(df))
            df.to_csv('data.csv', index = None, header=True)
        count+=1
    print()
    if olderMember==False:
        df = df.append({'POINTS': str(score), 'SERIAL_NUMBER': str(msg)}, ignore_index=True)
        print("\nDF: " + str(df))
        df.to_csv('data.csv', index = None, header=True)


def readCSV():
    SN = authSerialNumber()
    df = pandas.read_csv('data.csv')
    #print(df)

    for r in df.values:
        if str(SN) == r[1]:
            print("\nThe cliente has: ", r[0], " points.")


def allPoints():
    df = pandas.read_csv('data.csv')
    df = df.sort_values(by='POINTS', ascending=False)
    print(df)

def lerPrivKeyOfCard(challenge):
    try:
        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(lib)
        slots = pkcs11.getSlotList()
        for slot in slots :
            if 'CARTAO DE CIDADAO' in pkcs11.getTokenInfo(slot).label:
                # data = bytes('data to be signed', 'utf-8')
                session = pkcs11.openSession(slot)
                privKey = session.findObjects([(CKA_CLASS,CKO_PRIVATE_KEY), (CKA_LABEL,'CITIZEN AUTHENTICATION KEY')])[0]
                signature = bytes(session.sign(privKey,challenge,Mechanism(CKM_SHA1_RSA_PKCS)))
                session.closeSession
                return signature
    except:
        print("ERRO na função lerPrivKeyOfCard()")
        return False


def lerPublicKeyOfCard(signature, challenge):
    pkcs11 = PyKCS11.PyKCS11Lib()
    pkcs11.load(lib)
    slots = pkcs11.getSlotList()
    if slots==[]:   #este if é para caso não esteja inserido o leitor de cartões dar ERRO
        print("Insira o Leitor de Cartões!")
        session = pkcs11.openSession(slots)
    for slot in slots :
        session = pkcs11.openSession(slot)
        pubKeyHandle = session.findObjects ([(CKA_CLASS, CKO_PUBLIC_KEY) ,(CKA_LABEL , 'CITIZEN AUTHENTICATION KEY')])[0]
        pubKeyDer = session.getAttributeValue (pubKeyHandle, [CKA_VALUE], True )[0]
        session.closeSession

        pubKey = load_der_public_key(bytes(pubKeyDer), default_backend())
        pubKey.verify( signature , challenge ,padding.PKCS1v15() , hashes.SHA1())

# rr = saveScore(5)
# print(rr)
# readCSV()
# print()
# allPoints()
#authSerialNumber()

