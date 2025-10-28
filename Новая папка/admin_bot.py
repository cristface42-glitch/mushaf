# admin_bot.py
import logging
import os
import zipfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, InlineQueryResultArticle, InputTextMessageContent, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler, InlineQueryHandler
from telegram.ext import filters

from config import ADMIN_BOT_TOKEN, ADMIN_ID, CHANNEL_ID, SURA_NAMES
from database import db
from text_resources import get_text
from mistral_integration import translator
import json as json_module

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
WAITING_QARI_PHOTO, WAITING_QARI_NAME, WAITING_SURA_AUDIO, WAITING_ZIP_FILE, WAITING_NASHEED_PHOTO, WAITING_NASHEED_AUDIO, WAITING_NASHEED_NAME, CHATTING_WITH_USER, WAITING_DAILY_SURA, WAITING_DAILY_NASHEED, WAITING_BROADCAST_MESSAGE, SELECTING_SURA_FROM_LIST, WAITING_SELECTED_SURA_AUDIO = range(13)

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_ID:
            if update.message:
                await update.message.reply_text("❌ Доступ запрещен")
            elif update.callback_query:
                await update.callback_query.answer("❌ Доступ запрещен")
            return
        return await func(update, context)
    return wrapper

@admin_only
async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовая команда админ-бота"""
    
    # Проверяем новые сообщения от пользователей
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM messages m
        JOIN admin_chats ac ON m.chat_id = ac.chat_id
        WHERE m.is_from_admin = 0 AND ac.admin_id = ?
        AND m.message_id NOT IN (
            SELECT message_id FROM messages WHERE is_from_admin = 1
        )
    ''', (ADMIN_ID,))
    unread_count = cursor.fetchone()[0]
    conn.close()
    
    keyboard = [
        [InlineKeyboardButton("🎙 Добавить чтеца", callback_data="add_qari")],
        [InlineKeyboardButton("🎵 Добавить нашид", callback_data="add_nasheed")],
        [InlineKeyboardButton("🗑️ Управление чтецами", callback_data="manage_qaris")],
        [InlineKeyboardButton(f"👥 Управление пользователями {'🔴' + str(unread_count) if unread_count > 0 else ''}", callback_data="manage_users")],
        [InlineKeyboardButton("📊 Статистика", callback_data="statistics")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="broadcast")],
        [InlineKeyboardButton("☀️ Контент дня", callback_data="daily_content")]
    ]
    
    panel_text = "🛠 Панель администратора:"
    if unread_count > 0:
        panel_text += f"\n\n🔴 Новых сообщений: {unread_count}"
    
    if update.message:
        await update.message.reply_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard))

@admin_only
async def add_qari_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления чтеца"""
    query = update.callback_query
    await query.answer()
    context.user_data['qari_data'] = {}
    
    await query.message.reply_text("📷 Отправьте фото чтеца или /skip для пропуска")
    return WAITING_QARI_PHOTO

@admin_only
async def handle_qari_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото чтеца"""
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        photo_path = f"qari_photos/{update.message.message_id}.jpg"
        os.makedirs("qari_photos", exist_ok=True)
        await photo_file.download_to_drive(photo_path)
        context.user_data['qari_data']['photo'] = photo_path
        await update.message.reply_text("✅ Фото сохранено")
    elif update.message.text and update.message.text.strip() == "/skip":
        context.user_data['qari_data']['photo'] = None
        await update.message.reply_text("✅ Пропущено добавление фото")
    else:
        context.user_data['qari_data']['photo'] = None
        await update.message.reply_text("✅ Пропущено добавление фото")
    
    await update.message.reply_text("📝 Введите имя чтеца (на вашем языке):")
    return WAITING_QARI_NAME

@admin_only
async def handle_qari_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка имени чтеца с автоматическим переводом через Mistral AI"""
    name = update.message.text
    context.user_data['qari_data']['name'] = name
    
    # Отправляем уведомление о начале перевода
    processing_msg = await update.message.reply_text("🔄 Автоматический перевод имени чтеца на все языки...")
    
    # Вызываем AI для перевода имени на все языки
    translation_result = translator.translate_to_all_languages(name)
    
    # Получаем переводы из результата
    names = translation_result['translations']
    
    # Сохранение в БД
    qari_id = db.add_qari(
        context.user_data['qari_data'].get('photo'),
        names
    )
    
    # Формируем JSON-ответ для логов/отчета
    response_json = {
        "action": "add_qari",
        "status": translation_result['status'],
        "qari_id": qari_id,
        "names": names,
        "needs_review": translation_result.get('needs_review', False)
    }
    
    if translation_result.get('error'):
        response_json['error'] = translation_result['error']
    
    logger.info(f"Add qari response: {json_module.dumps(response_json, ensure_ascii=False)}")
    
    # Удаляем сообщение о процессе
    await processing_msg.delete()
    
    # Формируем сообщение для админа
    review_warning = ""
    if translation_result.get('needs_review'):
        review_warning = "\n⚠️ Внимание: перевод требует проверки (возможна ошибка AI)"
    
    await update.message.reply_text(
        f"✅ Чтец успешно добавлен (ID: {qari_id})\n\n"
        f"📝 Переводы:\n"
        f"🇸🇦 AR: {names['ar']}\n"
        f"🇺🇿 UZ: {names['uz']}\n"
        f"🇷🇺 RU: {names['ru']}\n"
        f"🇬🇧 EN: {names['en']}"
        f"{review_warning}"
    )
    
    # Предлагаем способы добавления сур
    keyboard = [
        [InlineKeyboardButton("🎵 Добавить суры по порядку (1-114)", callback_data=f"add_suras_audio_{qari_id}")],
        [InlineKeyboardButton("📋 Выбрать суру из списка", callback_data=f"add_suras_select_{qari_id}")],
        [InlineKeyboardButton("📦 Добавить суры (ZIP архив)", callback_data=f"add_suras_zip_{qari_id}")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="admin_back")]
    ]
    
    await update.message.reply_text(
        "✅ Чтец добавлен!\n\nВыберите способ добавления сур:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return ConversationHandler.END

@admin_only
async def start_suras_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор суры из списка 114 (Вариант B)"""
    query = update.callback_query
    await query.answer()
    
    qari_id = query.data.split("_")[3]
    context.user_data['current_qari_id'] = qari_id
    
    # Создаем инлайн-кнопки для всех 114 сур с пагинацией (по 10 на страницу)
    page = context.user_data.get('sura_select_page', 0)
    items_per_page = 10
    start_index = page * items_per_page + 1
    end_index = min((page + 1) * items_per_page, 114)
    
    keyboard = []
    for i in range(start_index, end_index + 1):
        sura_name = SURA_NAMES.get(i, {}).get('ru', f'Сура {i}')
        keyboard.append([InlineKeyboardButton(f"{i:03d}. {sura_name}", callback_data=f"select_sura_{i}")])
    
    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"sura_select_page_{page-1}"))
    if end_index < 114:
        nav_buttons.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"sura_select_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🚫 Отмена", callback_data="admin_back")])
    
    await query.edit_message_text(
        f"📋 Выберите суру для добавления (стр. {page+1}/12):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_SURA_FROM_LIST

@admin_only
async def handle_sura_select_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Навигация по страницам выбора сур"""
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.split("_")[-1])
    context.user_data['sura_select_page'] = page
    
    # Повторно показываем список с новой страницей
    return await start_suras_select(update, context)

