import click
import sqlite3
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        
    return g.db


def close_db(e=None):
    if e:
        print("An exception occurred:", e)
    db = g.pop("db", None)
    
    if db is not None:
        db.close()


# Init the db
def init_db():
    db = get_db()
    db.executescript("""
        DROP TABLE IF EXISTS inventory;

        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            condition TEXT NOT NULL CHECK(condition IN ('new', 'used', 'damaged')) DEFAULT 'new',
            category TEXT NOT NULL DEFAULT 'general',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            image TEXT DEFAULT 'static/images/ghost.svg'
        );
    """)
    db.commit()

@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("Initialized the database.")