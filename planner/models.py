from django.db import models
from datetime import date


class Subject(models.Model):
    name = models.CharField(max_length=100)
    exam_date = models.DateField()
    difficulty = models.CharField(
        max_length=10,
        choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
        default='medium'
    )
    syllabus = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (Exam: {self.exam_date})"


class StudyPlan(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Plan generated on {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class StudyTask(models.Model):
    study_plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='tasks')
    date = models.DateField()
    task_description = models.TextField()
    why_important = models.TextField(blank=True, default='')
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.date} - {self.subject.name}"


class DailyRecommendation(models.Model):
    date = models.DateField(default=date.today)
    recommendation_text = models.TextField()
    adjusted_tasks = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recommendation for {self.date}"


class Quiz(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes')
    topic = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quiz: {self.subject.name} - {self.topic or 'General'}"


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')])
    explanation = models.TextField()

    def __str__(self):
        return self.question_text[:50]


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField()
    total_questions = models.IntegerField(default=3)
    attempted_at = models.DateTimeField(auto_now_add=True)
    user_answers = models.JSONField()  # e.g., {"1": "A", "2": "C"}
    feedback = models.TextField()

    def __str__(self):
        return f"Attempt on {self.quiz} - Score: {self.score}/{self.total_questions}"
