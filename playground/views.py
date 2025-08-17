from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Topic, Question, Progress
from django.db.models import Exists, OuterRef
from django.db import connection
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login


# Utility to allow only SELECT queries
def is_safe_sql(sql, allow_select_only=True):
    blocked = ['ATTACH', 'PRAGMA', 'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'VACUUM']
    upper_sql = sql.upper()
    for b in blocked:
        if b in upper_sql:
            if allow_select_only or b != 'SELECT':
                return False
    if allow_select_only and not upper_sql.strip().startswith('SELECT'):
        return False
    return True


@login_required
def home(request):
    topics = Topic.objects.filter(is_active=True)

    # Annotate progress for logged-in user
    topic_progress = {}
    for topic in topics:
        completed = topic.questions.filter(
            progress_entries__user=request.user,
            progress_entries__completed=True
        ).count()
        total = topic.questions.count()
        topic_progress[topic.id] = {'completed': completed, 'total': total}

    return render(request, 'playground/home.html', {
        'topics': topics,
        'topic_progress': topic_progress
    })


@login_required
def topic_detail(request, topic_slug):
    topic = get_object_or_404(Topic, slug=topic_slug, is_active=True)
    questions = topic.questions.filter(is_active=True)

    completed_qs = Progress.objects.filter(
        user=request.user,
        question=OuterRef('pk'),
        completed=True
    )
    questions = questions.annotate(is_completed=Exists(completed_qs))

    return render(request, 'playground/topic_detail.html', {
        'topic': topic,
        'questions': questions
    })


@login_required
def question_detail(request, topic_slug, question_slug):
    topic = get_object_or_404(Topic, slug=topic_slug, is_active=True)
    question = get_object_or_404(topic.questions, slug=question_slug, is_active=True)
    all_topic_questions = topic.questions.filter(is_active=True)

    completed = Progress.objects.filter(user=request.user, question=question, completed=True).exists()

    return render(request, 'playground/question_detail.html', {
        'topic': topic,
        'question': question,
        'completed': completed,
        'all_topic_questions': all_topic_questions
    })


@csrf_exempt
@login_required
def run_sql(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'})

    try:
        data = json.loads(request.body)
        sql = data.get('sql', '').strip()
        topic_slug = data.get('topic_slug')
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Invalid JSON: {e}'})

    try:
        topic = Topic.objects.get(slug=topic_slug, is_active=True)
        seed_sql = topic.seed_sql
    except Topic.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Topic not found'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Topic error: {e}'})

    try:
        with connection.cursor() as cur:
            # Execute seed SQL (split for Postgres compatibility)
            statements = [stmt.strip() for stmt in seed_sql.split(';') if stmt.strip()]
            for stmt in statements:
                cur.execute(stmt)

            cur.execute(sql)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
        return JsonResponse({'ok': True, 'columns': columns, 'rows': rows, 'row_count': len(rows)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': f'SQL error: {e}'})


@login_required
@csrf_exempt
def check_answer(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'})

    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        user_sql = data.get('sql', '').strip()
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Invalid JSON: {e}'})

    if not user_sql:
        return JsonResponse({'ok': False, 'error': 'Empty SQL'})
    if not is_safe_sql(user_sql):
        return JsonResponse({'ok': False, 'error': 'Unsafe SQL detected or not allowed'})

    try:
        question = Question.objects.get(id=question_id, is_active=True)
        seed_sql = question.seed_sql_override or question.topic.seed_sql
        checker_sqls = [question.checker_sql] + question.get_alternate_checker_sqls()
    except Question.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Question not found'})

    try:
        with connection.cursor() as cur:
            # Seed database
            statements = [stmt.strip() for stmt in seed_sql.split(';') if stmt.strip()]
            for stmt in statements:
                cur.execute(stmt)

            # Execute user SQL
            cur.execute(user_sql)
            user_rows = sorted(cur.fetchall())

            # Check against all checker SQLs
            correct = False
            for sql in checker_sqls:
                cur.execute(sql)
                checker_rows = sorted(cur.fetchall())
                if user_rows == checker_rows:
                    correct = True
                    break

        # --- Progress tracking ---
        if correct:
            progress, created = Progress.objects.get_or_create(
                user=request.user,
                question=question,
                defaults={'completed': True}
            )
            if not created:
                progress.completed = True
                progress.save()

        if correct:
            return JsonResponse({'ok': True})
        else:
            return JsonResponse({'ok': False, 'error': 'Result does not match expected output'})

    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'SQL error: {e}'})


@login_required
@csrf_exempt
def show_answer(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'})

    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
    except Exception as e:
        return JsonResponse({'ok': False, 'error': f'Invalid JSON: {e}'})

    try:
        question = Question.objects.get(id=question_id, is_active=True)
        checker_sqls = [question.checker_sql] + question.get_alternate_checker_sqls()
    except Question.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Question not found'})

    solutions = ''
    for i, sql in enumerate(checker_sqls):
        solutions += f'Solution {i+1}: {sql}\n\n'

    return JsonResponse({'ok': True, 'solutions': solutions})


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Auto login after registration
            return redirect('playground:home')
    else:
        form = UserCreationForm()

    return render(request, 'playground/register.html', {'form': form})
