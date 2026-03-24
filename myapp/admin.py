from django.contrib import admin
from .models import (
    CodeSnippet, CodeVersion, QuestionCategory, Question,
    UserProgress, UserAnswer, CodeComment, CodeLike,
    DailyChallenge, UserChallengeProgress, UserTopicProgress,
    Achievement, UserAchievement, Leaderboard, QuestionHint
)

@admin.register(CodeSnippet)
class CodeSnippetAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'language', 'is_public', 'created_at')  
    list_filter = ('language', 'is_public', 'created_at')
    search_fields = ('title', 'code', 'user__username')

@admin.register(CodeVersion)
class CodeVersionAdmin(admin.ModelAdmin):
    list_display = ('snippet', 'version_number', 'created_at')

@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'created_at')
    search_fields = ('name',)

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'category', 'language', 'difficulty', 'topic', 'points', 'is_active')
    list_filter = ('category', 'language', 'difficulty', 'topic', 'is_active')
    search_fields = ('question_text',)
    fieldsets = (
        ('Question Details', {
            'fields': ('category', 'question_text', 'language', 'difficulty', 'topic', 'sub_topic', 'tags', 'points')
        }),
        ('Options', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_option')
        }),
        ('Solution', {
            'fields': ('explanation', 'solution_code', 'solution_explanation', 'video_link')
        }),
        ('Stats', {
            'fields': ('likes', 'solved_count', 'is_active', 'created_by')
        }),
    )


# ============ USER PROGRESS MODELS ============

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_codes_written', 'total_runs', 'total_points', 'streak_days')
    list_filter = ('streak_days',)
    search_fields = ('user__username',)

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'is_correct', 'points_earned', 'attempted_at')
    list_filter = ('is_correct', 'attempted_at')
    search_fields = ('user__username', 'question__question_text')


# ============ CODE INTERACTION MODELS ============

@admin.register(CodeComment)
class CodeCommentAdmin(admin.ModelAdmin):
    list_display = ('snippet', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('snippet__title', 'user__username')

@admin.register(CodeLike)
class CodeLikeAdmin(admin.ModelAdmin):
    list_display = ('snippet', 'user', 'created_at')
    list_filter = ('created_at',)


# ============ NEW ADVANCED FEATURES MODELS ============

@admin.register(DailyChallenge)
class DailyChallengeAdmin(admin.ModelAdmin):
    list_display = ('date', 'question', 'participants', 'completions')
    list_filter = ('date',)
    search_fields = ('question__question_text',)

@admin.register(UserChallengeProgress)
class UserChallengeProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'challenge', 'completed', 'score', 'completed_at')
    list_filter = ('completed', 'challenge__date')
    search_fields = ('user__username',)

@admin.register(UserTopicProgress)
class UserTopicProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'topic', 'questions_solved', 'correct_answers', 'mastery_level')
    list_filter = ('topic',)
    search_fields = ('user__username',)

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'points_required', 'questions_required', 'streak_required')
    list_filter = ('points_required',)
    search_fields = ('name',)

@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'earned_at')
    list_filter = ('earned_at',)
    search_fields = ('user__username', 'achievement__name')

@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_points', 'questions_solved', 'correct_answers', 'rank')
    list_filter = ('rank',)
    ordering = ('-total_points',)
    search_fields = ('user__username',)

@admin.register(QuestionHint)
class QuestionHintAdmin(admin.ModelAdmin):
    list_display = ('question', 'hint_number', 'hint_text', 'points_cost')
    list_filter = ('question__language', 'question__difficulty')
    search_fields = ('question__question_text',)