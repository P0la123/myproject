import sqlite3, random
import os
from classes import QuizSession, Result
from flask import Flask, render_template, request, session, redirect #request- handles form data, redirect- sends user to another page
from datetime import datetime
from zoneinfo import ZoneInfo
                                                                                                                                        
app = Flask(__name__)
app.secret_key = "my_secret_key" #used to secure sessions
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE = os.path.join(BASE_DIR, "database.db")

def init_db():
    connection = sqlite3.connect(DATABASE)
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        result_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        quiz_id INTEGER NOT NULL,
        quiz_type TEXT NOT NULL,
        score INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        date_completed TIMESTAMP DEFAULT (datetime('now', 'localtime'))
        )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shared_quizzes (
        share_id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        shared_with_user_id INTEGER NOT NULL
        )
    """)
    
    

    connection.commit()
    connection.close()

def save_result(user_id, quiz_id, quiz_type, score, total_questions):

    date_completed = datetime.now(
        ZoneInfo("Europe/Warsaw")
    ).strftime("%Y-%m-%d %H:%M:%S")

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO results
        (user_id, quiz_id, quiz_type, score, total_questions, date_completed)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            quiz_id,
            quiz_type,
            score,
            total_questions,
            date_completed
        )
    )

    connection.commit()
    connection.close()

@app.route("/users")
def users():
    connection = sqlite3.connect(DATABASE)
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

        connection = sqlite3.connect(DATABASE)
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

        connection = sqlite3.connect(DATABASE)
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

        connection = sqlite3.connect(DATABASE)
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

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            quizzes.quiz_id,
            quizzes.quiz_name,
            quizzes.user_id
        FROM quizzes
        WHERE quizzes.user_id = ?

        OR quizzes.quiz_id IN (
            SELECT quiz_id
            FROM shared_quizzes
            WHERE shared_with_user_id = ?
        )

        ORDER BY quizzes.quiz_id DESC
        """,
        (session["user_id"], session["user_id"])
    )

    quizzes = cursor.fetchall()

    connection.close()

    return render_template("library.html", quizzes=quizzes)


