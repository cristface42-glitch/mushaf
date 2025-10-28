# run_bots.py
import multiprocessing
import logging
import time
import os

# Создаем необходимые директории
os.makedirs("qari_photos", exist_ok=True)

def run_admin_bot():
    """Запуск админ-бота в отдельном процессе"""
    from admin_bot import main as admin_main
    admin_main()

def run_user_bot():
    """Запуск юзер-бота в отдельном процессе"""
    from user_bot import main as user_main
    user_main()

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting both bots...")
    
    # Создаем процессы для ботов
    admin_process = multiprocessing.Process(target=run_admin_bot)
    user_process = multiprocessing.Process(target=run_user_bot)
    
    # Запускаем процессы
    admin_process.start()
    user_process.start()
    
    logger.info("Both bots started successully!")
    
    try:
        # Ожидаем завершения процессов
        admin_process.join()
        user_process.join()
    except KeyboardInterrupt:
        logger.info("Stopping bots...")
        admin_process.terminate()
        user_process.terminate()
        admin_process.join()
        user_process.join()
        logger.info("Bots stopped successfully!")