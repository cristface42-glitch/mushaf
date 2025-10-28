# run_bots.py
import multiprocessing
import logging
import time
import os
import signal
import sys

# Создаем необходимые директории
os.makedirs("qari_photos", exist_ok=True)

def signal_handler(sig, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info("Получен сигнал завершения, останавливаем ботов...")
    sys.exit(0)

def run_admin_bot():
    """Запуск админ-бота в отдельном процессе"""
    try:
        from admin_bot import main as admin_main
        admin_main()
    except Exception as e:
        logger.error(f"Ошибка в админ-боте: {e}")

def run_user_bot():
    """Запуск юзер-бота в отдельном процессе"""
    try:
        from user_bot import main as user_main
        user_main()
    except Exception as e:
        logger.error(f"Ошибка в юзер-боте: {e}")

if __name__ == '__main__':
    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    logger = logging.getLogger(__name__)
    
    # Обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 Запуск ботов на Railway...")
    
    # Создаем процессы для ботов
    admin_process = multiprocessing.Process(target=run_admin_bot, name="AdminBot")
    user_process = multiprocessing.Process(target=run_user_bot, name="UserBot")
    
    # Запускаем процессы
    admin_process.start()
    user_process.start()
    
    logger.info("✅ Оба бота запущены успешно!")
    logger.info(f"Admin Bot PID: {admin_process.pid}")
    logger.info(f"User Bot PID: {user_process.pid}")
    
    try:
        # Мониторим процессы
        while True:
            if not admin_process.is_alive():
                logger.error("❌ Админ-бот остановлен, перезапускаем...")
                admin_process = multiprocessing.Process(target=run_admin_bot, name="AdminBot")
                admin_process.start()
                logger.info(f"🔄 Админ-бот перезапущен, PID: {admin_process.pid}")
            
            if not user_process.is_alive():
                logger.error("❌ Юзер-бот остановлен, перезапускаем...")
                user_process = multiprocessing.Process(target=run_user_bot, name="UserBot")
                user_process.start()
                logger.info(f"🔄 Юзер-бот перезапущен, PID: {user_process.pid}")
            
            time.sleep(10)  # Проверяем каждые 10 секунд
            
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        logger.info("🔄 Завершение работы ботов...")
        admin_process.terminate()
        user_process.terminate()
        admin_process.join(timeout=5)
        user_process.join(timeout=5)
        logger.info("✅ Боты остановлены")