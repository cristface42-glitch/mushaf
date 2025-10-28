# database.py
import sqlite3
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path='bot.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных с новыми таблицами"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        tables = [
            '''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                phone_number TEXT,
                profile_photo TEXT,
                registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                language TEXT DEFAULT 'ru',
                last_active DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS qaris (
                qari_id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo TEXT,
                name_ar TEXT, name_uz TEXT, name_ru TEXT, name_en TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS suras (
                sura_id INTEGER PRIMARY KEY AUTOINCREMENT,
                qari_id INTEGER,
                order_number INTEGER,
                file_id TEXT,
                name_ar TEXT, name_uz TEXT, name_ru TEXT, name_en TEXT,
                cover_photo TEXT,
                listens INTEGER DEFAULT 0,
                FOREIGN KEY (qari_id) REFERENCES qaris(qari_id)
            )''',
            '''CREATE TABLE IF NOT EXISTS nasheeds (
                nasheed_id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT,
                title_ar TEXT, title_uz TEXT, title_ru TEXT, title_en TEXT,
                performer TEXT,
                cover_photo TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                listens INTEGER DEFAULT 0
            )''',
            '''CREATE TABLE IF NOT EXISTS admin_chats (
                chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                user_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS user_favorite_suras (
                user_id INTEGER,
                sura_id INTEGER,
                added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, sura_id)
            )''',
            '''CREATE TABLE IF NOT EXISTS user_favorite_nasheeds (
                user_id INTEGER,
                nasheed_id INTEGER,
                added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, nasheed_id)
            )''',
            '''CREATE TABLE IF NOT EXISTS daily_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sura_id INTEGER,
                nasheed_id INTEGER,
                date DATE UNIQUE,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS user_activity (
                user_id INTEGER,
                activity_date DATE,
                actions_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, activity_date)
            )''',
            '''CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                from_user_id INTEGER,
                message_text TEXT,
                message_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_from_admin BOOLEAN DEFAULT 0
            )'''
        ]
        
        for table in tables:
            try:
                cursor.execute(table)
            except Exception as e:
                logger.error(f"Error creating table: {e}")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    # User methods
    def save_user(self, user_id, username, first_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        # Проверяем, существует ли пользователь
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Обновляем существующего пользователя без изменения языка
            cursor.execute('''
                UPDATE users SET username = ?, first_name = ?, last_active = CURRENT_TIMESTAMP 
                WHERE user_id = ?
            ''', (username, first_name, user_id))
        else:
            # Новый пользователь - НЕ устанавливаем язык, пусть будет NULL
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_active, language) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, NULL)
            ''', (user_id, username, first_name))
        conn.commit()
        conn.close()
    
    def update_user_activity(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute('''
            INSERT OR REPLACE INTO user_activity (user_id, activity_date, actions_count)
            VALUES (?, ?, COALESCE((SELECT actions_count FROM user_activity WHERE user_id = ? AND activity_date = ?), 0) + 1)
        ''', (user_id, today, user_id, today))
        conn.commit()
        conn.close()
    
    def get_user_language(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        # Возвращаем язык или None если не установлен
        return result[0] if result and result[0] else None
    
    def set_user_language(self, user_id, language):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
        conn.commit()
        conn.close()
    
    def get_all_users(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, first_name FROM users ORDER BY registration_date DESC")
        users = cursor.fetchall()
        conn.close()
        return users
    
    def get_today_users_count(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM user_activity WHERE activity_date = ?", (today,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def get_total_users_count(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    # Qari methods
    def add_qari(self, photo, names):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO qaris (photo, name_ar, name_uz, name_ru, name_en)
            VALUES (?, ?, ?, ?, ?)
        ''', (photo, names['ar'], names['uz'], names['ru'], names['en']))
        qari_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return qari_id
    
    def get_all_qaris(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT qari_id, name_ar, name_ru, name_uz, name_en FROM qaris")
        qaris = cursor.fetchall()
        conn.close()
        return qaris
    
    def get_qari_by_id(self, qari_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM qaris WHERE qari_id = ?", (qari_id,))
        qari = cursor.fetchone()
        conn.close()
        return qari

    def delete_qari(self, qari_id):
        """Удаляет чтеца, все его суры и связанные записи в избранном."""
        conn = self.get_connection()
        cursor = conn.cursor()
        photo_path = None
        try:
            # 1. Получить путь к фото для удаления файла
            cursor.execute("SELECT photo FROM qaris WHERE qari_id = ?", (qari_id,))
            result = cursor.fetchone()
            if result:
                photo_path = result[0]

            # 2. Получить ID всех сур этого чтеца
            cursor.execute("SELECT sura_id FROM suras WHERE qari_id = ?", (qari_id,))
            sura_ids_to_delete = [row[0] for row in cursor.fetchall()]

            # 3. Удалить эти суры из избранного у всех пользователей
            if sura_ids_to_delete:
                placeholders = ','.join('?' for _ in sura_ids_to_delete)
                cursor.execute(f"DELETE FROM user_favorite_suras WHERE sura_id IN ({placeholders})", sura_ids_to_delete)

            # 4. Удалить все суры этого чтеца
            cursor.execute("DELETE FROM suras WHERE qari_id = ?", (qari_id,))
            # 5. Удалить самого чтеца
            cursor.execute("DELETE FROM qaris WHERE qari_id = ?", (qari_id,))
            conn.commit()
        finally:
            conn.close()
        return photo_path
    
    # Sura methods
    def add_sura(self, qari_id, order_number, file_id, names):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO suras (qari_id, order_number, file_id, name_ar, name_uz, name_ru, name_en)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (qari_id, order_number, file_id, names['ar'], names['uz'], names['ru'], names['en']))
        conn.commit()
        conn.close()
    
    def get_suras_by_qari(self, qari_id, limit=10, offset=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT order_number, name_ar, name_ru, name_en 
            FROM suras 
            WHERE qari_id = ? 
            ORDER BY order_number
            LIMIT ? OFFSET ?
        ''', (qari_id, limit, offset))
        suras = cursor.fetchall()
        conn.close()
        return suras
    
    def get_sura_file_id(self, qari_id, order_number):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT file_id FROM suras 
            WHERE qari_id = ? AND order_number = ?
        ''', (qari_id, order_number))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def search_suras(self, query, language='ru'):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT s.order_number, s.name_ar, s.name_ru, s.name_en, q.name_{language} as qari_name
            FROM suras s
            JOIN qaris q ON s.qari_id = q.qari_id
            WHERE s.name_ru LIKE ? OR s.name_ar LIKE ? OR s.order_number = ?
            ORDER BY s.order_number
            LIMIT 20
        ''', (f'%{query}%', f'%{query}%', query if query.isdigit() else -1))
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_sura_by_qari_and_order(self, qari_id, order_number):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT sura_id FROM suras WHERE qari_id = ? AND order_number = ?
        ''', (qari_id, order_number))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    # Nasheed methods
    def add_nasheed(self, file_id, titles, performer, cover_photo=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO nasheeds (file_id, title_ar, title_uz, title_ru, title_en, performer, cover_photo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (file_id, titles['ar'], titles['uz'], titles['ru'], titles['en'], performer, cover_photo))
        nasheed_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return nasheed_id

    def get_nasheeds(self, limit=10, offset=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT nasheed_id, title_ru, performer 
            FROM nasheeds 
            ORDER BY created_date DESC
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        nasheeds = cursor.fetchall()
        conn.close()
        return nasheeds

    def get_total_nasheeds_count(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(nasheed_id) FROM nasheeds")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def get_nasheed_by_id(self, nasheed_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM nasheeds WHERE nasheed_id = ?", (nasheed_id,))
        nasheed = cursor.fetchone()
        conn.close()
        return nasheed

    def add_favorite_nasheed(self, user_id, nasheed_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO user_favorite_nasheeds (user_id, nasheed_id) VALUES (?, ?)', (user_id, nasheed_id))
        conn.commit()
        conn.close()

    def remove_favorite_nasheed(self, user_id, nasheed_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM user_favorite_nasheeds WHERE user_id = ? AND nasheed_id = ?', (user_id, nasheed_id))
        conn.commit()
        conn.close()

    def get_user_favorite_nasheeds(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT n.nasheed_id, n.title_ru, n.performer FROM user_favorite_nasheeds ufn JOIN nasheeds n ON ufn.nasheed_id = n.nasheed_id WHERE ufn.user_id = ? ORDER BY ufn.added_date DESC', (user_id,))
        nasheeds = cursor.fetchall()
        conn.close()
        return nasheeds

    def is_nasheed_favorite(self, user_id, nasheed_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM user_favorite_nasheeds WHERE user_id = ? AND nasheed_id = ?
        ''', (user_id, nasheed_id))
        result = cursor.fetchone()
        conn.close()
        return result is not None

    def search_users(self, query):
        conn = self.get_connection()
        cursor = conn.cursor()
        # Ищем по имени, юзернейму или ID
        cursor.execute('''
            SELECT user_id, username, first_name FROM users
            WHERE first_name LIKE ? OR username LIKE ? OR user_id = ?
            LIMIT 20
        ''', (f'%{query}%', f'%{query}%', query if query.isdigit() else -1))
        users = cursor.fetchall()
        conn.close()
        return users

    # Favorite methods
    def add_favorite_sura(self, user_id, sura_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO user_favorite_suras (user_id, sura_id)
            VALUES (?, ?)
        ''', (user_id, sura_id))
        conn.commit()
        conn.close()
    
    def remove_favorite_sura(self, user_id, sura_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM user_favorite_suras 
            WHERE user_id = ? AND sura_id = ?
        ''', (user_id, sura_id))
        conn.commit()
        conn.close()
    
    def get_user_favorite_suras(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        # Используем язык пользователя для названий
        lang = self.get_user_language(user_id)
        cursor.execute(f'''
            SELECT s.sura_id, s.order_number, s.name_{lang}, s.name_ar, q.name_{lang} as qari_name, s.qari_id
            FROM user_favorite_suras ufs
            JOIN suras s ON ufs.sura_id = s.sura_id
            JOIN qaris q ON s.qari_id = q.qari_id
            WHERE ufs.user_id = ?
            ORDER BY ufs.added_date DESC
        ''', (user_id,))
        favorites = cursor.fetchall()
        conn.close()
        return favorites
    
    def is_sura_favorite(self, user_id, sura_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 1 FROM user_favorite_suras 
            WHERE user_id = ? AND sura_id = ?
        ''', (user_id, sura_id))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    # Daily content methods
    def get_daily_sura(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute('''
            SELECT s.*, q.name_ru as qari_name 
            FROM daily_content dc
            JOIN suras s ON dc.sura_id = s.sura_id
            JOIN qaris q ON s.qari_id = q.qari_id
            WHERE dc.date = ?
        ''', (today,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_daily_nasheed(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute('''
            SELECT n.* FROM daily_content dc
            JOIN nasheeds n ON dc.nasheed_id = n.nasheed_id
            WHERE dc.date = ?
        ''', (today,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def set_daily_sura(self, sura_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute('''
            INSERT INTO daily_content (date, sura_id) VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET sura_id = excluded.sura_id
        ''', (today, sura_id))
        conn.commit()
        conn.close()

    def set_daily_nasheed(self, nasheed_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute('''
            INSERT INTO daily_content (date, nasheed_id) VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET nasheed_id = excluded.nasheed_id
        ''', (today, nasheed_id))
        conn.commit()
        conn.close()
    
    def get_random_sura(self):
        """Получить случайную суру"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, q.name_ru as qari_name 
            FROM suras s
            JOIN qaris q ON s.qari_id = q.qari_id
            ORDER BY RANDOM()
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_random_nasheed(self):
        """Получить случайный нашид"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM nasheeds
            ORDER BY RANDOM()
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()
        return result

    # Chat methods
    def get_chat_id(self, admin_id, user_id, create_if_not_exists=False):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM admin_chats WHERE admin_id = ? AND user_id = ?", (admin_id, user_id))
        result = cursor.fetchone()
        chat_id = result[0] if result else None
        if not chat_id and create_if_not_exists:
            cursor.execute("INSERT INTO admin_chats (admin_id, user_id, is_active) VALUES (?, ?, 1)", (admin_id, user_id))
            chat_id = cursor.lastrowid
            conn.commit()
        conn.close()
        return chat_id

    def create_admin_chat(self, admin_id, user_id): # Можно оставить для обратной совместимости
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO admin_chats (admin_id, user_id, is_active)
            VALUES (?, ?, 1)
        ''', (admin_id, user_id))
        conn.commit()
        conn.close()
    
    def save_message(self, chat_id, from_user_id, message_text, is_from_admin=False):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (chat_id, from_user_id, message_text, is_from_admin)
            VALUES (?, ?, ?, ?)
        ''', (chat_id, from_user_id, message_text, is_from_admin))
        conn.commit()
        conn.close()
    
    def get_chat_messages(self, chat_id, limit=50):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM messages
            WHERE chat_id = ? 
            ORDER BY message_date DESC 
            LIMIT ?
        ''', (chat_id, limit))
        messages = cursor.fetchall()
        conn.close()
        return messages

db = Database()