import sqlite3, random
from classes import QuizSession, Result
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

@app.route("/edit_word/<int:word_id>", methods=["GET", "POST"])
def edit_word(word_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    if request.method == "POST":
        term = request.form["term"]
        definition = request.form["definition"]
        quiz_id = request.form["quiz_id"]

        cursor.execute(
            """
            UPDATE vocabulary
            SET term = ?, definition = ?
            WHERE word_id = ?
            """,
            (term, definition, word_id)
        )

        connection.commit()
        connection.close()

        return redirect(f"/edit_quiz/{quiz_id}")

    cursor.execute(
        """
        SELECT word_id, quiz_id, term, definition
        FROM vocabulary
        WHERE word_id = ?
        """,
        (word_id,)
    )

    word = cursor.fetchone()

    connection.close()

    return render_template("edit_word.html", word=word)


@app.route("/add_word/<int:quiz_id>", methods=["GET", "POST"])
def add_word(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        terms = request.form.getlist("term")
        definitions = request.form.getlist("definition")

        connection = sqlite3.connect("database.db")
        cursor = connection.cursor()

        for i in range(len(terms)):
            cursor.execute(
                "INSERT INTO vocabulary (quiz_id, term, definition) VALUES (?, ?, ?)",
                (quiz_id, terms[i], definitions[i])
            )

        connection.commit()
        connection.close()

        return redirect(f"/edit_quiz/{quiz_id}")

    return render_template("add_word.html", quiz_id=quiz_id)


@app.route("/written_quiz/<int:quiz_id>", methods=["GET", "POST"])
def written_quiz(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    # Get words from selected quiz
    cursor.execute(
        """
        SELECT word_id, term, definition
        FROM vocabulary
        WHERE quiz_id = ?
        """,
        (quiz_id,)
    )

    words = cursor.fetchall()

    # Randomize question order
    random.shuffle(words)

    # User submitted answers
    if request.method == "POST":

        score = 0
        incorrect_words = []
        feedback = []

        for word in words:

            word_id = word[0]
            term = word[1]
            correct_definition = word[2]

            user_answer = request.form[
                f"answer_{word_id}"
            ]

            if (
                user_answer.strip().lower()
                ==
                correct_definition.strip().lower()
            ):

                score += 1

                feedback.append(
                    (
                        term,
                        user_answer,
                        correct_definition,
                        "Correct"
                    )
                )

            else:

                incorrect_words.append(word)

                feedback.append(
                    (
                        term,
                        user_answer,
                        correct_definition,
                        "Incorrect"
                    )
                )

        connection.close()

        session["incorrect_word_ids"] = [word[0] for word in incorrect_words]

        return render_template(
            "written_result.html",
            score=score,
            total_questions=len(words),
            incorrect_words=incorrect_words,
            feedback=feedback,
            quiz_id=quiz_id
        )

    connection.close()

    return render_template(
        "written_quiz.html",
        words=words,
        quiz_id=quiz_id
    )

@app.route("/repeat_incorrect/<int:quiz_id>", methods=["GET", "POST"])
def repeat_incorrect(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    incorrect_ids = session.get("incorrect_word_ids", [])

    if not incorrect_ids:
        return redirect(f"/written_quiz/{quiz_id}")

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    placeholders = ",".join(["?"] * len(incorrect_ids))

    cursor.execute(
        f"""
        SELECT word_id, term, definition
        FROM vocabulary
        WHERE word_id IN ({placeholders})
        """,
        incorrect_ids
    )

    words = cursor.fetchall()

    if request.method == "POST":

        score = 0
        feedback = []
        new_incorrect_ids = []

        for word in words:

            word_id = word[0]
            term = word[1]
            correct_definition = word[2]

            user_answer = request.form[f"answer_{word_id}"]

            if user_answer.strip().lower() == correct_definition.strip().lower():

                score += 1

                feedback.append(
                    (
                        term,
                        user_answer,
                        correct_definition,
                        "Correct"
                    )
                )

            else:

                new_incorrect_ids.append(word_id)

                feedback.append(
                    (
                        term,
                        user_answer,
                        correct_definition,
                        "Incorrect"
                    )
                )

        session["incorrect_word_ids"] = new_incorrect_ids

        connection.close()

        return render_template(
            "written_result.html",
            score=score,
            total_questions=len(words),
            feedback=feedback,
            quiz_id=quiz_id
        )

    random.shuffle(words)

    connection.close()

    return render_template(
        "written_quiz.html",
        words=words,
        quiz_id=quiz_id
    )

if __name__ == "__main__":
    init_db()
    app.run(debug=True)