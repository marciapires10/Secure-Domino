import pandas

from os import write
from PyKCS11 import *
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_der_public_key, load_pem_public_key
from cryptography.hazmat.primitives.asymmetric import (padding ,rsa ,utils)

lib = '/usr/local/lib/libpteidpkcs11.so'


def writeCSV(winner, pem, score):
    olderMember = False
    text = input("Your Name:")
    df = pandas.read_csv('data.csv')
    count = 0
    for r in df.values:
        if r[2] == pem.decode("utf-8"):  #if the person already exist in our DB
            olderMember = True
            df.loc[count,'POINTS'] = df.loc[count,'POINTS']+score
            print("DF: " + str(df))
            df.to_csv('data.csv', index = None, header=True)
        count+=1
    print()
    if olderMember==False:
        df = df.append({'NAME': text, 'POINTS': str(score), 'PUBLIC_KEY': pem.decode("utf-8")}, ignore_index=True)
        print("DF: " + str(df))
        df.to_csv('data.csv', index = None, header=True)

    print(df)


def savePubKey(name, score):                                                                                                                                     
    try :
        
        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(lib)
        slots = pkcs11.getSlotList()

        for slot in slots :
            if 'CARTAO DE CIDADAO' in pkcs11.getTokenInfo(slot).label:
            
                session = pkcs11.openSession(slot)
                pubKeyHandle = session.findObjects ([(CKA_CLASS, CKO_PUBLIC_KEY) ,(CKA_LABEL , 'CITIZEN AUTHENTICATION KEY')])[0]
                pubKeyDer = session.getAttributeValue (pubKeyHandle, [CKA_VALUE], True )[0]
                session.closeSession

                pubKey = load_der_public_key(bytes(pubKeyDer), default_backend())
                pem = pubKey.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
        
                #pubKey.verify( signature , data ,padding.PKCS1v15() , hashes.SHA1())
                print ('Load Pub Key succeeded')
                writeCSV(name, pem, score)
                #saveLogins(name, pem)
        return True
    except :
        writeCSVTomas(name, score)
        print ('Insira o cartao')
        return False

# def read_from_file():
#     f = open("login.txt", "r")
#     # print(f.read())
#     return f.read()

# def saveLogins(name, pem):
#     key = read_from_file()
#     with open('login.txt', 'w') as f:
#         f.write(key)
#         f.write('\n')
#         f.write(name)
#         f.write("!!")
#         f.write(pem.decode("utf-8"))
        
#         f.close()

#writeCSV("OLE2")
#savePubKey("r2")