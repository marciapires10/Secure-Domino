from deck_utils import *
from authentication import authSerialNumber, lerPublicKeyOfCard, writeCSV
import socket
import select
import sys
import json
import base64
import os
import queue
import pickle
import random
from game import Game
import signal
import Colors
import time
from security import DiffieHellman, SymmetricCipher, HMAC
import string
import random

from Crypto.Cipher import AES
from hashlib import sha256

# Main socket code from https://docs.python.org/3/howto/sockets.html
# Select with sockets from https://steelkiwi.com/blog/working-tcp-sockets/


class TableManager:

    def __init__(self, host, port,nplayers=4):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setblocking(False)  # non-blocking for select
        self.server.bind((host, port))  # binding to localhost on 50000
        self.server.listen()
        self.game = Game(nplayers)  # the game associated to this table manager
        self.nplayers=nplayers
        print("Nplayers = ",nplayers)
        #disconnecting players when CTRL + C is pressed
        signal.signal(signal.SIGINT, self.signal_handler)
        #signal.pause()
        self.agreement_players = dict()
        print("Server is On")

        # configuration for select()
        self.inputs = [self.server]  # sockets where we read
        self.outputs = []  # sockets where we write
        self.message_queue = {}  # queue of messages
        #--------------added--------------
        self.d_players = []
        self.d_players_idx = 0
        self.p_key_map = []
        self.p_tiles = []
        self.deciphered = 0
        self.ready = 0
        self.tmp_k_map = []
        self.authenticated = 0
        self.dicSerialNumber = {}
        self.challenge = ""
        self.pickup_keys = []
        #---------------------------------
        self.a = []
        self.symC = SymmetricCipher()
        self.hmac = HMAC()

        while self.inputs:
            readable, writeable, exceptional = select.select(self.inputs, self.outputs, self.inputs)
            for sock in readable:
                if sock is self.server:  # this is our main socket and we are receiving a new client
                    connection, ip_address = sock.accept()
                    print(Colors.BRed+"A new client connected -> "+Colors.BGreen+"{}".format(ip_address)+Colors.Color_Off)
                    connection.setblocking(False)
                    self.inputs.append(connection)  # add client to our input list
                    self.message_queue[connection] = queue.Queue()

                else:  # We are receiving data from a client socket
                    data = sock.recv(524288)
                    if data:
                        to_send = self.handle_action(data, sock)
                        if to_send != None:
                            self.message_queue[sock].put(to_send)  # add our response to the queue
                            if sock not in self.outputs:
                                self.outputs.append(sock)  # add this socket to the writeable sockets
                    else:
                        if sock in self.outputs:
                            self.outputs.remove(sock)
                        self.inputs.remove(sock)
                        sock.close()
                        del self.message_queue[sock]

            for sock in writeable:
                try:
                    to_send = self.message_queue[sock].get_nowait()
                except queue.Empty:  # Nothing more to send to this client
                    self.outputs.remove(sock)
                else:
                    sock.send(to_send)  # Send the info

            for sock in exceptional:  # if a socket is here, it has gone wrong and we must delete everything
                self.inputs.remove(sock)
                if sock in self.outputs:
                    self.outputs.remove(sock)
                sock.close()
                del self.message_queue[sock]


    def random_token_generator(size=16, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def send_all(self, msg, socket=None):
        if socket is None:
            socket=self.server

        for sock in self.inputs:
            if sock is not self.server and sock is not socket :
                self.message_queue[sock].put(pickle.dumps(msg))
                if sock not in self.outputs:
                    self.outputs.append(sock)
        time.sleep(0.1) #give server time to send all messages
    
    def send_to_socket(self, msg, socket):
        self.message_queue[socket].put(pickle.dumps(msg))
        if socket not in self.outputs:
            self.outputs.append(socket)

    def send_to(self, msg, player):
        if player.socket is None:
            socket=self.server
        print("send to: " + str(player.name) + " action: " + msg["action"])
        self.message_queue[player.socket].put(pickle.dumps(msg))
        if player.socket not in self.outputs:
            self.outputs.append(player.socket)

    def send_host(self,msg):
        self.message_queue[self.game.host_sock].put(pickle.dumps(msg))
        if self.game.host_sock not in self.outputs:
            self.outputs.append(self.game.host_sock)

    def handle_action(self, data, sock):
        data = pickle.loads(data)
        action = data["action"]
        print("\n"+action)
        if data:
            if action == "authentication":
                print("Trying Authentication... (creating challenge)")
                self.challenge = bytes(''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(16)), 'utf-8')
                msg = {"action": "authentication_2", "msg": self.challenge}
                self.send_to_socket(msg,sock)
                return

            if action == "authentication_3":
                try:
                    signature = data["msg"]
                    lerPublicKeyOfCard(signature, self.challenge)
                    self.challenge = ""
                    self.authenticated += 1
                    print("Autenticado com SUCESSO no Servidor!!")
                    msg = {"action": "login", "msg": "Welcome to the server, what will be your name?", "authentication":True ,"max_pieces": self.game.deck.pieces_per_player}
                except:
                    print("Falhou a Autenticação no Servidor")
                    msg = {"action": "login", "msg": "Welcome to the server, what will be your name?", "authentication":False ,"max_pieces": self.game.deck.pieces_per_player}

                return pickle.dumps(msg)


            # if action == "hello":
            #     #---------------------altered---------------------------
            #     msg = {"action": "login", "msg": "Welcome to the server, what will be your name?", "max_pieces": self.game.deck.pieces_per_player}
            #     #-------------------------------------------------------
            #     return pickle.dumps(msg)
            
            # TODO login mechanic is flawed, only nickname       
            if action == "req_login":
                print("User {} requests login, with nickname {}".format(sock.getpeername(), data["msg"]))
                if not self.game.hasHost():  # There is no game for this tabla manager
                    serialNumber = authSerialNumber()  #authentication initial
                    self.dicSerialNumber[data["msg"]] = serialNumber

                    player = self.game.addPlayer(data["msg"],sock,self.game.deck.pieces_per_player) # Adding host
                    dh = DiffieHellman(103079, 7)
                    self.a.append([player,dh])
                    public_key = dh.public_key

                    msg = {"action": "you_host", "msg": Colors.BRed+"You are the host of the game"+Colors.Color_Off, "public_key": public_key}
                    dh.getSharedKey(data["public_key"])
                    print("User "+Colors.BBlue+"{}".format(data["msg"])+Colors.Color_Off+" has created a game, he is the first to join")
                    return pickle.dumps(msg)
                else:
                    if not self.game.hasPlayer(data["msg"]):
                        if self.game.isFull():
                            msg = {"action": "full", "msg": "This table is full"}
                            print("User {} tried to join a full game".format(data["msg"]))
                            return pickle.dumps(msg)
                        else:
                            serialNumber = authSerialNumber()  #authentication initial
                            self.dicSerialNumber[data["msg"]] = serialNumber

                            player = self.game.addPlayer(data["msg"],sock,self.game.deck.pieces_per_player) # Adding host
                            dh = DiffieHellman(103079, 7)
                            self.a.append([player,dh])
                            public_key = dh.public_key
                            msg = {"action": "new_player", "msg": "New Player "+Colors.BGreen+data["msg"]+Colors.Color_Off+" registered in game",
                                   "nplayers": self.game.nplayers, "game_players": self.game.max_players, "public_key": public_key}
                            print("User "+Colors.BBlue+"{}".format(data["msg"])+Colors.Color_Off+" joined the game")
                            
                            dh.getSharedKey(data["public_key"])

                            #send info to all players
                            self.send_to(msg, player)

                            #check if table is full
                            if self.game.isFull():
                                #---------------altered--------------------
                                players_name = [p.name for p in self.game.players]
                                print(players_name)
                                print(Colors.BIPurple+"The game is Full"+Colors.Color_Off)
                                msg = {"action": "start_sessions", "players": players_name}
                                #------------------------------------------
                                self.send_all(msg,sock)
                            return pickle.dumps(msg)
                    else:
                        msg = {"action": "disconnect", "msg": "You are already in the game"}
                        print("User {} tried to join a game he was already in".format(data["msg"]))
                        return pickle.dumps(msg)

            #-------------------altered-------------------------------------
            if action == "player_sessions":
                for p in self.game.players:
                    if p.socket == sock:
                        msg = {"action": "share_key"}
                        self.send_to(msg, p)
                        return 
            if action == "send_dh":
                sk = [p[1].shared_key for p in self.a if p[0].name == data["from"]][0]
                verify = self.verify_sign(sk, data["sign"], data["key"])
                key = self.symC.decrypt_message(data["key"], sk)
                for pl in self.game.players:
                    if pl.name == data["send_to"]:
                        sk = [p[1].shared_key for p in self.a if pl.name == p[0].name][0]
                        key = self.symC.encrypt_message(key, sk)
                        key_sign = self.hmac_sign(key, sk)
                        msg = {"action": "get_key", "from": data["from"], "key": key, "sign": key_sign}
                        self.send_to(msg, pl)
                        return
            if action == "done":
                sk = [p[1].shared_key for p in self.a if p[0].name == data["from"]][0]
                verify = self.verify_sign(sk, data["sign"], data["key"])
                key = self.symC.decrypt_message(data["key"], sk)
                for pl in self.game.players:
                    if pl.name == data["send_to"]:
                        sk = [p[1].shared_key for p in self.a if pl.name == p[0].name][0]
                        key = self.symC.encrypt_message(key, sk)
                        key_sign = self.hmac_sign(key, sk)
                        msg = {"action": "dh_response", "from": data["from"], "key": key, "sign": key_sign}
                        self.send_to(msg, pl)
                        return
            if action == "sent":
                if self.game.player_index == self.game.nplayers-1:
                    player = self.game.nextPlayer()
                    msg = {"action": "host_start", "msg": Colors.BRed+"Waiting for host to start the game"+Colors.Color_Off}
                    self.send_to(msg, player)
                    return
                player = self.game.nextPlayer()
                msg = {"action": "share_key"}
                self.send_to(msg, player)
                return 
                
            if action == "start_game":
                # msg = {"action": "host_start_game", "msg": Colors.BYellow+"The Host started the game"+Colors.Color_Off}
                # self.send_all(msg,sock)
                player = self.game.currentPlayer()
                self.d_players.append(player)
                # for p in self.a:
                #     if p[0] == player:
                #         sk = p[1].shared_key
                
                sk = [p[1].shared_key for p in self.a if player.name == p[0].name][0]
                deck = self.symC.encrypt_message(pickle.dumps(self.game.deck.ps_deck), sk)
                deck_sign = self.hmac_sign(deck, sk)
                msg = {"action": "scrumble", "deck": deck, "sign": deck_sign}
                self.send_to(msg, player)
                return
            #----------------------------------------------------------------
            #------------------------added-------------------------------
            if action == "scrumbled":
                pl = [p.name for p in self.game.players if p.socket == sock][0]
                sk = [p[1].shared_key for p in self.a if p[0].name == pl][0]
                verify = self.verify_sign(sk, data["sign"], data["deck"])
                deck = self.symC.decrypt_message(data["deck"], sk)
                if self.game.player_index == self.game.max_players-1:
                    self.game.tiles = pickle.loads(deck)
                    self.game.s_deck = pickle.loads(deck)
                    player = self.game.nextPlayer()
                    msg = {"action": "select", "deck":self.game.s_deck, "from": "tm"}
                    self.send_to(msg, player)
                    return
                else:
                    player = self.game.nextPlayer()
                    self.d_players.append(player)
                    self.d_players_idx += 1
                    sk = [p[1].shared_key for p in self.a if player.name == p[0].name][0]
                    deck = self.symC.encrypt_message(deck, sk)
                    deck_sign = self.hmac_sign(deck, sk)
                    msg = {"action": "scrumble", "deck": deck, "sign": deck_sign}
                    self.send_to(msg, player)
                    return
            if action == "selected":
                if data["update"] == True:
                    self.game.players[self.game.player_index].n_pieces += 1
                    self.game.all_hand_pieces += 1
                if self.game.all_hand_pieces == self.game.deck.pieces_per_player*self.game.nplayers:
                    msg = {"action": "s_deck"}
                    player = [p for p in self.game.players if p.socket == sock][0]
                    self.send_to(msg, player)
                    return
                else:
                    for pl in self.game.players:
                        if pl.name == data["next_player"]:
                            player = pl
                    msg = {"action": "select", "deck":data["deck"], "from": data["from"], "sign": data["sign"]}
                    self.send_to(msg, player)
                return
            if action == "s_deck":
                self.game.s_deck = data["deck"]
                msg = {"action": "commitment"}
                player = self.game.currentPlayer()
                self.send_to(msg, player)
                return
            if action == "commited":
                player = self.game.currentPlayer()
                player.bitcommit, player.r1 = data["bitcommit"], data["r1"]
                if self.game.player_index == self.game.nplayers-1:
                    self.p_tiles = [d for d in self.game.tiles if d in self.game.tiles and d not in self.game.s_deck]
                    player = self.d_players[self.d_players_idx]
                    msg = {"action": "key_map", "key_map": self.p_key_map, "tiles": self.p_tiles}
                    self.send_to(msg, player)
                else:
                    player = self.game.nextPlayer()
                    msg = {"action": "commitment"}
                    self.send_to(msg, player)
                return
            if action == "key_map":
                self.p_key_map.append(data["key_map"])
                if self.d_players_idx == 0:
                    self.d_players_idx = len(self.d_players)-1
                    self.game.deck.decipher_all(self.p_tiles, self.p_key_map)
                    msg = {"action": "decipher", "key_map": self.p_key_map}
                    self.send_all(msg,sock)
                    return pickle.dumps(msg)
                else:
                    self.d_players_idx -= 1
                    player = self.d_players[self.d_players_idx]
                    msg = {"action": "key_map", "key_map": self.p_key_map, "tiles": self.p_tiles}
                    self.send_to(msg, player)
                    return
            if action == "deciphered":
                self.deciphered += 1
                if self.deciphered == self.game.max_players:
                    msg = {"action": "fill_array", "arr": self.game.deck.idx, "from": "tm"}
                    player = self.game.currentPlayer()
                    self.send_to(msg, player)
                return
            if action == "filled":
                if data["full"] == True:
                    player = [p for p in self.game.players if p.socket == sock][0]
                    msg = {"action": "array"}
                    self.send_to(msg, player)
                else:
                    for pl in self.game.players:
                        if pl.name == data["next_player"]:
                            player = pl
                    msg = {"action": "fill_array", "arr": data["arr"], "from": data["from"], "sign": data["sign"]}
                    self.send_to(msg, player)
                return
            if action == "array":
                self.game.deck.idx = data["arr"]
                self.game.deck.de_anonimyze()
                msg = {"action": "reveal_tiles", "arr": self.game.deck.idx}
                self.send_all(msg,sock)
                return pickle.dumps(msg)
            if action == "ready":
                self.ready += 1
                if self.ready >= self.game.nplayers:
                    msg = {"action": "host_start_game", "msg": Colors.BYellow+"The Host started the game"+Colors.Color_Off}
                    self.send_all(msg,sock)
                    return pickle.dumps(msg)
                return
            if action == "piece_key":
                self.p_key_map[int(data["rec"])].update(data["key_map"])
                self.tmp_k_map.append(data["key_map"])
                if self.d_players_idx == 0:
                    self.d_players_idx = len(self.d_players)-1
                    self.game.deck.decipher_all([data["piece"]], self.p_key_map)
                    msg = {"action": "decipher_piece", "key_map": self.p_key_map}
                    self.tmp_k_map = []
                    player = self.game.currentPlayer()
                    self.send_to(msg, player)
                    return
                else:
                    self.d_players_idx -= 1
                    player = self.d_players[self.d_players_idx]
                    msg = {"action": "piece_key", "piece": data["piece"], "key_map": self.p_key_map, "rec": data["rec"]}
                    self.send_to(msg, player)
                    return
            if action == "de_anonymize":
                piece = self.game.deck.deck2[int(data["idx"])]
                msg = {"action": "de-anonymized", "piece": piece}
                player = self.game.currentPlayer()
                self.pickup_keys.append([player.name, piece])
                player.n_pieces += 1
                self.send_to(msg, player)
                return
            #-------------------------------------------------------------

            if action == "ready_to_play":
                msg = {"action": "host_start_game", "msg": "ready to play"}
                self.send_all(msg,sock)
                return pickle.dumps(msg)

            if action == "get_game_propreties":
                msg = {"action": "rcv_game_propreties"}
                msg.update(self.game.toJson())
                return pickle.dumps(msg)

            elif action == "agreement":
                    self.agreement_players[data["player"]] = data["choice"]
                    if len(self.agreement_players) >= len(self.game.players):
                        for player in self.agreement_players:
                            if self.agreement_players[player] == "n":
                                print("Not aproved")
                                msg = {"action": "agreement_result", "agreement_result": "Not Aproved"}
                                self.send_all(msg,sock)
                                return pickle.dumps(msg)  
                        print("Result Aproved")
                        msg = {"action": "agreement_result", "agreement_result": "Aproved"} 
                        self.send_all(msg,sock)
                        try:
                            serialNumber = self.dicSerialNumber[self.dicSerialNumber["win"]]
                            points = self.dicSerialNumber["points"]
                            writeCSV(serialNumber,int(points[self.dicSerialNumber["win"]]))
                        except:
                            print("Nobody win points because it's a draw")
                        
                    else:
                        print("Aproving")
                        msg = {"action": "agreement_result", "agreement_result": "Waiting for Response."}
                    return pickle.dumps(msg)

            player = self.game.currentPlayer()
            #check if the request is from a valid player
            if  sock == player.socket:
                if action == "get_piece":
                    self.game.s_deck=data["deck"]
                    print(player.name)
                    player = self.d_players[self.d_players_idx]
                    msg = {"action": "piece_key", "piece": data["piece"], "key_map": self.p_key_map, "rec": -1}
                    self.send_to(msg, player)
                    return

                elif action == "play_piece":
                    score = str(data["score"])
                    self.game.currentPlayer().score = score
                    
                    if data["piece"]is not None:
                        player.nopiece = False
                        player.n_pieces += 1

                        ## Check if piece is not on deck
                        try:
                            if self.check_piece_in_deck(data["piece"]):
                                print(str(player.name) + " is cheating. Rolling back play")
                                msg = {"action": "rcv_game_propreties"}
                                msg.update(self.game.toJson())
                                next_action = {"next_action":"play"}
                                msg.update(next_action)
                                self.send_all(msg, sock)
                                return pickle.dumps(msg)
                            else:
                                print(str(player.name) + " is not cheating.")
                        except Exception as e:
                            print(e)

                        self.game.nextPlayer()
                        if data["edge"]==0:
                            self.game.deck.in_table.insert(0,data["piece"])
                        else:
                            self.game.deck.in_table.insert(len(self.game.deck.in_table),data["piece"])

                    print("player pieces ",player.num_pieces)
                    print("player "+player.name+" played "+str(data["piece"]))
                    print("in table -> " + ' '.join(map(str, self.game.deck.in_table)) + "\n")
                    print("deck -> " + ' '.join(map(str, self.game.deck.deck)) + "\n")
                    print(data["win"])
                    if data["win"]:
                        if player.checkifWin():
                            print(Colors.BGreen+" WINNER "+player.name+Colors.Color_Off)
                            print(Colors.BGreen+" SCORE: "+ score +Colors.Color_Off)
                            players_score = dict()
                            for p in self.game.players:
                                players_score[p.name] = p.score
                            msg = {"action": "end_game","winner":player.name, "players": players_score, "piece_played": data["piece"], "previous_player": player.name}
                            self.dicSerialNumber["win"] = player.name
                            self.dicSerialNumber["points"] = players_score
                    else:
                        msg = {"action": "rcv_game_propreties", "piece_played": data["piece"], "previous_player": player.name}
                    msg.update(self.game.toJson())
                    self.send_all(msg,sock)
                #no pieces to pick
                elif action == "pass_play":
                    score = str(data["score"])
                    self.game.currentPlayer().score = score
                    self.game.nextPlayer()
                    #If the player passed the previous move
                    if player.nopiece:
                        players_score = dict()
                        for p in self.game.players:
                            players_score[p.name] = p.score
                        msg = {"action": "end_game", "winner": Colors.BYellow+"TIE"+Colors.Color_Off, "players": players_score}
                    #Update the variable nopiece so that the server can know if the player has passed the previous move
                    else:
                        print("No piece")
                        player.nopiece = True
                        msg = {"action": "rcv_game_propreties"}
                        msg.update(self.game.toJson())

                    self.send_all(msg, sock)
                    return pickle.dumps(msg)
                elif action == "report_cheating":
                    print(str(data["player_cheating"]) + " was caught cheating.")
                    msg = {"action": "ask_value", "player": data["player_cheating"], "piece":data["piece"]}
                    self.send_all(msg, sock)
                    return pickle.dumps(msg)
            elif action == "send_values":
                    _name = data["player_cheating"]
                    _piece = data["piece"]
                    _hand = data["hand"]
                    _hand2 = data["hand2"]
                    _start_hand = data["start_hand"]
                    _r1 = data["r1"]
                    _r2 = data["r2"]
                    _bitcommit = data["bitcommit"]


                    print("Reviewing this accusation.")

                    digest = hashes.Hash(hashes.SHA256(), default_backend())
                    digest.update(str(_start_hand).encode('utf-8'))
                    digest.update(_r1)
                    digest.update(_r2)
                    _bitcommit2 = digest.finalize()
                    
                    _hand_decoded = self.game.deck.decipher_all_return(_hand2, self.p_key_map)
                    idx_decode = [p[0] for p in _hand_decoded]
                    found = False
                    if str(_bitcommit2) == str(_bitcommit):
                        print("The starting hand was not adultered.")
                        for id in idx_decode:
                            id = int(id)
                            p2 = str(_piece).split(":")[1] + ":" + str(_piece).split(":")[0]
                            if str(self.game.deck.deck2[id]) == str(_piece) or str(self.game.deck.deck2[id]) == str(p2):
                                found = True
                                break

                    if not found:
                        print("The player was cheating.")
                        msg = {"action": "end_game", "winner": Colors.BYellow+"TIE"+Colors.Color_Off}
                        self.send_all(msg, sock)
                        return pickle.dumps(msg)

                    found2 = False
                    for p in self.pickup_keys:
                        if p[1] == data["piece"]:
                            print(p[0] + " picked up piece " + p[1])
                            if p[0] == _name:
                                found2 = True
                                break

                    if not found2:
                        print("The player was cheating.")
                    else:
                        print("The player was not cheating")

                    msg = {"action": "end_game", "winner": Colors.BYellow+"TIE"+Colors.Color_Off}
                    self.send_all(msg, sock)
                    return pickle.dumps(msg)
            else:
                msg = {"action": "wait","msg":Colors.BRed+"Not Your Turn"+Colors.Color_Off}
            return pickle.dumps(msg)

    #Function to handle CTRL + C Command disconnecting all players
    def signal_handler(self,sig, frame):
        print('You pressed Ctrl+C!')
        size = len(self.inputs)-1
        msg = {"action": "disconnect", "msg": "The server disconnected you"}
        i = 1
        for sock in self.inputs:
            if sock is not self.server:
                print("Disconnecting player " + str(i) + "/" + str(size))
                sock.send(pickle.dumps(msg))
                i+=1
        print("Disconnecting Server ")
        self.server.close()
        sys.exit(0)
    
    # Cheating mechanism
    def check_piece_in_deck(self, piece):
        piece2 = piece.split(":")[1]+":"+piece.split(":")[0]
        print("Play piece: " + str(piece))
        deck_idx = None
        for i in range(len(self.game.deck.deck2)):
            if str(self.game.deck.deck2[i]) == str(piece) or str(self.game.deck.deck2[i]) == str(piece2):
                if str(piece) in self.game.deck.in_table or str(piece2) in self.game.deck.in_table:
                    return True
                deck_idx = i
                break
        if not (str(deck_idx) in [p[0] for p in self.game.deck.idx]):
            return True
    
    # Sign messages
    def hmac_sign(self, msg, key):
        new_key = sha256(key).hexdigest()
        data = self.hmac.hmac_update(new_key, msg)

        return data
        
    # Verify signature
    def verify_sign(self, key, data, msg):
        new_key = sha256(key).hexdigest()
        self.hmac.hmac_verify(new_key, data, msg)
    
try:
    NUM_PLAYERS = int(sys.argv[1])
except:
    NUM_PLAYERS = 2
a = TableManager('localhost', 50000,NUM_PLAYERS)
