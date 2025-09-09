from functools import lru_cache
from nltk.corpus import wordnet as wn
import os
os.system("title WordTrial v1.2.0")
import random
import sqlite3

from rich.text import Text

from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Input, Static
from textual.containers import Grid, VerticalScroll
from textual.events import Key

from models import ThisRun, ThisTurn

from initial_function import conn_db

def get_definitions(word: str):
    synsets = wn.synsets(word)[:5]
    definitions = [s.definition() for s in synsets]
    return definitions

@lru_cache(maxsize=1)
def _cached_words():
    return [
        w for w in wn.all_lemma_names()
        if 4 <= len(w) <= 12 and "_" not in w and w.isalpha()
    ]

def get_word():
    words = _cached_words()
    return random.choice(words)

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


def colored_word(word_to_match, user_input):
    result = []

    longest = max(len(word_to_match), len(user_input))
    for i in range(longest):
        char_match = word_to_match[i] if i < len(word_to_match) else None
        char_input = user_input[i] if i < len(user_input) else None

        if char_input == char_match and char_input is not None:
            result.append(f"[green]{char_input}[/green]")
        else:
            wrong_char = char_input if char_input is not None else char_match
            result.append(f"[red]{wrong_char}[/red]")

    return "".join(result)

class GameScreen(Screen):
    def __init__(self, game_run: ThisRun, game_turn: ThisTurn):
        super().__init__()
        self.game_run = game_run
        self.game_turn = game_turn

    def compose(self):
        yield Header()
        
        self.main_grid = Grid(id="grid")
        self.main_grid.styles.grid_size_rows = 1
        self.main_grid.styles.grid_size_columns = 2
        self.main_grid.styles.grid_columns = "1fr 7fr"
        self.main_grid.styles.grid_rows = "auto"
        yield self.main_grid


        ########### START LEFT GRID ###########
        self.left_grid = Grid(id="left_grid")
        self.left_grid.styles.border = ('round', 'gray')
        self.left_grid.styles.margin = (0, 0, 2, 0)
        
        self.btn_save_and_exit = Button("Exit", variant="error", id='btn_exit_game_screen')
        self.btn_save_and_exit.styles.margin = (1, 1)
        ########### END LEFT GRID ###########


        ########### START RIGHT GRID ###########
        self.right_grid = Grid(id="right_grid")
        self.right_grid.styles.border = ("round", 'gray')
        self.right_grid.styles.margin = (0, 0, 2, 0)
        self.right_grid.styles.grid_size_rows = 4
        self.right_grid.styles.grid_rows = "1fr auto 5 3"

        self.turns_table = DataTable()
        self.turns_table.add_columns("ID", "Word", "Plus", "Minus", "User Input")
        self.turns_table.border_title = "[cyan]History[/cyan]"
        self.turns_table.styles.border = ('round', 'white')

        self.defs_list = Static("")

        self.defs_list_scrl = VerticalScroll(self.defs_list)
        self.defs_list_scrl.border_title = "[cyan]Definitions[/cyan]"
        self.defs_list_scrl.styles.align = ("left", "top")
        self.defs_list_scrl.styles.padding = (0, 1, 0, 1)
        self.defs_list_scrl.styles.border = ('round', 'white')

        self.score_panel = Static("Score: 0", id="score", markup=True)
        self.score_panel.border_title = "[cyan]Score[/cyan]"
        self.score_panel.styles.border = ('round', 'white')
        self.score_panel.styles.padding = (0, 1, 0, 1)
        self.score_panel.styles.content_align_vertical = "bottom"

        self.current_panel = Static("", id="current")
        self.current_panel.border_title = "[cyan]Word[/cyan]"
        self.current_panel.styles.border = ('round', 'white')
        self.current_panel.styles.padding = (0, 1, 0, 1)
        self.current_panel.styles.min_height = 3
        ########### END RIGHT GRID ###########

        
        self.input_box = Input(placeholder="Type here and press Enter...", id="input_box")
        # self.input_box.styles.margin = (1, 0, 0, 0)
        self.input_box.focus()
        
        yield self.input_box
        
        return super().compose()
    
    async def on_mount(self):
        self.validate_turns()
        await self.main_grid.mount(self.left_grid, self.right_grid)
        await self.left_grid.mount(self.btn_save_and_exit)
        await self.right_grid.mount(self.turns_table, self.defs_list_scrl, self.score_panel, self.current_panel)
        
    async def on_key(self, event: Key):
        if event.key == "escape":  # user presses Esc
            self.input_box.blur()

    def validate_turns(self):
        conn = conn_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM turns WHERE run_id = ? ORDER BY id DESC LIMIT 1",
            (self.game_run.id,)
        )
        last_turn = cursor.fetchone()

        if not last_turn:
            self.game_turn.id = 1
        else:
            self.game_turn.id = int(last_turn['id']) + 1

            cursor.execute(
                """
                SELECT 
                    SUM(plus_score) AS total_plus_score, 
                    SUM(minus_score) AS total_minus_score
                FROM turns
                WHERE run_id = ?
                """,
                (self.game_run.id,)
            )
            totals = cursor.fetchone()
            self.game_run.total_plus_score = totals['total_plus_score']
            self.game_run.total_minus_score = totals['total_minus_score']
        
        self.game_turn.word_to_match = get_word()    
        self.update_turn_history_data_table()    
        conn.close()

    
    def update_turn_history_data_table(self):
        conn = conn_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Fetch all turns for this run (latest first)
        cursor.execute("""
            SELECT * FROM turns 
            WHERE run_id = ? 
            ORDER BY run_id DESC
            """, (
                self.game_run.id,
            )
        )
        turn_history = cursor.fetchall()
        self.turns_table.clear()

        # Populate table
        if not turn_history:
            pass
        else:
            for turn in sorted(turn_history, key=lambda t: t['id'], reverse=True):
                self.turns_table.add_row(
                    str(turn["id"]),
                    turn["word_to_match"],
                    f"[green]{turn['plus_score']}[/green]",
                    f"[red]{turn['minus_score']}[/red]",
                    colored_word(turn["word_to_match"], turn["user_input"]),
                )

        score_text = Text()
        score_text.append(f"+{self.game_run.total_plus_score} ", style="green")
        score_text.append(f"{self.game_run.total_minus_score}\n", style="red")
        score_text.append("Accuracy: ")

        total_letter_submitted = self.game_run.total_plus_score + (self.game_run.total_minus_score * -1)
        accuracy = (self.game_run.total_plus_score / total_letter_submitted * 100) if total_letter_submitted > 0 else 0
        color = accuracy_color(accuracy)

        score_text.append(f"{accuracy:.2f}%\n", style=color)
        score_text.append(f"Total: {self.game_run.total_plus_score + self.game_run.total_minus_score}")

        self.score_panel.update(score_text)
        
        defs = get_definitions(self.game_turn.word_to_match)
        defs_text = "\n".join(f"{i+1}. {d}" for i, d in enumerate(defs))
        self.defs_list.update(defs_text)

        self.current_panel.update(self.game_turn.word_to_match)
        
        conn.close()
    
    def calculate_turn_score(self):
        turn = self.game_turn
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
    
    def update_total_score(self):
        turn = self.game_turn

        conn = conn_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO turns (
                run_id,
                id,
                word_to_match,
                user_input,
                plus_score,
                minus_score
            )
            VALUES (?, ?, ?, ?, ?, ?)""", (
                self.game_run.id,
                self.game_turn.id,
                self.game_turn.word_to_match,
                self.game_turn.user_input,
                self.game_turn.plus_score,
                self.game_turn.minus_score,
            ),
        )
        conn.commit()
        
        # self.game_run.total_plus_score += turn.plus_score
        # self.game_run.total_minus_score += turn.minus_score
        conn.close()
    
    async def on_input_submitted(self, message: Input.Submitted):
        self.game_turn.user_input = message.value.lower().strip()
        self.calculate_turn_score()
        self.update_total_score()
        self.game_turn.reset()

        self.input_box.value = ""
        self.input_box.focus()
        self.validate_turns()
