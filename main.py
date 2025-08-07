import os
import json
from dotenv import load_dotenv
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from threading import Thread
from flask import Flask

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


def main():
    if not TOKEN:
        print("Токен не найден")
        return

    vk_session = vk_api.VkApi(token=TOKEN)
    longpoll = VkLongPoll(vk_session)
    vk = vk_session.get_api()
    known_users = load_known_users()

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

    print("Бот запущен")

    with open("citizenship_responses.json", "r", encoding="utf-8") as f:
        citizenship_responses = json.load(f)
    with open("site_responses.json", "r", encoding="utf-8") as f:
        site_responses = json.load(f)

    def reset_user(user_id):
        for state in user_states.values():
            state.discard(user_id)

    def handle_response(event, message_dict, category_map):
        message = message_dict[event.text]
        if event.text in category_map:
            user_states[category_map[event.text]].add(str(event.user_id))
        if message:
            vk.messages.send(
                user_id=event.user_id,
                message=message,
                keyboard=get_back_to_main_keyboard(),
                random_id=0
            )

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = str(event.user_id)
            msg = event.text.strip()

            print(f"Сообщение от {user_id}: {msg}")

            if user_id not in known_users:
                vk.messages.send(user_id=event.user_id, message="👋 Здравствуйте, гражданин Королевства Волерия! \nРады приветствовать вас в официальном сообществе нашего великого государства. \nЗдесь вы можете получить помощь по вопросам гражданства и сайту, а также оставить свои обращения и предложения. \n⬇️ Выберите нужный раздел в меню ниже, и я с радостью помогу вам!", keyboard=get_keyboard(), random_id=0)
                save_known_user(user_id)
                known_users.add(user_id)
                continue

            if msg == "Вопрос с гражданством":
                keyboard = generate_keyboard(list(citizenship_responses.keys()))
                vk.messages.send(user_id=event.user_id, message="🛂 Пожалуйста, выберите один из доступных вопросов, чтобы я мог помочь вам с информацией и поддержкой по вопросам гражданства Королевства Волерия.", keyboard=keyboard, random_id=0)
                continue

            if msg == "Вопрос с сайтом":
                keyboard = generate_keyboard(list(site_responses.keys()))
                vk.messages.send(user_id=event.user_id, message="🌐 Пожалуйста, выберите интересующий вас вопрос, связанный с работой сайта, чтобы получить помощь или оставить обращение.", keyboard=keyboard, random_id=0)
                continue

            if msg in ("Назад", "В главное меню"):
                reset_user(user_id)
                vk.messages.send(user_id=event.user_id, message="🔙 Вы вернулись в главное меню. Выберите действие из списка ниже, чтобы продолжить.", keyboard=get_keyboard(), random_id=0)
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
                    vk.messages.send(user_id=ADMIN_ID, message=f"📩 {label}:\n\n{msg}", random_id=0)
                    vk.messages.send(user_id=event.user_id, message="✅ Обращение отправлено! Администрация рассмотрит его в ближайшее время.", keyboard=get_back_to_main_keyboard(), random_id=0)
                    user_states[state].remove(user_id)
                    break
            else:
                vk.messages.send(user_id=event.user_id, message="Команда не распознана. Выберите действие:", keyboard=get_keyboard(), random_id=0)


if __name__ == "__main__":
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "I'm alive!"

    Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()
    main()
