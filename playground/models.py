from django.db import models
from django.contrib.auth.models import User
import json

DIFFICULTY_CHOICES = [
    ('Easy', 'Easy'),
    ('Medium', 'Medium'),
    ('Hard', 'Hard'),
]

class Topic(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    seed_sql = models.TextField(help_text="SQL to setup tables and data for this topic")

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class Question(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions")
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    prompt_md = models.TextField()
    seed_sql_override = models.TextField(
        blank=True, null=True,
        help_text="Optional SQL to override topic seed"
    )
    checker_sql = models.TextField(help_text="SQL to check correct answer")
    alternate_checker_sqls = models.TextField(
        blank=True, null=True,
        help_text="Optional JSON list of alternate correct SQLs"
    )
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default='Easy'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['topic', 'title']

    def get_alternate_checker_sqls(self):
        """Return alternate checker SQLs as a Python list."""
        if self.alternate_checker_sqls:
            try:
                return json.loads(self.alternate_checker_sqls)
            except json.JSONDecodeError:
                return []
        return []

    def __str__(self):
        return f"{self.topic.title} - {self.title}"


class Progress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="progress_entries")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="progress_entries")
    completed = models.BooleanField(default=False)
    last_attempted = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'question')
        ordering = ['-last_attempted']

    def __str__(self):
        return f"{self.user.username} - {self.question.title} - {'Done' if self.completed else 'Pending'}"
