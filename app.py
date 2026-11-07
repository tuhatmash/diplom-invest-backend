import os
import json
import random
import string
from flask import Flask, request, jsonify
from flask_cors import CORS
from firebase_admin import credentials, initialize_app, db

app = Flask(__name__)
CORS(app)

# Инициализация Firebase
firebase_creds_json = os.getenv('FIREBASE_CREDENTIALS')
if firebase_creds_json:
    cred_dict = json.loads(firebase_creds_json)
    cred = credentials.Certificate(cred_dict)
else:
    cred = credentials.Certificate("serviceAccount.json")

initialize_app(cred, {
    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
})

def generate_access_code(length=6):
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(random.choices(alphabet, k=length))

@app.route('/request_code', methods=['POST'])
def request_code():
    data = request.get_json()
    if not data or 'fullName' not in data:
        return jsonify({"message": "Ошибка: не указано имя"}), 400

    full_name = data['fullName'].strip()
    
    # Ищем пользователя в базе
    users_ref = db.reference('users')
    result = users_ref.order_by_child('fullName').equal_to(full_name).get()

    if not result:
        return jsonify({"message": "Пользователь не найден в базе. Проверьте ФИО."}), 404

    user_data = list(result.values())[0]
    
    # Генерируем код
    code = generate_access_code()
    code_ref = db.reference(f'access_codes/{code}')
    code_ref.set({
        'email': user_data.get('email', 'no-email'),
        'fullName': full_name,
        'used': False
    })

    # Просто возвращаем код на сайт!
    return jsonify({
        "message": "Код успешно сгенерирован!", 
        "code": code
    }), 200

if __name__ == '__main__':
    print("🚀 Сервер запущен!")
    app.run(debug=True, host='0.0.0.0', port=5000)
