set -e
start()
{
    echo "starting sanjaya app_main "
    poetry run uvicorn app.app_main:app --host 0.0.0.0 --port 8003 2>&1 &
}


start
tail -f /dev/null