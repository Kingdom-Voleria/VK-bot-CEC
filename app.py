import os
import threading
import time
from flask import Flask, jsonify
import logging

# Импортируем основную логику бота
from main import main as bot_main

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания состояния бота
bot_running = False
bot_thread = None

def run_bot():
    """Запуск бота в отдельном потоке"""
    global bot_running
    try:
        bot_running = True
        logger.info("Запуск VK бота...")
        bot_main()
    except Exception as e:
        logger.error(f"Ошибка в работе бота: {e}")
    finally:
        bot_running = False

@app.route('/')
def health_check():
    """Проверка здоровья сервиса"""
    return jsonify({
        "status": "healthy",
        "bot_running": bot_running,
        "timestamp": time.time()
    })

@app.route('/start')
def start_bot():
    """Запуск бота"""
    global bot_thread, bot_running
    
    if bot_running:
        return jsonify({"status": "error", "message": "Бот уже запущен"})
    
    try:
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        return jsonify({"status": "success", "message": "Бот запущен"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ошибка запуска: {e}"})

@app.route('/status')
def bot_status():
    """Статус бота"""
    return jsonify({
        "bot_running": bot_running,
        "thread_alive": bot_thread.is_alive() if bot_thread else False
    })

if __name__ == '__main__':
    # Автоматически запускаем бота при старте
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask сервер
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 