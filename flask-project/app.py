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

        terms = request.form.getlist("term")
        definitions = request.form.getlist("definition")

        connection = sqlite3.connect("database.db")
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO quizzes (quiz_name, user_id) VALUES (?, ?)",
            (quiz_name, session["user_id"])
        )

        quiz_id = cursor.lastrowid

        for i in range(len(terms)):
            cursor.execute(
                "INSERT INTO vocabulary (quiz_id, term, definition) VALUES (?, ?, ?)",
                (quiz_id, terms[i], definitions[i])
            )

        connection.commit()
        connection.close()

        return redirect("/dashboard")

    return render_template("create.html")

@app.route("/library")
def library():
    if "user_id" not in session:
        return redirect("/login")

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT quiz_id, quiz_name FROM quizzes WHERE user_id = ?",
        (session["user_id"],)
    )

    quizzes = cursor.fetchall()

    connection.close()

    return render_template("library.html", quizzes=quizzes)

@app.route("/written_quiz/<int:quiz_id>")
def written_quiz(quiz_id):
    if "user_id" not in session:
        return redirect("/login")

    return "Written quiz page for quiz ID: " + str(quiz_id)


@app.route("/multiple_choice_quiz/<int:quiz_id>")
def multiple_choice_quiz(quiz_id):
    if "user_id" not in session:
        return redirect("/login")

    return "Multiple choice quiz page for quiz ID: " + str(quiz_id)


@app.route("/edit_quiz/<int:quiz_id>")
def edit_quiz(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT word_id, term, definition
        FROM vocabulary
        WHERE quiz_id = ?
        """,
        (quiz_id,)
    )

    words = cursor.fetchall()

    cursor.execute(
        """
        SELECT quiz_name
        FROM quizzes
        WHERE quiz_id = ?
        """,
        (quiz_id,)
    )

    quiz_name = cursor.fetchone()[0]

    connection.close()

    return render_template(
        "edit_quiz.html",
        words=words,
        quiz_id=quiz_id,
        quiz_name=quiz_name
    )

@app.route("/delete_word/<int:word_id>")
def delete_word(word_id):

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute(
        "SELECT quiz_id FROM vocabulary WHERE word_id = ?",
        (word_id,)
    )

    quiz_id = cursor.fetchone()[0]

    cursor.execute(
        "DELETE FROM vocabulary WHERE word_id = ?",
        (word_id,)
    )

    connection.commit()
    connection.close()

    return redirect(f"/edit_quiz/{quiz_id}")








if __name__ == "__main__":
    init_db()
    app.run(debug=True)