source env.sh
poetry run uvicorn --reload app.main:app --host 0.0.0.0 > /tmp/temp.out 2>&1 &
redis-cli flushall && rm -rf logs 
poetry run python /app/main.py > /tmp/temp.out 2>&1  # (in another window)