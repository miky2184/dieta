import os


def printer(text):
    if os.getenv('LOG_LEVEL') == 'DEBUG':
        print(text)