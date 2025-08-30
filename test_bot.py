#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы VK бота
"""

import requests
import json

def test_bot_api():
    """Тестирует API бота"""
    
    # URL вашего бота на Vercel (замените на ваш)
    bot_url = "https://your-project-name.vercel.app/api/bot"
    
    print("🧪 Тестирование VK бота...")
    
    # Тест 1: GET запрос (проверка работоспособности)
    print("\n1️⃣ Тест GET запроса...")
    try:
        response = requests.get(bot_url)
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {response.text}")
        
        if response.status_code == 200:
            print("   ✅ GET запрос работает")
        else:
            print("   ❌ GET запрос не работает")
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тест 2: POST запрос с подтверждением VK
    print("\n2️⃣ Тест POST запроса (подтверждение VK)...")
    try:
        confirmation_data = {
            "type": "confirmation",
            "group_id": 123456789
        }
        
        response = requests.post(bot_url, json=confirmation_data)
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {response.text}")
        
        if response.status_code == 200 and "b1564bca" in response.text:
            print("   ✅ Подтверждение VK работает")
        else:
            print("   ❌ Подтверждение VK не работает")
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тест 3: POST запрос с новым сообщением
    print("\n3️⃣ Тест POST запроса (новое сообщение)...")
    try:
        message_data = {
            "type": "message_new",
            "object": {
                "from_id": 123456,
                "text": "Тест"
            }
        }
        
        response = requests.post(bot_url, json=message_data)
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {response.text}")
        
        if response.status_code == 200 and response.text == "ok":
            print("   ✅ Обработка сообщений работает")
        else:
            print("   ❌ Обработка сообщений не работает")
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("\n🏁 Тестирование завершено!")

if __name__ == "__main__":
    test_bot_api()
