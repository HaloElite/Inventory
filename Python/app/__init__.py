import os
from flask import Flask
from flask_cors import CORS
from config import Config
from app.db import close_db, init_db_command

app = Flask(__name__, instance_relative_config=True, static_folder='static', static_url_path='/static')
CORS(app)

app.config.from_object(Config)

os.makedirs(app.instance_path, exist_ok=True)

app.teardown_appcontext(close_db)
app.cli.add_command(init_db_command)

from app import routes

# When do you run flask init-db?
# ✅ Typically:
# Once at the beginning (after creating the project)
# 🔁 Run it again when:
# you delete the database file (todos.db)
# you change your schema (e.g. add a column/table)
# you set up a new environment (new machine, deployment)