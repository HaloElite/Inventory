# Entry point -> Imports the flask app from the app/ pöackage and runs it
from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)