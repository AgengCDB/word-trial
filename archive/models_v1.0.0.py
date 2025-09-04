class ThisRun:
    def __init__(self, name):
        self.name = name
        self.word_history = []
        self.total_score = 0
        self.plus_score = 0
        self.minus_score = 0
        self.turn_count = 0
    
    def reset(self):
        self.word_history = []
        self.total_score = 0
        self.plus_score = 0
        self.minus_score = 0

class ThisTurn:
    def __init__(self, name):
        self.name = name
        self.word_to_match = ""
        self.plus_score = 0
        self.minus_score = 0
        self.total_score = 0
        self.user_input = ""
        self.colored_word = ""

    def reset(self):
        self.word_to_match = ""
        self.plus_score = 0
        self.minus_score = 0
        self.total_score = 0
        self.user_input = ""
        self.colored_word = ""