@admin_only
async def handle_selected_sura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбранной суры из списка"""
    query = update.callback_query
    await query.answer()
    
    sura_number = int(query.data.split("_")[2])
    context.user_data['selected_sura_number'] = sura_number
    
    sura_name = SURA_NAMES.get(sura_number, {}).get('ru', f'Сура {sura_number}')
    
    await query.edit_message_text(
        f"📖 Вы выбрали: {sura_number:03d}. {sura_name}\n\n"
        f"Отправьте аудиофайл для этой суры.\n"
        f"Формат: MP3, M4A, OGG"
    )
    return WAITING_SELECTED_SURA_AUDIO

@admin_only
async def handle_selected_sura_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка аудио для выбранной суры"""
    if not update.message.audio:
        await update.message.reply_text("❌ Пожалуйста, отправьте аудиофайл")
        return WAITING_SELECTED_SURA_AUDIO
    
    qari_id = context.user_data.get('current_qari_id')
    sura_number = context.user_data.get('selected_sura_number')
    
    if not qari_id or not sura_number:
        await update.message.reply_text("❌ Ошибка: данные не найдены")
        return ConversationHandler.END
    
    try:
        # Пересылаем аудио на канал
        message_on_channel = await context.bot.send_audio(
            chat_id=CHANNEL_ID,
            audio=update.message.audio.file_id
        )
        file_id = message_on_channel.audio.file_id
        
        if not file_id:
            raise ValueError("Не удалось получить file_id с канала")
        
        # Получаем название суры
        sura_names = SURA_NAMES.get(sura_number, {
            'ar': f'سورة {sura_number}',
            'uz': f'Sura {sura_number}',
            'ru': f'Сура {sura_number}',
            'en': f'Surah {sura_number}'
        })
        
        # Сохраняем в БД
        db.add_sura(qari_id, sura_number, file_id, sura_names)
        
        # Удаляем сообщение с аудио
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        
        # Спрашиваем, хочет ли админ добавить еще одну суру
        keyboard = [
            [InlineKeyboardButton("➕ Добавить еще суру", callback_data=f"add_suras_select_{qari_id}")],
            [InlineKeyboardButton("✅ Завершить", callback_data="admin_back")]
        ]
        
        await update.message.reply_text(
            f"✅ Сура {sura_number} успешно добавлена!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error processing selected sura audio: {e}")
        await update.message.reply_text(f"❌ Ошибка обработки аудио: {str(e)}")
        return WAITING_SELECTED_SURA_AUDIO

