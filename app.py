import os
import json
import random
import string
import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from flask_cors import CORS
from firebase_admin import credentials, initialize_app, db
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

app = Flask(__name__)
# Разрешаем запросы с твоего сайта на Neocities (CORS)
CORS(app)

# ==========================================
# НАСТРОЙКА FIREBASE
# ==========================================
# Убедись, что файл serviceAccount.json лежит в той же папке, что и app.py
SERVICE_ACCOUNT_FILE = "serviceAccount.json"
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    raise FileNotFoundError(f"Файл {SERVICE_ACCOUNT_FILE} не найден! Скачай его в консоли Firebase.")

cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
initialize_app(cred, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
})

# ==========================================
# НАСТРОЙКА ПОЧТЫ (GMAIL)
# ==========================================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv('SENDER_EMAIL')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')

def generate_access_code(length=6):
    """Генерирует случайный код из заглавных букв и цифр."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(random.choices(alphabet, k=length))

def send_email(recipient_email: str, access_code: str) -> bool:
    """Отправляет письмо с кодом доступа."""
    msg = MIMEText(
        f"Здравствуйте!\n\n"
        f"Ваш код доступа к системе АО «Диплом Инвестмент Групп»: {access_code}\n\n"
        f"Код действителен для одного входа. Введите его на странице входа.\n\n"
        f"С уважением,\nАдминистрация АО ДИГ"
    )
    msg['Subject'] = "Код доступа к конспектам команды"
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
        return False

# ==========================================
# ОСНОВНОЙ ЭНДПОИНТ
# ==========================================
@app.route('/request_code', methods=['POST'])
def request_code():
    data = request.get_json()
    
    if not data or 'fullName' not in data:
        return jsonify({"message": "Ошибка: не указано имя (fullName)"}), 400

    full_name = data['fullName'].strip()
    
    # Ищем пользователя в базе данных Firebase
    users_ref = db.reference('users')
    # Ищем по точному совпадению fullName
    result = users_ref.order_by_child('fullName').equal_to(full_name).get()

    if not result:
        return jsonify({"message": "Пользователь не найден в базе. Проверьте ФИО или обратитесь к лидеру."}), 404

    # Получаем данные первого найденного пользователя
    user_data = list(result.values())[0]
    user_email = user_data.get('email')

    if not user_email:
        return jsonify({"message": "У пользователя не указана почта."}), 500

    # Генерируем код и сохраняем его в Firebase
    code = generate_access_code()
    code_ref = db.reference(f'access_codes/{code}')
    code_ref.set({
        'email': user_email,
        'fullName': full_name,
        'used': False,
        'created_at': db.ServerValue.TIMESTAMP
    })

    # Отправляем письмо
    if send_email(user_email, code):
        return jsonify({"message": f"Код успешно отправлен на почту {user_email}!"}), 200
    else:
        return jsonify({"message": "Код сгенерирован, но произошла ошибка при отправке письма."}), 500

if __name__ == '__main__':
    print("🚀 Сервер запущен! Ожидание запросов...")
    app.run(debug=True, host='0.0.0.0', port=5000)
