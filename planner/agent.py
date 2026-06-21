import os
import json
from datetime import date, timedelta
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

MODEL_NAME = "gemini-2.5-flash"
MOCK_MODE = False
_client = None


def get_client():
    """Lazily create the Gemini client so the app doesn't crash on startup.
    If the API key isn't set, sets MOCK_MODE = True."""
    global _client, MOCK_MODE
    if MOCK_MODE:
        return None
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            try:
                from decouple import config
                api_key = config("GEMINI_API_KEY", default="")
            except Exception:
                pass
        if not api_key:
            MOCK_MODE = True
            print("[WARNING] GEMINI_API_KEY is not set. Study Planner Agent is running in MOCK MODE.")
            return None
        try:
            _client = genai.Client(api_key=api_key)
        except Exception as e:
            MOCK_MODE = True
            print(f"[WARNING] Failed to initialize Gemini Client ({e}). Study Planner Agent is running in MOCK MODE.")
            return None
    return _client


# Pydantic schemas for structured Gemini outputs
class StudyTaskSchema(BaseModel):
    date: str = Field(description="Date of the task in YYYY-MM-DD format")
    subject: str = Field(description="Subject name, matching exactly one of the input subjects")
    task: str = Field(description="A short, practical study task (1-2 lines)")
    why_important: str = Field(description="Explanation of why this task is scheduled today based on difficulty and exam date")


class StudyPlanSchema(BaseModel):
    tasks: List[StudyTaskSchema] = Field(description="List of daily study tasks")


class QuizQuestionSchema(BaseModel):
    question_text: str = Field(description="The multiple-choice question text")
    option_a: str = Field(description="Option A text")
    option_b: str = Field(description="Option B text")
    option_c: str = Field(description="Option C text")
    option_d: str = Field(description="Option D text")
    correct_answer: str = Field(description="The correct option letter, must be exactly A, B, C, or D")
    explanation: str = Field(description="Explanation of why this answer is correct")


class QuizSchema(BaseModel):
    questions: List[QuizQuestionSchema] = Field(description="List of exactly 3 multiple-choice questions")


class DailyRecommendationSchema(BaseModel):
    recommendation_text: str = Field(
        description="A friendly study coach message analyzing recent completion progress, missed tasks, quiz scores, and recommending focus."
    )
    adjusted_tasks: List[str] = Field(
        description="A list of 1 to 3 specific study tasks recommended for today, adjusted based on progress and quiz weaknesses."
    )


class SuggestedTopicsSchema(BaseModel):
    topics: List[str] = Field(description="Exactly 8 to 10 specific topics or subtopics extracted from the syllabus")


def generate_study_plan(subjects):
    """
    subjects: list of dicts like
        [{"name": "Maths", "exam_date": "2026-06-20", "difficulty": "hard"}, ...]
    """
    get_client()
    
    diff_map = {"hard": 3, "medium": 2, "easy": 1}
    # Pre-sort subjects by exam date (nearest first) and difficulty (hardest first)
    sorted_subjects = sorted(
        subjects,
        key=lambda x: (x["exam_date"], -diff_map.get(x.get("difficulty", "medium"), 2))
    )

    if MOCK_MODE:
        plan = []
        today_val = date.today()
        # Parse syllabus topics for each subject
        sub_topics = {}
        for sub in sorted_subjects:
            topics = []
            if sub.get("syllabus"):
                raw_topics = [t.strip() for t in sub["syllabus"].replace("\n", ",").split(",") if t.strip()]
                topics = raw_topics
            if not topics:
                topics = ["Foundations and definitions", "Core theorems and concepts", "Practical problem-solving", "Formula review", "Mock exam practice"]
            sub_topics[sub["name"]] = topics

        # Generate 5 days of study tasks
        for i in range(5):
            curr_date = (today_val + timedelta(days=i)).isoformat()
            sub = sorted_subjects[i % len(sorted_subjects)]
            topics_list = sub_topics[sub["name"]]
            topic_index = (i // len(sorted_subjects)) % len(topics_list)
            selected_topic = topics_list[topic_index]
            
            plan.append({
                "date": curr_date,
                "subject": sub["name"],
                "task": f"Study {selected_topic} - review notes, formulas, and solve practice questions.",
                "why_important": f"Subject {sub['name']} is prioritized because it is a {sub['difficulty']} difficulty subject with exam on {sub['exam_date']}. Focusing on syllabus topic: {selected_topic}."
            })
        return plan

    today = date.today().isoformat()

    prompt = f"""
You are a helpful study planning agent for a college student.
Today's date is {today}.

Here are the subjects with their exam dates, difficulty, and full syllabus/topics, pre-prioritized (nearer exams and harder subjects prioritized):
{json.dumps(sorted_subjects, indent=2, ensure_ascii=False)}

Create a day-by-day study plan from today until the last exam date.
Guidelines:
1. Schedule study tasks for each day.
2. Prioritize harder subjects and subjects with nearer exam dates in terms of frequency and intensity.
3. For each subject, look at its full `syllabus` text. Break down this syllabus into smaller, specific daily topics and spread them logically across the available days before that subject's exam date.
4. Do NOT use generic task descriptions like "Revise unit 1" or "Read chapter 2". Instead, specify the exact topic details from the syllabus (e.g. "Revise Laplace Transform - definition and existence theorem" or "Practice Linear Algebra - matrix multiplication and eigenvalues").
5. Provide a clear, detailed `why_important` explanation for each day explaining the scheduling logic.
"""

    response = get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=StudyPlanSchema,
        )
    )

    return json.loads(response.text).get('tasks', [])


