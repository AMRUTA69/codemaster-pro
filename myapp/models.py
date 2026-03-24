# Create your models here.
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class CodeSnippet(models.Model):
    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('javascript', 'JavaScript'),
        ('java', 'Java'),
        ('cpp', 'C++'),
        ('c', 'C'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='codesnippets')
    title = models.CharField(max_length=200, default='Untitled')
    code = models.TextField()
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='python')
    output = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=False)  # Public/Private code sharing
    is_favorite = models.BooleanField(default=False)  # Favorite codes
    tags = models.CharField(max_length=500, blank=True, help_text="Comma separated tags")  # Code tags
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.language}"
    
    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    class Meta:
        ordering = ['-updated_at', '-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['language', 'is_public']),
        ]


class CodeVersion(models.Model):
    snippet = models.ForeignKey(CodeSnippet, on_delete=models.CASCADE, related_name='versions')
    code = models.TextField()
    version_number = models.IntegerField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-version_number']
    
    def __str__(self):
        return f"{self.snippet.title} - v{self.version_number}"


# ============ MCQ MODELS ============
class QuestionCategory(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='📘')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Question Categories"
        ordering = ['name']


class Question(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    
    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('javascript', 'JavaScript'),
        ('java', 'Java'),
        ('cpp', 'C++'),
        ('c', 'C'),
        ('all', 'All Languages'),
    ]
    
    TOPIC_CHOICES = [
        ('general', 'General'),
        ('arrays', 'Arrays'),
        ('strings', 'Strings'),
        ('linked_list', 'Linked List'),
        ('trees', 'Trees'),
        ('graphs', 'Graphs'),
        ('dynamic_programming', 'Dynamic Programming'),
        ('sorting', 'Sorting'),
        ('searching', 'Searching'),
        ('recursion', 'Recursion'),
        ('oop', 'Object Oriented Programming'),
        ('functions', 'Functions'),
        ('loops', 'Loops'),
        ('conditionals', 'Conditionals'),
    ]
    
    category = models.ForeignKey(QuestionCategory, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    question_text = models.TextField()
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)
    correct_option = models.CharField(max_length=1, choices=[
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ])
    explanation = models.TextField(blank=True)
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='python')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    points = models.IntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_questions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ============ NEW FIELDS ============
    topic = models.CharField(max_length=50, choices=TOPIC_CHOICES, default='general')
    sub_topic = models.CharField(max_length=100, blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma separated tags")
    likes = models.IntegerField(default=0)
    solved_count = models.IntegerField(default=0)
    solution_code = models.TextField(blank=True, help_text="Solution code for the question")
    solution_explanation = models.TextField(blank=True, help_text="Detailed solution explanation")
    video_link = models.URLField(blank=True, help_text="YouTube video link for solution")
    
    def __str__(self):
        return f"{self.get_language_display()} - {self.question_text[:50]}"
    
    def get_options_dict(self):
        return {
            'A': self.option_a,
            'B': self.option_b,
            'C': self.option_c,
            'D': self.option_d,
        }
    
    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['language', 'difficulty']),
            models.Index(fields=['is_active']),
            models.Index(fields=['topic']),
        ]


class UserProgress(models.Model):
    """Track user's progress in coding"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coding_progress')
    total_codes_written = models.IntegerField(default=0)
    total_runs = models.IntegerField(default=0)
    total_questions_attempted = models.IntegerField(default=0)
    total_correct_answers = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_active = models.DateField(auto_now=True)
    favorite_language = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Progress"
    
    def update_streak(self):
        from datetime import date, timedelta
        if self.last_active == date.today() - timedelta(days=1):
            self.streak_days += 1
        elif self.last_active != date.today():
            self.streak_days = 1
        self.save()
    
    class Meta:
        verbose_name_plural = "User Progress"


class UserAnswer(models.Model):
    """Store user's answers to questions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='user_answers')
    selected_option = models.CharField(max_length=1)
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    attempted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.question.question_text[:30]}"
    
    class Meta:
        unique_together = ['user', 'question']
        ordering = ['-attempted_at']


class CodeComment(models.Model):
    """Allow users to comment on public codes"""
    snippet = models.ForeignKey(CodeSnippet, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='code_comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Comment by {self.user.username} on {self.snippet.title}"
    
    class Meta:
        ordering = ['-created_at']


class CodeLike(models.Model):
    """Allow users to like public codes"""
    snippet = models.ForeignKey(CodeSnippet, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='code_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['snippet', 'user']
    
    def __str__(self):
        return f"{self.user.username} liked {self.snippet.title}"


# ============ NEW MODELS FOR ADVANCED FEATURES ============

class DailyChallenge(models.Model):
    """Daily coding challenge"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='daily_challenges')
    date = models.DateField(unique=True)
    participants = models.IntegerField(default=0)
    completions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Challenge for {self.date}"
    
    class Meta:
        ordering = ['-date']


class UserChallengeProgress(models.Model):
    """Track user's daily challenge progress"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenge_progress')
    challenge = models.ForeignKey(DailyChallenge, on_delete=models.CASCADE, related_name='user_progress')
    completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'challenge']
    
    def __str__(self):
        return f"{self.user.username} - {self.challenge.date}"


class UserTopicProgress(models.Model):
    """Track user's progress per topic"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topic_progress')
    topic = models.CharField(max_length=50)
    questions_solved = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    mastery_level = models.IntegerField(default=0)  # 0-100
    
    class Meta:
        unique_together = ['user', 'topic']
    
    def __str__(self):
        return f"{self.user.username} - {self.topic}: {self.mastery_level}%"
    
    def update_mastery(self):
        if self.questions_solved > 0:
            self.mastery_level = int((self.correct_answers / self.questions_solved) * 100)
            self.save()


class Achievement(models.Model):
    """Achievements/Badges for users"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='🏆')
    points_required = models.IntegerField(default=0)
    questions_required = models.IntegerField(default=0)
    streak_required = models.IntegerField(default=0)
    codes_required = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['points_required']


class UserAchievement(models.Model):
    """User earned achievements"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='users')
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'achievement']
    
    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"


class Leaderboard(models.Model):
    """User ranking"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='leaderboard_entry')
    total_points = models.IntegerField(default=0)
    questions_solved = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    codes_written = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.total_points} points"
    
    class Meta:
        ordering = ['-total_points']


class QuestionHint(models.Model):
    """Hints for questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='hints')
    hint_text = models.TextField()
    hint_number = models.IntegerField(default=1)
    points_cost = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Hint {self.hint_number} for {self.question.question_text[:30]}"
    
    class Meta:
        ordering = ['hint_number']
        unique_together = ['question', 'hint_number']