@admin_only
async def start_suras_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления сур через аудиофайлы по порядку"""
    query = update.callback_query
    await query.answer()
    
    qari_id = query.data.split("_")[3]
    context.user_data['current_qari_id'] = qari_id
    context.user_data['current_sura_number'] = 1
    
    await query.message.reply_text(
        f"🎵 Начинаем добавление сур для чтеца {qari_id}\n"
        f"Отправьте аудиофайл для суры 1 (Аль-Фатиха)\n"
        f"Формат: MP3, M4A, OGG"
    )
    return WAITING_SURA_AUDIO

@admin_only
async def handle_sura_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка аудиофайлов сур - собираем все файлы, потом загружаем пакетом"""
    import asyncio
    
    if not update.message.audio:
        await update.message.reply_text("❌ Пожалуйста, отправьте аудиофайл")
        return WAITING_SURA_AUDIO
    
    qari_id = context.user_data.get('current_qari_id')
    sura_number = context.user_data.get('current_sura_number', 1)
    
    if not qari_id:
        await update.message.reply_text("❌ Ошибка: чтец не выбран")
        return ConversationHandler.END
    
    # Инициализируем список файлов если нет
    if 'pending_suras' not in context.user_data:
        context.user_data['pending_suras'] = []
    
    # Сохраняем file_id во временный список
    context.user_data['pending_suras'].append({
        'sura_number': sura_number,
        'file_id': update.message.audio.file_id,
        'message_id': update.message.message_id
    })
    
    # Удаляем сообщение с аудио из чата
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except:
        pass
    
    # Переходим к следующей суре
    next_sura = sura_number + 1
    
    if next_sura <= 114:
        context.user_data['current_sura_number'] = next_sura
        next_sura_name = SURA_NAMES.get(next_sura, {}).get('ru', f'Сура {next_sura}')
        
        keyboard = [
            [InlineKeyboardButton(f"✅ Завершить и загрузить ({len(context.user_data['pending_suras'])} сур)", callback_data="finish_sura_batch")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_sura_addition")]
        ]
        
        await update.message.reply_text(
            f"✅ Сура {sura_number} добавлена в очередь ({len(context.user_data['pending_suras'])}/114)\n\n"
            f"📖 Следующая: {next_sura}. {next_sura_name}\n\n"
            f"Отправьте аудио или нажмите 'Завершить' для загрузки на канал.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_SURA_AUDIO
    else:
        # Все 114 суры собраны - автоматически загружаем
        await process_sura_batch(update, context)
        return ConversationHandler.END

async def process_sura_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Загружает собранные суры на канал с прогресс-баром"""
    import asyncio
    
    qari_id = context.user_data.get('current_qari_id')
    pending = context.user_data.get('pending_suras', [])
    
    if not pending:
        await update.message.reply_text("❌ Нет сур для загрузки")
        return
    
    total = len(pending)
    progress_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🔄 Загрузка {total} сур на канал...\n\n▱▱▱▱▱▱▱▱▱▱ 0%"
    )
    
    success = 0
    errors = []
    
    for i, sura_data in enumerate(pending):
        try:
            # Задержка для flood control
            await asyncio.sleep(2)
            
            # Загружаем на канал
            message_on_channel = await context.bot.send_audio(
                chat_id=CHANNEL_ID,
                audio=sura_data['file_id']
            )
            file_id = message_on_channel.audio.file_id
            
            # Сохраняем в БД
            sura_names = SURA_NAMES.get(sura_data['sura_number'], {
                'ar': f'سورة {sura_data["sura_number"]}',
                'uz': f'Sura {sura_data["sura_number"]}',
                'ru': f'Сура {sura_data["sura_number"]}',
                'en': f'Surah {sura_data["sura_number"]}'
            })
            
            db.add_sura(qari_id, sura_data['sura_number'], file_id, sura_names)
            success += 1
            
            # Обновляем прогресс-бар
            percent = int((i + 1) / total * 100)
            filled = int(percent / 10)
            bar = "▰" * filled + "▱" * (10 - filled)
            
            await progress_msg.edit_text(
                f"🔄 Загрузка {total} сур на канал...\n\n{bar} {percent}%\n\n"
                f"✅ Загружено: {success}/{total}"
            )
            
        except Exception as e:
            logger.error(f"Error uploading sura {sura_data['sura_number']}: {e}")
            errors.append(f"Сура {sura_data['sura_number']}: {str(e)}")
    
    # Финальный отчет
    await progress_msg.edit_text(
        f"✅ Загрузка завершена!\n\n"
        f"📊 Успешно: {success}/{total}\n"
        f"❌ Ошибок: {len(errors)}"
    )
    
    # Спрашиваем хотите ли еще добавить
    keyboard = [
        [InlineKeyboardButton("➕ Добавить еще сур", callback_data=f"add_suras_audio_{qari_id}")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="admin_back")]
    ]
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Хотите добавить еще сур для этого чтеца?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Очищаем временные данные
    context.user_data.pop('pending_suras', None)
    context.user_data.pop('current_qari_id', None)
    context.user_data.pop('current_sura_number', None)

async def finish_sura_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Завершить' - запускает загрузку"""
    query = update.callback_query
    await query.answer("Начинаем загрузку...")
    await process_sura_batch(update, context)
    return ConversationHandler.END

@admin_only
async def cancel_sura_addition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершает процесс добавления сур по одному"""
    query = update.callback_query
    await query.answer()
    context.user_data.pop('current_qari_id', None)
    context.user_data.pop('current_sura_number', None)
    await query.edit_message_text("✅ Добавление сур завершено.")
    await admin_start(update, context)
    return ConversationHandler.END
@admin_only
async def start_zip_addition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления сур через ZIP"""
    query = update.callback_query
    await query.answer()
    
    qari_id = query.data.split("_")[3]
    context.user_data['current_qari_id'] = qari_id
    
    await query.message.reply_text(
        "📦 Отправьте ZIP-архив с аудиофайлами сур.\n"
        "Файлы должны быть названы по порядку: 001.mp3, 002.mp3, ..."
    )
    return WAITING_ZIP_FILE

@admin_only
async def handle_zip_addition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ZIP архива с сурами - детальная валидация"""
    if not update.message.document:
        await update.message.reply_text("❌ Пожалуйста, отправьте ZIP файл")
        return WAITING_ZIP_FILE
    
    qari_id = context.user_data.get('current_qari_id')
    if not qari_id:
        await update.message.reply_text("❌ Ошибка: не выбран чтец")
        return ConversationHandler.END
    
    zip_path = f"temp_{update.message.message_id}.zip"
    extract_path = f"temp_extract_{update.message.message_id}"
    
    # Инициализация отчета
    validation_report = {
        "action": "process_zip",
        "status": "ok",
        "qari_id": qari_id,
        "uploaded": 0,
        "skipped": 0,
        "errors": [],
        "missing_files": [],
        "integrity_check": "ok"
    }
    
    processing_msg = await update.message.reply_text("🔄 Обработка ZIP архива...")
    
    try:
        # 1. Скачивание и проверка целостности
        zip_file = await update.message.document.get_file()
        await zip_file.download_to_drive(zip_path)
        
        # Проверка целостности ZIP
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                bad_file = zip_ref.testzip()
                if bad_file is not None:
                    validation_report['integrity_check'] = "failed"
                    validation_report['status'] = "error"
                    validation_report['errors'].append(f"Поврежденный файл в архиве: {bad_file}")
                    raise ValueError(f"ZIP архив поврежден: {bad_file}")
                
                # Извлечение
                os.makedirs(extract_path, exist_ok=True)
                zip_ref.extractall(extract_path)
        except zipfile.BadZipFile as e:
            validation_report['integrity_check'] = "failed"
            validation_report['status'] = "error"
            validation_report['errors'].append(f"Невалидный ZIP файл: {str(e)}")
            raise
        
        # 2. Получаем аудио файлы и парсим их номера
        audio_files = {}
        allowed_extensions = ('.mp3', '.m4a', '.ogg')
        
        for filename in os.listdir(extract_path):
            if filename.lower().endswith(allowed_extensions):
                # Пытаемся извлечь номер суры из имени файла
                # Поддерживаем форматы: 001.mp3, 1.mp3, sura_001.mp3 и т.д.
                import re
                match = re.search(r'(\d+)', filename)
                if match:
                    sura_number = int(match.group(1))
                    if 1 <= sura_number <= 114:
                        audio_files[sura_number] = filename
        
        if len(audio_files) == 0:
            validation_report['status'] = "error"
            validation_report['errors'].append("В архиве не найдено аудио файлов с корректными номерами (1-114)")
            await processing_msg.edit_text("❌ В архиве не найдено аудио файлов")
            return WAITING_ZIP_FILE
        
        # 3. Проверка последовательности (выявление пропусков)
        expected_numbers = set(range(1, 115))
        found_numbers = set(audio_files.keys())
        missing_numbers = sorted(expected_numbers - found_numbers)
        
        if missing_numbers:
            validation_report['missing_files'] = [f"{num:03d}.mp3" for num in missing_numbers[:10]]  # Первые 10
            if len(missing_numbers) > 10:
                validation_report['missing_files'].append(f"...и еще {len(missing_numbers)-10}")
        
        # 4. Обработка файлов с детальной валидацией
        await processing_msg.edit_text(f"🔄 Загрузка {len(audio_files)} сур на канал...")
        
        for sura_number in sorted(audio_files.keys()):
            filename = audio_files[sura_number]
            file_path = os.path.join(extract_path, filename)
            
            try:
                # Проверка размера файла
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    validation_report['errors'].append(f"Сура {sura_number}: пустой файл")
                    validation_report['skipped'] += 1
                    continue
                
                if file_size < 10000:  # Меньше 10KB - подозрительно
                    validation_report['errors'].append(f"Сура {sura_number}: подозрительно малый размер ({file_size} байт)")
                
                # Загружаем на канал
                with open(file_path, 'rb') as audio_file:
                    message = await context.bot.send_audio(
                        chat_id=CHANNEL_ID,
                        audio=InputFile(audio_file, filename=filename),
                        title=f"Surah {sura_number}",
                        duration=0  # Telegram сам определит длительность
                    )
                    
                    file_id = message.audio.file_id
                    duration = message.audio.duration or 0
                    
                    # Проверка длительности
                    if duration < 1:
                        validation_report['errors'].append(f"Сура {sura_number}: длительность меньше 1 секунды")
                
                # Получаем название суры
                sura_names = SURA_NAMES.get(sura_number, {
                    'ar': f'سورة {sura_number}',
                    'uz': f'Sura {sura_number}',
                    'ru': f'Сура {sura_number}',
                    'en': f'Surah {sura_number}'
                })
                
                # Сохраняем в БД
                db.add_sura(qari_id, sura_number, file_id, sura_names)
                validation_report['uploaded'] += 1
                
            except Exception as e:
                logger.error(f"Error processing file {filename}: {e}")
                validation_report['errors'].append(f"Сура {sura_number} ({filename}): {str(e)}")
                validation_report['skipped'] += 1
                continue
        
        # 5. Формирование итогового отчета
        if validation_report['errors'] or validation_report['missing_files']:
            validation_report['status'] = "warning" if validation_report['uploaded'] > 0 else "error"
        
        logger.info(f"ZIP processing report: {json_module.dumps(validation_report, ensure_ascii=False)}")
        
        # 6. Отправка отчета админу
        report_text = f"📦 **Отчет обработки ZIP архива**\n\n"
        report_text += f"✅ Загружено сур: {validation_report['uploaded']}\n"
        report_text += f"⏭ Пропущено: {validation_report['skipped']}\n"
        
        if validation_report['missing_files']:
            report_text += f"\n⚠️ **Отсутствующие суры:** {len(missing_numbers)}\n"
            report_text += f"Номера: {', '.join(str(n) for n in missing_numbers[:20])}\n"
            if len(missing_numbers) > 20:
                report_text += f"...и еще {len(missing_numbers)-20}\n"
        
        if validation_report['errors']:
            report_text += f"\n❌ **Ошибки ({len(validation_report['errors'])}):**\n"
            for error in validation_report['errors'][:10]:
                report_text += f"• {error}\n"
            if len(validation_report['errors']) > 10:
                report_text += f"...и еще {len(validation_report['errors'])-10} ошибок\n"
        
        await processing_msg.edit_text(report_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"ZIP processing error: {e}")
        validation_report['status'] = "error"
        validation_report['errors'].append(str(e))
        
        await processing_msg.edit_text(
            f"❌ Критическая ошибка обработки ZIP:\n{str(e)}\n\n"
            f"Загружено: {validation_report['uploaded']}, Пропущено: {validation_report['skipped']}"
        )
    
    finally:
        # Очистка временных файлов
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
            if os.path.exists(extract_path):
                import shutil
                shutil.rmtree(extract_path)
        except Exception as cleanup_error:
            logger.error(f"Cleanup error: {cleanup_error}")
    
    await admin_start(update, context)
    return ConversationHandler.END

@admin_only
async def add_nasheed_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления нашида"""
    query = update.callback_query
    await query.answer()
    context.user_data['nasheed_data'] = {}
    await query.message.reply_text("🎵 Отправьте аудиофайл нашида.")
    return WAITING_NASHEED_AUDIO

@admin_only
async def handle_nasheed_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка аудио нашида"""
    if not update.message.audio:
        await update.message.reply_text("❌ Пожалуйста, отправьте аудиофайл.")
        return WAITING_NASHEED_AUDIO

    # Пересылаем аудио на канал, чтобы получить постоянный file_id
    message_on_channel = await context.bot.send_audio(
        chat_id=CHANNEL_ID,
        audio=update.message.audio.file_id
    )
    file_id = message_on_channel.audio.file_id
    if not file_id:
        await update.message.reply_text("❌ Ошибка: не удалось загрузить аудио на канал.")
        return WAITING_NASHEED_AUDIO
    context.user_data['nasheed_data']['file_id'] = file_id
    await update.message.reply_text("📝 Введите название нашида (на вашем языке).")
    return WAITING_NASHEED_NAME

@admin_only
async def handle_nasheed_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия нашида с автоматическим переводом"""
    name = update.message.text
    context.user_data['nasheed_data']['name'] = name

    # Отправляем уведомление о начале перевода
    processing_msg = await update.message.reply_text("🔄 Автоматический перевод названия нашида...")

    # Вызываем AI для перевода названия на все языки
    translation_result = translator.translate_to_all_languages(name)
    titles = translation_result['translations']
    context.user_data['nasheed_data']['titles'] = titles
    context.user_data['nasheed_data']['translation_result'] = translation_result

    await processing_msg.delete()
    
    review_warning = ""
    if translation_result.get('needs_review'):
        review_warning = "\n⚠️ Внимание: перевод требует проверки"
    
    await update.message.reply_text(
        f"✅ Название переведено:\n"
        f"🇸🇦 AR: {titles['ar']}\n"
        f"🇺🇿 UZ: {titles['uz']}\n"
        f"🇷🇺 RU: {titles['ru']}\n"
        f"🇬🇧 EN: {titles['en']}"
        f"{review_warning}"
    )

    await update.message.reply_text("👤 Введите имя исполнителя (или /skip, чтобы пропустить).")
    return WAITING_NASHEED_PHOTO # Используем состояние для фото как состояние для исполнителя

@admin_only
async def handle_nasheed_performer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка исполнителя и сохранение нашида с JSON-отчетом"""
    performer = update.message.text if update.message.text != '/skip' else "Не указан"
    
    nasheed_data = context.user_data.get('nasheed_data')
    if not nasheed_data:
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте снова.")
        return ConversationHandler.END

    # Сохраняем в БД
    nasheed_id = db.add_nasheed(
        file_id=nasheed_data['file_id'],
        titles=nasheed_data['titles'],
        performer=performer
    )

    # Формируем JSON-ответ
    translation_result = nasheed_data.get('translation_result', {})
    response_json = {
        "action": "add_nasheed",
        "status": "ok",
        "nasheed_id": nasheed_id,
        "titles": nasheed_data['titles'],
        "performer": performer,
        "needs_review": translation_result.get('needs_review', False)
    }
    
    logger.info(f"Add nasheed response: {json_module.dumps(response_json, ensure_ascii=False)}")

    await update.message.reply_text(f"✅ Нашид '{nasheed_data['name']}' успешно добавлен (ID: {nasheed_id}).")
    
    # Очищаем user_data
    context.user_data.pop('nasheed_data', None)
    
    await admin_start(update, context)
    return ConversationHandler.END

@admin_only
async def skip_performer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропуск ввода исполнителя"""
    update.message.text = '/skip'
    return await handle_nasheed_performer(update, context)

@admin_only
async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление пользователями"""
    query = update.callback_query
    await query.answer()
    
    users = db.get_all_users()
    
    keyboard = []
    for user_id, username, first_name in users:
        btn_text = f"👤 {first_name} (@{username})" if username else f"👤 {first_name}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"user_info_{user_id}")])
    
    keyboard.append([InlineKeyboardButton("🔍 Поиск пользователя", switch_inline_query_current_chat="")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")])
    
    await query.edit_message_text(
        f"👥 Управление пользователями ({len(users)}):", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@admin_only
async def show_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация о пользователе"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split("_")[2]
    users = db.get_all_users()
    user = next((u for u in users if u[0] == int(user_id)), None)
    
    if not user:
        await query.message.reply_text("Пользователь не найден")
        return
    
    text = f"""📋 Информация о пользователе:
ID: {user[0]}
Имя: {user[2]}
Username: @{user[1] or 'Не указан'}
Язык: {db.get_user_language(user[0])}"""
    
    keyboard = [
        [InlineKeyboardButton("💬 Открыть чат", callback_data=f"open_chat_{user_id}")],
        [InlineKeyboardButton("❌ Удалить пользователя", callback_data=f"delete_user_{user_id}")],
        [InlineKeyboardButton("⬅️ Назад к пользователям", callback_data="manage_users")]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

@admin_only
async def open_chat_with_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает чат с пользователем, показывает ВСЕ сообщения компактно"""
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split("_")[-1])
    context.user_data['chatting_with_user_id'] = user_id

    user = db.get_user_by_id(user_id)
    if not user:
        await query.edit_message_text("❌ Пользователь не найден.")
        return ConversationHandler.END

    # Удаляем старое сообщение
    try:
        await query.message.delete()
    except:
        pass

    chat_id = db.get_chat_id(ADMIN_ID, user_id)
    
    # Отправляем заголовок
    header = f"💬 Чат с {user[2]} (@{user[1] or 'N/A'}, ID: {user_id})\n"
    header += "=" * 40 + "\n\n"
    
    # Получаем сообщения
    if chat_id:
        messages = db.get_chat_messages(chat_id, limit=50)
        
        if messages:
            # Группируем сообщения компактно
            history = ""
            for msg in reversed(messages):  # От старых к новым
                sender_icon = "👨‍💼" if msg[5] else "👤"
                sender_name = "Admin" if msg[5] else user[2]
                message_text = msg[3]
                
                # Компактный формат
                history += f"{sender_icon} {sender_name}: {message_text}\n"
            
            # Отправляем историю одним сообщением
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=header + history,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚪 Закрыть чат", callback_data=f"close_chat_{user_id}")]
                ])
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=header + "📭 Нет сообщений",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚪 Закрыть", callback_data=f"close_chat_{user_id}")]
                ])
            )
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=header + "📭 Чат пуст",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚪 Закрыть", callback_data=f"close_chat_{user_id}")]
            ])
        )
    
    return CHATTING_WITH_USER

