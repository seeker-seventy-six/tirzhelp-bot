web: gunicorn --worker-class gevent --workers=1 bot:app
release: python bot.py --delete-webhook && python bot.py --set-webhook && python bot.py --check-webhook
