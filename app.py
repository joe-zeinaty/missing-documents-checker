from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "<h1>Missing Documents Checker</h1><p>The app is running.</p>"


if __name__ == "__main__":
    app.run()