@admin_only
async def handle_admin_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщения от админа пользователю"""
    user_id = context.user_data.get('chatting_with_user_id')
    text = update.message.text

    if not user_id:
        await update.message.reply_text("❌ Ошибка: не выбран пользователь для чата. Начните заново.")
        return ConversationHandler.END

    try:
        # Отправляем сообщение пользователю
        await context.bot.send_message(
            chat_id=user_id,
            text=f"Сообщение от Администратора:\n\n{text}"
        )
        # Сохраняем в БД
        chat_id = db.get_chat_id(ADMIN_ID, user_id, create_if_not_exists=True)
        db.save_message(chat_id, ADMIN_ID, text, is_from_admin=True)

        await update.message.reply_text("✅ Сообщение отправлено пользователю.")
    except Exception as e:
        await update.message.reply_text(f"❌ Не удалось отправить сообщение: {e}")

    return CHATTING_WITH_USER

@admin_only
async def close_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Закрывает чат с пользователем"""
    query = update.callback_query
    await query.answer("Чат закрыт")
    context.user_data.pop('chatting_with_user_id', None)
    await query.edit_message_text("Вы вышли из режима чата.")
    await admin_start(update, context)
    return ConversationHandler.END

@admin_only
async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика"""
    query = update.callback_query
    await query.answer()
    
    total_users = db.get_total_users_count()
    today_users = db.get_today_users_count()
    
    text = f"""📊 Статистика бота:
