from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

USERNAME = "admin"
PASSWORD = "1234"


@app.route("/")
def login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def do_login():

    username = request.form["username"]
    password = request.form["password"]

    if username == USERNAME and password == PASSWORD:
        return redirect(url_for("dashboard"))

    return """
    <h2>Invalid username or password</h2>
    <a href="/">Try again</a>
    """


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/health")
def health():
    return {
        "status": "OK",
        "application": "Docker Auto Login"
    }


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )