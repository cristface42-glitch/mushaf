# init_db.py
import os
import sqlite3
from database import DatabaseManager

def init_database():
    """Инициализация базы данных для Railway"""
    print("🔄 Инициализация базы данных...")
    
    # Создаем директории
    os.makedirs("qari_photos", exist_ok=True)
    
    # Инициализируем базу данных
    db = DatabaseManager()
    db.init_database()
    
    print("✅ База данных инициализирована успешно!")

if __name__ == "__main__":
    init_database()
