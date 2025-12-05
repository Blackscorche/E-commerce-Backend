web: python3 manage.py migrate --noinput || true && python3 -m gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 120 --access-logfile - --error-logfile - src.wsgi:application

