import os

broker_url = os.getenv("CELERY_BROKER", "redis://")
result_backend = os.getenv("CELERY_BACKEND", "redis://")
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Europe/Oslo'
enable_utc = True
