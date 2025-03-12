#run.py
import os
from flask import request, redirect

from dotenv import load_dotenv

from app import create_app

# Carica le variabili d'ambiente dal file .env
load_dotenv()

app = create_app()

@app.before_request
def before_request():
    if os.getenv('FLASK_ENV', 'dev') == 'prd':
        if request.headers.get("X-Forwarded-Proto", "http") == "http":
            return redirect(request.url.replace("http://", "https://", 1), code=301)

if __name__ == '__main__':
    app.run(debug=True, host=os.getenv('WEBAPP_HOST'), port=os.getenv('WEBAPP_PORT'))
