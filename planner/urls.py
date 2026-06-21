from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('add-subject/', views.add_subject, name='add_subject'),
    path('delete-subject/<int:subject_id>/', views.delete_subject, name='delete_subject'),
    path('subject/<int:subject_id>/', views.subject_detail, name='subject_detail'),
    path('generate-plan/', views.generate_plan, name='generate_plan'),
    path('today-focus/', views.today_focus, name='today_focus'),
    path('quiz/', views.quiz_me, name='quiz_me'),
    path('quiz/<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),
    path('quiz/attempt/<int:attempt_id>/', views.quiz_result, name='quiz_result'),
    path('ask-agent/', views.ask_agent, name='ask_agent'),
    path('plans/', views.plan_history, name='plan_history'),
    path('plans/activate/<int:plan_id>/', views.activate_plan, name='activate_plan'),
    path('plans/delete/<int:plan_id>/', views.delete_plan, name='delete_plan'),
    path('mark-complete/<int:task_id>/', views.mark_complete, name='mark_complete'),
]
