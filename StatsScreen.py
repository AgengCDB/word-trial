from datetime import datetime
import sqlite3

from textual.screen import Screen
from textual.widgets import Button, DataTable, Header

from initial_function import conn_db

class StatsScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Pop screen")]

    def compose(self):
        yield Header()

        self.stats_table = DataTable()
        self.stats_table.add_columns(
            "Run ID",
            "Total Words",
            "Total Letters",
            "Plus",
            "Minus",
            "Score",
            "Finished"
        )
        self.stats_table.border_title = "[cyan]Run History[/cyan]"
        self.stats_table.styles.border = ("round", "white")
        self.stats_table.styles.height = "1fr"  # scroll if too many rows

        yield self.stats_table

    async def on_mount(self) -> None:
        """Load stats from DB when the screen is shown."""
        conn = conn_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM scores
            ORDER BY run_id DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            run_finished = (
                datetime.fromisoformat(row["run_finished"]).strftime("%Y-%m-%d %H:%M")
                if row["run_finished"] else "N/A"
            )

            self.stats_table.add_row(
                str(row["run_id"]),
                str(row["total_word"]),
                str(row["total_letter"]),
                f"[green]{row['total_plus_score']}[/green]",
                f"[red]{row['total_minus_score']}[/red]",
                str(row["total_score"]),
                run_finished,
            )