👥 Всего пользователей: {total_users}
📈 Активных сегодня: {today_users}"""
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

@admin_only
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало рассылки с автопереводом"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 **Режим рассылки с автопереводом**\n\n"
        "Отправьте сообщение (текст) на вашем языке.\n"
        "Система автоматически переведет его на язык каждого пользователя:\n"
        "🇸🇦 Арабский\n🇺🇿 Узбекский\n🇷🇺 Русский\n🇬🇧 Английский\n\n"
        "⚡ Рассылка выполняется с интеллектуальным throttling (30 сообщений/мин)",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_back")]]),
        parse_mode='Markdown'
    )
    
    return WAITING_BROADCAST_MESSAGE

@admin_only
async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщения для рассылки с автопереводом"""
    import asyncio
    from datetime import datetime
    
    broadcast_text = update.message.text
    if not broadcast_text:
        await update.message.reply_text("❌ Пожалуйста, отправьте текстовое сообщение")
        return WAITING_BROADCAST_MESSAGE
    
    # Получаем всех пользователей, ИСКЛЮЧАЯ админа
    all_users = db.get_all_users()
    users = [u for u in all_users if u[0] != ADMIN_ID]  # Исключаем админа!
    
    if not users:
        await update.message.reply_text("❌ Нет пользователей для рассылки (админ не считается)")
        await admin_start(update, context)
        return ConversationHandler.END
    
    # Инициализация отчета
    broadcast_report = {
        "action": "broadcast",
        "status": "ok",
        "total": len(users),
        "sent": 0,
        "failed": 0,
        "errors": [],
        "translations": {},
        "start_time": datetime.now().isoformat()
    }
    
    # Отправляем уведомление о начале рассылки
    progress_msg = await update.message.reply_text(
        f"🔄 Подготовка рассылки для {len(users)} пользователей...\n"
        f"Переводим сообщение на все языки..."
    )
    
    # Генерируем переводы для всех языков заранее
    translations = {'ru': broadcast_text}  # Предполагаем что исходный текст на русском
    
    for lang in ['ar', 'uz', 'en']:
        try:
            translated = translator.translate_broadcast_message(broadcast_text, lang)
            translations[lang] = translated
            broadcast_report['translations'][lang] = translated
        except Exception as e:
            logger.error(f"Translation error for {lang}: {e}")
            translations[lang] = broadcast_text  # Fallback к оригиналу
            broadcast_report['errors'].append(f"Ошибка перевода на {lang}: {str(e)}")
    
    await progress_msg.edit_text(
        f"✅ Переводы готовы!\n"
        f"🔄 Начинаем рассылку {len(users)} пользователям...\n"
        f"Отправлено: 0/{len(users)}"
    )
    
    # Группируем пользователей по языкам для оптимизации
    users_by_lang = {'ar': [], 'uz': [], 'ru': [], 'en': []}
    for user in users:
        user_id, username, first_name = user
        user_lang = db.get_user_language(user_id)
        if user_lang in users_by_lang:
            users_by_lang[user_lang].append((user_id, username, first_name))
        else:
            users_by_lang['ru'].append((user_id, username, first_name))  # По умолчанию русский
    
    # Конфигурация throttling
    BATCH_SIZE = 30
    BATCH_DELAY = 60  # секунд
    RETRY_LIMIT = 3
    
    sent_count = 0
    failed_count = 0
    batch_count = 0
    
    # Рассылка по языкам
    for lang, lang_users in users_by_lang.items():
        message_text = translations.get(lang, broadcast_text)
        
        for i, (user_id, username, first_name) in enumerate(lang_users):
            retry_count = 0
            success = False
            
            while retry_count < RETRY_LIMIT and not success:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"📢 {message_text}"
                    )
                    sent_count += 1
                    success = True
                    
                except Exception as e:
                    retry_count += 1
                    logger.error(f"Broadcast error for user {user_id} (attempt {retry_count}): {e}")
                    
                    if retry_count >= RETRY_LIMIT:
                        failed_count += 1
                        broadcast_report['errors'].append(f"User {user_id} ({username}): {str(e)}")
                    else:
                        await asyncio.sleep(1)  # Небольшая задержка перед повтором
            
            # Обновляем прогресс каждые 10 пользователей
            if (sent_count + failed_count) % 10 == 0:
                try:
                    await progress_msg.edit_text(
                        f"🔄 Рассылка в процессе...\n"
                        f"✅ Отправлено: {sent_count}/{len(users)}\n"
                        f"❌ Ошибок: {failed_count}"
                    )
                except:
                    pass  # Игнорируем ошибки обновления прогресса
            
            # Throttling: пауза после каждых BATCH_SIZE сообщений
            batch_count += 1
            if batch_count >= BATCH_SIZE:
                logger.info(f"Throttling: sent {batch_count} messages, waiting {BATCH_DELAY}s...")
                await asyncio.sleep(BATCH_DELAY)
                batch_count = 0
            else:
                await asyncio.sleep(0.05)  # Минимальная задержка между сообщениями
    
    # Финальный отчет
    broadcast_report['sent'] = sent_count
    broadcast_report['failed'] = failed_count
    broadcast_report['end_time'] = datetime.now().isoformat()
    
    if failed_count > 0:
        broadcast_report['status'] = "warning"
    
    logger.info(f"Broadcast report: {json_module.dumps(broadcast_report, ensure_ascii=False)}")
    
    # Отправляем итоговый отчет админу
    final_report = (
        f"📊 **Отчет о рассылке**\n\n"
        f"✅ Успешно отправлено: {sent_count}\n"
        f"❌ Ошибок: {failed_count}\n"
        f"📝 Всего пользователей: {len(users)}\n\n"
        f"🌍 **Распределение по языкам:**\n"
        f"🇸🇦 AR: {len(users_by_lang['ar'])}\n"
        f"🇺🇿 UZ: {len(users_by_lang['uz'])}\n"
        f"🇷🇺 RU: {len(users_by_lang['ru'])}\n"
        f"🇬🇧 EN: {len(users_by_lang['en'])}\n"
    )
    
    if broadcast_report['errors'] and len(broadcast_report['errors']) <= 10:
        final_report += f"\n❌ **Ошибки:**\n"
        for error in broadcast_report['errors']:
            final_report += f"• {error}\n"
    elif len(broadcast_report['errors']) > 10:
        final_report += f"\n❌ Всего ошибок: {len(broadcast_report['errors'])} (см. логи)\n"
    
    await progress_msg.edit_text(final_report, parse_mode='Markdown')
    
    await admin_start(update, context)
    return ConversationHandler.END

