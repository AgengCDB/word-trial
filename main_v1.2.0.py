from datetime import datetime
from functools import lru_cache
from nltk.corpus import wordnet as wn
import os
os.system("title WordTrial v1.2.0")
import random
import sqlite3

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Input, Static
from textual.containers import Grid, Horizontal, VerticalScroll

from models import ThisRun, ThisTurn

from initial_function import init_db, conn_db
init_db()

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

class WordTrial(App):
    CSS_PATH = "style.tcss"

    def on_mount(self) -> None:
        self.install_screen(HomeScreen(), name="home")
        self.push_screen("home")
    
    async def on_button_pressed(self, event: Button.Pressed):
        actions = {
            "btn_home_play": lambda: self.push_screen(PlayScreen()),
            "btn_home_quit": lambda: self.exit(),
        }

        for i in range(10):
            actions[f"save_slot_{i}"] = lambda slot=i: self.push_game_screen(save_id=slot)

        action = actions.get(event.button.id)
        if action:
            action()

    def push_game_screen(self, save_id):
        conn = conn_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM saves WHERE id = ?", (save_id,))
        save_row = cursor.fetchone()

        if not save_row['run_id']:
            cursor.execute("INSERT INTO runs DEFAULT VALUES")
            run_id = cursor.lastrowid

            # Update save slot with new run_id and timestamp
            now = datetime.now().isoformat(timespec="seconds")
            cursor.execute(
                "UPDATE saves SET run_id = ?, last_saved = ? WHERE id = ?",
                (run_id, now, save_id)
            )
            conn.commit()
            self.game_run.id = save_row['run_id']
            
            cursor.execute("UPDATE saves SET run_id = ? WHERE id = ?", (run_id, save_id))
            conn.commit()
        else:
            self.game_run.id = save_row['run_id']

        self.push_screen(GameScreen(game_run=self.game_run, game_turn=self.game_turn))
    
    def __init__(self):
        super().__init__()
        self.game_run = ThisRun("dummy")
        self.game_turn = ThisTurn("dummy")

class HomeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()

        yield VerticalScroll(
            Button("Play", variant="success", classes="btns_home", id="btn_home_play"),
            Button("Settings", variant="warning", classes="btns_home", id="btn_home_settings"),
            Button("Quit", variant="error", classes="btns_home", id="btn_home_quit"),
            id="v_scrl_home"
        )

class PlayScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def compose(self):
        yield Header()

        conn = conn_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM saves")
        all_saves = cursor.fetchall()
        conn.close()

        buttons = []
        default_id = 0
        for slot in all_saves:
            default_id += 1
            slot_run_id = slot['run_id']
            slot_last_saved = slot['last_saved']

            if slot_run_id is None:
                label = f"New {default_id}"
                btn = Button(label, id=f"save_slot_{default_id}", classes="btns_save_slot")
            else:
                if slot_last_saved:
                    last_saved_str = datetime.fromisoformat(slot_last_saved).strftime("%Y-%m-%d %H:%M")
                else:
                    last_saved_str = None
                label = f"Saves {slot_run_id}\nlast saved: {last_saved_str}"
                btn = Button(label, variant="success", id=f"save_slot_{default_id}", classes="btns_save_slot")

            buttons.append(btn)
        yield VerticalScroll(*buttons, id="v_scrl_play")

        return super().compose()
    
class GameScreen (Screen):
    def __init__(self, game_run: ThisRun, game_turn: ThisTurn):
        super().__init__()
        self.game_run = game_run
        self.game_turn = game_turn

    def compose(self):
        yield Header()

        self.grid = Grid(id="grid")

        self.turns_table = DataTable()
        self.turns_table.add_columns("ID", "Word", "Input", "Plus", "Minus")

        self.score_panel = Static("Score: 0", id="score", markup=True)
        self.score_panel.border_title = "[cyan]Score[/cyan]"

        self.current_panel = Static("Word: \nInput: ", id="current")

        yield self.grid
        
        self.input_box = Input(placeholder="Type here and press Enter...", id="input_box")
        self.input_box.focus()

        yield self.input_box
        
        return super().compose()
    
    async def on_mount(self):
        self.validate_turns()
        self.grid.mount(self.turns_table)
        self.grid.mount(self.score_panel)
        self.grid.mount(self.current_panel)

    def validate_turns(self):
        conn = conn_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT run_id FROM turns WHERE run_id = ? ORDER BY run_id DESC LIMIT 1",
            (self.game_run.id,)
        )
        last_turn = cursor.fetchone()
        conn.close()

        if not last_turn:
            self.game_turn.id = 1
        else:
            self.game_turn.id = int(last_turn['id']) + 1
        
        self.game_turn.word_to_match = get_word()
    
    def update_turn_history_data_table(self):
        conn = conn_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Fetch all turns for this run (latest first)
        cursor.execute(
            "SELECT id, word_to_match, user_input, plus_score, minus_score "
            "FROM turns WHERE run_id = ? ORDER BY id DESC",
            (self.game_run.id,)
        )
        turn_history = cursor.fetchall()
        conn.close()

        # Populate table
        for turn in turn_history:
            self.turns_table.add_row(
                str(turn["id"]),
                turn["word_to_match"],
                turn["user_input"],
                str(turn["plus_score"]),
                str(turn["minus_score"])
            )
        pass

if __name__ == "__main__":
    # Run the game with error handling
    try:
        WordTrial().run()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")