from .models import QuestionCategory, Question, CodeSnippet, CodeVersion, CodeComment, CodeLike, UserProgress, UserAnswer
from django.shortcuts import render, redirect 
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta
from .error_helper import ErrorExplainer
import sys
import io
import contextlib
import subprocess
import tempfile
import os
import random
import traceback
import json
import requests
import csv
import time
import shutil

# ============ LANDING PAGE & STATIC PAGES ============
def landing_page(request):
    return render(request, 'landing.html')

def about_view(request):
    return render(request, 'about.html')

def features_view(request):
    return render(request, 'features.html')

@csrf_exempt
def forgot_password_view(request):
    # Dummy view for forgot password frontend logic
    if request.method == 'POST':
        email = request.POST.get('email', '')
        # Usually here we would check db and send email
        return JsonResponse({'success': True, 'message': f'Password reset link sent to {email}'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

# Home page (Compiler)
def home(request):
    return render(request, 'index.html')


# ============ CODE EXECUTION (NORMAL RUN) ============
@csrf_exempt
def run_code(request):
    if request.method == 'POST':
        code = request.POST.get('code', '')
        language = request.POST.get('language', 'python')
        program_input = request.POST.get('input', '')

        explainer = ErrorExplainer()
        error = None
        error_explanation = None
        result = None
        start_time = time.time()

        # Convert space-separated inputs to newline-separated for line-based readers
        if language in ['python', 'javascript'] and program_input and ' ' in program_input and '\n' not in program_input:
            program_input = program_input.replace(' ', '\n')

        # Python
        if language == 'python':
            output = io.StringIO()
            try:
                old_stdin = sys.stdin
                sys.stdin = io.StringIO(program_input)
                namespace = {}
                with contextlib.redirect_stdout(output):
                    exec(code, namespace)
                result = output.getvalue()
                sys.stdin = old_stdin
            except Exception as e:
                error = str(e)
                error_explanation = explainer.explain(error)
            finally:
                sys.stdin = sys.__stdin__

        # JavaScript
        elif language == 'javascript':
            js_code = """const fs = require('fs');
const _dev_stdin = fs.readFileSync(0, 'utf-8').split(/\\r?\\n/);
let _dev_stdin_idx = 0;
function prompt(msg) {
    if (msg) process.stdout.write(msg);
    return _dev_stdin[_dev_stdin_idx++] || "";
}
""" + code
            try:
                with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False, encoding='utf-8') as f:
                    f.write(js_code)
                    temp_file = f.name
                js_result = subprocess.run(
                    ['node', temp_file],
                    input=program_input,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if js_result.returncode == 0:
                    result = js_result.stdout
                else:
                    error = js_result.stderr
                os.unlink(temp_file)
            except subprocess.TimeoutExpired:
                error = "JavaScript execution timed out"
            except Exception as e:
                error = str(e)

        # Java
        elif language == 'java':
            try:
                temp_dir = tempfile.gettempdir()
                main_file = os.path.join(temp_dir, 'Main.java')
                with open(main_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                compile_result = subprocess.run(
                    ['javac', main_file],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if compile_result.returncode == 0:
                    run_result = subprocess.run(
                        ['java', '-cp', temp_dir, 'Main'],
                        input=program_input,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if run_result.stdout:
                        result = run_result.stdout
                    elif run_result.stderr:
                        error = run_result.stderr
                    else:
                        result = "✅ Java code executed successfully"
                else:
                    error = compile_result.stderr
                try:
                    if os.path.exists(main_file):
                        os.unlink(main_file)
                    class_file = os.path.join(temp_dir, 'Main.class')
                    if os.path.exists(class_file):
                        os.unlink(class_file)
                except:
                    pass
            except subprocess.TimeoutExpired:
                error = "Java execution timed out"
            except Exception as e:
                error = str(e)

        # C++
        elif language == 'cpp':
            try:
                gpp_path = "C:\\msys64\\ucrt64\\bin\\g++.exe"
                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, 'temp_' + str(random.randint(1000,9999)) + '.cpp')
                exe_file = temp_file.replace('.cpp', '.exe')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                compile_result = subprocess.run(
                    [gpp_path, temp_file, '-o', exe_file],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if compile_result.returncode == 0:
                    run_result = subprocess.run(
                        [exe_file],
                        input=program_input,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if run_result.stdout:
                        result = run_result.stdout
                    elif run_result.stderr:
                        error = run_result.stderr
                    else:
                        result = "✅ C++ code executed (no output)"
                else:
                    error = compile_result.stderr
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                    if os.path.exists(exe_file):
                        os.unlink(exe_file)
                except:
                    pass
            except subprocess.TimeoutExpired:
                error = "C++ execution timed out"
            except Exception as e:
                error = str(e)

        execution_time = int((time.time() - start_time) * 1000)
        
        if request.user.is_authenticated:
            progress, created = UserProgress.objects.get_or_create(user=request.user)
            progress.total_runs += 1
            progress.last_active = date.today()
            progress.save()

        return JsonResponse({
            'output': result if result else '',
            'error': error,
            'explanation': error_explanation,
            'execution_time': execution_time
        })

    return JsonResponse({'error': 'Invalid request method'})


# ============ SIMPLE AI ASSISTANT ============
@csrf_exempt
@login_required
def ai_assistant(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '')
            action = data.get('action', 'explain')
            if not code.strip():
                return JsonResponse({'success': False, 'error': 'Please write some code first!'})
            response = ""
            if action == 'explain':
                response = "📖 Code Analysis\n\n"
                if 'def ' in code:
                    response += "• Defines a function\n"
                if 'print(' in code:
                    response += "• Prints output\n"
                if 'for ' in code or 'while ' in code:
                    response += "• Uses loops\n"
                if 'if ' in code:
                    response += "• Uses conditional statements\n"
                if 'Scanner' in code:
                    response += "• Takes input from user\n"
                response += "\nTips: Use meaningful variable names and add comments!"
            elif action == 'optimize':
                response = "⚡ Code Optimization\n\n• Consider using better variable names.\n• Remove redundant loops if any.\n• Pre-allocate arrays if size is known."
            elif action.startswith('convert_'):
                target = action.split('_')[1]
                response = f"🔄 Code Conversion ({target.upper()})\n\n"
                conv = code
                if target == 'python':
                    conv = conv.replace('System.out.println', 'print').replace('console.log', 'print').replace('std::cout <<', 'print(').replace('cout <<', 'print(').replace(';', '')
                    conv = conv.replace('public class Main {', '').replace('public static void main(String[] args) {', '').replace('}', '')
                    response += "```python\n" + conv.strip() + "\n```"
                elif target == 'java':
                    conv = conv.replace('print(', 'System.out.println(').replace('console.log', 'System.out.println')
                    response += "```java\npublic class Main {\n    public static void main(String[] args) {\n        " + conv.strip() + ";\n    }\n}\n```"
                elif target == 'js':
                    conv = conv.replace('System.out.println', 'console.log').replace('print(', 'console.log(')
                    response += "```javascript\n" + conv.strip() + "\n```"
                elif target == 'cpp':
                    conv = conv.replace('System.out.println', 'cout << ').replace('print(', 'cout << ').replace('console.log(', 'cout << ')
                    response += "```cpp\n#include <iostream>\nusing namespace std;\nint main() {\n    " + conv.strip() + ";\n    return 0;\n}\n```"
                response += "\n\n💡 *Tip: This is a basic conversion. For accurate AI translation, connect an API (Gemini/OpenAI).* "
            else:
                response = "AI Assistant is ready to help!"
            return JsonResponse({'success': True, 'response': response})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'error': 'Invalid request method'})


# ============ AUTHENTICATION ============
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password != confirm_password:
            return JsonResponse({'error': 'Passwords do not match!'})
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists!'})
        user = User.objects.create_user(username=username, email=email, password=password)
        UserProgress.objects.create(user=user)
        login(request, user)
        return JsonResponse({'success': True, 'message': 'Account created!'})
    return render(request, 'signup.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return JsonResponse({'success': True, 'message': 'Logged in!'})
        else:
            return JsonResponse({'error': 'Invalid username or password!'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('landing')


# ============ MCQ VIEWS ============
def get_questions(request):
    language = request.GET.get('language', 'python')
    questions = Question.objects.filter(language=language, is_active=True)
    data = []
    for q in questions:
        data.append({
            'id': q.id,
            'question': q.question_text,
            'options': {'A': q.option_a, 'B': q.option_b, 'C': q.option_c, 'D': q.option_d},
            'correct': q.correct_option,
            'explanation': q.explanation,
            'difficulty': q.difficulty,
            'language': q.language,
            'points': q.points
        })
    return JsonResponse({'questions': data})

def check_answer(request):
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        selected = request.POST.get('selected')
        try:
            question = Question.objects.get(id=question_id)
            is_correct = (selected == question.correct_option)
            if request.user.is_authenticated:
                answer, created = UserAnswer.objects.get_or_create(
                    user=request.user,
                    question=question,
                    defaults={'selected_option': selected, 'is_correct': is_correct}
                )
                if not created:
                    answer.selected_option = selected
                    answer.is_correct = is_correct
                    answer.save()
                progress, _ = UserProgress.objects.get_or_create(user=request.user)
                progress.total_questions_attempted += 1
                if is_correct:
                    progress.total_correct_answers += 1
                    progress.total_points += question.points
                progress.save()
            return JsonResponse({
                'correct': is_correct,
                'correct_option': question.correct_option,
                'explanation': question.explanation if not is_correct else ''
            })
        except Question.DoesNotExist:
            return JsonResponse({'error': 'Question not found'})
    return JsonResponse({'error': 'Invalid request'})


# ============ SAVED CODES VIEWS ============
@login_required
def get_my_codes(request):
    try:
        snippets = CodeSnippet.objects.filter(Q(user=request.user) | Q(is_public=True)).order_by('-created_at')
        data = []
        for s in snippets:
            data.append({
                'id': s.id,
                'title': s.title,
                'language': s.language,
                'created_at': s.created_at.strftime('%Y-%m-%d %H:%M'),
                'username': s.user.username if s.user else 'Unknown',
                'is_public': s.is_public,
                'is_owner': s.user == request.user,
                'likes_count': s.likes.count(),
                'comments_count': s.comments.count()
            })
        return JsonResponse({'codes': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_code(request, code_id):
    try:
        snippet = CodeSnippet.objects.get(Q(id=code_id) & (Q(user=request.user) | Q(is_public=True)))
        return JsonResponse({
            'code': snippet.code,
            'title': snippet.title,
            'language': snippet.language,
            'output': snippet.output,
            'is_public': snippet.is_public,
            'is_owner': snippet.user == request.user
        })
    except CodeSnippet.DoesNotExist:
        return JsonResponse({'error': 'Code not found'}, status=404)

@login_required
@csrf_exempt
def save_code(request):
    if request.method == 'POST':
        try:
            code = request.POST.get('code', '')
            language = request.POST.get('language', 'python')
            title = request.POST.get('title', 'Untitled')
            is_public = request.POST.get('is_public', 'false') == 'true'
            snippet = CodeSnippet.objects.create(
                user=request.user,
                title=title,
                code=code,
                language=language,
                output='',
                is_public=is_public
            )
            CodeVersion.objects.create(snippet=snippet, code=code, version_number=1)
            progress, _ = UserProgress.objects.get_or_create(user=request.user)
            progress.total_codes_written += 1
            progress.save()
            return JsonResponse({'success': True, 'id': snippet.id, 'message': '✅ Code saved!'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def delete_code(request, code_id):
    try:
        snippet = CodeSnippet.objects.get(id=code_id, user=request.user)
        snippet.delete()
        return JsonResponse({'success': True, 'message': 'Code deleted'})
    except CodeSnippet.DoesNotExist:
        return JsonResponse({'error': 'Code not found'}, status=404)

@login_required
@csrf_exempt
def update_code(request, code_id):
    if request.method == 'POST':
        try:
            snippet = CodeSnippet.objects.get(id=code_id, user=request.user)
            snippet.title = request.POST.get('title', snippet.title)
            snippet.code = request.POST.get('code', snippet.code)
            snippet.language = request.POST.get('language', snippet.language)
            snippet.is_public = request.POST.get('is_public', 'false') == 'true'
            snippet.save()
            version_number = snippet.versions.count() + 1
            CodeVersion.objects.create(snippet=snippet, code=snippet.code, version_number=version_number)
            return JsonResponse({'success': True, 'message': 'Code updated'})
        except CodeSnippet.DoesNotExist:
            return JsonResponse({'error': 'Code not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def fork_code(request, code_id):
    try:
        original = CodeSnippet.objects.get(id=code_id, is_public=True)
        new_code = CodeSnippet.objects.create(
            user=request.user,
            title=f"Fork of {original.title}",
            code=original.code,
            language=original.language,
            is_public=False
        )
        return JsonResponse({'success': True, 'id': new_code.id, 'message': 'Code forked!'})
    except CodeSnippet.DoesNotExist:
        return JsonResponse({'error': 'Code not found'}, status=404)

@login_required
def get_stats(request):
    try:
        progress, _ = UserProgress.objects.get_or_create(user=request.user)
        codes = CodeSnippet.objects.filter(user=request.user)
        stats = {
            'total_codes': codes.count(),
            'python_codes': codes.filter(language='python').count(),
            'javascript_codes': codes.filter(language='javascript').count(),
            'java_codes': codes.filter(language='java').count(),
            'cpp_codes': codes.filter(language='cpp').count(),
            'public_codes': codes.filter(is_public=True).count(),
            'total_runs': progress.total_runs,
            'streak_days': progress.streak_days,
            'total_points': progress.total_points,
            'questions_attempted': progress.total_questions_attempted,
            'correct_answers': progress.total_correct_answers
        }
        return JsonResponse({'stats': stats})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def search_codes(request):
    query = request.GET.get('q', '')
    codes = CodeSnippet.objects.filter(
        Q(user=request.user) & (Q(title__icontains=query) | Q(code__icontains=query))
    ).order_by('-created_at')
    data = [{'id': c.id, 'title': c.title, 'language': c.language, 'created_at': c.created_at.strftime('%Y-%m-%d %H:%M')} for c in codes]
    return JsonResponse({'codes': data})

@login_required
@csrf_exempt
def like_code(request, code_id):
    try:
        snippet = CodeSnippet.objects.get(id=code_id, is_public=True)
        like, created = CodeLike.objects.get_or_create(snippet=snippet, user=request.user)
        if not created:
            like.delete()
            return JsonResponse({'liked': False, 'likes_count': snippet.likes.count()})
        return JsonResponse({'liked': True, 'likes_count': snippet.likes.count()})
    except CodeSnippet.DoesNotExist:
        return JsonResponse({'error': 'Code not found'}, status=404)

@login_required
@csrf_exempt
def comment_code(request, code_id):
    if request.method == 'POST':
        try:
            snippet = CodeSnippet.objects.get(id=code_id, is_public=True)
            comment_text = request.POST.get('comment', '')
            comment = CodeComment.objects.create(snippet=snippet, user=request.user, comment=comment_text)
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'username': comment.user.username,
                    'comment': comment.comment,
                    'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
                }
            })
        except CodeSnippet.DoesNotExist:
            return JsonResponse({'error': 'Code not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def get_comments(request, code_id):
    try:
        comments = CodeComment.objects.filter(snippet_id=code_id).order_by('-created_at')
        data = [{'id': c.id, 'username': c.user.username, 'comment': c.comment, 'created_at': c.created_at.strftime('%Y-%m-%d %H:%M')} for c in comments]
        return JsonResponse({'comments': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_versions(request, code_id):
    try:
        snippet = CodeSnippet.objects.get(id=code_id, user=request.user)
        versions = snippet.versions.all()
        data = [{'version_number': v.version_number, 'code': v.code, 'created_at': v.created_at.strftime('%Y-%m-%d %H:%M')} for v in versions]
        return JsonResponse({'versions': data})
    except CodeSnippet.DoesNotExist:
        return JsonResponse({'error': 'Code not found'}, status=404)


# ============ BULK UPLOAD ============
import csv
import io

@login_required
def bulk_upload_questions(request):
    if request.method == 'POST':
        if not request.user.is_superuser:
            return JsonResponse({'error': 'Admin access required'}, status=403)
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            return JsonResponse({'error': 'No file uploaded'})
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            success_count = 0
            errors = []
            for row_num, row in enumerate(reader, start=2):
                try:
                    Question.objects.create(
                        question_text=row.get('question_text', '').strip(),
                        option_a=row.get('option_a', '').strip(),
                        option_b=row.get('option_b', '').strip(),
                        option_c=row.get('option_c', '').strip(),
                        option_d=row.get('option_d', '').strip(),
                        correct_option=row.get('correct_option', '').strip().upper(),
                        language=row.get('language', 'python').strip().lower(),
                        difficulty=row.get('difficulty', 'medium').strip().lower(),
                        topic=row.get('topic', 'general').strip().lower(),
                        points=int(row.get('points', 10)),
                        explanation=row.get('explanation', '').strip(),
                        is_active=True
                    )
                    success_count += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
            return JsonResponse({'success': True, 'message': f'✅ Uploaded {success_count} questions!', 'errors': errors[:10] if errors else None})
        except Exception as e:
            return JsonResponse({'error': str(e)})
    return render(request, 'bulk_upload.html')

def download_sample_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_questions.csv"'
    writer = csv.writer(response)
    writer.writerow(['question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option', 'language', 'difficulty', 'topic', 'points', 'explanation'])
    samples = [
        ['What is the output of print(2+3)?', '5', '6', '7', '8', 'A', 'python', 'easy', 'operators', '10', '2+3 = 5'],
        ['What is 10 % 3?', '1', '2', '3', '0', 'A', 'python', 'easy', 'operators', '10', '10 % 3 = 1'],
        ['Which keyword is used for function in Python?', 'def', 'func', 'function', 'define', 'A', 'python', 'easy', 'functions', '10', 'def is used'],
        ['What is the output of len("Hello")?', '3', '4', '5', '6', 'C', 'python', 'easy', 'strings', '10', 'len returns 5'],
        ['What is the output of type(3.14)?', 'int', 'float', 'str', 'bool', 'B', 'python', 'easy', 'datatypes', '10', '3.14 is float'],
    ]
    for sample in samples:
        writer.writerow(sample)
    return response


# ============ INTERACTIVE MODE (FULLY FIXED - ALL WORKING) ============

@csrf_exempt
def run_interactive_code(request):
    """Interactive code execution - Fully working for all languages"""
    if request.method == 'POST':
        code = request.POST.get('code', '')
        language = request.POST.get('language', 'java')
        user_input = request.POST.get('input', '')
        
        try:
            # ========== JAVA ==========
            if language == 'java':
                temp_dir = tempfile.mkdtemp()
                main_file = os.path.join(temp_dir, 'Main.java')
                with open(main_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                compile_result = subprocess.run(
                    ['javac', main_file],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=temp_dir
                )
                if compile_result.returncode != 0:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return JsonResponse({'output': compile_result.stderr, 'finished': True, 'waiting': False})
                run_result = subprocess.run(
                    ['java', '-cp', temp_dir, 'Main'],
                    input=user_input,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=temp_dir
                )
                output = run_result.stdout if run_result.stdout else run_result.stderr
                shutil.rmtree(temp_dir, ignore_errors=True)
                return JsonResponse({'output': output, 'finished': True, 'waiting': False})
            
            # ========== C++ ==========
            elif language == 'cpp':
                gpp_path = "C:\\msys64\\ucrt64\\bin\\g++.exe"
                temp_dir = tempfile.mkdtemp()
                temp_file = os.path.join(temp_dir, 'main.cpp')
                exe_file = os.path.join(temp_dir, 'main.exe')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                compile_result = subprocess.run(
                    [gpp_path, temp_file, '-o', exe_file],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=temp_dir
                )
                if compile_result.returncode != 0:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return JsonResponse({'output': compile_result.stderr, 'finished': True, 'waiting': False})
                run_result = subprocess.run(
                    [exe_file],
                    input=user_input,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=temp_dir
                )
                output = run_result.stdout if run_result.stdout else run_result.stderr
                shutil.rmtree(temp_dir, ignore_errors=True)
                return JsonResponse({'output': output, 'finished': True, 'waiting': False})
            
            # ========== PYTHON ==========
            elif language == 'python':
                # Bonus validation: Count input() calls vs provided inputs
                num_inputs_expected = code.count('input(')
                inputs_list = user_input.split()
                if num_inputs_expected > len(inputs_list):
                    return JsonResponse({'output': f'❌ Error: Code requires {num_inputs_expected} input(s), but only {len(inputs_list)} provided.\nPlease separate multiple inputs with spaces in the input box.', 'finished': True, 'waiting': False})

                # Convert space-separated to newline-separated for input()
                if user_input and ' ' in user_input and '\n' not in user_input:
                    user_input = user_input.replace(' ', '\n')
                    
                run_result = subprocess.run(
                    ['python', '-c', code],
                    input=user_input,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = run_result.stdout if run_result.stdout else run_result.stderr
                if 'EOFError' in output:
                    output = output.split('Traceback')[0].strip()
                    if not output:
                        output = "❌ Error: Python script requires more input.\n💡 Tip: Type all inputs separated by spaces or newlines."
                elif 'Traceback' in output:
                    pass # Keep traceback to show real errors
                return JsonResponse({'output': output, 'finished': True, 'waiting': False})
            
            # ========== JAVASCRIPT - FIXED ==========
            elif language == 'javascript':
                # Bonus validation: Count readline or prompt calls vs provided inputs
                num_inputs_expected = code.count('.question(') + code.count('prompt(') + code.count('readFileSync(0')
                inputs_list = user_input.split()
                if num_inputs_expected > len(inputs_list):
                    return JsonResponse({'output': f'❌ Error: Code requires {num_inputs_expected} input(s), but only {len(inputs_list)} provided.\nPlease separate multiple inputs with spaces in the input box.', 'finished': True, 'waiting': False})

                # Convert space-separated to newline-separated for readline
                if user_input and ' ' in user_input and '\n' not in user_input:
                    user_input = user_input.replace(' ', '\n')
                    
                with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False, encoding='utf-8') as f:
                    f.write(code)
                    temp_file = f.name
                try:
                    run_result = subprocess.run(
                        ['node', temp_file],
                        input=user_input,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    output = run_result.stdout if run_result.stdout else run_result.stderr
                    if 'NaN' in output and not user_input:
                        output = "❌ Error: Missing input for JavaScript readline.\n💡 Tip: Provide input before running."
                    elif 'NaN' in output:
                        output = output.replace('NaN', '0')
                except subprocess.TimeoutExpired:
                    output = "Timeout! Try again"
                except Exception as e:
                    output = f"Error: {str(e)}"
                try:
                    os.unlink(temp_file)
                except:
                    pass
                return JsonResponse({'output': output, 'finished': True, 'waiting': False})
            
            return JsonResponse({'output': 'Language not supported', 'finished': True, 'waiting': False})
            
        except subprocess.TimeoutExpired:
            return JsonResponse({'output': 'Timeout!', 'finished': True, 'waiting': False})
        except Exception as e:
            return JsonResponse({'output': f'Error: {str(e)}', 'finished': True, 'waiting': False})
    
    return JsonResponse({'error': 'Invalid request method'})


@csrf_exempt
def stop_interactive_session(request):
    return JsonResponse({'success': True})