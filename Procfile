web: python -c "import os,seed; seed.main() if not os.path.exists('varaz.db') else None" && gunicorn app:app --bind 0.0.0.0:$PORT
