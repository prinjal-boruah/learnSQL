from django.contrib import admin
from .models import Topic, Question, Progress

# --- Inline for Questions under a Topic (collapsible + sortable) ---
class QuestionInline(admin.TabularInline):
    model = Question
    fields = ('title', 'slug', 'difficulty', 'is_active')
    readonly_fields = ()
    extra = 0
    show_change_link = True
    prepopulated_fields = {"slug": ("title",)}
    classes = ['collapse']
    ordering = ('difficulty', 'title')  # sort questions by difficulty then title

# --- Topic admin with collapsible & sorted questions inline ---
@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active')
    prepopulated_fields = {"slug": ("title",)}
    list_filter = ('is_active',)
    search_fields = ('title',)
    inlines = [QuestionInline]

# --- Question admin (standalone) ---
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic_title', 'difficulty', 'is_active')
    list_filter = ('topic', 'difficulty', 'is_active')  # filter by topic + difficulty
    search_fields = ('title', 'prompt_md')
    prepopulated_fields = {"slug": ("title",)}
    ordering = ('topic__title', 'difficulty', 'title')  # default ordering in list view

    def topic_title(self, obj):
        return obj.topic.title
    topic_title.admin_order_field = 'topic'
    topic_title.short_description = 'Topic'

# --- Progress admin ---
@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'completed', 'last_attempted')
    list_filter = ('completed', 'question__topic')  # filter by topic
    search_fields = ('user__username', 'question__title')
    ordering = ('-last_attempted',)
