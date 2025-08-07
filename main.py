import os
import json
import logging
from dotenv import load_dotenv
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("VK_GROUP_TOKEN")
KNOWN_USERS_FILE = "known_users.txt"
ADMIN_ID = 443835275


def load_known_users():
    if not os.path.exists(KNOWN_USERS_FILE):
        return set()
    with open(KNOWN_USERS_FILE, "r") as file:
        return set(line.strip() for line in file)


def save_known_user(user_id):
    with open(KNOWN_USERS_FILE, "a") as file:
        file.write(f"{user_id}\n")


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

def safe_send_message(vk, user_id, message, keyboard=None, random_id=0):
    """Безопасная отправка сообщения с обработкой ошибок"""
    try:
        if keyboard:
            vk.messages.send(user_id=user_id, message=message, keyboard=keyboard, random_id=random_id)
        else:
            vk.messages.send(user_id=user_id, message=message, random_id=random_id)
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        return False


def main():
    if not TOKEN:
        print("Токен не найден. Проверьте переменную окружения VK_GROUP_TOKEN")
        return

    try:
        vk_session = vk_api.VkApi(token=TOKEN)
        longpoll = VkLongPoll(vk_session)
        vk = vk_session.get_api()
        known_users = load_known_users()
    except Exception as e:
        print(f"Ошибка при инициализации VK API: {e}")
        return

    # Проверяем подключение к VK API
    try:
        vk.groups.getById()
        print("Подключение к VK API успешно установлено")
    except Exception as e:
        print(f"Ошибка при проверке подключения к VK API: {e}")
        return

    user_states = {
        "awaiting_application": set(),
        "awaiting_citizenship_refusal": set(),
        "awaiting_citizenship_feedback": set(),
        "awaiting_site_feedback": set(),
        "awaiting_citizenship_other": set(),
        "awaiting_site_other": set(),
        "awaiting_site_request": set(),
        "awaiting_party_registration": set(),
        "awaiting_vote_request": set(),
        "awaiting_error_report": set(),
    }

    logger.info("Бот запущен")

    try:
        with open("citizenship_responses.json", "r", encoding="utf-8") as f:
            citizenship_responses = json.load(f)
    except FileNotFoundError:
        print("Ошибка: файл citizenship_responses.json не найден")
        citizenship_responses = {}
    
    try:
        with open("site_responses.json", "r", encoding="utf-8") as f:
            site_responses = json.load(f)
    except FileNotFoundError:
        print("Ошибка: файл site_responses.json не найден")
        site_responses = {}

    def reset_user(user_id):
        for state in user_states.values():
            state.discard(user_id)

    def handle_response(event, message_dict, category_map):
        try:
            message = message_dict.get(event.text, "")
            if event.text in category_map:
                user_states[category_map[event.text]].add(str(event.user_id))
            if message:
                safe_send_message(vk, event.user_id, message, keyboard=get_back_to_main_keyboard())
        except Exception as e:
            logger.error(f"Ошибка в handle_response: {e}")
            # Отправляем сообщение об ошибке пользователю
            safe_send_message(vk, event.user_id, "Произошла ошибка при обработке запроса. Попробуйте позже.", keyboard=get_keyboard())

    for event in longpoll.listen():
        try:
            # Обрабатываем только новые сообщения, адресованные боту
            if event.type != VkEventType.MESSAGE_NEW or not event.to_me:
                continue
                
            user_id = str(event.user_id)
            msg = event.text.strip() if event.text else ""

            # Пропускаем пустые сообщения
            if not msg:
                continue

            logger.info(f"Сообщение от {user_id}: {msg}")

            if user_id not in known_users:
                safe_send_message(vk, event.user_id, "👋 Здравствуйте, гражданин Королевства Волерия! \nРады приветствовать вас в официальном сообществе нашего великого государства. \nЗдесь вы можете получить помощь по вопросам гражданства и сайту, а также оставить свои обращения и предложения. \n⬇️ Выберите нужный раздел в меню ниже, и я с радостью помогу вам!", keyboard=get_keyboard())
                save_known_user(user_id)
                known_users.add(user_id)
                continue

            if msg == "Вопрос с гражданством":
                keyboard = generate_keyboard(list(citizenship_responses.keys()))
                safe_send_message(vk, event.user_id, "🛂 Пожалуйста, выберите один из доступных вопросов, чтобы я мог помочь вам с информацией и поддержкой по вопросам гражданства Королевства Волерия.", keyboard=keyboard)
                continue

            if msg == "Вопрос с сайтом":
                keyboard = generate_keyboard(list(site_responses.keys()))
                safe_send_message(vk, event.user_id, "🌐 Пожалуйста, выберите интересующий вас вопрос, связанный с работой сайта, чтобы получить помощь или оставить обращение.", keyboard=keyboard)
                continue

            if msg in ("Назад", "В главное меню"):
                reset_user(user_id)
                safe_send_message(vk, event.user_id, "🔙 Вы вернулись в главное меню. Выберите действие из списка ниже, чтобы продолжить.", keyboard=get_keyboard())
                continue

            citizenship_map = {
                "Стать гос. служащим": "awaiting_application",
                "Отказ от гражданства": "awaiting_citizenship_refusal",
                "Жалоба/предложение": "awaiting_citizenship_feedback",
                "Другая проблема": "awaiting_citizenship_other"
            }
            if msg in citizenship_responses:
                handle_response(event, citizenship_responses, citizenship_map)
                continue

            site_map = {
                "Подтвердить заявку на сайте": "awaiting_site_request",
                "Зарегистрировать партию на выборы": "awaiting_party_registration",
                "Подать заявку на проведение голосования": "awaiting_vote_request",
                "Сообщить об ошибке": "awaiting_error_report",
                "Жалоба/предложение": "awaiting_site_feedback",
                "Другая проблема": "awaiting_site_other"
            }

            if msg in site_responses:
                handle_response(event, site_responses, site_map)
                continue
                
            # Проверяем, находится ли пользователь в состоянии ожидания
            user_in_state = False
            for state, label in [
                ("awaiting_application", "Заявка на госслужбу"),
                ("awaiting_citizenship_refusal", "Отказ от гражданства"),
                ("awaiting_citizenship_feedback", "Жалоба/предложение (гражданство)"),
                ("awaiting_citizenship_other", "Другая проблема (гражданство)"),
                ("awaiting_site_request", "Подтверждение заявки на сайте"),
                ("awaiting_party_registration", "Заявка на регистрацию партии"),
                ("awaiting_vote_request", "Заявка на проведение голосования"),
                ("awaiting_error_report", "Сообщение об ошибке на сайте"),
                ("awaiting_site_feedback", "Жалоба/предложение (сайт)"),
                ("awaiting_site_other", "Другая проблема (сайт)")
            ]:
                if user_id in user_states[state]:
                    safe_send_message(vk, ADMIN_ID, f"📩 {label}:\n\n{msg}")
                    safe_send_message(vk, event.user_id, "✅ Обращение отправлено! Администрация рассмотрит его в ближайшее время.", keyboard=get_back_to_main_keyboard())
                    user_states[state].remove(user_id)
                    user_in_state = True
                    break
                    
            if not user_in_state:
                safe_send_message(vk, event.user_id, "Команда не распознана. Выберите действие:", keyboard=get_keyboard())
                
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
            safe_send_message(vk, event.user_id, "Произошла ошибка. Попробуйте позже.", keyboard=get_keyboard())


if __name__ == "__main__":
    main()
