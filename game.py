from deck_utils import Deck,Player

class Game:
    def __init__(self,max_players):
        self.deck = Deck()
        print("Deck created \n",self.deck)
        self.max_players = max_players
        self.nplayers = 0
        self.players = []
        self.player_index = 0
        self.init_distribution = True
        self.next_action="play"
        self.started = False
        self.all_ready_to_play = False
        #----------added-------------
        self.s_deck = []
        self.tiles = []
        self.all_hand_pieces = 0

    def checkDeadLock(self):
        return all([ player.nopiece for player in self.players ])

    def allPlayersWithPieces(self):
        return all([p.num_pieces == p.pieces_per_player for p in self.players])

    def currentPlayer(self):
        return self.players[self.player_index]

    def nextPlayer(self):
        self.player_index +=1
        if self.player_index == self.max_players:
            self.player_index = 0
        return self.players[self.player_index]

    def addPlayer(self,name,socket,pieces):
        self.nplayers+=1
        assert  self.max_players>=self.nplayers
        player = Player(name,socket,pieces)
        print(player)
        self.players.append(player)
        return player

    def hasHost(self):
        return len(self.players)>0

    def hasPlayer(self,name):
        for player in self.players:
            if name == player.name:
                return True
        return False

    def getPlayer(self,name):
        for player in self.players:
            if player.start_hand != []:
                print("Mão não vazia")
            # if name == player.name:
            #     print("HAND: " + str(player.hand))
            #     print("HAND2: " + str(player.hand2))
            #     input("Inside player")
            #     return player
        return False

    def isFull(self):
        return self.nplayers == self.max_players    

    def toJson(self):
        msg = {"next_player":self.players[self.player_index].name ,"nplayers":self.nplayers
            ,"next_action":self.next_action, "npieces": self.deck.npieces, "pieces_per_player": self.deck.pieces_per_player
            ,"in_table": self.deck.in_table, "deck": self.s_deck}
        #msg.update(self.deck.toJson())
        return msg