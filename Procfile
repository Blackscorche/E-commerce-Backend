web: python manage.py migrate && gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 120 --access-logfile - --error-logfile - src.wsgi:application

