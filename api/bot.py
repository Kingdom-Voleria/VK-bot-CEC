from http.server import BaseHTTPRequestHandler
import json
import os
from dotenv import load_dotenv
import vk_api
import hmac
import hashlib

load_dotenv()

TOKEN = os.getenv("VK_GROUP_TOKEN")
SECRET_KEY = os.getenv("VK_SECRET_KEY", "your_secret_key")
ADMIN_ID = 443835275

# Глобальные переменные для хранения состояния (в продакшене лучше использовать базу данных)
user_states = {}

def generate_keyboard(labels, one_time=False):
    return json.dumps({
        "one_time": one_time,
        "buttons": [[{"action": {"type": "text", "label": label}, "color": "secondary"}] for label in labels]
    }, ensure_ascii=False)

def get_keyboard():
    return json.dumps({
        "one_time": False,
        "buttons": [[
            {"action": {"type": "text", "label": "Вопрос с гражданством", "payload": '{"button": "1"}'}, "color": "primary"},
            {"action": {"type": "text", "label": "Вопрос с сайтом", "payload": '{"button": "2"}'}, "color": "primary"}
        ]]
    }, ensure_ascii=False)

def get_back_to_main_keyboard():
    return generate_keyboard(["В главное меню"])

def reset_user(user_id):
    if user_id in user_states:
        del user_states[user_id]

def send_message(vk, user_id, message, keyboard=None):
    try:
        vk.messages.send(
            user_id=user_id,
            message=message,
            keyboard=keyboard,
            random_id=0
        )
        return True
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        return False

def handle_message(vk, user_id, message_text):
    """Обработка входящего сообщения"""
    user_id = str(user_id)
    
    # Загружаем ответы
    try:
        with open("citizenship_responses.json", "r", encoding="utf-8") as f:
            citizenship_responses = json.load(f)
        with open("site_responses.json", "r", encoding="utf-8") as f:
            site_responses = json.load(f)
    except FileNotFoundError:
        # Если файлы не найдены, используем базовые ответы
        citizenship_responses = {
            "Стать гос. служащим": "Для подачи заявки на госслужбу, пожалуйста, опишите ваши навыки и опыт работы.",
            "Отказ от гражданства": "Для отказа от гражданства необходимо подать официальное заявление. Опишите причину отказа.",
            "Жалоба/предложение": "Спасибо за ваше обращение. Опишите подробнее вашу жалобу или предложение.",
            "Другая проблема": "Опишите вашу проблему, и мы постараемся помочь."
        }
        site_responses = {
            "Подтвердить заявку на сайте": "Для подтверждения заявки на сайте, пожалуйста, укажите номер заявки и опишите проблему.",
            "Зарегистрировать партию на выборы": "Для регистрации партии на выборы, пожалуйста, предоставьте необходимую информацию.",
            "Подать заявку на проведение голосования": "Для подачи заявки на проведение голосования, опишите детали мероприятия.",
            "Сообщить об ошибке": "Спасибо за сообщение об ошибке. Опишите, что произошло и на какой странице.",
            "Жалоба/предложение": "Спасибо за ваше обращение. Опишите подробнее вашу жалобу или предложение.",
            "Другая проблема": "Опишите вашу проблему, и мы постараемся помочь."
        }

    # Проверяем, новый ли пользователь
    if user_id not in user_states:
        user_states[user_id] = {"known": True, "state": None}
        welcome_message = "👋 Здравствуйте, гражданин Королевства Волерия! \nРады приветствовать вас в официальном сообществе нашего великого государства. \nЗдесь вы можете получить помощь по вопросам гражданства и сайту, а также оставить свои обращения и предложения. \n⬇️ Выберите нужный раздел в меню ниже, и я с радостью помогу вам!"
        send_message(vk, user_id, welcome_message, get_keyboard())
        return

    # Обработка команд
    if message_text == "Вопрос с гражданством":
        keyboard = generate_keyboard(list(citizenship_responses.keys()))
        send_message(vk, user_id, "🛂 Пожалуйста, выберите один из доступных вопросов, чтобы я мог помочь вам с информацией и поддержкой по вопросам гражданства Королевства Волерия.", keyboard)
        return

    if message_text == "Вопрос с сайтом":
        keyboard = generate_keyboard(list(site_responses.keys()))
        send_message(vk, user_id, "🌐 Пожалуйста, выберите интересующий вас вопрос, связанный с работой сайта, чтобы получить помощь или оставить обращение.", keyboard)
        return

    if message_text in ("Назад", "В главное меню"):
        reset_user(user_id)
        send_message(vk, user_id, "🔙 Вы вернулись в главное меню. Выберите действие из списка ниже, чтобы продолжить.", get_keyboard())
        return

    # Обработка ответов по гражданству
    citizenship_map = {
        "Стать гос. служащим": "awaiting_application",
        "Отказ от гражданства": "awaiting_citizenship_refusal",
        "Жалоба/предложение": "awaiting_citizenship_feedback",
        "Другая проблема": "awaiting_citizenship_other"
    }

    if message_text in citizenship_responses:
        user_states[user_id]["state"] = citizenship_map.get(message_text)
        response_message = citizenship_responses.get(message_text, "")
        if response_message:
            send_message(vk, user_id, response_message, get_back_to_main_keyboard())
        return

    # Обработка ответов по сайту
    site_map = {
        "Подтвердить заявку на сайте": "awaiting_site_request",
        "Зарегистрировать партию на выборы": "awaiting_party_registration",
        "Подать заявку на проведение голосования": "awaiting_vote_request",
        "Сообщить об ошибке": "awaiting_error_report",
        "Жалоба/предложение": "awaiting_site_feedback",
        "Другая проблема": "awaiting_site_other"
    }

    if message_text in site_responses:
        user_states[user_id]["state"] = site_map.get(message_text)
        response_message = site_responses.get(message_text, "")
        if response_message:
            send_message(vk, user_id, response_message, get_back_to_main_keyboard())
        return

    # Обработка пользовательского ввода в зависимости от состояния
    current_state = user_states[user_id].get("state")
    if current_state:
        state_labels = {
            "awaiting_application": "Заявка на госслужбу",
            "awaiting_citizenship_refusal": "Отказ от гражданства",
            "awaiting_citizenship_feedback": "Жалоба/предложение (гражданство)",
            "awaiting_citizenship_other": "Другая проблема (гражданство)",
            "awaiting_site_request": "Подтверждение заявки на сайте",
            "awaiting_party_registration": "Заявка на регистрацию партии",
            "awaiting_vote_request": "Заявка на проведение голосования",
            "awaiting_error_report": "Сообщение об ошибке на сайте",
            "awaiting_site_feedback": "Жалоба/предложение (сайт)",
            "awaiting_site_other": "Другая проблема (сайт)"
        }
        
        label = state_labels.get(current_state, "Обращение")
        
        # Отправляем сообщение администратору
        admin_message = f"📩 {label}:\n\n{message_text}"
        send_message(vk, ADMIN_ID, admin_message)
        
        # Подтверждаем пользователю
        send_message(vk, user_id, "✅ Обращение отправлено! Администрация рассмотрит его в ближайшее время.", get_back_to_main_keyboard())
        
        # Сбрасываем состояние
        user_states[user_id]["state"] = None
        return

    # Если команда не распознана
    send_message(vk, user_id, "Команда не распознана. Выберите действие:", get_keyboard())

