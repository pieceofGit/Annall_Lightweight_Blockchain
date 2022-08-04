class Round:
    def __init__(self, round=0) -> None:
        self.round = round
    
    def set_round(self, round: int):
        isinstance(round, int)
        self.round = round