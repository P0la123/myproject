class QuizSession:

    def __init__(self, quiz_id, quiz_type):
        self.quiz_id = quiz_id
        self.quiz_type = quiz_type
        self.score = 0
        self.current_question = 0
        self.incorrect_words = []

class Result:

    def __init__(self, quiz_id, score, total_questions):
        self.quiz_id = quiz_id
        self.score = score
        self.total_questions = total_questions

    def percentage(self):
        return round(
            self.score / self.total_questions * 100,
            2
        )