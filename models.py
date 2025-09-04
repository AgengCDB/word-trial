class ThisRun:
    def __init__(self, name):
        self.name = name
        self.id = None
        self.total_plus_score = 0
        self.total_minus_score = 0
        self.turn_count = 0
    
    def reset(self):
        self.id = None
        self.total_plus_score = 0
        self.total_minus_score = 0
        self.turn_count = 0

class ThisTurn:
    def __init__(self, name):
        self.name = name
        self.id = None
        self.word_to_match = ""
        self.plus_score = 0
        self.minus_score = 0
        self.user_input = ""

    def reset(self):
        self.id = None
        self.word_to_match = ""
        self.plus_score = 0
        self.minus_score = 0
        self.user_input = ""
