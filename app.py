from flask import Flask, request, jsonify
import threading
import os
import sys
import datetime
from main import main as bot_main

app = Flask(__name__)

# Глобальная переменная для хранения потока бота
bot_thread = None
bot_running = False

def run_bot():
    """Запуск бота в отдельном потоке"""
    global bot_running
    if bot_running:
        print("Бот уже запущен")
        return
    
    bot_running = True
    print("Запуск бота...")
    try:
        bot_main()
    except Exception as e:
        print(f"Ошибка в боте: {e}")
    finally:
        bot_running = False
        print("Бот остановлен")

@app.route('/')
def home():
    return jsonify({
        "status": "VK Bot Service",
        "bot_running": bot_running,
        "message": "Бот работает в фоновом режиме"
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "bot_running": bot_running,
        "timestamp": str(datetime.datetime.now())
    })

@app.route('/start', methods=['POST'])
def start_bot():
    global bot_thread, bot_running
    
    if bot_running:
        return jsonify({"status": "error", "message": "Бот уже запущен"}), 400
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    return jsonify({
        "status": "success", 
        "message": "Бот запущен"
    })

@app.route('/start', methods=['GET'])
def start_bot_get():
    """GET эндпоинт для запуска бота через браузер"""
    global bot_thread, bot_running
    
    if bot_running:
        return jsonify({"status": "info", "message": "Бот уже запущен"})
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    return jsonify({
        "status": "success", 
        "message": "Бот запущен"
    })

@app.route('/stop', methods=['POST'])
def stop_bot():
    global bot_running
    
    if not bot_running:
        return jsonify({"status": "error", "message": "Бот не запущен"}), 400
    
    bot_running = False
    return jsonify({
        "status": "success", 
        "message": "Бот остановлен"
    })

if __name__ == '__main__':
    # Автоматически запускаем бота при старте приложения
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask приложение
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 