@app.route("/edit_quiz/<int:quiz_id>")
def edit_quiz(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # Check that the logged-in user owns this quiz
    cursor.execute(
        """
        SELECT quiz_name
        FROM quizzes
        WHERE quiz_id = ? AND user_id = ?
        """,
        (quiz_id, session["user_id"])
    )

    quiz = cursor.fetchone()

    if not quiz:
        connection.close()
        return redirect("/library")

    quiz_name = quiz[0]

    cursor.execute(
        """
        SELECT word_id, term, definition
        FROM vocabulary
        WHERE quiz_id = ?
        """,
        (quiz_id,)
    )

    words = cursor.fetchall()

    connection.close()

    return render_template(
        "edit_quiz.html",
        words=words,
        quiz_id=quiz_id,
        quiz_name=quiz_name
    )


@app.route("/delete_word/<int:word_id>", methods=["POST"])
def delete_word(word_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # Find the word's quiz, but only if the logged-in user owns it
    cursor.execute(
        """
        SELECT vocabulary.quiz_id
        FROM vocabulary
        JOIN quizzes
        ON vocabulary.quiz_id = quizzes.quiz_id
        WHERE vocabulary.word_id = ?
        AND quizzes.user_id = ?
        """,
        (word_id, session["user_id"])
    )

    word = cursor.fetchone()

    if not word:
        connection.close()
        return redirect("/library")

    quiz_id = word[0]

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

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # Find the word only if it belongs to a quiz owned by this user
    cursor.execute(
        """
        SELECT vocabulary.word_id,
               vocabulary.quiz_id,
               vocabulary.term,
               vocabulary.definition
        FROM vocabulary
        JOIN quizzes
        ON vocabulary.quiz_id = quizzes.quiz_id
        WHERE vocabulary.word_id = ?
        AND quizzes.user_id = ?
        """,
        (word_id, session["user_id"])
    )

    word = cursor.fetchone()

    if not word:
        connection.close()
        return redirect("/library")

    quiz_id = word[1]

    if request.method == "POST":

        term = request.form["term"]
        definition = request.form["definition"]

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

    connection.close()

    return render_template("edit_word.html", word=word)



@app.route("/add_word/<int:quiz_id>", methods=["GET", "POST"])
def add_word(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # Check that the logged-in user owns this quiz
    cursor.execute(
        """
        SELECT quiz_id
        FROM quizzes
        WHERE quiz_id = ? AND user_id = ?
        """,
        (quiz_id, session["user_id"])
    )

    quiz = cursor.fetchone()

    if not quiz:
        connection.close()
        return redirect("/library")

    if request.method == "POST":

        terms = request.form.getlist("term")
        definitions = request.form.getlist("definition")

        for i in range(len(terms)):
            cursor.execute(
                """
                INSERT INTO vocabulary (quiz_id, term, definition)
                VALUES (?, ?, ?)
                """,
                (quiz_id, terms[i], definitions[i])
            )

        connection.commit()
        connection.close()

        return redirect(f"/edit_quiz/{quiz_id}")

    connection.close()

    return render_template("add_word.html", quiz_id=quiz_id)


@app.route("/written_quiz/<int:quiz_id>", methods=["GET", "POST"])
def written_quiz(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "GET":

        connection = sqlite3.connect(DATABASE)
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
        random.shuffle(words)

        connection.close()

        session["quiz_words"] = words
        session["current_question"] = 0
        session["score"] = 0
        session["incorrect_word_ids"] = []
        session["feedback"] = []
        session["result_saved"] = False

    if request.method == "POST":

        words = session["quiz_words"]
        current_question = session["current_question"]

        word = words[current_question]

        word_id = word[0]
        term = word[1]
        correct_definition = word[2]

        user_answer = request.form["answer"]

        if user_answer.strip().lower() == correct_definition.strip().lower():
            session["score"] += 1
            session["feedback"].append(
                (term, user_answer, correct_definition, "Correct")
            )
        else:
            session["incorrect_word_ids"].append(word_id)
            session["feedback"].append(
                (term, user_answer, correct_definition, "Incorrect")
            )

        session["current_question"] += 1

    words = session["quiz_words"]
    current_question = session["current_question"]

    if current_question >= len(words):

        if not session.get("result_saved", False):

            save_result(
                session["user_id"],
                quiz_id,
                "written",
                session["score"],
                len(words)
            )

            session["results_saved"] = True

            return render_template(
                "quiz_result.html",
                score=session["score"],
                total_questions=len(words),
                feedback=session["feedback"],
                quiz_id=quiz_id,
                quiz_type="written"
            )

    word = words[current_question]

    return render_template(
        "written_quiz.html",
        word=word,
        question_number=current_question + 1,
        total_questions=len(words),
        quiz_id=quiz_id
    )

@app.route("/repeat_incorrect_written/<int:quiz_id>", methods=["GET", "POST"])
def repeat_incorrect_written(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    # START repeating incorrect questions
    if request.method == "GET":

        incorrect_ids = session.get("incorrect_word_ids", [])

        if not incorrect_ids:
            return redirect(f"/written_quiz/{quiz_id}")

        connection = sqlite3.connect(DATABASE)
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
        random.shuffle(words)

        connection.close()

        session["quiz_words"] = words
        session["current_question"] = 0
        session["score"] = 0
        session["feedback"] = []

    # CHECK repeated answer
    if request.method == "POST":

        words = session["quiz_words"]
        current_question = session["current_question"]

        word = words[current_question]

        word_id = word[0]
        term = word[1]
        correct_definition = word[2]

        user_answer = request.form["answer"]

        if user_answer.strip().lower() == correct_definition.strip().lower():

            session["score"] += 1

            session["feedback"].append(
                (term, user_answer, correct_definition, "Correct")
            )

            # remove from incorrect list if now correct
            if word_id in session["incorrect_word_ids"]:
                session["incorrect_word_ids"].remove(word_id)

        else:

            session["feedback"].append(
                (term, user_answer, correct_definition, "Incorrect")
            )

        session["current_question"] += 1

    words = session["quiz_words"]
    current_question = session["current_question"]

    if current_question >= len(words):

        return render_template(
            "quiz_result.html",
            score=session["score"],
            total_questions=len(words),
            feedback=session["feedback"],
            quiz_id=quiz_id,
            quiz_type="written"
        )

    word = words[current_question]

    return render_template(
        "written_quiz.html",
        word=word,
        question_number=current_question + 1,
        total_questions=len(words),
        quiz_id=quiz_id
    )

@app.route("/multiple_choice_quiz/<int:quiz_id>", methods=["GET", "POST"])
def multiple_choice_quiz(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "GET":

        connection = sqlite3.connect(DATABASE)
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
        random.shuffle(words)

        questions = []

        for word in words:
            word_id = word[0]
            term = word[1]
            correct_definition = word[2]

            wrong_options = []

            for other_word in words:
                if other_word[0] != word_id:
                    wrong_options.append(other_word[2])

            wrong_options = random.sample(
                wrong_options,
                min(3, len(wrong_options))
            )

            options = wrong_options + [correct_definition]
            random.shuffle(options)

            questions.append(
                (word_id, term, correct_definition, options)
            )

        connection.close()

        session["mc_questions"] = questions
        session["current_question"] = 0
        session["score"] = 0
        session["feedback"] = []
        session["incorrect_word_ids"] = []
        session["result_saved"] = False

    if request.method == "POST":

        questions = session["mc_questions"]
        current_question = session["current_question"]

        question = questions[current_question]

        word_id = question[0]
        term = question[1]
        correct_definition = question[2]

        user_answer = request.form["answer"]

        if user_answer == correct_definition:
            session["score"] += 1

            session["feedback"].append(
                (term, user_answer, correct_definition, "Correct")
            )

        else:
            session["incorrect_word_ids"].append(word_id)

            session["feedback"].append(
                (term, user_answer, correct_definition, "Incorrect")
            )

        session["current_question"] += 1

    questions = session["mc_questions"]
    current_question = session["current_question"]

    if current_question >= len(questions):

        if not session.get("result_saved", False):

            save_result(
                session["user_id"],
                quiz_id,
                "multiple_choice",
                session["score"],
                len(questions)
            )

            session["result_saved"] = True


            return render_template(
                "quiz_result.html",
                score=session["score"],
                total_questions=len(questions),
                feedback=session["feedback"],
                quiz_id=quiz_id,
                quiz_type="multiple_choice"
            )

    question = questions[current_question]

    return render_template(
        "multiple_choice_quiz.html",
        question=question,
        question_number=current_question + 1,
        total_questions=len(questions),
        quiz_id=quiz_id
    )

@app.route("/repeat_incorrect_mc/<int:quiz_id>", methods=["GET", "POST"])
def repeat_incorrect_mc(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "GET":

        incorrect_ids = session.get("incorrect_word_ids", [])

        if not incorrect_ids:
            return redirect(f"/multiple_choice_quiz/{quiz_id}")

        connection = sqlite3.connect(DATABASE)
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

        cursor.execute(
            """
            SELECT word_id, term, definition
            FROM vocabulary
            WHERE quiz_id = ?
            """,
            (quiz_id,)
        )

        all_words = cursor.fetchall()

        connection.close()

        random.shuffle(words)

        questions = []

        for word in words:
            word_id = word[0]
            term = word[1]
            correct_definition = word[2]

            wrong_options = []

            for other_word in all_words:
                if other_word[0] != word_id:
                    wrong_options.append(other_word[2])

            wrong_options = random.sample(
                wrong_options,
                min(3, len(wrong_options))
            )

            options = wrong_options + [correct_definition]
            random.shuffle(options)

            questions.append(
                (word_id, term, correct_definition, options)
            )

        session["mc_questions"] = questions
        session["current_question"] = 0
        session["score"] = 0
        session["feedback"] = []

    if request.method == "POST":

        questions = session["mc_questions"]
        current_question = session["current_question"]

        question = questions[current_question]

        word_id = question[0]
        term = question[1]
        correct_definition = question[2]

        user_answer = request.form["answer"]

        if user_answer == correct_definition:

            session["score"] += 1

            session["feedback"].append(
                (term, user_answer, correct_definition, "Correct")
            )

            if word_id in session["incorrect_word_ids"]:
                session["incorrect_word_ids"].remove(word_id)

        else:

            session["feedback"].append(
                (term, user_answer, correct_definition, "Incorrect")
            )

        session["current_question"] += 1

    questions = session["mc_questions"]
    current_question = session["current_question"]

    if current_question >= len(questions):

        return render_template(
            "quiz_result.html",
            score=session["score"],
            total_questions=len(questions),
            feedback=session["feedback"],
            quiz_id=quiz_id,
            quiz_type="multiple_choice"
        )

    question = questions[current_question]

    return render_template(
        "multiple_choice_quiz.html",
        question=question,
        question_number=current_question + 1,
        total_questions=len(questions),
        quiz_id=quiz_id
    )

@app.route("/repeat_incorrect/<quiz_type>/<int:quiz_id>")
def repeat_incorrect_choice(quiz_type, quiz_id):

    if quiz_type == "written":
        return redirect(f"/repeat_incorrect_written/{quiz_id}")

    elif quiz_type == "multiple_choice":
        return redirect(f"/repeat_incorrect_mc/{quiz_id}")

    return redirect("/library")

@app.route("/results")
def results():

    if "user_id" not in session:
        return redirect("/login")

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT quizzes.quiz_name,
               results.quiz_type,
               results.score,
               results.total_questions,
               results.date_completed
        FROM results
        JOIN quizzes
        ON results.quiz_id = quizzes.quiz_id
        WHERE results.user_id = ?
        ORDER BY results.result_id DESC
        """,
        (session["user_id"],)
    )

    results = cursor.fetchall()

    connection.close()

    return render_template(
        "results.html",
        results=results
    )

@app.route("/flashcards/<int:quiz_id>")
def flashcards(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = sqlite3.connect(DATABASE)
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

    connection.close()

    random.shuffle(words)

    session["flashcard_words"] = words
    session["flashcard_position"] = 0
    session["difficult_words"] = []

    return redirect(f"/flashcard/{quiz_id}")


@app.route("/flashcard/<int:quiz_id>")
def flashcard(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    words = session["flashcard_words"]
    position = session["flashcard_position"]

    if position >= len(words):
        return redirect(f"/flashcards_finished/{quiz_id}")

    word = words[position]

    return render_template(
        "flashcards.html",
        word=word,
        card_number=position + 1,
        total_cards=len(words),
        quiz_id=quiz_id
    )


@app.route("/flashcard_answer/<int:quiz_id>/<answer>")
def flashcard_answer(quiz_id, answer):

    if "user_id" not in session:
        return redirect("/login")

    words = session["flashcard_words"]
    position = session["flashcard_position"]

    word = words[position]
    word_id = word[0]

    if answer == "dont_know":

        difficult_words = session["difficult_words"]

        if word_id not in difficult_words:
            difficult_words.append(word_id)

        session["difficult_words"] = difficult_words

    session["flashcard_position"] += 1

    return redirect(f"/flashcard/{quiz_id}")


@app.route("/flashcards_finished/<int:quiz_id>")
def flashcards_finished(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    total_cards = len(session["flashcard_words"])
    difficult_cards = len(session["difficult_words"])
    known_cards = total_cards - difficult_cards

    return render_template(
        "flashcards_finished.html",
        quiz_id=quiz_id,
        total_cards=total_cards,
        known_cards=known_cards,
        difficult_cards=difficult_cards
    )


@app.route("/repeat_difficult/<int:quiz_id>")
def repeat_difficult(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    difficult_ids = session.get("difficult_words", [])

    if not difficult_ids:
        return redirect(f"/flashcards/{quiz_id}")

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    placeholders = ",".join(["?"] * len(difficult_ids))

    cursor.execute(
        f"""
        SELECT word_id, term, definition
        FROM vocabulary
        WHERE word_id IN ({placeholders})
        """,
        difficult_ids
    )

    words = cursor.fetchall()

    connection.close()

    random.shuffle(words)

    session["flashcard_words"] = words
    session["flashcard_position"] = 0
    session["difficult_words"] = []

    return redirect(f"/flashcard/{quiz_id}")


@app.route("/share_quiz/<int:quiz_id>", methods=["GET", "POST"])
def share_quiz(quiz_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = sqlite3.connect(DATABASE)
    cursor = connection.cursor()

    # Get the quiz and check that it belongs to the logged-in user
    cursor.execute(
        """
        SELECT quiz_name
        FROM quizzes
        WHERE quiz_id = ? AND user_id = ?
        """,
        (quiz_id, session["user_id"])
    )

    quiz = cursor.fetchone()

    if not quiz:
        connection.close()
        return redirect("/library")

    message = None

    if request.method == "POST":

        username = request.form["username"]

        # Find the user
        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE username = ?
            """,
            (username,)
        )

        user = cursor.fetchone()

        if not user:
            message = "User not found."

        else:
            shared_with_user_id = user[0]

            # Do not allow sharing with yourself
            if shared_with_user_id == session["user_id"]:
                message = "You cannot share a quiz with yourself."

            else:
                # Check if the quiz has already been shared with this user
                cursor.execute(
                    """
                    SELECT share_id
                    FROM shared_quizzes
                    WHERE quiz_id = ? AND shared_with_user_id = ?
                    """,
                    (quiz_id, shared_with_user_id)
                )

                existing_share = cursor.fetchone()

                if existing_share:
                    message = "This quiz has already been shared with this user."

                else:
                    cursor.execute(
                        """
                        INSERT INTO shared_quizzes
                        (quiz_id, shared_with_user_id)
                        VALUES (?, ?)
                        """,
                        (quiz_id, shared_with_user_id)
                    )

                    connection.commit()

                    message = "Quiz shared successfully."

    connection.close()

    return render_template(
        "share_quiz.html",
        quiz_id=quiz_id,
        quiz_name=quiz[0],
        message=message
    )

if __name__ == "__main__":
    init_db()
    app.run(debug=True)