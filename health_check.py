#!/usr/bin/env python3
"""
Простой health check для Render
"""
import os
import sys

def main():
    """Проверка доступности основных компонентов"""
    try:
        # Проверяем наличие токена
        token = os.getenv("VK_GROUP_TOKEN")
        if not token:
            print("VK_GROUP_TOKEN не найден")
            sys.exit(1)
        
        # Проверяем наличие необходимых файлов
        required_files = [
            "citizenship_responses.json",
            "site_responses.json",
            "known_users.txt"
        ]
        
        for file in required_files:
            if not os.path.exists(file):
                print(f"Файл {file} не найден")
                sys.exit(1)
        
        print("Все проверки пройдены успешно")
        sys.exit(0)
        
    except Exception as e:
        print(f"Ошибка при проверке: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 