def verify_vk_signature(request_body, vk_signature):
    """Проверка подписи VK для безопасности"""
    if not SECRET_KEY or SECRET_KEY == "your_secret_key":
        return True  # Пропускаем проверку в режиме разработки
    
    expected_signature = "sha256=" + hmac.new(
        SECRET_KEY.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, vk_signature)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработка GET запросов (для проверки работоспособности)"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            "status": "success",
            "message": "VK Bot API is running",
            "bot_status": "active",
            "endpoint": "/api/bot"
        }
        
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode())
        return

    def do_POST(self):
        """Обработка POST запросов от VK"""
        try:
            # Получаем размер тела запроса
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length)
            
            # Проверяем подпись VK (если настроена)
            vk_signature = self.headers.get('X-Vk-Signature', '')
            if not verify_vk_signature(request_body, vk_signature):
                self.send_response(403)
                self.end_headers()
                return
            
            # Парсим JSON
            data = json.loads(request_body.decode('utf-8'))
            
            # Проверяем тип события
            if data.get('type') == 'confirmation':
                # Подтверждение вебхука
                confirmation_code = os.getenv("VK_CONFIRMATION_CODE", "default_code")
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(confirmation_code.encode())
                return
            
            elif data.get('type') == 'message_new':
                # Новое сообщение
                if not TOKEN:
                    self.send_response(500)
                    self.end_headers()
                    return
                
                try:
                    vk_session = vk_api.VkApi(token=TOKEN)
                    vk = vk_session.get_api()
                    
                    # Извлекаем данные сообщения
                    message_obj = data.get('object', {})
                    user_id = message_obj.get('from_id')
                    message_text = message_obj.get('text', '')
                    
                    if user_id and message_text:
                        # Обрабатываем сообщение
                        handle_message(vk, user_id, message_text)
                    
                    # Отвечаем VK
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write('ok'.encode())
                    
                except Exception as e:
                    print(f"Ошибка обработки сообщения: {e}")
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write('ok'.encode())
                
                return
            
            else:
                # Неизвестный тип события
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write('ok'.encode())
                return
                
        except Exception as e:
            print(f"Ошибка обработки POST запроса: {e}")
            self.send_response(500)
            self.end_headers()
            return

    def log_message(self, format, *args):
        """Отключаем логирование для Vercel"""
        pass
