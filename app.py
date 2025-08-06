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
    status = "🟢 Работает" if bot_running else "🔴 Остановлен"
    thread_status = "🟢 Активен" if bot_thread and bot_thread.is_alive() else "🔴 Неактивен"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>VK Bot Status</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .running {{ background-color: #d4edda; color: #155724; }}
            .stopped {{ background-color: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <h1>🤖 VK Bot Status</h1>
        <div class="status {'running' if bot_running else 'stopped'}">
            <strong>Статус бота:</strong> {status}
        </div>
        <div class="status {'running' if bot_thread and bot_thread.is_alive() else 'stopped'}">
            <strong>Поток бота:</strong> {thread_status}
        </div>
        <p><strong>Порт:</strong> {os.environ.get('PORT', '5000')}</p>
        <p><strong>Время:</strong> {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><a href="/status">JSON статус</a> | <a href="/start">Запустить бота</a></p>
    </body>
    </html>
    """
    return html

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
    """Статус бота в JSON формате"""
    return jsonify({
        "status": "healthy",
        "bot_running": bot_running,
        "thread_alive": bot_thread.is_alive() if bot_thread else False,
        "port": os.environ.get('PORT', '5000'),
        "timestamp": time.time()
    })

if __name__ == '__main__':
    # Автоматически запускаем бота при старте
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask сервер
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Запуск Flask сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 