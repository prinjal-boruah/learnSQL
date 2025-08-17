from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'playground'

urlpatterns = [
    path('', views.home, name='home'),
    path('topics/<slug:topic_slug>/', views.topic_detail, name='topic_detail'),
    path('q/<slug:topic_slug>/<slug:question_slug>/', views.question_detail, name='question_detail'),
    path('run_sql/', views.run_sql, name='run_sql'),
    path('check_answer/', views.check_answer, name='check_answer'),
    path('show_answer/', views.show_answer, name='show_answer'),

    # Login / Logout
    path('login/', auth_views.LoginView.as_view(
        template_name='playground/login.html',
        redirect_authenticated_user=True
    ), name='login'),

    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('register/', views.register, name='register'),
]
