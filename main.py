from datetime import datetime
from nltk.corpus import wordnet as wn
import os
os.system("title WordTrial v1.2.0")
import sqlite3

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Header, Static
from textual.containers import Horizontal, VerticalScroll

from models import ThisRun, ThisTurn

from initial_function import init_db, conn_db
init_db()

from GameScreen import GameScreen
from StatsScreen import StatsScreen

class WordTrial(App):
    CSS_PATH = "style.tcss"

    def on_mount(self) -> None:
        self.install_screen(HomeScreen(), name="home")
        self.push_screen("home")
    
    async def on_button_pressed(self, event: Button.Pressed):
        actions = {
            "btn_home_play": lambda: self.push_screen(PlayScreen()),
            "btn_home_quit": lambda: self.exit(),
            "btn_exit_game_screen": lambda:self.exit_from_game_screen_to_play_screen(),
            "btn_home_stats": lambda: self.push_screen(StatsScreen())
        }

        for i in range(10):
            actions[f"save_slot_{i}"] = lambda slot=i: self.push_game_screen(save_id=slot)
            actions[f'btn_del_save_{i}'] = lambda slot=i: self.end_this_save(save_id=slot)

        action = actions.get(event.button.id)
        if action:
            action()

    def push_game_screen(self, save_id):
        conn = conn_db()
        self.game_run.reset()
        self.game_turn.reset()

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
            self.game_run.id = run_id
            
            cursor.execute("UPDATE saves SET run_id = ? WHERE id = ?", (run_id, save_id))
            conn.commit()
        else:
            self.game_run.id = save_row['run_id']
        self.push_screen(GameScreen(game_run=self.game_run, game_turn=self.game_turn))

    def exit_from_game_screen_to_play_screen(self):
        self.game_turn.reset()
        self.game_run.reset()
        self.pop_screen()              
        self.pop_screen()
        self.push_screen(PlayScreen()) # push a fresh one
    
    def end_this_save(self, save_id):
        conn = conn_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM saves WHERE id = ?", (save_id, ))
        row_saves = cursor.fetchone()
        run_id = row_saves['run_id']

        
        cursor.execute("SELECT * FROM turns WHERE run_id = ?", (run_id,))
        all_turns = cursor.fetchall()

        total_word = 0
        total_letter = 0
        total_plus_score = 0
        total_minus_score = 0
        
        if not all_turns:
            pass
        else:
            for i in all_turns:
                total_word += 1
                total_letter += len(i['user_input'])
                total_plus_score += i['plus_score']
                total_minus_score += i['minus_score']
        
        total_score = total_plus_score + total_minus_score

        cursor.execute("""
            INSERT INTO scores (
                run_id, 
                total_word, 
                total_letter, 
                total_plus_score, 
                total_minus_score, 
                total_score, 
                run_finished)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", (
                run_id,
                total_word,
                total_letter,
                total_plus_score, 
                total_minus_score,
                total_score,
                datetime.now().isoformat(timespec="seconds"),
            )
        )
        
        cursor.execute("""
            UPDATE saves 
            SET 
                run_id = ?, 
                last_saved = ? 
            WHERE id = ?""", (
                None, 
                None, 
                save_id
            )
        )

        conn.commit()
        conn.close()
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
            Button("Stats", variant="primary", classes="btns_home", id="btn_home_stats"),
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
                static = Static("Empty save")
                btn_load = Button("New", id=f"save_slot_{default_id}", classes="btns_save_slot")
                btn_del = Button("Delete", variant="error", id=f"btn_del_save_{default_id}", disabled=True)
            else:
                if slot_last_saved:
                    last_saved_str = datetime.fromisoformat(slot_last_saved).strftime("%Y-%m-%d %H:%M")
                else:
                    last_saved_str = "unknown"
                static = Static(f"Saves {slot_run_id}\nlast saved: {last_saved_str}")
                btn_load = Button("Load", variant="success", id=f"save_slot_{default_id}", classes="btns_save_slot")
                btn_del = Button("End", variant="error", id=f"btn_del_save_{default_id}")    

            row = Horizontal(
                static,
                btn_load,
                btn_del,
                classes="save_row"
            )

            static.styles.width = "auto"
            static.styles.margin = (0, 2, 0, 0)

            btn_load.styles.margin = (0, 2, 0, 0)

            row.border_title = f"Slot {default_id}"
            row.styles.width = "1fr"
            row.styles.border = ('round', 'gray')
            row.styles.border_title_color = "cyan"
            row.styles.height = "auto"
            row.styles.padding = (0, 1, 0, 1)

            buttons.append(row)

        self.v_scrl_play = VerticalScroll(*buttons, id="v_scrl_play")
        self.v_scrl_play.styles.overflow_y = "scroll"
        yield self.v_scrl_play

if __name__ == "__main__":
    # Run the game with error handling
    try:
        WordTrial().run()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")