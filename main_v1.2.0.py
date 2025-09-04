from datetime import datetime
import os
os.system("title WordTrial v1.2.0")
import sqlite3

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Header, Static
from textual.containers import Horizontal, VerticalScroll

from initial_function import init_db, conn_db
init_db()



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
            actions[f"save_slot_{i}"] = lambda slot=i: self.push_game_screen(slot)

        action = actions.get(event.button.id)
        if action:
            action()

    def push_game_screen(self, saves_id):
        conn = conn_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM saves WHERE id = ?", (saves_id,))
        save_row = cursor.fetchone()

        if not save_row['run_id']:
            cursor.execute("INSERT INTO runs DEFAULT VALUES")
            conn.commit()
            run_id = cursor.lastrowid

            cursor.execute("UPDATE saves SET run_id = ? WHERE id = ?", (run_id, saves_id))
            conn.commit()

        self.push_screen(GameScreen())

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
    def compose(self):
        yield Header()
        return super().compose()

if __name__ == "__main__":
    # Run the game with error handling
    try:
        WordTrial().run()
    except Exception:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")