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
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.events import Key

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
            "btn_exit_game_screen": lambda:self.exit_from_game_screen_to_play_screen()
        }

        for i in range(10):
            actions[f"save_slot_{i}"] = lambda slot=i: self.push_game_screen(save_id=slot)
            actions[f'btn_del_save_{i}'] = lambda slot=i: self.del_this_save(save_id=slot)

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

    def exit_from_game_screen_to_play_screen(self):
        self.pop_screen()              
        self.pop_screen()
        self.push_screen(PlayScreen()) # push a fresh one
    
    def del_this_save(self, save_id):
        conn = conn_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("UPDATE saves SET run_id = ? WHERE id = ?", (None, save_id))
        conn.commit()
        self.pop_screen()              # remove current PlayScreen
        self.push_screen(PlayScreen())

    def __init__(self):
        super().__init__()
        self.game_run = ThisRun("dummy")
        self.game_turn = ThisTurn("dummy")

class HomeScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Header()

        self.v_scrl_home = VerticalScroll(
            Button("Play", variant="success", classes="btns_home", id="btn_home_play"),
            Button("Settings", variant="warning", classes="btns_home", id="btn_home_settings"),
            Button("Quit", variant="error", classes="btns_home", id="btn_home_quit"),
            id="v_scrl_home"
        )
        self.v_scrl_home.styles.align = ("left", "top")

        yield self.v_scrl_home

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
                static = Static("Empty save")
                btn_load = Button("New", id=f"save_slot_{default_id}", classes="btns_save_slot")
                btn_del = Button("Delete", variant="error", id=f"btn_del_save_{default_id}", disabled=True)
            else:
                if slot_last_saved:
                    last_saved_str = datetime.fromisoformat(slot_last_saved).strftime("%Y-%m-%d %H:%M")
                else:
                    last_saved_str = "unknown"
                label = f"Saves {slot_run_id}\nlast saved: {last_saved_str}"
                static = Static(label)
                btn_load = Button("Load", variant="success", id=f"save_slot_{default_id}", classes="btns_save_slot")
                btn_del = Button("Delete", variant="error", id=f"btn_del_save_{default_id}")    

            row = Horizontal(
                static,
                btn_load,
                btn_del,
                classes="save_row"
            )

            static.styles.width = "auto"
            static.styles.margin = (0, 2, 0, 0)

            btn_load.styles.margin = (0, 2, 0, 0)

            row.styles.width = "1fr"
            row.styles.border = ('round', 'gray')
            row.border_title = f"Slot {default_id}"
            row.styles.border_title_color = "cyan"
            row.styles.height = "auto"
            row.styles.padding = (0, 1, 0, 1)

            buttons.append(row)

        self.v_scrl_play = VerticalScroll(*buttons, id="v_scrl_play")
        self.v_scrl_play.styles.overflow_y = "scroll"
        yield self.v_scrl_play
    
class GameScreen(Screen):
    def __init__(self, game_run: ThisRun, game_turn: ThisTurn):
        super().__init__()
        self.game_run = game_run
        self.game_turn = game_turn

    def compose(self):
        yield Header()
        
        self.main_grid = Grid(id="grid")
        yield self.main_grid
        
        self.input_box = Input(placeholder="Type here and press Enter...", id="input_box")
        # self.input_box.styles.margin = (1, 0, 0, 0)
        self.input_box.focus()

        yield self.input_box
        
        return super().compose()
    
    async def on_mount(self):
        self.validate_turns()

        self.main_grid.styles.grid_size_rows = 1
        self.main_grid.styles.grid_size_columns = 2
        self.main_grid.styles.grid_columns = "1fr 7fr"
        self.main_grid.styles.grid_rows = "auto"
        # self.main_grid.styles.margin = (0, 0, 0, 2)

        # child grids
        self.right_grid = Grid(id="right_grid")
        self.right_grid.styles.border = ('round', 'gray')
        self.right_grid.styles.margin = (0, 0, 2, 0)

        self.left_grid = Grid(id="left_grid")
        self.left_grid.styles.border = ('round', 'gray')
        self.left_grid.styles.margin = (0, 0, 2, 0)

        await self.main_grid.mount(self.left_grid, self.right_grid)

        self.btn_save_and_exit = Button("Exit", variant="error", id='btn_exit_game_screen')
        self.btn_save_and_exit.styles.margin = (1, 1)

        await self.left_grid.mount(self.btn_save_and_exit)

        # configure right grid: stack score, table, current
        self.right_grid.styles.grid_size_rows = 3
        self.right_grid.styles.grid_rows = "auto 1fr auto"

        self.turns_table = DataTable()
        self.turns_table.add_columns("ID", "Word", "Input", "Plus", "Minus")
        self.turns_table.border_title = "[cyan]History[/cyan]"
        self.turns_table.styles.border = ('round', 'white')

        self.score_panel = Static("Score: 0", id="score", markup=True)
        self.score_panel.border_title = "[cyan]Score[/cyan]"
        self.score_panel.styles.border = ('round', 'white')

        self.current_panel = Static("Word: \nInput: ", id="current")
        self.current_panel.styles.border = ('round', 'white')
        await self.right_grid.mount(self.turns_table, self.score_panel, self.current_panel)
        
    async def on_key(self, event: Key):
        if event.key == "escape":  # user presses Esc
            self.input_box.blur()

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