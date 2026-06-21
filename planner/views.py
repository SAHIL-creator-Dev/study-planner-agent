from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from datetime import date, timedelta
from .models import Subject, StudyPlan, StudyTask, DailyRecommendation, Quiz, QuizQuestion, QuizAttempt
from . import agent


def home(request):
    subjects = Subject.objects.all().order_by('exam_date')
    active_plan = StudyPlan.objects.filter(is_active=True).first()
    today_tasks = StudyTask.objects.filter(study_plan=active_plan, date=date.today()) if active_plan else []
    
    # Calculate progress of today's tasks
    total_today = today_tasks.count() if today_tasks else 0
    completed_today = today_tasks.filter(is_completed=True).count() if today_tasks else 0
    percent_completed = int((completed_today / total_today) * 100) if total_today > 0 else 0

    return render(request, 'planner/home.html', {
        'subjects': subjects,
        'active_plan': active_plan,
        'today_tasks': today_tasks,
        'percent_completed': percent_completed,
    })


def add_subject(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        exam_date = request.POST.get('exam_date')
        difficulty = request.POST.get('difficulty')
        syllabus = request.POST.get('syllabus', '')
        Subject.objects.create(name=name, exam_date=exam_date, difficulty=difficulty, syllabus=syllabus)
        messages.success(request, f"Added subject: {name}")
        return redirect('home')
    return render(request, 'planner/add_subject.html')


def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    name = subject.name
    subject.delete()
    messages.success(request, f"Deleted subject: {name}")
    # Force recommendation regeneration for today
    DailyRecommendation.objects.filter(date=date.today()).delete()
    return redirect('home')


def subject_detail(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    return render(request, 'planner/subject_detail.html', {
        'subject': subject,
    })


def generate_plan(request):
    """Calls the agent to generate a study plan for all subjects."""
    subjects = Subject.objects.all()
    if not subjects:
        messages.error(request, "Add at least one subject first!")
        return redirect('home')

    subject_data = [
        {
            "name": s.name,
            "exam_date": str(s.exam_date),
            "difficulty": s.difficulty,
            "syllabus": s.syllabus,
        }
        for s in subjects
    ]

    try:
        plan = agent.generate_study_plan(subject_data)

        if not plan:
            raise ValueError("The agent returned an empty study plan.")

        # Parse dates to find start and end date of the generated plan
        dates = [date.fromisoformat(item['date']) for item in plan]
        start_date = min(dates) if dates else date.today()
        end_date = max(dates) if dates else date.today()

        # Deactivate all existing study plans
        StudyPlan.objects.all().update(is_active=False)

        # Create new active study plan
        study_plan = StudyPlan.objects.create(
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )

        for item in plan:
            subject_obj = Subject.objects.filter(name=item['subject']).first()
            if subject_obj:
                StudyTask.objects.create(
                    study_plan=study_plan,
                    subject=subject_obj,
                    date=item['date'],
                    task_description=item['task'],
                    why_important=item.get('why_important', '')
                )
        messages.success(request, f"New study plan ({start_date} to {end_date}) generated successfully!")
        
        # Invalidate daily recommendation for today so it regenerates for the new plan
        DailyRecommendation.objects.filter(date=date.today()).delete()
    except Exception as e:
        messages.error(request, f"Error generating plan: {e}")

    return redirect('home')


def today_focus(request):
    """Agent gives a personalized daily recommendation considering missed tasks and quiz scores."""
    today_val = date.today()
    regenerate = request.GET.get('regenerate') == 'true'
    
    recommendation = DailyRecommendation.objects.filter(date=today_val).first()
    
    if regenerate or not recommendation:
        active_plan = StudyPlan.objects.filter(is_active=True).first()
        today_tasks = StudyTask.objects.filter(study_plan=active_plan, date=today_val) if active_plan else []
        today_tasks_list = [f"{t.subject.name}: {t.task_description}" for t in today_tasks]
        
        # Get tasks from last 7 days to evaluate completion
        recent_tasks = StudyTask.objects.filter(
            study_plan=active_plan,
            date__lt=today_val,
            date__gte=today_val - timedelta(days=7)
        ) if active_plan else []
        recent_progress_data = [
            {
                "date": str(t.date),
                "subject": t.subject.name,
                "task": t.task_description,
                "completed": t.is_completed
            }
            for t in recent_tasks
        ]
        
        # Recent quizzes (last 5)
        recent_attempts = QuizAttempt.objects.all().order_by('-attempted_at')[:5]
        recent_quizzes_data = [
            {
                "subject": a.quiz.subject.name,
                "topic": a.quiz.topic,
                "score": a.score,
                "total": a.total_questions
            }
            for a in recent_attempts
        ]
        
        # Subjects list
        subjects = Subject.objects.all()
        subjects_data = [
            {
                "name": s.name,
                "exam_date": str(s.exam_date),
                "difficulty": s.difficulty
            }
            for s in subjects
        ]
        
        try:
            rec_json = agent.generate_daily_recommendation(
                today_tasks=today_tasks_list,
                recent_progress=recent_progress_data,
                recent_quizzes=recent_quizzes_data,
                subjects=subjects_data
            )
            
            if recommendation:
                recommendation.recommendation_text = rec_json['recommendation_text']
                recommendation.adjusted_tasks = rec_json['adjusted_tasks']
                recommendation.save()
            else:
                recommendation = DailyRecommendation.objects.create(
                    date=today_val,
                    recommendation_text=rec_json['recommendation_text'],
                    adjusted_tasks=rec_json['adjusted_tasks']
                )
            messages.success(request, "Generated personalized recommendation!")
        except Exception as e:
            fallback_text = f"Could not generate personalized recommendation: {e}. Let's focus on today's scheduled tasks!"
            if recommendation:
                recommendation.recommendation_text = fallback_text
                recommendation.adjusted_tasks = today_tasks_list
                recommendation.save()
            else:
                recommendation = DailyRecommendation.objects.create(
                    date=today_val,
                    recommendation_text=fallback_text,
                    adjusted_tasks=today_tasks_list
                )
                
    # Also grab missed tasks from the last 3 days to show alert on page
    active_plan = StudyPlan.objects.filter(is_active=True).first()
    missed_tasks = []
    if active_plan:
        missed_tasks = StudyTask.objects.filter(
            study_plan=active_plan,
            date__lt=today_val,
            date__gte=today_val - timedelta(days=3),
            is_completed=False
        )

    return render(request, 'planner/today_focus.html', {
        'recommendation': recommendation,
        'missed_tasks': missed_tasks,
    })


def quiz_me(request):
    """Agent generates a quiz; saves it to database, and shows past attempts."""
    subjects = Subject.objects.all()
    attempts = QuizAttempt.objects.all().order_by('-attempted_at')

    if request.method == 'POST':
        selected_subject_name = request.POST.get('subject')
        topic = request.POST.get('topic', '')
        
        subject_obj = Subject.objects.filter(name=selected_subject_name).first()
        if not subject_obj:
            messages.error(request, "Selected subject does not exist!")
            return redirect('quiz_me')

        try:
            quiz_data = agent.generate_quiz(selected_subject_name, subject_obj.syllabus, topic)
            
            # Save Quiz to DB
            quiz = Quiz.objects.create(
                subject=subject_obj,
                topic=topic
            )
            
            # Save Questions
            for q in quiz_data['questions']:
                QuizQuestion.objects.create(
                    quiz=quiz,
                    question_text=q['question_text'],
                    option_a=q['option_a'],
                    option_b=q['option_b'],
                    option_c=q['option_c'],
                    option_d=q['option_d'],
                    correct_answer=q['correct_answer'],
                    explanation=q['explanation']
                )
                
            return redirect('take_quiz', quiz_id=quiz.id)
        except Exception as e:
            messages.error(request, f"Error generating quiz: {e}")
            return redirect('quiz_me')

    return render(request, 'planner/quiz.html', {
        'subjects': subjects,
        'attempts': attempts,
    })


def take_quiz(request, quiz_id):
    """Render the interactive quiz and score answers."""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()
    
    if request.method == 'POST':
        user_answers = {}
        score = 0
        q_and_a_details = []
        
        for q in questions:
            ans_key = f"question_{q.id}"
            user_ans = request.POST.get(ans_key, '').upper()
            user_answers[str(q.id)] = user_ans
            
            is_correct = (user_ans == q.correct_answer)
            if is_correct:
                score += 1
                
            q_and_a_details.append({
                "question_text": q.question_text,
                "user_answer": user_ans,
                "correct_answer": q.correct_answer,
                "explanation": q.explanation,
                "is_correct": is_correct
            })
            
        try:
            feedback = agent.generate_quiz_feedback(
                subject_name=quiz.subject.name,
                topic=quiz.topic,
                score=score,
                total_questions=len(questions),
                q_and_a_details=q_and_a_details
            )
        except Exception as e:
            feedback = f"Could not generate feedback: {e}"
            
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            score=score,
            total_questions=len(questions),
            user_answers=user_answers,
            feedback=feedback
        )
        
        # Trigger daily recommendation update to incorporate quiz results
        DailyRecommendation.objects.filter(date=date.today()).delete()
        
        return redirect('quiz_result', attempt_id=attempt.id)
        
    return render(request, 'planner/quiz_take.html', {
        'quiz': quiz,
        'questions': questions,
    })


def quiz_result(request, attempt_id):
    """Show details of the completed quiz attempt with agent critique."""
    attempt = get_object_or_404(QuizAttempt, id=attempt_id)
    questions = attempt.quiz.questions.all()
    
    results = []
    for q in questions:
        user_ans = attempt.user_answers.get(str(q.id), '')
        is_correct = (user_ans == q.correct_answer)
        results.append({
            'question': q,
            'user_answer': user_ans,
            'is_correct': is_correct,
        })
        
    return render(request, 'planner/quiz_result.html', {
        'attempt': attempt,
        'results': results,
    })


def plan_history(request):
    """View generated plans list."""
    plans = StudyPlan.objects.all().order_by('-created_at')
    return render(request, 'planner/plan_history.html', {
        'plans': plans,
    })


def activate_plan(request, plan_id):
    """Set specified plan as active and others as inactive."""
    StudyPlan.objects.all().update(is_active=False)
    plan = get_object_or_404(StudyPlan, id=plan_id)
    plan.is_active = True
    plan.save()
    messages.success(request, f"Activated study plan generated on {plan.created_at.strftime('%Y-%m-%d %H:%M')}")
    # Force recommendation regeneration for today
    DailyRecommendation.objects.filter(date=date.today()).delete()
    return redirect('plan_history')


def delete_plan(request, plan_id):
    """Delete study plan."""
    plan = get_object_or_404(StudyPlan, id=plan_id)
    plan.delete()
    messages.success(request, "Deleted study plan.")
    # Force recommendation regeneration for today
    DailyRecommendation.objects.filter(date=date.today()).delete()
    return redirect('plan_history')


def mark_complete(request, task_id):
    task = StudyTask.objects.filter(id=task_id).first()
    if task:
        task.is_completed = not task.is_completed
        task.save()
        
        # Trigger daily recommendation update to incorporate updated status
        DailyRecommendation.objects.filter(date=date.today()).delete()
    return redirect('home')


def ask_agent(request):
    question = None
    answer = None
    if request.method == 'POST':
        question = request.POST.get('question')
        try:
            answer = agent.ask_agent_question(question)
        except Exception as e:
            answer = f"Error generating answer: {e}"
            
    # Retrieve non-empty syllabi from Subjects in database
    syllabi = list(Subject.objects.exclude(syllabus='').values_list('syllabus', flat=True))
    suggestions = []
    if syllabi:
        try:
            suggestions = agent.generate_suggested_topics(syllabi)
        except Exception as e:
            # Fallback to empty if error occurs during extraction
            pass
            
    return render(request, 'planner/ask_agent.html', {
        'question': question,
        'answer': answer,
        'suggestions': suggestions,
    })
