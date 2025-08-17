import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sql_practice.settings')
django.setup()

User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='pboruah',
        email='prinjalboruah@gmail.com',
        password='DapGit@2025'
    )
    print("Superuser created!")
else:
    print("Superuser already exists.")
