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

# ============ GEMINI AI IMPORT ============
# Configure Gemini AI with your API key
GEMINI_API_KEY = "AIzaSyBX3CjdEZ8AU8tkKk4IY5A0V6opIoLpDLc"

# Home page (Compiler)
def home(request):
    return render(request, 'index.html')


# ============ CODE EXECUTION (FIXED) ============
@csrf_exempt
def run_code(request):
    if request.method == 'POST':
        code = request.POST.get('code', '')
        language = request.POST.get('language', 'python')

        explainer = ErrorExplainer()
        error = None
        error_explanation = None
        result = None
        execution_time = 0
        import time
        start_time = time.time()

        # ---------- PYTHON (FIXED) ----------
        if language == 'python':
            output = io.StringIO()
            try:
                # Create a namespace for execution
                namespace = {}
                with contextlib.redirect_stdout(output):
                    exec(code, namespace)
                result = output.getvalue()
                
                # If no output but function was defined, try to call it with a test value
                if not result and 'factorial' in namespace:
                    test_result = namespace['factorial'](5)
                    result = str(test_result) + "\n"
            except Exception as e:
                error = str(e)
                error_explanation = explainer.explain(error)

        # ---------- JAVASCRIPT ----------
        elif language == 'javascript':
            try:
                with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False, encoding='utf-8') as f:
                    f.write(code)
                    temp_file = f.name

                js_result = subprocess.run(
                    ['node', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=5
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

        # ---------- JAVA ----------
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
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    result = run_result.stdout
                    error = run_result.stderr
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

        # ---------- C++ ----------
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
        
        # Update user progress
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


# ============ AI ASSISTANT (Direct API Call - Working Model) ============
@csrf_exempt
@login_required
def ai_assistant(request):
    """AI Assistant - Explain, Fix, Optimize, Convert Code using Direct API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '')
            action = data.get('action', 'explain')
            target_lang = data.get('target_lang', '')
            
            if not code.strip():
                return JsonResponse({
                    'success': False,
                    'error': 'Please write some code first!'
                })
            
            # Create prompt based on action
            if action == 'explain':
                prompt = f"""Explain this code in simple, easy to understand language:

Code:
{code}

Please explain:
1. What does this code do? (in simple terms)
2. How does it work step by step?
3. What is the time complexity and space complexity?
4. Any suggestions for improvement?

Answer in a friendly, helpful tone."""
                
            elif action == 'fix':
                prompt = f"""Find and fix bugs in this code:

Code:
{code}

Please provide:
1. What bugs did you find? (list them)
2. The fixed code (complete code)
3. Explanation of what was fixed and why

Answer in a friendly, helpful tone."""
                
            elif action == 'optimize':
                prompt = f"""Optimize this code for better performance:

Code:
{code}

Please provide:
1. Optimized code (complete code)
2. What improvements were made and why they make it faster
3. Performance comparison (before vs after)

Answer in a friendly, helpful tone."""
                
            elif action == 'convert':
                prompt = f"""Convert this code to {target_lang} language:

Code:
{code}

Please provide:
1. Converted code in {target_lang}
2. Key differences between the original and converted code
3. Any notes about running this code

Answer in a friendly, helpful tone."""
            
            else:
                prompt = f"Explain this code:\n{code}"
            
            # Direct API call to Google Gemini with WORKING MODEL
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=30)
            result = response.json()
            
            if 'candidates' in result and len(result['candidates']) > 0:
                ai_response = result['candidates'][0]['content']['parts'][0]['text']
                return JsonResponse({
                    'success': True,
                    'response': ai_response
                })
            else:
                error_msg = result.get('error', {}).get('message', 'Unknown error')
                return JsonResponse({
                    'success': False,
                    'error': f'API Error: {error_msg}'
                })
            
        except requests.exceptions.Timeout:
            return JsonResponse({
                'success': False,
                'error': 'AI request timed out. Please try again.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'error': 'Invalid request method'})


# ============ AUTHENTICATION ============
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect


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
        
        # Create user progress
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


# ============ LANDING PAGE ============
def landing_page(request):
    return render(request, 'landing.html')


# ============ MCQ VIEWS ============
def get_questions(request):
    language = request.GET.get('language', 'python')
    questions = Question.objects.filter(language=language, is_active=True)
    data = []
    for q in questions:
        data.append({
            'id': q.id,
            'question': q.question_text,
            'options': {
                'A': q.option_a,
                'B': q.option_b,
                'C': q.option_c,
                'D': q.option_d,
            },
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
            
            # Save user answer
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
                
                # Update user progress
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
    """Return list of user's own codes + public codes"""
    try:
        snippets = CodeSnippet.objects.filter(
            Q(user=request.user) | Q(is_public=True)
        ).order_by('-created_at')
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
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_code(request, code_id):
    """Return a specific saved code"""
    try:
        snippet = CodeSnippet.objects.get(
            Q(id=code_id) & (Q(user=request.user) | Q(is_public=True))
        )
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
    """Save code to database"""
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
            
            # Save version
            CodeVersion.objects.create(
                snippet=snippet,
                code=code,
                version_number=1
            )
            
            # Update user progress
            progress, _ = UserProgress.objects.get_or_create(user=request.user)
            progress.total_codes_written += 1
            progress.save()
            
            return JsonResponse({
                'success': True,
                'id': snippet.id,
                'message': '✅ Code saved successfully!'
            })
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
@csrf_exempt
def delete_code(request, code_id):
    """Delete code (only if owner)"""
    try:
        snippet = CodeSnippet.objects.get(id=code_id, user=request.user)
        snippet.delete()
        return JsonResponse({'success': True, 'message': 'Code deleted'})
    except CodeSnippet.DoesNotExist:
        return JsonResponse({'error': 'Code not found'}, status=404)


@login_required
@csrf_exempt
def update_code(request, code_id):
    """Update existing code"""
    if request.method == 'POST':
        try:
            snippet = CodeSnippet.objects.get(id=code_id, user=request.user)
            
            snippet.title = request.POST.get('title', snippet.title)
            snippet.code = request.POST.get('code', snippet.code)
            snippet.language = request.POST.get('language', snippet.language)
            snippet.is_public = request.POST.get('is_public', 'false') == 'true'
            snippet.save()
            
            # Save new version
            version_number = snippet.versions.count() + 1
            CodeVersion.objects.create(
                snippet=snippet,
                code=snippet.code,
                version_number=version_number
            )
            
            return JsonResponse({'success': True, 'message': 'Code updated'})
        except CodeSnippet.DoesNotExist:
            return JsonResponse({'error': 'Code not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
@csrf_exempt
def fork_code(request, code_id):
    """Fork a public code"""
    try:
        original = CodeSnippet.objects.get(id=code_id, is_public=True)
        new_title = f"Fork of {original.title}"
        
        new_code = CodeSnippet.objects.create(
            user=request.user,
            title=new_title,
            code=original.code,
            language=original.language,
            is_public=False
        )
        
        return JsonResponse({'success': True, 'id': new_code.id, 'message': 'Code forked!'})
    except CodeSnippet.DoesNotExist:
        return JsonResponse({'error': 'Code not found'}, status=404)


@login_required
def get_stats(request):
    """Get user statistics"""
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
    """Search codes by title or tags"""
    query = request.GET.get('q', '')
    codes = CodeSnippet.objects.filter(
        Q(user=request.user) & (Q(title__icontains=query) | Q(code__icontains=query))
    ).order_by('-created_at')
    
    data = [{
        'id': c.id,
        'title': c.title,
        'language': c.language,
        'created_at': c.created_at.strftime('%Y-%m-%d %H:%M')
    } for c in codes]
    
    return JsonResponse({'codes': data})


@login_required
@csrf_exempt
def like_code(request, code_id):
    """Like a public code"""
    try:
        snippet = CodeSnippet.objects.get(id=code_id, is_public=True)
        like, created = CodeLike.objects.get_or_create(
            snippet=snippet,
            user=request.user
        )
        
        if not created:
            like.delete()
            return JsonResponse({'liked': False, 'likes_count': snippet.likes.count()})
        
        return JsonResponse({'liked': True, 'likes_count': snippet.likes.count()})
    except CodeSnippet.DoesNotExist:
        return JsonResponse({'error': 'Code not found'}, status=404)


@login_required
@csrf_exempt
def comment_code(request, code_id):
    """Comment on a public code"""
    if request.method == 'POST':
        try:
            snippet = CodeSnippet.objects.get(id=code_id, is_public=True)
            comment_text = request.POST.get('comment', '')
            
            comment = CodeComment.objects.create(
                snippet=snippet,
                user=request.user,
                comment=comment_text
            )
            
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
    """Get comments for a code"""
    try:
        comments = CodeComment.objects.filter(snippet_id=code_id).order_by('-created_at')
        data = [{
            'id': c.id,
            'username': c.user.username,
            'comment': c.comment,
            'created_at': c.created_at.strftime('%Y-%m-%d %H:%M')
        } for c in comments]
        return JsonResponse({'comments': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_versions(request, code_id):
    """Get code versions"""
    try:
        snippet = CodeSnippet.objects.get(id=code_id, user=request.user)
        versions = snippet.versions.all()
        data = [{
            'version_number': v.version_number,
            'code': v.code,
            'created_at': v.created_at.strftime('%Y-%m-%d %H:%M')
        } for v in versions]
        return JsonResponse({'versions': data})
    except CodeSnippet.DoesNotExist:
        return JsonResponse({'error': 'Code not found'}, status=404)


# ============ BULK UPLOAD FUNCTIONS ============
import csv
import io

@login_required
def bulk_upload_questions(request):
    """Bulk upload questions from CSV"""
    if request.method == 'POST':
        # Only admin can upload
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
            error_count = 0
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
                    error_count += 1
                    errors.append(f"Row {row_num}: {str(e)}")
            
            return JsonResponse({
                'success': True,
                'message': f'✅ Uploaded {success_count} questions successfully!',
                'errors': errors[:10] if errors else None
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)})
    
    return render(request, 'bulk_upload.html')


def download_sample_csv(request):
    """Download sample CSV file"""
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