import sqlite3
from flask import Flask, render_template, request, session, redirect #request- handles form data, redirect- sends user to another page
                                                                                                                                        
app = Flask(__name__)
app.secret_key = "my_secret_key" #used to secure sessions

def init_db():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quizzes (
        quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_name TEXT NOT NULL,
        user_id INTEGER NOT NULL 
        )
    """) #each quiz belonds to a user_id

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vocabulary (
        word_id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        term TEXT NOT NULL,
        definition TEXT NOT NULL
        )
    """) #storing words inside the quiz

    connection.commit()
    connection.close()

@app.route("/users")
def users():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM users")
    data = cursor.fetchall()

    connection.close()

    return str(data) #not secure?

@app.route("/")
def home():
    return render_template("index.html") #loading homepage

@app.route("/register", methods=["GET", "POST"]) #GET - shows registration form, POST - gets data from form
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        connection = sqlite3.connect("database.db")
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )

        connection.commit()
        connection.close()

        return "User registered successfully!"

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        connection = sqlite3.connect("database.db")
        cursor = connection.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        ) #check if users exist

        user = cursor.fetchone() #get a matching user
        connection.close()

        if user:
            session["user_id"] = user[0]
            session["username"] = user[1] #storing user info in session
            return redirect("/dashboard")
        else:
            return "Invalid username or password"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login") #only logged in users can access the page

    return render_template("dashboard.html", username=session["username"])

@app.route("/create", methods=["GET", "POST"])
def create():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        quiz_name = request.form["quiz_name"]
        term = request.form["term"]
        definition = request.form["definition"]
        action = request.form["action"] #add or finish

        connection = sqlite3.connect("database.db")
        cursor = connection.cursor()

        # Get or create quiz
        cursor.execute(
            "SELECT quiz_id FROM quizzes WHERE quiz_name = ? AND user_id = ?",
            (quiz_name, session["user_id"])
        )
        quiz = cursor.fetchone()

        if quiz:
            quiz_id = quiz[0]
        else:
            cursor.execute(
                "INSERT INTO quizzes (quiz_name, user_id) VALUES (?, ?)",
                (quiz_name, session["user_id"])
            )
            quiz_id = cursor.lastrowid

        if action == "add":
            cursor.execute(
                "INSERT INTO vocabulary (quiz_id, term, definition) VALUES (?, ?, ?)",
                (quiz_id, term, definition)
            ) #saving words
            connection.commit()
            connection.close()

            return redirect("/create")  #reloads the page to add more words - need to be fixed!!!

        elif action == "finish":
            connection.commit()
            connection.close()

            return redirect("/dashboard")

    return render_template("create.html")





# @app.route("/register")
# def register():
#     return "Register Page"

# @app.route("/login")
# def login():
#     return "Login Page"

# @app.route("/logout")
# def logout():
#     return "Logout Page"

# @app.route("/add")
# def add():
#     return "Add Vocabulary Page"

# @app.route("/manage")
# def manage():
#     return "Manage Vocabulary Page"

# @app.route("/quiz")
# def quiz():
#     return "Quiz Page"

# @app.route("/results")
# def results():
#     return "Results Page"

if __name__ == "__main__":
    init_db()
    app.run(debug=True)