def generate_quiz(subject_name, syllabus, topic=""):
    """
    Generates 3 quick multiple-choice quiz questions for a subject/topic using Gemini.
    """
    get_client()
    
    if MOCK_MODE:
        # Determine focus concepts for mock questions
        concepts = []
        if topic:
            concepts = [f"{topic} basic structure", f"{topic} implementation", f"{topic} performance"]
        elif syllabus:
            raw = [p.strip() for p in syllabus.replace("\n", ",").split(",") if p.strip()]
            concepts = raw[:3]
        
        while len(concepts) < 3:
            concepts.append(f"General concept {len(concepts)+1}")
            
        return {
            "questions": [
                {
                    "question_text": f"Which of the following is a key definition concerning '{concepts[0]}' in the study of {subject_name}?",
                    "option_a": "The primary abstraction interface",
                    "option_b": "The secondary configuration model",
                    "option_c": "The local state variable",
                    "option_d": "The static pointer value",
                    "correct_answer": "A",
                    "explanation": f"The primary abstraction interface is standard for defining '{concepts[0]}'."
                },
                {
                    "question_text": f"What is a main challenge when implementing '{concepts[1]}' in {subject_name}?",
                    "option_a": "Resource constraints and performance overhead",
                    "option_b": "Color syntax highlighting in code editors",
                    "option_c": "Text alignment in margins",
                    "option_d": "None of the above",
                    "correct_answer": "A",
                    "explanation": f"Constraint management is the major challenge when dealing with '{concepts[1]}'."
                },
                {
                    "question_text": f"How do we typically verify correct operation of '{concepts[2]}'?",
                    "option_a": "By checking compile-time syntax errors",
                    "option_b": "By measuring runtime correctness and validation criteria",
                    "option_c": "By counting the number of source files",
                    "option_d": "By printing debug logs",
                    "correct_answer": "B",
                    "explanation": f"Verification of '{concepts[2]}' relies on correctness and validation metrics."
                }
            ]
        }

    prompt = f"""
Create 3 multiple-choice quiz questions (with choices A, B, C, D, the correct answer, and an explanation) for a college student studying the subject "{subject_name}".

Here is the subject's syllabus text:
"{syllabus}"

The student has requested a quiz on this specific topic: "{topic}" (if empty, they want a general quiz).

Guidelines for topic selection:
1. If the requested topic is empty, generate questions strictly from the topics mentioned in the syllabus.
2. If the requested topic is provided and matches or is related to a topic in the syllabus, restrict questions strictly to that syllabus topic.
3. If the requested topic is provided but is NOT related to the syllabus, ignore the requested topic and generate questions strictly from the subject's syllabus instead.

Keep questions concise and targeted to college-level revision.
"""
    response = get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=QuizSchema,
        )
    )
    return json.loads(response.text)


def generate_quiz_feedback(subject_name, topic, score, total_questions, q_and_a_details):
    """
    Generates study coach feedback based on quiz performance.
    """
    get_client()
    
    if MOCK_MODE:
        if score == total_questions:
            return f"Excellent performance on {subject_name}! You answered all {total_questions} questions correctly. You show strong mastery of {topic or 'general concepts'}. Continue maintaining this level of prep."
        elif score > 0:
            return f"Good effort on {subject_name}! You scored {score}/{total_questions}. You did well on the concepts you got right, but make sure to review the explanations for the remaining questions to fill in any gaps."
        else:
            return f"Keep studying! You scored {score}/{total_questions} on {subject_name}. Review the concepts and explanations provided below, and try generating another quiz to test your progress."

    prompt = f"""
You are a supportive academic mentor. A student has just taken a quiz on "{subject_name}" (Topic: {topic or 'General'}).
Score: {score}/{total_questions}.

Here are the questions they attempted along with their answers:
{json.dumps(q_and_a_details, indent=2, ensure_ascii=False)}

Write a short (4-5 lines), encouraging, and coaching summary of their performance.
Explain the core concepts they struggled with, validate their correct answers, and recommend specific revision actions.
"""
    response = get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text.strip()


