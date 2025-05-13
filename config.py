import os

# Основные пути и директории
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
PDF_FOLDER = os.path.join(BASE_DIR, 'pdf')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

# Ограничения размеров файлов
FILE_LIMIT_MB = 100
FILE_LIMIT_BYTES = FILE_LIMIT_MB * 1024 * 1024

# Токены и API
TOKEN = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
API_URL = f'https://api.telegram.org/bot{TOKEN}'

# Логин и пароль для почты
SENDER_EMAIL = 'XXXXXXXXXXXXXXX'
EMAIL_PASSWORD = 'XXXXXXXXXXXXXXX'

# Почта получателя
RECEIVER_EMAILS = ['XXXXXXXXXXXXX'] #если их несколько, то добаляем через запятую
