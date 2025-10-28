#!/usr/bin/env python3
"""
Скрипт для сброса базы данных
Удаляет старую БД и создает новую с правильной структурой
"""

import os
import sys

# Путь к файлу базы данных
DB_FILE = "bot.db"

def reset_database():
    """Удаляет старую БД и инициализирует новую"""
    
    # Проверяем, существует ли файл БД
    if os.path.exists(DB_FILE):
        print(f"🔍 Найден файл базы данных: {DB_FILE}")
        
        # Запрашиваем подтверждение
        response = input("⚠️  Удалить старую базу данных? Все данные будут потеряны! (yes/no): ")
        
        if response.lower() in ['yes', 'y', 'да', 'д']:
            try:
                os.remove(DB_FILE)
                print(f"✅ База данных {DB_FILE} успешно удалена!")
            except Exception as e:
                print(f"❌ Ошибка при удалении БД: {e}")
                sys.exit(1)
        else:
            print("❌ Отменено пользователем")
            sys.exit(0)
    else:
        print(f"ℹ️  Файл {DB_FILE} не найден")
    
    # Импортируем database для инициализации новой БД
    print("\n🔄 Инициализация новой базы данных...")
    try:
        from database import db
        print("✅ Новая база данных создана успешно!")
        print("\n📋 Созданные таблицы:")
        print("  - users (с полем language = NULL для новых пользователей)")
        print("  - qaris")
        print("  - suras")
        print("  - nasheeds")
        print("  - user_favorite_suras")
        print("  - user_favorite_nasheeds")
        print("  - daily_content")
        print("  - admin_chats")
        print("  - messages")
        print("  - user_activity")
        print("\n✨ Готово! Теперь запустите бота: python user_bot.py")
    except Exception as e:
        print(f"❌ Ошибка при инициализации БД: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("🗄️  СБРОС БАЗЫ ДАННЫХ")
    print("=" * 60)
    reset_database()

