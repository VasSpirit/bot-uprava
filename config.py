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
TOKEN = '7462117397:AAGTDHHJAJnJ1oJWBsRA5BZQ_W0VwHDfMSY'
API_URL = f'https://api.telegram.org/bot{TOKEN}'

# Логин и пароль для почты
SENDER_EMAIL = 'eslicey@mail.ru'
EMAIL_PASSWORD = '4TUZ20STrqgj6CLXQG4u'

# Почта получателя
RECEIVER_EMAILS = ['vas_spirit@live.com'] #если их несколько, то добаляем через запятую