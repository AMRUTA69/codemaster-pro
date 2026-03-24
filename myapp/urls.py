from django.urls import path
from myapp import views

urlpatterns = [
    # Landing & Home
    path('', views.landing_page, name='landing'),
    path('compiler/', views.home, name='home'),
    
    # Authentication
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Code Execution
    path('run-code/', views.run_code, name='run_code'),
    
    # AI Assistant
    path('ai-assistant/', views.ai_assistant, name='ai_assistant'),
    
    # Code Management
    path('save-code/', views.save_code, name='save_code'),
    path('my-codes/', views.get_my_codes, name='my_codes'),
    path('get-code/<int:code_id>/', views.get_code, name='get_code'),
    path('delete-code/<int:code_id>/', views.delete_code, name='delete_code'),
    path('update-code/<int:code_id>/', views.update_code, name='update_code'),
    path('fork-code/<int:code_id>/', views.fork_code, name='fork_code'),
    path('search-codes/', views.search_codes, name='search_codes'),
    
    # Statistics
    path('get-stats/', views.get_stats, name='get_stats'),
    
    # Interactive Features
    path('like-code/<int:code_id>/', views.like_code, name='like_code'),
    path('comment-code/<int:code_id>/', views.comment_code, name='comment_code'),
    path('get-comments/<int:code_id>/', views.get_comments, name='get_comments'),
    
    # Version Control
    path('get-versions/<int:code_id>/', views.get_versions, name='get_versions'),
    
    # MCQ / Questions
    path('get-questions/', views.get_questions, name='get_questions'),
    path('check-answer/', views.check_answer, name='check-answer'),
    
    # ============ BULK UPLOAD (NEW) ============
    path('bulk-upload/', views.bulk_upload_questions, name='bulk_upload'),
    path('sample-csv/', views.download_sample_csv, name='sample_csv'),
]