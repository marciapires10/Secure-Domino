from deck_utils import *
from authentication import authSerialNumber, writeCSV
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


# Main socket code from https://docs.python.org/3/howto/sockets.html
# Select with sockets from https://steelkiwi.com/blog/working-tcp-sockets/

dicSerialNumber = {}

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
        #---------------------------------


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
                    time.sleep(0.1)
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

    def send_all(self, msg, socket=None):
        if socket is None:
            socket=self.server

        for sock in self.inputs:
            if sock is not self.server and sock is not socket :
                self.message_queue[sock].put(pickle.dumps(msg))
                if sock not in self.outputs:
                    self.outputs.append(sock)
        time.sleep(0.1) #give server time to send all messages
    
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
            if action == "hello":
                #---------------------altered---------------------------
                msg = {"action": "login", "msg": "Welcome to the server, what will be your name?", "max_pieces": self.game.deck.pieces_per_player}
                #-------------------------------------------------------
                return pickle.dumps(msg)
            # TODO login mechanic is flawed, only nickname
            if action == "req_login":
                print("User {} requests login, with nickname {}".format(sock.getpeername(), data["msg"]))
                if not self.game.hasHost():  # There is no game for this tabla manager
                    serialNumber = authSerialNumber()  #authentication initial
                    dicSerialNumber[data["msg"]] = serialNumber

                    self.game.addPlayer(data["msg"],sock,self.game.deck.pieces_per_player) # Adding host
                    msg = {"action": "you_host", "msg": Colors.BRed+"You are the host of the game"+Colors.Color_Off}
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
                            dicSerialNumber[data["msg"]] = serialNumber

                            self.game.addPlayer(data["msg"], sock,self.game.deck.pieces_per_player)  # Adding player
                            msg = {"action": "new_player", "msg": "New Player "+Colors.BGreen+data["msg"]+Colors.Color_Off+" registered in game",
                                   "nplayers": self.game.nplayers, "game_players": self.game.max_players}
                            print("User "+Colors.BBlue+"{}".format(data["msg"])+Colors.Color_Off+" joined the game")
                            
                            #send info to all players
                            self.send_all(msg)

                            #check if table is full
                            if self.game.isFull():
                                #---------------altered--------------------
                                players_name = [p.name for p in self.game.players]
                                print(Colors.BIPurple+"The game is Full"+Colors.Color_Off)
                                msg = {"action": "waiting_for_host", "msg": Colors.BRed+"Waiting for host to start the game"+Colors.Color_Off, "players": players_name}
                                #------------------------------------------
                                self.send_all(msg,sock)
                            return pickle.dumps(msg)
                    else:
                        msg = {"action": "disconnect", "msg": "You are already in the game"}
                        print("User {} tried to join a game he was already in".format(data["msg"]))
                        return pickle.dumps(msg)

            #-------------------altered-------------------------------------
            if action == "start_game":
                # msg = {"action": "host_start_game", "msg": Colors.BYellow+"The Host started the game"+Colors.Color_Off}
                # self.send_all(msg,sock)
                player = self.game.currentPlayer()
                self.d_players.append(player)
                msg = {"action": "scrumble", "deck": self.game.deck.ps_deck}
                self.send_to(msg, player)
                return
            #----------------------------------------------------------------
            #------------------------added-------------------------------
            if action == "scrumbled":
                if self.game.player_index == self.game.max_players-1:
                    self.game.tiles = data["deck"]
                    self.game.s_deck = data["deck"]
                    player = self.game.nextPlayer()
                    msg = {"action": "select", "deck":self.game.s_deck}
                    self.send_to(msg, player)
                    return
                else:
                    player = self.game.nextPlayer()
                    self.d_players.append(player)
                    self.d_players_idx += 1
                    msg = {"action": "scrumble", "deck": data["deck"]}
                    self.send_to(msg, player)
                    return
            if action == "selected":
                if len(self.game.s_deck) != len(data["deck"]):
                    self.game.players[self.game.player_index].n_pieces += 1
                self.game.s_deck = data["deck"]
                # hands_full = True
                # for p in self.game.players:
                #     print("player: {} hand pieces: {}".format(p.name, p.n_pieces))
                #     if p.n_pieces < p.pieces_per_player:
                #         hands_full = False
                # if hands_full:
                #     print("stock: "+str(len(self.game.deck.deck)-(self.game.deck.pieces_per_player*self.game.nplayers)))
                #     print("r stock: "+str(len(self.game.s_deck)))
                if len(self.game.s_deck) == self.game.deck_len-(self.game.deck.pieces_per_player*self.game.nplayers):
                    msg = {"action": "commitment"}
                    player = self.game.currentPlayer()
                    self.send_to(msg, player)
                    return
                else:
                    for pl in self.game.players:
                        if pl.name == data["next_player"]:
                            player = pl
                    msg = {"action": "select", "deck":self.game.s_deck}
                    self.send_to(msg, player)
                return
            if action == "commited":
                player = self.game.currentPlayer()
                player.bitcommit, player.r1 = data["bitcommit"], data["r1"]
                if self.game.player_index == self.game.nplayers-1:
                    self.p_tiles = [d for d in self.game.s_deck + self.game.tiles if d in self.game.tiles and d not in self.game.s_deck]
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
                    msg = {"action": "fill_array", "arr": self.game.deck.idx}
                    player = self.game.currentPlayer()
                    self.send_to(msg, player)
                return
            if action == "filled":
                self.game.deck.idx = data["arr"]
                if None not in [i[1] for i in data["arr"]]:
                    self.game.deck.de_anonimyze()
                    msg = {"action": "reveal_tiles", "arr": self.game.deck.idx}
                    #msg = {"action": "host_start_game", "msg": Colors.BYellow+"The Host started the game"+Colors.Color_Off}
                    self.send_all(msg,sock)
                    return pickle.dumps(msg)
                else:
                    for pl in self.game.players:
                        if pl.name == data["next_player"]:
                            player = pl
                    msg = {"action": "fill_array", "arr":self.game.deck.idx}
                    self.send_to(msg, player)
                return
            if action == "ready":
                self.ready += 1
                if self.ready >= self.game.nplayers:
                    msg = {"action": "host_start_game", "msg": Colors.BYellow+"The Host started the game"+Colors.Color_Off}
                    self.send_all(msg,sock)
                    return pickle.dumps(msg)
                return
            if action == "piece_key":
                print(data["rec"])
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
                player.updatePieces(1)
                self.send_to(msg, player)
                return
            #-------------------------------------------------------------

            if action == "ready_to_play":
                input("wait")
                msg = {"action": "host_start_game", "msg": Colors.BYellow+"The Host started the game"+Colors.Color_Off}
                self.send_all(msg,sock)
                return pickle.dumps(msg)

            if action == "get_game_propreties":
                #---------------test------------------------
                # for player in self.game.players:
                #     print("player: "+str(player.name)+" bitcommit: "+str(player.bitcommit)+" r1: "+str(player.r1))
                #-------------------------------------------
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
                            print(dicSerialNumber)
                            serialNumber = dicSerialNumber[dicSerialNumber["win"]]
                            points = dicSerialNumber["points"]
                            writeCSV(serialNumber,int(points[dicSerialNumber["win"]]))
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
                    # player.updatePieces(1)
                    # if not self.game.started:
                    #     print("player pieces ", player.num_pieces)
                    #     print("ALL-> ", self.game.allPlayersWithPieces())
                    #     self.game.nextPlayer()
                    #     if self.game.allPlayersWithPieces():
                    #         self.game.started = True
                    #         self.game.next_action = "play"
                    # msg = {"action": "rcv_game_propreties"}
                    # msg.update(self.game.toJson())
                    # self.send_all(msg,sock)

                elif action == "play_piece":
                    score = str(data["score"])
                    self.game.currentPlayer().score = score
                    next_p = self.game.nextPlayer()
                    if data["piece"]is not None:
                        player.nopiece = False
                        player.updatePieces(-1)

                        ## Check if piece is not on deck
                        try:
                            if self.check_piece_in_deck(data["piece"], self.game.deck.deck):
                                print(str(self.game.currentPlayer().name) + " is cheating.")
                            else:
                                print(str(self.game.currentPlayer().name) + " is not cheating.")
                        except:
                            print("Deck problems")


                        if data["edge"]==0:
                            self.game.deck.in_table.insert(0,data["piece"])
                        else:
                            self.game.deck.in_table.insert(len(self.game.deck.in_table),data["piece"])

                    print("player pieces ",player.num_pieces)
                    print("player "+player.name+" played "+str(data["piece"]))
                    print("in table -> " + ' '.join(map(str, self.game.deck.in_table)) + "\n")
                    print("deck -> " + ' '.join(map(str, self.game.deck.deck)) + "\n")
                    if data["win"]:
                        if player.checkifWin():
                            print(Colors.BGreen+" WINNER "+player.name+Colors.Color_Off)
                            print(Colors.BGreen+" SCORE: "+ score +Colors.Color_Off)
                            players_score = dict()
                            for p in self.game.players:
                                players_score[p.name] = p.score
                            msg = {"action": "end_game","winner":player.name, "players": players_score}
                            dicSerialNumber["win"] = player.name
                            dicSerialNumber["points"] = players_score
                    else:
                        msg = {"action": "rcv_game_propreties"}
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
    def check_piece_in_deck(self,piece,deck):
        return piece in deck


try:
    NUM_PLAYERS = int(sys.argv[1])
except:
    NUM_PLAYERS = 3
a = TableManager('localhost', 50000,NUM_PLAYERS)
