from app import create_app
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3002)
