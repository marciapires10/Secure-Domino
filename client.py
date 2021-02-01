from authentication import lerPrivKeyOfCard
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
import time
from security import DiffieHellman, SymmetricCipher, HMAC
import socket
import getpass
import hashlib
from Crypto.Cipher import AES
from hashlib import sha256



class client():

    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.connect((host, port))
        first_msg = {"action": "authentication_3"}  #Mudar para authentication na Versão Final!
        self.sock.send(pickle.dumps(first_msg))
        self.player = None
        #-------added-------------
        self.p_deck = []
        self.key_map = dict()
        self.p_hand = []
        self.receiveData()
        self.players = [] #list of players
        self.dh = None
        self.dh_idx = None
        self.tmp_tiles = []
        self.tmp_arr = []

    def receiveData(self):
        while True:
            data = self.sock.recv(524288)
            if data:
                self.handle_data(data)

    def handle_data(self, data):
        data = pickle.loads(data)
        action = data["action"]
        print("\n" + str(action))
        if action == "authentication_2":
            try:
                print("Trying Autenticação do cliente...")
                challenge = data["msg"]  #challenge
                signature = lerPrivKeyOfCard(challenge) #ler do cartão a chave privada
                if signature==False:
                    self.sock.close()
                    print("\nTem de inserir o catão para ser Autenticado!")
                    sys.exit(0)
                msg = {"action": "authentication_3", "msg": signature} 
                self.sock.send(pickle.dumps(msg))
                return 
            except:            
                self.sock.close()
                print("Falhou a autenticação no cliente")
                sys.exit(0)
        
        if action == "login":
            # if data["authentication"] == False:       #Voltar a descomentar na Versão final!!
            #     self.sock.close()
            #     print("Cliente não Autenticado")
            #     sys.exit(0)
            nickname = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) #input(data["msg"])
            print("Your name is "+Colors.BBlue+nickname+Colors.Color_Off)
            self.dh = DiffieHellman(103079, 7)
            self.symC = SymmetricCipher()
            self.hmac = HMAC()
            public_key = self.dh.public_key
            print(public_key)
            msg = {"action": "req_login", "msg": nickname, "public_key": public_key}
            self.player = Player(nickname,self.sock,data["max_pieces"])
            self.sock.send(pickle.dumps(msg))
            return
            # todo login
        elif action == "you_host":
            self.player.host=True
            print("Host public key", data["public_key"])
            self.dh.getSharedKey(data["public_key"])
            print(self.dh.shared_key)
        elif action == "new_player":
            print("New player public key", data["public_key"])
            self.dh.getSharedKey(data["public_key"])
            print(self.dh.shared_key)
            print("There are "+str(data["nplayers"])+"\\"+str(data["game_players"]))
        #---------------------------added-----------------------------
        elif action == "start_sessions":
            print("start")
            self.players = [[p, DiffieHellman(23, 5)] for p in data["players"] if p != self.player.name]
            self.dh_idx = 0
            for i in self.players:
                print("name: "+i[0]+" session key: "+str(base64.b64decode(i[1].public_key)))
            if self.player.host:
                print("host")
                msg = {"action": "player_sessions"}
                print(msg)
                self.sock.send(pickle.dumps(msg))
        elif action == "waiting_for_host":
            #--------------------added--------------------------
            self.players = [[p, DiffieHellman(23, 5)] for p in data["players"] if p != self.player.name]
            self.dh_idx = 0
            print(self.players)
            #---------------------------------------------------
            if self.player.host:
                msg = {"action": "start_game"}
                self.sock.send(pickle.dumps(msg))

        elif action == "share_key":
            print("me: "+self.player.name)
            if self.players[self.dh_idx][1].shared_key == None:
                print("send to: "+str(self.players[self.dh_idx][0]))
                print("key status: "+str(self.players[self.dh_idx][1].shared_key))
                print("my public: "+str(self.players[self.dh_idx][1].public_key))
                public_key = self.players[self.dh_idx][1].public_key
                key = self.symC.encrypt_message(public_key, self.dh.shared_key)
                key_sign = self.hmac_sign(key, self.dh.shared_key)
                msg = {"action": "send_dh", "key": key, "send_to": self.players[self.dh_idx][0], "from": self.player.name, "sign": key_sign}
                self.sock.send(pickle.dumps(msg))
            else:
                msg = {"action": "sent"}
                self.sock.send(pickle.dumps(msg))
        elif action == "get_key":
            print("me: "+self.player.name)
            sk = self.dh.shared_key
            verify = self.verify_sign(sk, data["sign"], data["key"])
            key = self.symC.decrypt_message(data["key"], self.dh.shared_key)
            print("get key from: " + data["from"] + " key: "+ str(key))
            for p in self.players:
                if p[0] == data["from"]:
                    print("my public: ", p[1].public_key)
                    p[1].getSharedKey(key)
                    print("SHARED KEY: " + str(p[1].shared_key))
                    key = self.symC.encrypt_message(p[1].public_key, self.dh.shared_key)
                    k_sign = self.hmac_sign(key, self.dh.shared_key)
                    msg = {"action": "done", "from": self.player.name, "key": key, "send_to": data["from"], "sign": k_sign}
                    self.sock.send(pickle.dumps(msg))
        elif action =="dh_response":
            sk = self.dh.shared_key
            verify = self.verify_sign(sk, data["sign"], data["key"])
            key = self.symC.decrypt_message(data["key"], self.dh.shared_key)
            for p in self.players:
                if p[0] == data["from"]:
                    p[1].getSharedKey(key)
                    print("SHAAARED KEY from " + data["from"] + " " + str(p[1].shared_key))
            self.dh_idx += 1
            if None not in [p[1].shared_key for p in self.players]:  
                msg = {"action": "sent"}
                self.sock.send(pickle.dumps(msg))
            else:
                for p in self.players:
                    if p[1].shared_key == None:
                        key = self.symC.encrypt_message(p[1].public_key, self.dh.shared_key)
                        key_sign = self.hmac_sign(key, self.dh.shared_key)
                        msg = {"action": "send_dh", "key": key, "send_to": p[0], "from": self.player.name, "sign": key_sign}
                        self.sock.send(pickle.dumps(msg))

        elif action == "host_start":
            input(Colors.BGreen+"PRESS ENTER TO START THE GAME"+Colors.Color_Off)
            msg = {"action": "start_game"}
            self.sock.send(pickle.dumps(msg))
        #---------------added----------------------------
        elif data["action"] == "scrumble":
            ## verify signature
            verify = self.verify_sign(self.dh.shared_key, data["sign"], data["deck"])
            scrumble_deck = self.symC.decrypt_message(data["deck"], self.dh.shared_key)
            self.player.cipher_tiles(pickle.loads(scrumble_deck))
            deck = self.symC.encrypt_message(pickle.dumps(self.player.ciphered_deck), self.dh.shared_key)
            sign = self.hmac_sign(deck, self.dh.shared_key)
            msg = {"action": "scrumbled", "deck": deck, "sign": sign}
            self.sock.send(pickle.dumps(msg))
        elif data["action"] == "select":
            if data["from"] == "tm":
                self.tmp_tiles, update = self.player.pick_tile(data["deck"])
            else:
                sk = [p[1].shared_key for p in self.players if p[0] == data["from"]][0]
                verify = self.verify_sign(sk, data["sign"], data["deck"])
                pick = self.symC.decrypt_message(data["deck"], sk)
                self.tmp_tiles, update = self.player.pick_tile(pickle.loads(pick))
            next_player = random.choice(self.players)
            c_tiles = self.symC.encrypt_message(pickle.dumps(self.tmp_tiles), next_player[1].shared_key)
            sign = self.hmac_sign(c_tiles, next_player[1].shared_key)
            msg = {"action": "selected", "deck": c_tiles, "next_player": next_player[0], "sign": sign, "update": update, "from": self.player.name}
            self.sock.send(pickle.dumps(msg))
        elif action == "s_deck":
            msg = {"action": "s_deck", "deck": self.tmp_tiles}
            self.sock.send(pickle.dumps(msg))
        elif data["action"] == "commitment":
            self.player.bitcommitment()
            self.player.start_hand = self.player.hand2
            msg = {"action": "commited", "bitcommit": self.player.bitcommit, "r1": self.player.r1}
            self.sock.send(pickle.dumps(msg))
        elif data["action"] == "key_map":
            k_map = self.player.decipher_tiles(data["tiles"], data["key_map"])
            msg = {"action": "key_map", "key_map": k_map}
            self.sock.send(pickle.dumps(msg))
        elif data["action"] == "decipher":
            self.player.decipher_all(self.player.hand2, data["key_map"])
            msg = {"action": "deciphered"}
            self.sock.send(pickle.dumps(msg))
        elif data["action"] == "fill_array":
            if data["from"] == "tm":
                self.tmp_arr = self.player.fill_array(data["arr"])
            else:
                sk = [p[1].shared_key for p in self.players if p[0] == data["from"]][0]
                verify = self.verify_sign(sk, data["sign"], data["arr"])
                arr = self.symC.decrypt_message(data["arr"], sk)
                self.tmp_arr = self.player.fill_array(pickle.loads(arr))
            next_player = random.choice(self.players)
            full = False
            if True not in [a[1] == None for a in self.tmp_arr]:
                full = True
            array = self.symC.encrypt_message(pickle.dumps(self.tmp_arr), next_player[1].shared_key)
            sign = self.hmac_sign(array, next_player[1].shared_key)
            msg = {"action": "filled", "arr": array, "next_player": next_player[0], "from": self.player.name, "full": full, "sign": sign}
            self.sock.send(pickle.dumps(msg))
        elif data["action"] == "array":
            msg = {"action": "array", "arr": self.tmp_arr}
            self.sock.send(pickle.dumps(msg))
        elif data["action"] == "reveal_tiles":
            self.player.reveal_tiles(data["arr"])
            msg = {"action": "ready"}
            self.sock.send(pickle.dumps(msg))
        elif data["action"] == "piece_key":
            k_map = self.player.decipher_tiles([data["piece"]], data["key_map"])
            msg = {"action": "piece_key", "key_map": k_map, "rec": int(data["rec"])+1, "piece": data["piece"]}
            self.sock.send(pickle.dumps(msg))
        elif data["action"] == "decipher_piece":
            self.player.decipher_all([self.player.tmp_piece], data["key_map"])
            msg = {"action": "de_anonymize", "idx": self.player.indexes[-1]}
            self.sock.send(pickle.dumps(msg))
        elif data["action"] == "de-anonymized":
            self.player.insertInHand(data["piece"])
            msg = {"action": "ready_to_play"}
            self.sock.send(pickle.dumps(msg))
        #-------------------------------------------------------------------------
        elif action == "host_start_game":
            msg = {"action": "get_game_propreties"}
            self.sock.send(pickle.dumps(msg))

        elif action == "rcv_game_propreties":
            self.player.nplayers = data["nplayers"]
            self.player.npieces = data ["npieces"]
            self.player.pieces_per_player = data["pieces_per_player"]
            self.player.in_table = data["in_table"]
            self.player.deck = data["deck"]
            player_name = data["next_player"]
            if data["next_player"] == self.player.name:
                player_name = Colors.BRed + "YOU" + Colors.Color_Off
            if "previous_player" in data.keys():
                print("Piece: " + str(data["piece_played"]))
                if data["previous_player"] == self.player.name:
                    print("It was my turn.")
                elif "piece_played" in data.keys():
                    _piece = str(data["piece_played"])
                    _piece2 = _piece.split(":")[1] + ":" + _piece.split(":")[0]
                    for p in self.player.all_hand:
                        if _piece == str(p) or _piece2 == str(p):
                            print(str(data["previous_player"]) + " is cheating.")
                            print("Cheated piece: " + str(data["piece_played"]))
                            _player = self.player
                            msg = {"action": "report_cheating", "player_cheating": data["previous_player"], "piece": data["piece_played"]}
                            self.sock.send(pickle.dumps(msg))
                            return

            if self.player.name == data["next_player"]:

                if data["next_action"]=="get_piece":
                    # if len(self.player.hand) < self.player.pieces_per_player:
                    #     self.player.pick_tile()
                    if not self.player.ready_to_play:
                        #input("Press ENter \n\n")
                        random.shuffle(self.player.deck)
                        piece = self.player.deck.pop()
                        self.player.insertInHand(piece)
                        msg = {"action": "get_piece","deck":self.player.deck}
                        self.sock.send(pickle.dumps(msg))
                if data["next_action"]=="play":
                    #input(Colors.BGreen+"Press ENter \n\n"+Colors.Color_Off)
                    msg = self.player.play(False)
                    self.sock.send(pickle.dumps(msg))
        elif action == "ask_value":
            print("Asking...")
            if self.player.name == data["player"]:
                print("It's a me")
                _hand = self.player.hand
                _hand2 = self.player.hand2
                _start_hand = self.player.start_hand
                _r1 = self.player.r1
                _r2 = self.player.r2
                _bitcommit = self.player.bitcommit
                msg = {"action": "send_values", "player_cheating": self.player.name, "piece": data["piece"], "hand": _hand, "hand2": _hand2, "start_hand": _start_hand, "r1": _r1, "r2": _r2, "bitcommit": _bitcommit}
                self.sock.send(pickle.dumps(msg))
                return
            else:
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
            #while( agreement != "y" and agreement != "n"):
            agreement_input = str(input("Do you agree with this result? (Y/n)"))
            agreement = agreement_input.lower()
            while(" " in agreement):
                agreement = agreement.replace(" ","")
            if agreement != "n":
                agreement = "y"
            msg = {"action": "agreement","player": self.player.name, "choice":agreement}
            self.sock.send(pickle.dumps(msg))

        elif action =="disconnect":
            self.sock.close()
            print("PRESS ANY KEY TO EXIT ")
            sys.exit(0)

        elif action == "agreement_result":
            print("Result:" + str(data["agreement_result"]))
            # if str(data["agreement_result"]) == "Aproved":
            #     saveScore(self.player.score)

    def hmac_sign(self, msg, key):
        new_key = sha256(key).hexdigest()
        print(new_key)
        data = self.hmac.hmac_update(new_key, msg)

        return data

    def verify_sign(self, key, data, msg):
        new_key = sha256(key).hexdigest()
        self.hmac.hmac_verify(new_key, data, msg)

a = client('localhost', 50000)
