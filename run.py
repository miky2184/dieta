#run.py
from app import create_app
from dotenv import load_dotenv
import os

# Carica le variabili d'ambiente dal file .env
load_dotenv()

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host=os.getenv('WEBAPP_HOST'), port=os.getenv('WEBAPP_PORT'))
