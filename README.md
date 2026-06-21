# Study Planner Agent 📚🤖

A Django web app where an AI agent (powered by Google Gemini) builds you a
personalized study plan, tells you what to focus on today, quizzes you on
your syllabus, and answers your questions — built for the Kaggle
**"5-Day AI Agents Intensive" Capstone Project**.

## ✨ Features

1. **Add Subjects** — add each subject with its exam date, difficulty, and
   full syllabus/topics text.
2. **Generate Study Plan** — the agent (Gemini) creates a day-by-day plan
   based on your actual syllabus content, prioritizing harder subjects and
   nearer exam dates.
3. **Today's Focus (Agent Coach)** — the agent analyzes your progress, past
   quiz attempts, and upcoming exams to give a personalized, motivating
   summary of what to study today.
4. **Syllabus View** — a separate page per subject showing the full
   syllabus you've added, kept off the cluttered home page.
5. **AI Quiz Coach** — generates a 3-question MCQ quiz strictly from a
   subject's syllabus (or a specific topic you type), scores you instantly,
   and gives personalized feedback. Past quiz performance is saved and
   viewable.
6. **Ask Study Agent** — a tutor-style Q&A chat. Ask any topic and get a
   clear explanation. Includes syllabus-based suggested topics you can
   click instead of typing.
7. **Plan History** — view, switch between, or delete previously generated
   study plans.

## 🤖 How it maps to "AI Agent" concepts (for the capstone writeup)

- **Model** → Gemini 2.5 Flash
- **Tools** → Date calculations, Django ORM database read/write
- **Memory** → Subjects, syllabus content, generated plans, and quiz
  history are all persisted in the database, so the agent's recommendations
  build on past activity
- **Task / Orchestration** → `agent.py` decides what prompt to send (study
  plan generation, daily coaching, quiz generation, Q&A) and parses
  Gemini's response into structured data used across the app

## 🛠️ Setup Instructions (Windows)

### 1. Clone or extract the project
```bash
git clone https://github.com/yourusername/study-planner-agent.git
cd study-planner-agent/study_planner
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your Gemini API key
Get one free from Google AI Studio (`aistudio.google.com/apikey`).

**PowerShell (current session only):**
```powershell
$env:GEMINI_API_KEY="paste_your_key_here"
```

**Or set it permanently (then restart your terminal):**
```powershell
setx GEMINI_API_KEY "paste_your_key_here"
```

### 4. Run migrations (creates the database)
```bash
python manage.py migrate
```

### 5. Start the server
```bash
python manage.py runserver
```

### 6. Open in browser
Go to: http://127.0.0.1:8000/

## 📖 Using the app

1. **+ Add Subject** — add each exam subject with its date, difficulty,
   and paste in the syllabus/topics text.
2. **🤖 Generate Study Plan** — the agent creates your full schedule based
   on your real syllabus content.
3. **Today's Focus** — see your personalized daily coaching message and
   adjusted task checklist.
4. **Quiz Me** — pick a subject (and optionally a topic) for a syllabus-
   based quiz, get scored instantly, and review past attempts.
5. **Ask Agent** — type any topic, or click a suggested one pulled from
   your syllabus, for a clear tutorial-style explanation.
6. **Plan History** — revisit or switch between previously generated plans.

## 📁 Project structure
```
study_planner/
├── manage.py
├── requirements.txt
├── study_planner/         # Django project settings
│   ├── settings.py
│   └── urls.py
└── planner/                # The app
    ├── models.py            # Subject, StudyTask, Quiz, QuizAttempt, Plan
    ├── agent.py             # ⭐ The AI agent logic (all Gemini calls)
    ├── views.py             # Connects web pages to the agent
    ├── urls.py
    └── templates/planner/   # HTML pages (Home, Syllabus, Quiz, Ask Agent...)
```

## 🏆 For the Kaggle Capstone submission

- **Category:** Agents for Good
- **Problem solved:** Helps students manage exam stress by turning a messy
  list of subjects, exam dates, and syllabus content into a clear,
  prioritized daily study plan — with personalized coaching, syllabus-based
  self-testing, and an on-demand AI tutor for stuck topics.
- **Tech used:** Python, Django, Google Gemini API (`google-genai` SDK)

## ⚠️ Notes

- Never commit your API key to GitHub — it's read from the `GEMINI_API_KEY`
  environment variable only, never hardcoded.
- The database (`db.sqlite3`) is excluded via `.gitignore` and is created
  fresh when you run migrations.
- Gemini's free tier has daily/per-minute rate limits — if you see a `429`
  error, wait a short while and try again.
