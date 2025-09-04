import random
from english_words import get_english_words_set
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input
from textual.containers import Grid

from models import ThisRun, ThisTurn

WORDS = [w for w in get_english_words_set(['web2'], lower=True) if 5 <= len(w) <= 10]

def get_word():
    return random.choice(WORDS)

class WordGameApp(App):
    CSS = """
    Grid {
        grid-columns: 3;
        grid-rows: 1;
    }
    Panel {
        padding: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.game_run = ThisRun("player1")
        self.turn_counter = 0
        self.current_turn = None

    def compose(self) -> ComposeResult:
        yield Header()
        self.grid = Grid()
        self.history_panel = Static("No history yet", id="history")
        self.score_panel = Static("Score: 0", id="score")
        self.current_panel = Static("Word: \nInput: ", id="current")
        self.input_box = Input(placeholder="Type here and press Enter...", id="input_box")
        self.input_box.focus()
        yield self.grid
        yield self.input_box
        yield Footer()
        self.grid.mount(self.history_panel, self.score_panel, self.current_panel)

    async def on_mount(self):
        self.start_turn()
        self.grid.mount(self.history_panel)
        self.grid.mount(self.score_panel)
        self.grid.mount(self.current_panel)

    def start_turn(self):
        self.turn_counter += 1
        self.current_turn = ThisTurn(self.turn_counter)
        self.current_turn.word_to_match = get_word()
        self.update_panels()

    def update_panels(self):
        # History panel (last 10)
        history_lines = []
        for w_match, colored, plus, minus in self.game_run.word_history[-10:]:
            history_lines.append(f"{w_match} {colored} [+{plus}] [-{minus}]")
        history_text = "\n".join(history_lines) if history_lines else "No history yet"
        self.history_panel.update(history_text)

        # Score panel
        score_text = f"[green]+{self.game_run.plus_score}[/green] [red]{self.game_run.minus_score}[/red]\nTotal: {self.game_run.total_score}"
        self.score_panel.update(score_text)

        # Current turn panel
        input_preview = self.current_turn.user_input or ""
        current_text = f"Word: {self.current_turn.word_to_match}\nInput: {input_preview}"
        self.current_panel.update(current_text)

    async def on_input_submitted(self, message: Input.Submitted):
        self.current_turn.user_input = message.value
        self.calculate_turn_score()
        self.update_total_score()
        self.game_run.word_history.append((
            self.current_turn.word_to_match,
            self.current_turn.colored_word,
            self.current_turn.plus_score,
            self.current_turn.minus_score
        ))
        self.current_turn.reset()
        self.update_panels()
        self.input_box.value = ""
        self.input_box.focus()
        self.start_turn()

    def calculate_turn_score(self):
        turn = self.current_turn
        turn.plus_score = 0
        turn.minus_score = 0
        result = []

        longest = max(len(turn.word_to_match), len(turn.user_input))
        for i in range(longest):
            char_match = turn.word_to_match[i] if i < len(turn.word_to_match) else None
            char_input = turn.user_input[i] if i < len(turn.user_input) else None

            if char_input == char_match and char_input is not None:
                result.append(f"[green]{char_input}[/green]")
                turn.plus_score += 1
            else:
                wrong_char = char_input if char_input is not None else char_match
                result.append(f"[red]{wrong_char}[/red]")
                turn.minus_score -= 1

        turn.total_score = turn.plus_score + turn.minus_score
        turn.colored_word = "".join(result)

    def update_total_score(self):
        turn = self.current_turn
        self.game_run.plus_score += turn.plus_score
        self.game_run.minus_score += turn.minus_score
        self.game_run.total_score = self.game_run.plus_score + self.game_run.minus_score

if __name__ == "__main__":
    WordGameApp().run()