def generate_daily_recommendation(today_tasks, recent_progress, recent_quizzes, subjects):
    """
    Generates a personalized daily focus recommendation based on:
    - Originally scheduled tasks for today
    - Recent task completion/miss history
    - Quiz results
    - All subjects context
    """
    get_client()
    
    if MOCK_MODE:
        missed = [t for t in recent_progress if not t["completed"]]
        quizzes_failed = [q for q in recent_quizzes if q["score"] < q["total"]]
        
        rec_text = "Here is your study coach analysis (Mock Mode):\n"
        if missed:
            rec_text += f"- I noticed you missed some tasks recently (e.g. {missed[0]['subject']}: {missed[0]['task']}). Let's allocate time to catch up on these first.\n"
        if quizzes_failed:
            rec_text += f"- Your recent quiz score for {quizzes_failed[0]['subject']} was {quizzes_failed[0]['score']}/{quizzes_failed[0]['total']}. I recommend spending 15 minutes reviewing the incorrect answers.\n"
        
        rec_text += "- Based on difficulty levels and upcoming dates, today's focus is on building solid foundations. Stay consistent!"
        
        adj = []
        if missed:
            adj.append(f"Catch up: {missed[0]['subject']} - {missed[0]['task']}")
        for t in today_tasks[:2]:
            adj.append(f"Focus: {t}")
        if not adj:
            adj.append("Revise subjects with nearest exams")
            
        return {
            "recommendation_text": rec_text,
            "adjusted_tasks": adj[:3]
        }

    today = date.today().isoformat()
    prompt = f"""
You are a personalized study planning AI coach.
Today is {today}.

Here is the student's context:
1. Today's originally scheduled study tasks:
{json.dumps(today_tasks, indent=2, ensure_ascii=False)}

2. Recent tasks progress (last 7 days of completed/incomplete tasks):
{json.dumps(recent_progress, indent=2, ensure_ascii=False)}

3. Recent quiz attempts:
{json.dumps(recent_quizzes, indent=2, ensure_ascii=False)}

4. Subject list:
{json.dumps(subjects, indent=2, ensure_ascii=False)}

Formulate a daily recommendation:
- Acknowledge if they missed tasks recently and how they should catch up.
- Address low quiz scores (e.g. less than 3/3) and suggest a quick review.
- Suggest 1-3 adjusted tasks for today that incorporate these factors, keeping them actionable.
"""
    response = get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DailyRecommendationSchema,
        )
    )
    return json.loads(response.text)


def ask_agent_question(question_text):
    """
    Answers a general student query using Gemini.
    """
    get_client()
    if MOCK_MODE:
        return f"Mock Mode Answer to: '{question_text}'\n\nThis is a simulated explanation. In a real environment, the Study Planner Agent uses the Gemini 2.5 Flash model to provide a clear, detailed tutorial on this topic. Make sure to set GEMINI_API_KEY to see real AI explanations!"

    prompt = f"""
You are a helpful study tutor. A student has asked you this question:
"{question_text}"

Provide a clear, simple, and detailed explanation to help them understand this topic. Use formatting like bullet points or short paragraphs where appropriate to make it easy to read.
"""
    response = get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text.strip()


def generate_suggested_topics(syllabi):
    """
    Extracts 8-10 specific topics from syllabus texts.
    """
    get_client()
    if MOCK_MODE:
        # Local mock parsing: split by commas/newlines and extract non-empty ones
        extracted = []
        for s in syllabi:
            if s:
                parts = [p.strip() for p in s.replace("\n", ",").split(",") if p.strip()]
                extracted.extend(parts)
        unique_topics = []
        for item in extracted:
            if item not in unique_topics:
                unique_topics.append(item)
        return unique_topics[:10]

    prompt = f"""
Analyze the following subject syllabus details entered by a student:
{json.dumps(syllabi, indent=2, ensure_ascii=False)}

Extract exactly 8 to 10 specific topics or subtopics mentioned explicitly in these syllabus texts that would be suitable for Q&A questions.
For example, if the syllabus mentions "Laplace Transforms", generate a short question/topic like "Explain Laplace Transforms".
Do NOT add any generic topics that are not explicitly part of the syllabus content provided.
"""
    response = get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SuggestedTopicsSchema,
        )
    )
    return json.loads(response.text).get('topics', [])