@admin_only
async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback админ-меню"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "admin_back":
        await admin_start(update, context)
    elif data == "manage_qaris":
        await manage_qaris(update, context)
    elif data == "manage_users":
        await manage_users(update, context)
    elif data.startswith("user_info_"):
        await show_user_info(update, context)
    elif data.startswith("open_chat_"):
        # Этот callback теперь обрабатывается ConversationHandler'ом
        # Но оставим заглушку на всякий случай
        await query.message.reply_text("Для чата используется новый обработчик.")
    elif data == "statistics":
        await statistics(update, context)
    elif data == "broadcast":
        # Эта функция теперь обрабатывается ConversationHandler
        await broadcast_start(update, context)
    elif data == "daily_content":
        await daily_content_menu(update, context)
    elif data == "set_daily_sura":
        await set_daily_sura_start(update, context)
    elif data == "set_daily_nasheed":
        await set_daily_nasheed_start(update, context)
    elif data.startswith("delete_qari_confirm_"):
        qari_id = int(data.split("_")[-1])
        qari = db.get_qari_by_id(qari_id)
        if not qari:
            await query.edit_message_text("❌ Чтец не найден.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="manage_qaris")]]))
            return
        
        keyboard = [
            [InlineKeyboardButton(f"‼️ Да, удалить {qari[4]}", callback_data=f"delete_qari_execute_{qari_id}")],
            [InlineKeyboardButton("⬅️ Нет, отмена", callback_data="manage_qaris")]
        ]
        await query.edit_message_text(f"Вы уверены, что хотите удалить чтеца и все его суры? Это действие необратимо.", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("delete_qari_execute_"):
        qari_id = int(data.split("_")[-1])
        photo_path = db.delete_qari(qari_id)
        if photo_path and os.path.exists(photo_path):
            os.remove(photo_path)
        await query.answer("✅ Чтец удален!")
        await manage_qaris(update, context) # Обновляем список
    
    elif data.startswith("add_suras_menu_"):
        await show_add_suras_menu(update, context)

@admin_only
async def manage_qaris(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления чтецами (просмотр, добавление сур, удаление)"""
    query = update.callback_query
    if query:
        await query.answer()

    qaris = db.get_all_qaris()
    keyboard = []

    if not qaris:
        await query.edit_message_text("Нет добавленных чтецов.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]]))
        return

    for qari_id, name_ar, name_ru, name_uz, name_en in qaris:
        keyboard.append([
            InlineKeyboardButton(name_ru, callback_data=f"qari_info_{qari_id}"),
            InlineKeyboardButton("➕ Суры", callback_data=f"add_suras_menu_{qari_id}"),
            InlineKeyboardButton("❌", callback_data=f"delete_qari_confirm_{qari_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")])
    await query.edit_message_text("🗑️ Управление чтецами:", reply_markup=InlineKeyboardMarkup(keyboard))

@admin_only
async def show_add_suras_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать меню добавления сур для чтеца"""
    query = update.callback_query
    await query.answer()
    
    qari_id = int(query.data.split("_")[-1])
    qari = db.get_qari_by_id(qari_id)
    qari_name = qari[4] if qari else f"Чтец {qari_id}"  # name_ru
    
    keyboard = [
        [InlineKeyboardButton("🎵 По порядку (1-114)", callback_data=f"add_suras_audio_{qari_id}")],
        [InlineKeyboardButton("📋 Выбрать из списка", callback_data=f"add_suras_select_{qari_id}")],
        [InlineKeyboardButton("📦 ZIP архив", callback_data=f"add_suras_zip_{qari_id}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="manage_qaris")]
    ]
    
    await query.edit_message_text(
        f"Добавление сур для чтеца: {qari_name}\n\nВыберите способ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@admin_only
async def daily_content_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления контентом дня"""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🌙 Установить Суру дня", callback_data="set_daily_sura")],
        [InlineKeyboardButton("⭐ Установить Нашид дня", callback_data="set_daily_nasheed")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="admin_back")]
    ]
    await query.edit_message_text("Выберите, что установить:", reply_markup=InlineKeyboardMarkup(keyboard))

@admin_only
async def set_daily_sura_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало установки суры дня - выбор чтеца"""
    query = update.callback_query
    await query.answer()
    
    qaris = db.get_all_qaris()
    if not qaris:
        await query.edit_message_text(
            "❌ Нет чтецов в базе. Сначала добавьте чтеца.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="daily_content")]])
        )
        return ConversationHandler.END
    
    keyboard = []
    for qari_id, name_ar, name_ru, name_uz, name_en in qaris:
        keyboard.append([InlineKeyboardButton(name_ru, callback_data=f"daily_sura_qari_{qari_id}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="daily_content")])
    
    await query.edit_message_text(
        "🎙 Выберите чтеца для суры дня:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_DAILY_SURA

@admin_only
async def handle_daily_sura_qari_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора чтеца для суры дня - показываем суры"""
    query = update.callback_query
    await query.answer()
    
    qari_id = int(query.data.split("_")[-1])
    context.user_data['daily_sura_qari'] = qari_id
    
    # Получаем все суры этого чтеца
    suras = db.get_suras_by_qari(qari_id, 114, 0)
    
    if not suras:
        await query.edit_message_text(
            "❌ У этого чтеца нет сур",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="set_daily_sura")]])
        )
        return WAITING_DAILY_SURA
    
    # Показываем первые 10 с пагинацией
    page = 0
    items_per_page = 10
    context.user_data['daily_sura_page'] = page
    
    keyboard = []
    for sura_data in suras[page*items_per_page:(page+1)*items_per_page]:
        order = sura_data[0]
        name_ru = sura_data[2]
        # Получаем sura_id из БД
        sura_id = db.get_sura_by_qari_and_order(qari_id, order)
        keyboard.append([InlineKeyboardButton(f"{order}. {name_ru}", callback_data=f"set_daily_sura_id_{sura_id}")])
    
    # Навигация
    nav_buttons = []
    if len(suras) > (page+1)*items_per_page:
        nav_buttons.append(InlineKeyboardButton("Далее ▶️", callback_data=f"daily_sura_page_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад к чтецам", callback_data="set_daily_sura")])
    
    qari_name = db.get_qari_by_id(qari_id)[4]  # name_ru
    await query.edit_message_text(
        f"📖 Выберите суру ({qari_name}):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_DAILY_SURA

@admin_only
async def handle_daily_sura_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора конкретной суры для 'Суры дня'"""
    query = update.callback_query
    await query.answer()
    
    sura_id = int(query.data.split("_")[-1])
    db.set_daily_sura(sura_id)
    
    await query.edit_message_text(f"✅ Сура установлена как 'Сура дня'!")
    await admin_start(update, context)
    return ConversationHandler.END

@admin_only
async def set_daily_nasheed_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало установки нашида дня - inline выбор"""
    query = update.callback_query
    await query.answer()
    
    nasheeds = db.get_nasheeds(20, 0)  # Первые 20
    if not nasheeds:
        await query.edit_message_text(
            "❌ Нет нашидов в базе. Сначала добавьте нашид.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="daily_content")]])
        )
        return ConversationHandler.END
    
    keyboard = []
    for nasheed_id, title, performer in nasheeds:
        display = f"{title} - {performer or '...'}"
        keyboard.append([InlineKeyboardButton(display, callback_data=f"set_daily_nasheed_id_{nasheed_id}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="daily_content")])
    
    await query.edit_message_text(
        "🎵 Выберите нашид дня:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WAITING_DAILY_NASHEED

@admin_only
async def handle_daily_nasheed_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора нашида для 'Нашида дня'"""
    query = update.callback_query
    await query.answer()
    
    nasheed_id = int(query.data.split("_")[-1])
    db.set_daily_nasheed(nasheed_id)
    
    await query.edit_message_text(f"✅ Нашид установлен как 'Нашид дня'!")
    await admin_start(update, context)
    return ConversationHandler.END

@admin_only
async def cancel_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    await update.message.reply_text("❌ Операция отменена")
    await admin_start(update, context)
    return ConversationHandler.END

@admin_only
async def inline_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инлайн-поиск пользователей"""
    query = update.inline_query.query
    results = []

    if len(query) < 2:
        return

    users = db.search_users(query)

    for user_id, username, first_name in users:
        title = f"{first_name} (@{username or 'N/A'})"
        description = f"ID: {user_id}"
        # При нажатии на результат, бот отправит сообщение с кнопкой для управления
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🛠 Управлять", callback_data=f"user_info_{user_id}")]])
        results.append(
            InlineQueryResultArticle(
                id=str(user_id),
                title=title,
                description=description,
                input_message_content=InputTextMessageContent(f"Выбран пользователь: {title}"),
                reply_markup=keyboard
            )
        )
    await update.inline_query.answer(results, cache_time=5)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    """Запуск админ-бота"""
    os.makedirs("qari_photos", exist_ok=True)
    
    application = Application.builder().token(ADMIN_BOT_TOKEN).build()
    
    # Conversation Handler для добавления чтеца
    qari_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_qari_start, pattern='^add_qari$')],
        states={
            WAITING_QARI_PHOTO: [
                MessageHandler(filters.PHOTO, handle_qari_photo),
                CommandHandler("skip", handle_qari_photo),
                MessageHandler(filters.TEXT & filters.Regex("^/skip$"), handle_qari_photo)
            ],
            WAITING_QARI_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_qari_name)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_operation)],
        per_message=False
    )
    
    # Conversation Handler для добавления сур через аудио
    sura_audio_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_suras_audio, pattern='^add_suras_audio_')],
        states={
            WAITING_SURA_AUDIO: [
                MessageHandler(filters.AUDIO, handle_sura_audio),
                CallbackQueryHandler(finish_sura_batch, pattern='^finish_sura_batch$'),
                CallbackQueryHandler(cancel_sura_addition, pattern='^cancel_sura_addition$')
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_operation)],
        per_message=False
    )
    
    # Conversation Handler для добавления сур через ZIP
    zip_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_zip_addition, pattern='^add_suras_zip_')],
        states={
            WAITING_ZIP_FILE: [
                MessageHandler(filters.Document.ALL, handle_zip_addition)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_operation)],
        per_message=False
    )
    
    # Conversation Handler для чата с пользователем
    chat_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(open_chat_with_user, pattern='^open_chat_')],
        states={
            CHATTING_WITH_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_chat_message),
                CallbackQueryHandler(close_chat, pattern='^close_chat_')
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel_operation)],
        per_message=False
    )
    
    # Conversation Handler для установки контента дня
    daily_content_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(set_daily_sura_start, pattern='^set_daily_sura$'),
            CallbackQueryHandler(set_daily_nasheed_start, pattern='^set_daily_nasheed$')
        ],
        states={
            WAITING_DAILY_SURA: [
                CallbackQueryHandler(handle_daily_sura_qari_select, pattern='^daily_sura_qari_'),
                CallbackQueryHandler(handle_daily_sura_id, pattern='^set_daily_sura_id_')
            ],
            WAITING_DAILY_NASHEED: [
                CallbackQueryHandler(handle_daily_nasheed_id, pattern='^set_daily_nasheed_id_')
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_operation)],
        per_message=False
    )

    # Conversation Handler для добавления нашида
    nasheed_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_nasheed_start, pattern='^add_nasheed$')],
        states={
            WAITING_NASHEED_AUDIO: [MessageHandler(filters.AUDIO, handle_nasheed_audio)],
            WAITING_NASHEED_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_nasheed_name)],
            WAITING_NASHEED_PHOTO: [ # Re-using state for performer
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_nasheed_performer),
                CommandHandler("skip", skip_performer)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_operation)],
        per_message=False
    )
    
    # Conversation Handler для рассылки с автопереводом
    broadcast_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(broadcast_start, pattern='^broadcast$')],
        states={
            WAITING_BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message)]
        },
        fallbacks=[CommandHandler("cancel", cancel_operation)],
        per_message=False
    )
    
    # Conversation Handler для выбора суры из списка (Вариант B)
    sura_select_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_suras_select, pattern='^add_suras_select_')],
        states={
            SELECTING_SURA_FROM_LIST: [
                CallbackQueryHandler(handle_sura_select_page, pattern='^sura_select_page_'),
                CallbackQueryHandler(handle_selected_sura, pattern='^select_sura_')
            ],
            WAITING_SELECTED_SURA_AUDIO: [MessageHandler(filters.AUDIO, handle_selected_sura_audio)]
        },
        fallbacks=[CommandHandler("cancel", cancel_operation)],
        per_message=False
    )

    # Обработчики
    application.add_handler(CommandHandler("start", admin_start))
    application.add_handler(qari_conv_handler)
    application.add_handler(sura_audio_conv_handler)
    application.add_handler(sura_select_conv_handler)
    application.add_handler(zip_conv_handler)
    application.add_handler(chat_conv_handler)
    application.add_handler(daily_content_conv_handler)
    application.add_handler(nasheed_conv_handler)
    application.add_handler(broadcast_conv_handler)
    application.add_handler(InlineQueryHandler(inline_user_search))
    application.add_handler(CallbackQueryHandler(handle_admin_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_start))
    
    application.add_error_handler(error_handler)
    
    logger.info("Admin bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()