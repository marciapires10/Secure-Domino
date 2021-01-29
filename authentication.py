import pandas
from Crypto.Cipher import DES3, AES
from PyKCS11 import *

lib = '/usr/local/lib/libpteidpkcs11.so'



def saveScore(score):                                                                                                                                     
    try :

        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(lib)
        slots = pkcs11.getSlotList()

        for slot in slots :
            if 'CARTAO DE CIDADAO' in pkcs11.getTokenInfo(slot).label:
                
                session = pkcs11.openSession(slot)
                objects = session.findObjects()
                serialNumber = ""

                for obj in objects:
                    l = session.getAttributeValue(obj, [CKA_LABEL])[0]
                    if l == 'CITIZEN SIGNATURE CERTIFICATE':
                        serialNumber=session.getAttributeValue(obj, [CKA_SERIAL_NUMBER], True)[0]

                session.closeSession
                print ('Load Pub Key succeeded')
                encryptDES(serialNumber, score)
        return True
    except :
        print ('Insira o cartao antes de o jogo terminal')
        return False


def encryptDES(serialNumber, score):
    ## Encrypt with DES
    key = b'Sixteen byte key'
    iv = b'\xd1\xd1\x10\x9e\xaeB\xc9u'
    #iv = os.urandom(DES3.block_size)

    cipher = DES3.new(key, DES3.MODE_OFB, iv)
    plaintext = str(serialNumber)
    msg = cipher.encrypt(plaintext)
    # print(plaintext)
    # print(msg)
    writeCSV(msg, score)


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
    except :
        print("You didn\'t have the card inserted!")
        return serialNumber


def encryptSerialNumber(serialNumber):
    ## Encrypt with DES
    key = b'Sixteen byte key'
    iv = b'\xd1\xd1\x10\x9e\xaeB\xc9u'
    #iv = os.urandom(DES3.block_size)
    print("ola")
    plaintext = str(serialNumber)
    
    cipher = DES3.new(key, DES3.MODE_OFB, iv)
    pad_len = 8 - len(plaintext) % 8 # length of padding
    padding = chr(pad_len) * pad_len # PKCS5 padding content
    plaintext += padding
    msg = cipher.encrypt(plaintext)
    print(msg)
    return msg


def dencryptSerialNumber(msg):
    ## Decrypt with DES
    key = b'Sixteen byte key'
    iv = b'\xd1\xd1\x10\x9e\xaeB\xc9u'

    cipher = DES3.new(key, DES3.MODE_OFB, iv)
    #print(cipher.decrypt(msg).decode())
    return cipher.decrypt(msg).decode()


def writeCSV(msg, score):
    olderMember = False
    df = pandas.read_csv('data.csv')
    count = 0
    for r in df.values:
        if r[1] == str(msg):  #if the person already exist in our DB
            olderMember = True
            df.loc[count,'POINTS'] = df.loc[count,'POINTS']+score
            print("DF: " + str(df))
            df.to_csv('data.csv', index = None, header=True)
        count+=1
    print()
    if olderMember==False:
        df = df.append({'POINTS': str(score), 'SERIAL_NUMBER': str(msg)}, ignore_index=True)
        print("DF: " + str(df))
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

# rr = saveScore(5)
# print(rr)
# readCSV()
# print()
# allPoints()
#authSerialNumber()

