from authentication import savePubKey, writeCSV
import socket
import os
import sys
import pickle
import json
import base64
import Colors
import string
from deck_utils import Player
import random
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class client():
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.connect((host, port))
        first_msg = {"action": "hello"}
        self.sock.send(pickle.dumps(first_msg))
        self.player = None
        #-------added-------------
        self.next_player = None	
        self.first_player = None
        self.last_player = None
        #-----messages------------
        self.msg = dict()
        #-------------------------
        #----client vars---------
        self.p_deck = []
        self.block_size_cbc = algorithms.AES.block_size // 8
        self.key_map = dict()
        self.p_hand = []
        self.receiveData()

    def receiveData(self):
        while True:
            data = self.sock.recv(4096)
            if data:
                self.handle_data(data)

    def handle_data(self, data):
        data = pickle.loads(data)
        action = data["action"]
        print("\n"+action)
        if action == "login":
            nickname = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) #input(data["msg"])
            print("Your name is "+Colors.BBlue+nickname+Colors.Color_Off)
            msg = {"action": "req_login", "msg": nickname}
            self.player = Player(nickname,self.sock)
            self.sock.send(pickle.dumps(msg))
            return
            # todo login
        elif action == "you_host":
            self.player.host=True
        elif action == "new_player":
            print(data["msg"])
            print("There are "+str(data["nplayers"])+"\\"+str(data["game_players"]))

        elif action == "waiting_for_host":
            if self.player.host:
                input(Colors.BGreen+"PRESS ENTER TO START THE GAME"+Colors.Color_Off)
                msg = {"action": "start_game"}
                self.sock.send(pickle.dumps(msg))
                print("Sent ", msg)
            else:
                print(data["msg"])

        elif action == "host_start_game":
            print(data["msg"])
            msg = {"action": "get_game_propreties"}
            self.sock.send(pickle.dumps(msg))
            print("Sent ", msg)

        elif action == "rcv_game_propreties":
            self.player.nplayers = data["nplayers"]
            self.player.npieces = data ["npieces"]
            self.player.pieces_per_player = data["pieces_per_player"]
            self.player.in_table = data["in_table"]
            self.player.deck = data["deck"]
            self.p_deck = data["deck"] #added
            player_name = data["next_player"]
            if data["next_player"] == self.player.name:
                player_name = Colors.BRed + "YOU" + Colors.Color_Off
            print("deck -> " + ' '.join(map(str, self.player.deck)) + "\n")
            print("hand -> " + ' '.join(map(str, self.player.hand)))
            print("in table -> " + ' '.join(map(str, data["in_table"])) + "\n")
            print("Current player ->",player_name)
            print("next Action ->", data["next_action"])
            if self.player.name == data["next_player"]:

                if data["next_action"]=="get_piece":
                    if not self.player.ready_to_play:
                        #input("Press ENter \n\n")
                        random.shuffle(self.player.deck)
                        piece = self.player.deck.pop()
                        self.player.insertInHand(piece)
                        msg = {"action": "get_piece","deck":self.player.deck}
                        self.sock.send(pickle.dumps(msg))
                if data["next_action"]=="play":
                    #input(Colors.BGreen+"Press ENter \n\n"+Colors.Color_Off)
                    msg = self.player.play()
                    self.sock.send(pickle.dumps(msg))

        elif action == "scrumble":
            cipher_deck = self.cipher(self.p_deck)
            return

        elif action == "pick":
            if len(self.p_hand) < self.player.pieces_per_player:
                self.p_deck = self.pick_tile(self.p_deck)
            else:
                return

        elif action == "decipher":
            self.p_deck = self.decipher(self.p_deck)
            return

        elif action == "end_game":
            winner = data["winner"]
            if data["winner"] == self.player.name:
                winner = Colors.BRed + "YOU" + Colors.Color_Off
            else:
                winner = Colors.BBlue + winner + Colors.Color_Off
            print(Colors.BGreen+"End GAME, THE WINNER IS: "+winner)
            
            # Check Agreement
            agreement = ""
            while( agreement != "y" and agreement != "n"):
                agreement_input = str(input("Do you agree with this result? (Y/n)"))
                agreement = agreement_input.lower()
                while(" " in agreement):
                    agreement = agreement.replace(" ","")
            msg = {"action": "agreement","player": self.player.name, "choice":agreement}
            self.sock.send(pickle.dumps(msg))


        elif action == "wait":
            print(data["msg"])

        elif action =="disconnect":
            self.sock.close()
            print("PRESS ANY KEY TO EXIT ")
            sys.exit(0)

        elif action == "agreement_result":
            print("Result:" + str(data["agreement_result"]))
            if str(data["agreement_result"]) == "Aproved":
                savePubKey(self.player.name, self.player.score)
    #------------------------------added----------------------------
    def generate_symmetric_key(self):
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(hashes.SHA512(), 32, salt, 100000, default_backend())
        key = kdf.derive(os.urandom(16))
        return key

    def pick_tile(self, decrypted_deck):
        prob = random.choice([i for i in range(100)])
        ids = [id for id in range(len(decrypted_deck))]
        if prob > 5:
            if prob > 52.5 and len(self.p_hand) > 0:
                hand_ids = [id for id in range(len(self.p_hand))]
                decrypted_deck.append(self.p_hand.pop(random.choice(hand_ids)))
                self.p_hand.append(decrypted_deck.pop(random.choice(ids)))
            return decrypted_deck
        else:
            self.p_hand.append(decrypted_deck.pop(random.choice(ids)))
            return decrypted_deck
    #------------------------------------------------------------------------------------

a = client('localhost', 50000)
