cd /home/ati/fleet_manager
poetry run uvicorn --reload app.main:app --host 0.0.0.0
redis-cli flushall && rm -rf logs && poetry run python main.py  # (in another window)