import random
import sqlite3
import os
os.system("title KeyboardTrial")
from functools import lru_cache

# from english_words import get_english_words_set
# import nltk
from nltk.corpus import wordnet as wn

from rich.text import Text

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, Label
from textual.containers import Grid
from textual import events

from models import ThisRun, ThisTurn

@lru_cache(maxsize=1)
def _cached_words():
    return [
        w for w in wn.all_lemma_names()
        if 4 <= len(w) <= 12 and "_" not in w and w.isalpha()
    ]

def get_word():
    words = _cached_words()
    return random.choice(words)

def get_definitions(word: str):
    synsets = wn.synsets(word)[:5]
    definitions = [s.definition() for s in synsets]
    return definitions

def accuracy_color(accuracy: float) -> str:
    """
    Returns a color from red → yellow → green for accuracy 0–100%.
    """
    accuracy = max(0, min(100, accuracy))  # clamp 0–100
    if accuracy <= 50:
        r, g = 255, int(255 * accuracy / 50)
    else:
        r = int(255 * (100 - accuracy) / 50)
        g = 255
    # clamp just in case
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    return f"#{r:02x}{g:02x}00"

class WordGameApp(App):
    CSS_PATH = "style.tcss"

    def __init__(self):
        super().__init__()
        self.game_run = ThisRun("player1")
        self.turn_counter = 0
        self.current_turn = None

    def compose(self):
        yield Header()

        # yield Static("""Hello World!\nPress "q" to exit""")
        self.grid = Grid(id="grid")
        
        self.history_panel = Static("No history yet", id="history")
        self.history_panel.border_title = "[cyan]History[/cyan]"

        self.score_panel = Static("Score: 0", id="score", markup=True)
        self.score_panel.border_title = "[cyan]Score[/cyan]"

        self.current_panel = Static("Word: \nInput: ", id="current")
        
        self.input_box = Input(placeholder="Type here and press Enter...", id="input_box")
        self.input_box.focus()

        yield self.grid
        
        yield self.input_box

        # yield Footer()

    async def on_key(self, event: events.Key):
        # if event.key == "q":  # just press 'q' instead of Ctrl-Q
        #     self.exit()
        if event.key == "escape":  # user presses Esc
            self.input_box.blur()
    
    async def on_mount(self):
        self.start_turn()
        self.grid.mount(self.history_panel)
        self.grid.mount(self.score_panel)
        self.grid.mount(self.current_panel)

    def start_turn(self):
        self.turn_counter += 1
        self.current_panel.border_title = f"[cyan]Turn {self.turn_counter}[/cyan]"
        self.current_turn = ThisTurn(self.turn_counter)
        self.current_turn.word_to_match = get_word()
        self.update_panels()
    
    def update_panels(self):
        # History panel (last 10)
        history_lines = []

        for turn_counter, w_match, colored, plus, minus in self.game_run.word_history[-50:]:
            history_lines.insert(0, f"[gray][{turn_counter}][/gray] {w_match} {colored} [green][{plus}][/green] [red][{minus}][/red]")

        history_text = "\n".join(history_lines) if history_lines else "No history yet"
        self.history_panel.update(history_text)

        total_letter_submitted = self.game_run.plus_score + (self.game_run.minus_score * -1)
        accuracy = (self.game_run.plus_score / total_letter_submitted * 100) if total_letter_submitted > 0 else 0
        color = accuracy_color(accuracy)

        # Score panel
        # score_text = (
        #     f"[green]+{self.game_run.plus_score}[/green] [red]{self.game_run.minus_score}[/red]\n"
        #     f"Accuracy: [{color}]{accuracy:.3f}%[/]\n"
        #     f"Total: {self.game_run.total_score}"
        # )
        # self.score_panel.update(score_text)

        score_text = Text()
        score_text.append(f"+{self.game_run.plus_score} ", style="green")
        score_text.append(f"{self.game_run.minus_score}\n", style="red")
        score_text.append("Accuracy: ")
        score_text.append(f"{accuracy:.2f}%\n", style=color)
        score_text.append(f"Total: {self.game_run.total_score}")

        self.score_panel.update(score_text)

        # Current turn panel
        # input_preview = self.current_turn.user_input or ""
        defs = get_definitions(self.current_turn.word_to_match)
        defs_text = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(defs))
        current_text = f"[gray]Definitions:[/gray]\n{defs_text}\n\n[gray]Word:[/gray] [white]{self.current_turn.word_to_match}[/white]"
        self.current_panel.update(current_text)

    async def on_input_submitted(self, message: Input.Submitted):
        self.current_turn.user_input = message.value.lower().strip()
        self.calculate_turn_score()
        self.update_total_score()
        self.game_run.word_history.append((
            self.turn_counter,
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
    # Run the game with error handling
    try:
        WordGameApp().run()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")