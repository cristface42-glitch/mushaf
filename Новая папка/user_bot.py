# user_bot.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ConversationHandler, InlineQueryHandler
from telegram.ext import filters

from config import USER_BOT_TOKEN, ADMIN_ID, SURA_NAMES
from database import db
from text_resources import get_text
from mistral_integration import translator

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def _get_main_keyboard(user_id):
    """Формирует клавиатуру главного меню в зависимости от наличия избранного."""
    lang = db.get_user_language(user_id) or 'ru'  # Дефолт на русский если None
    
    keyboard = [
        [InlineKeyboardButton(get_text('btn_listen_quran', lang), callback_data="listen_quran"),
         InlineKeyboardButton(get_text('btn_listen_nasheed', lang), callback_data="listen_nasheed")],
        [InlineKeyboardButton(get_text('btn_sura_of_day', lang), callback_data="sura_of_day"),
         InlineKeyboardButton(get_text('btn_nasheed_of_day', lang), callback_data="nasheed_of_day")],
    ]
    
    favorite_buttons = []
    # Проверяем, есть ли у пользователя избранные суры или нашиды
    if db.get_user_favorite_suras(user_id):
        favorite_buttons.append(InlineKeyboardButton(get_text('btn_favorite_suras', lang), callback_data="favorite_suras"))
    if db.get_user_favorite_nasheeds(user_id):
        favorite_buttons.append(InlineKeyboardButton(get_text('btn_favorite_nasheeds', lang), callback_data="favorite_nasheeds"))
    
    if favorite_buttons:
        keyboard.append(favorite_buttons)

    keyboard.append([InlineKeyboardButton(get_text('btn_chat_admin', lang), callback_data="chat_with_admin"),
                     InlineKeyboardButton(get_text('btn_language', lang), callback_data="change_language")])
    return InlineKeyboardMarkup(keyboard)

async def user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовая команда юзер-бота - сначала выбор языка для новых пользователей, потом меню"""
    user = update.effective_user
    
    logger.info(f"✅ /start received from user {user.id}")
    
    # Сохраняем/обновляем пользователя
    db.save_user(user.id, user.username, user.first_name)
    db.update_user_activity(user.id)
    
    # Проверяем, выбран ли язык
    user_lang = db.get_user_language(user.id)
    logger.info(f"🌍 User {user.id} language: {user_lang}")
    
    # Если язык НЕ выбран (None) - показываем выбор языка
    if user_lang is None:
        logger.info(f"📝 Showing language selection to user {user.id}")
        keyboard = [
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")],
            [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz")],
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
        ]
        
        welcome_msg = (
            "🌸 Assalamu Alaykum!\n"
            "السلام عليكم\n"
            "Ассаламу алейкум\n\n"
            "Выберите язык / Choose language / اختر اللغة / Tilni tanlang:"
        )
        
        if update.message:
            await update.message.reply_text(
                welcome_msg,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                welcome_msg,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    # Если язык выбран - показываем главное меню
    keyboard = await _get_main_keyboard(user.id)
    main_menu_text = get_text('main_menu', user_lang)

    if update.message:
        await update.message.reply_text(
            main_menu_text,
            reply_markup=keyboard
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(main_menu_text, reply_markup=keyboard)

async def listen_quran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню выбора чтеца"""
    query = update.callback_query
    db.update_user_activity(query.from_user.id)
    
    lang = db.get_user_language(query.from_user.id) or 'ru'
    qaris = db.get_all_qaris()
    
    if not qaris:
        await query.edit_message_text(
            get_text('no_reciters', lang),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text('back', lang), callback_data="main_menu")]])
        )
        return
    
    keyboard = []
    lang_map = {'ar': 1, 'ru': 2, 'uz': 3, 'en': 4}
    name_index = lang_map.get(lang, 2) # default to russian

    for qari in qaris:
        qari_id = qari[0]
        display_name = qari[name_index]
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"qari_{qari_id}")])
    
    keyboard.append([InlineKeyboardButton(get_text('back', lang), callback_data="main_menu")])
    
    await query.edit_message_text(
        get_text('choose_reciter', lang),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_qari_suras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать суры чтеца с пагинацией"""
    query = update.callback_query
    db.update_user_activity(query.from_user.id)

    # Определяем qari_id из callback_data или user_data
    if query.data.startswith("qari_page_"):
        qari_id = context.user_data.get('current_qari')
        page = int(query.data.split("_")[-1])
        context.user_data['sura_page'] = page
    else: # qari_...
        qari_id = int(query.data.split("_")[1])
        context.user_data['current_qari'] = qari_id
        context.user_data['sura_page'] = 0 # Сброс страницы

    user_id = query.from_user.id
    page = context.user_data.get('sura_page', 0)
    items_per_page = 5  # Уменьшено до 5 для удобства
    
    suras = db.get_suras_by_qari(qari_id, items_per_page, page * items_per_page)
    
    # Получаем общее количество сур для этого чтеца
    qari_suras_all = db.get_suras_by_qari(qari_id, 114, 0)
    total_suras = len(qari_suras_all)
    if not total_suras: # Проверка, если get_suras_by_qari вернет пустой список
        total_suras = 0
    
    if not suras:
        lang = db.get_user_language(user_id) or 'ru'
        await query.edit_message_text(
            get_text('no_suras', lang),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text('back', lang), callback_data="listen_quran")]])
        )
        return
    
    # Получаем имя чтеца и язык
    qari = db.get_qari_by_id(qari_id)
    lang = db.get_user_language(user_id) or 'ru'
    lang_map = {'ar': 2, 'uz': 3, 'ru': 4, 'en': 5}
    name_index = lang_map.get(lang, 4) # default to ru
    qari_name = qari[name_index] if qari else f"Чтец {qari_id}"
    
    keyboard = []
    # Используем SURA_NAMES для локализации
    for sura_data in suras:
        order = sura_data[0]
        # Берем название из SURA_NAMES на языке пользователя
        sura_name = SURA_NAMES.get(order, {}).get(lang, f"Sura {order}")
        display_name = f"{order}. {sura_name}"
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"play_sura_{order}")])
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(get_text('previous', lang), callback_data=f"qari_page_{page-1}"))
    
    if (page + 1) * items_per_page < total_suras:
        nav_buttons.append(InlineKeyboardButton(get_text('next', lang), callback_data=f"qari_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton(get_text('btn_search_sura', lang), switch_inline_query_current_chat="")])
    keyboard.append([InlineKeyboardButton(get_text('back', lang), callback_data="listen_quran")])
    keyboard.append([InlineKeyboardButton(get_text('home', lang), callback_data="main_menu")])
    
    # Сохраняем message_id для возможности возврата
    if query.message:
        context.user_data['suras_list_message_id'] = query.message.message_id
    
    await query.edit_message_text(
        f"🎙 {qari_name}\n📖 Суры {page*items_per_page+1}-{page*items_per_page+len(suras)}:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def play_sura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Воспроизведение суры с добавлением в избранное"""
    query = update.callback_query
    db.update_user_activity(query.from_user.id)
    
    parts = query.data.split("_")
    sura_number = int(parts[2])
    # Если callback play_sura_NUMBER_QARIID (из избранного)
    if len(parts) > 3:
        qari_id = int(parts[3])
        context.user_data['current_qari'] = qari_id # Обновляем на случай, если пользователь пойдет назад
    else:
        qari_id = context.user_data.get('current_qari')
    user_id = query.from_user.id
    
    if not qari_id:
        await query.message.reply_text("❌ Ошибка: чтец не выбран")
        return
    
    file_id = db.get_sura_file_id(qari_id, sura_number)
    sura_id = db.get_sura_by_qari_and_order(qari_id, sura_number)
    
    # Получаем название суры на языке пользователя
    lang = db.get_user_language(user_id) or 'ru'
    sura_name = SURA_NAMES.get(sura_number, {}).get(lang, f"Sura {sura_number}")
    
    if file_id:
        try:
            is_favorite = db.is_sura_favorite(user_id, sura_id) if sura_id else False
            keyboard = []
            if sura_id:
                if not is_favorite:
                    keyboard.append([InlineKeyboardButton(get_text('btn_add_favorite', lang), callback_data=f"add_fav_sura_{sura_id}")])
                else:
                    keyboard.append([InlineKeyboardButton(get_text('btn_remove_favorite', lang), callback_data=f"remove_fav_sura_{sura_id}")])
            
            # Кнопка назад к сурам - сохраняем контекст
            if qari_id:
                context.user_data['current_qari'] = qari_id
                keyboard.append([InlineKeyboardButton(get_text('back', lang) + " к сурам", callback_data=f"qari_{qari_id}")])
            keyboard.append([InlineKeyboardButton(get_text('home', lang), callback_data="main_menu")])

            # Отправляем аудио с локализованным названием
            await context.bot.send_audio(
                chat_id=user_id,
                audio=file_id,
                caption=f"📖 {sura_number}. {sura_name}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            # Удаляем старое сообщение со списком сур
            try:
                await query.message.delete()
            except:
                pass  # Игнорируем если уже удалено
            
            # Автоматически возвращаемся к сурам через 3 секунды
            import asyncio
            await asyncio.sleep(3)
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🔄 Возвращаемся к списку сур...",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ К сурам", callback_data=f"qari_{qari_id}")]])
                )
            except:
                pass
            
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            await query.message.reply_text("❌ Ошибка отправки аудио")
    else:
        await query.message.reply_text("❌ Сура не найдена")

async def sura_of_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сура дня или случайная сура"""
    query = update.callback_query
    db.update_user_activity(query.from_user.id)
    
    daily_sura = db.get_daily_sura()
    if not daily_sura:
        # Предлагаем случайную суру
        keyboard = [
            [InlineKeyboardButton("🎲 Случайная сура", callback_data="random_sura")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "🌙 Сура дня сегодня еще не установлена.\n\nПопробуйте случайную суру!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Логика отправки суры дня
        sura_id, qari_id, order_number, file_id, name_ar, name_uz, name_ru, name_en, _, _, qari_name = daily_sura
        lang = db.get_user_language(query.from_user.id) or 'ru'
        lang_map = {'ar': name_ar, 'uz': name_uz, 'ru': name_ru, 'en': name_en}
        sura_name = lang_map.get(lang, name_ru)
        
        await context.bot.send_audio(
            chat_id=query.from_user.id, 
            audio=file_id, 
            caption=f"🌙 Сура дня: {sura_name} - {qari_name}"
        )
        await query.message.delete()
        
        # Автоматически возвращаемся в меню через 3 секунды
        import asyncio
        await asyncio.sleep(3)
        try:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="🔄 Возвращаемся в главное меню...",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
            )
        except:
            pass
async def nasheed_of_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Нашид дня или случайный нашид"""
    query = update.callback_query
    db.update_user_activity(query.from_user.id)
    
    daily_nasheed = db.get_daily_nasheed()
    if not daily_nasheed:
        # Предлагаем случайный нашид
        keyboard = [
            [InlineKeyboardButton("🎲 Случайный нашид", callback_data="random_nasheed")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            "⭐ Нашид дня сегодня еще не установлен.\n\nПопробуйте случайный нашид!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        nasheed_id, file_id, title_ar, title_uz, title_ru, title_en, performer, _, _, _ = daily_nasheed
        lang = db.get_user_language(query.from_user.id) or 'ru'
        lang_map = {'ar': title_ar, 'uz': title_uz, 'ru': title_ru, 'en': title_en}
        nasheed_title = lang_map.get(lang, title_ru)
        
        await context.bot.send_audio(
            chat_id=query.from_user.id, 
            audio=file_id, 
            caption=f"⭐ Нашид дня: {nasheed_title} - {performer}"
        )
        await query.message.delete()
        
        # Автоматически возвращаемся в меню через 3 секунды
        import asyncio
        await asyncio.sleep(3)
        try:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text="🔄 Возвращаемся в главное меню...",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
            )
        except:
            pass

async def chat_with_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Чат с администратором"""
    query = update.callback_query
    db.update_user_activity(query.from_user.id)
    
    user_id = query.from_user.id
    lang = db.get_user_language(user_id) or 'ru'
    
    # Удаляем старое меню
    try:
        await query.message.delete()
    except:
        pass
    
    # Отправляем НОВОЕ сообщение с кнопкой выхода
    chat_msg = await context.bot.send_message(
        chat_id=user_id,
        text=get_text('chat_with_admin_msg', lang),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text('btn_exit_chat', lang), callback_data="exit_chat")]])
    )
    
    context.user_data['in_chat'] = True
    context.user_data['chat_message_id'] = chat_msg.message_id

    # Уведомление админу
    user = query.from_user
    chat_info = f"👤 Пользователь {user.first_name} (@{user.username or 'нет username'}, ID: {user_id}) хочет связаться с вами."
    
    # Создаем чат в БД
    db.get_chat_id(ADMIN_ID, user_id, create_if_not_exists=True)

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=chat_info,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Открыть чат", callback_data=f"open_chat_{user_id}")]
        ])
    )

async def favorite_suras(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Избранные суры пользователя"""
    query = update.callback_query
    db.update_user_activity(query.from_user.id)
    
    user_id = query.from_user.id
    favorites = db.get_user_favorite_suras(user_id)
    
    if not favorites:
        await query.edit_message_text(
            "❌ У вас пока нет избранных сур",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]])
        )
        return
    
    keyboard = []
    for sura_id, order, name, name_ar, qari_name, qari_id in favorites:
        display_name = f"{order}. {name} ({qari_name or '...'})"
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"play_sura_{order}_{qari_id}"), InlineKeyboardButton("❌", callback_data=f"remove_fav_sura_{sura_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
    
    await query.edit_message_text(
        "❤️ Ваши избранные суры:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def listen_nasheed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список нашидов с пагинацией"""
    query = update.callback_query
    db.update_user_activity(query.from_user.id)

    page = context.user_data.get('nasheed_page', 0)
    items_per_page = 10

    nasheeds = db.get_nasheeds(items_per_page, page * items_per_page)
    total_nasheeds = db.get_total_nasheeds_count()

    if not nasheeds:
        await query.edit_message_text(
            "🎵 Нашидов пока нет.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]])
        )
        return

    keyboard = []
    for nasheed_id, title, performer in nasheeds:
        display_name = f"{title} - {performer or '... '}"
        keyboard.append([InlineKeyboardButton(display_name, callback_data=f"play_nasheed_{nasheed_id}")])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"nasheed_page_{page-1}"))
    if (page + 1) * items_per_page < total_nasheeds:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"nasheed_page_{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    
    await query.edit_message_text(
        f"🎵 Нашиды (Стр. {page+1})",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def play_nasheed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Воспроизведение нашида"""
    query = update.callback_query
    user_id = query.from_user.id
    nasheed_id = int(query.data.split("_")[-1])

    nasheed = db.get_nasheed_by_id(nasheed_id)
    if not nasheed:
        await query.message.reply_text("❌ Нашид не найден.")
        return

    file_id = nasheed[1]
    title = nasheed[4] # title_ru

    is_favorite = db.is_nasheed_favorite(user_id, nasheed_id)
    keyboard = []
    if not is_favorite:
        keyboard.append([InlineKeyboardButton("💝 Добавить в избранное", callback_data=f"add_fav_nasheed_{nasheed_id}")])
    else:
        keyboard.append([InlineKeyboardButton("💔 Удалить из избранного", callback_data=f"remove_fav_nasheed_{nasheed_id}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад к нашидам", callback_data="listen_nasheed")])

    # Отправляем аудио с кнопками
    await context.bot.send_audio(
        chat_id=user_id, 
        audio=file_id, 
        caption=f"🎵 {title}",
        reply_markup=InlineKeyboardMarkup(keyboard))
    # Удаляем старое сообщение со списком
    await query.message.delete()
    
    # Автоматически возвращаемся к нашидам через 3 секунды
    import asyncio
    await asyncio.sleep(3)
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="🔄 Возвращаемся к списку нашидов...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ К нашидам", callback_data="listen_nasheed")]])
        )
    except:
        pass

async def favorite_nasheeds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Избранные нашиды пользователя"""
    query = update.callback_query
    user_id = query.from_user.id
    favorites = db.get_user_favorite_nasheeds(user_id)

    if not favorites:
        await query.edit_message_text(
            "❌ У вас пока нет избранных нашидов.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]])
        )
        return

    keyboard = []
    for nasheed_id, title, performer in favorites:
        display_name = f"{title} - {performer or '...'}"
        keyboard.append([
            InlineKeyboardButton(display_name, callback_data=f"play_nasheed_{nasheed_id}"),
            InlineKeyboardButton("❌", callback_data=f"remove_fav_nasheed_{nasheed_id}")
        ])

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
    await query.edit_message_text(
        "💝 Ваши избранные нашиды:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def exit_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выход из режима чата с админом"""
    query = update.callback_query
    user_id = query.from_user.id
    lang = db.get_user_language(user_id) or 'ru'
    
    context.user_data['in_chat'] = False
    context.user_data.pop('chat_message_id', None)
    
    # Удаляем сообщение чата
    try:
        await query.message.delete()
    except:
        pass
    
    # Показываем главное меню заново
    keyboard = await _get_main_keyboard(user_id)
    main_menu_text = get_text('main_menu', lang)
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ Вы вышли из чата.\n\n{main_menu_text}",
        reply_markup=keyboard
    )

async def handle_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех callback от пользователя"""
    query = update.callback_query
    await query.answer()  # ОБЯЗАТЕЛЬНО отвечаем на callback!
    data = query.data # No await needed here
    
    logger.info(f"📞 CALLBACK RECEIVED: {data} from user {query.from_user.id}")
    
    if data == "main_menu":
        await user_start_from_callback(update, context)
    elif data == "chat_with_admin":
        await chat_with_admin(update, context)
    elif data == "listen_quran":
        await listen_quran(update, context)
    elif data == "listen_nasheed":
        context.user_data['nasheed_page'] = 0
        await listen_nasheed(update, context)
    elif data.startswith("nasheed_page_"):
        context.user_data['nasheed_page'] = int(data.split("_")[-1])
        await listen_nasheed(update, context)
    elif data.startswith("qari_"):
        await show_qari_suras(update, context)
    elif data.startswith("back_to_suras_"):
        qari_id = int(data.split("_")[-1])
        context.user_data['current_qari'] = qari_id
        await show_qari_suras(update, context)
    elif data.startswith("play_sura_"):
        await play_sura(update, context)
    elif data.startswith("play_nasheed_"):
        await play_nasheed(update, context)
    elif data == "sura_of_day":
        await sura_of_day(update, context)
    elif data == "nasheed_of_day":
        await nasheed_of_day(update, context)
    elif data == "favorite_suras":
        await favorite_suras(update, context)
    elif data == "favorite_nasheeds":
        await favorite_nasheeds(update, context)
    elif data == "exit_chat":
        await exit_chat(update, context)
    elif data == "change_language":
        await change_language(update, context)
    elif data.startswith("add_fav_sura_"):
        sura_id = data.split("_")[3]
        user_id = query.from_user.id
        db.add_favorite_sura(user_id, sura_id)
        await query.answer("✅ Добавлено в избранное!")
        # Обновляем клавиатуру
        qari_id = context.user_data.get('current_qari')
        new_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💔 Удалить из избранного", callback_data=f"remove_fav_sura_{sura_id}")],
            [InlineKeyboardButton("⬅️ Назад к сурам", callback_data=f"back_to_suras_{qari_id}")]
        ])
        await query.edit_message_reply_markup(reply_markup=new_keyboard)

    elif data.startswith("remove_fav_sura_"):
        sura_id = data.split("_")[3]
        user_id_from_query = query.from_user.id
        db.remove_favorite_sura(user_id_from_query, sura_id)
        await query.answer("✅ Удалено из избранного!")
        # Обновляем клавиатуру или список избранного
        if query.message and "Ваши избранные суры" in query.message.text: # Если мы в избранном
            await favorite_suras(update, context)
        else: # Если мы в списке сур чтеца
            qari_id = context.user_data.get('current_qari')
            new_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❤️ Добавить в избранное", callback_data=f"add_fav_sura_{sura_id}")],
                [InlineKeyboardButton("⬅️ Назад к сурам", callback_data=f"back_to_suras_{qari_id}")]
            ])
            await query.edit_message_reply_markup(reply_markup=new_keyboard)

    elif data.startswith("add_fav_nasheed_"):
        nasheed_id = int(data.split("_")[-1])
        db.add_favorite_nasheed(query.from_user.id, nasheed_id)
        await query.answer("✅ Добавлено в избранное!")
        new_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💔 Удалить из избранного", callback_data=f"remove_fav_nasheed_{nasheed_id}")],
            [InlineKeyboardButton("⬅️ Назад к нашидам", callback_data="listen_nasheed")]
        ])
        await query.edit_message_reply_markup(reply_markup=new_keyboard)

    elif data.startswith("remove_fav_nasheed_"):
        nasheed_id = int(data.split("_")[-1])
        db.remove_favorite_nasheed(query.from_user.id, nasheed_id)
        await query.answer("✅ Удалено из избранного!")
        if query.message and "Ваши избранные нашиды" in query.message.text:
            await favorite_nasheeds(update, context)
        else:
            new_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💝 Добавить в избранное", callback_data=f"add_fav_nasheed_{nasheed_id}")],
                [InlineKeyboardButton("⬅️ Назад к нашидам", callback_data="listen_nasheed")]
            ])
            await query.edit_message_reply_markup(reply_markup=new_keyboard)

    elif data.startswith("lang_"):
        await set_language(update, context)
    
    elif data == "random_sura":
        await play_random_sura(update, context)
    
    elif data == "random_nasheed":
        await play_random_nasheed(update, context)

async def play_random_sura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Воспроизведение случайной суры"""
    query = update.callback_query
    user_id = query.from_user.id
    
    random_sura = db.get_random_sura()
    if not random_sura:
        await query.edit_message_text(
            "❌ Суры не найдены в базе данных",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]])
        )
        return
    
    sura_id, qari_id, order_number, file_id, name_ar, name_uz, name_ru, name_en, _, _, qari_name = random_sura
    lang = db.get_user_language(user_id) or 'ru'
    lang_map = {'ar': name_ar, 'uz': name_uz, 'ru': name_ru, 'en': name_en}
    sura_name = lang_map.get(lang, name_ru)
    
    # Кнопки для избранного
    is_favorite = db.is_sura_favorite(user_id, sura_id)
    keyboard = []
    if not is_favorite:
        keyboard.append([InlineKeyboardButton("❤️ Добавить в избранное", callback_data=f"add_fav_sura_{sura_id}")])
    else:
        keyboard.append([InlineKeyboardButton("💔 Удалить из избранного", callback_data=f"remove_fav_sura_{sura_id}")])
    
    keyboard.append([InlineKeyboardButton("🎲 Еще одна случайная", callback_data="random_sura")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
    
    await context.bot.send_audio(
        chat_id=user_id,
        audio=file_id,
        caption=f"🎲 Случайная сура: {sura_name} - {qari_name}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await query.message.delete()
    
    # Автоматически возвращаемся в меню через 3 секунды
    import asyncio
    await asyncio.sleep(3)
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="🔄 Возвращаемся в главное меню...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
        )
    except:
        pass

async def play_random_nasheed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Воспроизведение случайного нашида"""
    query = update.callback_query
    user_id = query.from_user.id
    
    random_nasheed = db.get_random_nasheed()
    if not random_nasheed:
        await query.edit_message_text(
            "❌ Нашиды не найдены в базе данных",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]])
        )
        return
    
    nasheed_id, file_id, title_ar, title_uz, title_ru, title_en, performer, _, _, _ = random_nasheed
    lang = db.get_user_language(user_id) or 'ru'
    lang_map = {'ar': title_ar, 'uz': title_uz, 'ru': title_ru, 'en': title_en}
    nasheed_title = lang_map.get(lang, title_ru)
    
    # Кнопки для избранного
    is_favorite = db.is_nasheed_favorite(user_id, nasheed_id)
    keyboard = []
    if not is_favorite:
        keyboard.append([InlineKeyboardButton("💝 Добавить в избранное", callback_data=f"add_fav_nasheed_{nasheed_id}")])
    else:
        keyboard.append([InlineKeyboardButton("💔 Удалить из избранного", callback_data=f"remove_fav_nasheed_{nasheed_id}")])
    
    keyboard.append([InlineKeyboardButton("🎲 Еще один случайный", callback_data="random_nasheed")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
    
    await context.bot.send_audio(
        chat_id=user_id,
        audio=file_id,
        caption=f"🎲 Случайный нашид: {nasheed_title} - {performer}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await query.message.delete()
    
    # Автоматически возвращаемся в меню через 3 секунды
    import asyncio
    await asyncio.sleep(3)
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="🔄 Возвращаемся в главное меню...",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])
        )
    except:
        pass

async def user_start_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт из callback (без сообщения)"""
    query = update.callback_query
    user = query.from_user
    db.save_user(user.id, user.username, user.first_name)
    db.update_user_activity(user.id)
    keyboard = await _get_main_keyboard(user.id)
    
    lang = db.get_user_language(user.id) or 'ru'
    main_menu_text = get_text('main_menu', lang)
    
    await query.edit_message_text(
        main_menu_text,
        reply_markup=keyboard,
    )

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Смена языка"""
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru")],
        [InlineKeyboardButton("English 🇺🇸", callback_data="lang_en")],
        [InlineKeyboardButton("العربية 🇸🇦", callback_data="lang_ar")],
        [InlineKeyboardButton("O'zbek 🇺🇿", callback_data="lang_uz")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        "🌍 Выберите язык:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка языка и переход к главному меню"""
    query = update.callback_query
    
    language = query.data.split("_")[1]
    user_id = query.from_user.id
    
    logger.info(f"🌍 User {user_id} selected language: {language}")
    
    db.set_user_language(user_id, language)
    
    # Показываем главное меню на выбранном языке
    keyboard = await _get_main_keyboard(user_id)
    main_menu_text = get_text('main_menu', language)
    
    await query.edit_message_text(
        main_menu_text,
        reply_markup=keyboard
    )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений пользователя - поддержка текста, фото, видео, аудио"""
    db.update_user_activity(update.effective_user.id)
    user_id = update.effective_user.id
    lang = db.get_user_language(user_id) or 'ru'

    # Проверяем, находится ли пользователь в режиме чата с админом
    if context.user_data.get('in_chat'):
        user = update.effective_user
        chat_id = db.get_chat_id(ADMIN_ID, user_id, create_if_not_exists=True)
        
        # Определяем тип сообщения
        message_text = ""
        if update.message.text:
            message_text = update.message.text
        elif update.message.photo:
            message_text = "[ФОТО]"
        elif update.message.video:
            message_text = "[ВИДЕО]"
        elif update.message.audio:
            message_text = "[АУДИО]"
        elif update.message.voice:
            message_text = "[ГОЛОСОВОЕ]"
        elif update.message.document:
            message_text = "[ДОКУМЕНТ]"
        
        # Сохраняем сообщение в БД
        if chat_id and message_text:
            db.save_message(chat_id, user_id, message_text, is_from_admin=False)
            logger.info(f"💬 Message from user {user_id} saved to DB: {message_text}")
        
        # НЕ ОТПРАВЛЯЕМ подтверждения - просто сохраняем
        # Уведомляем админа только при ПЕРВОМ сообщении в чате
        if not context.user_data.get('admin_notified'):
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔔 Новое сообщение от {user.first_name} (@{user.username or 'N/A'}, ID: {user_id})\n\n"
                     f"Откройте 'Управление пользователями' для просмотра.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💬 Открыть чат", callback_data=f"open_chat_{user_id}")]
                ])
            )
            context.user_data['admin_notified'] = True
    else:
        # Если пользователь просто пишет текст вне чата, предлагаем использовать меню
        await update.message.reply_text(
            get_text('use_menu_buttons', lang)
        )

async def inline_sura_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI-поиск сур с автодополнением - показывает сразу варианты"""
    from telegram import InlineQueryResultAudio
    
    query_text = update.inline_query.query.strip()
    
    results = []
    
    # Если пустой запрос - показываем популярные суры
    if len(query_text) == 0:
        popular = [1, 36, 55, 67, 112]  # Фатиха, Йа-Син, Рахман, Мульк, Ихлас
        for sura_num in popular:
            names = SURA_NAMES.get(sura_num, {})
            qaris = db.get_all_qaris()
            
            for qari in qaris[:3]:  # Топ 3 чтеца
                qari_id = qari[0]
                qari_name_ru = qari[2]
                file_id = db.get_sura_file_id(qari_id, sura_num)
                
                if file_id:
                    results.append(
                        InlineQueryResultAudio(
                            id=f"pop_{qari_id}_{sura_num}",
                            audio_file_id=file_id,
                            title=f"⭐ {sura_num}. {names.get('ru', '')}",
                            performer=qari_name_ru
                        )
                    )
        
        await update.inline_query.answer(results[:10], cache_time=30)
        return
    
    logger.info(f"🔍 Inline search: '{query_text}'")
    
    # Поиск с автодополнением на ВСЕХ языках
    for sura_num, names in SURA_NAMES.items():
        found = False
        
        # Поиск по всем языкам + номеру
        for lang_code, name in names.items():
            if query_text.lower() in name.lower() or str(sura_num) == query_text:
                found = True
                break
        
        if found:
            # Получаем всех чтецов с этой сурой
            qaris = db.get_all_qaris()
            
            for qari in qaris:
                qari_id = qari[0]
                qari_name_ru = qari[2]
                
                file_id = db.get_sura_file_id(qari_id, sura_num)
                
                if file_id:
                    # Автодополнение в заголовке
                    title = f"{sura_num}. {names['ru']} ({names['ar']})"
                    
                    results.append(
                        InlineQueryResultAudio(
                            id=f"s_{qari_id}_{sura_num}",
                            audio_file_id=file_id,
                            title=title,
                            performer=f"🎙 {qari_name_ru}",
                            caption=f"📖 {names['ru']}\n🇸🇦 {names['ar']}\n🎙 {qari_name_ru}"
                        )
                    )
            
            if len(results) >= 20:
                break
    
    await update.inline_query.answer(results, cache_time=10, is_personal=True)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

async def force_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительное обновление - для тестирования"""
    logger.info(f"🔄 Force refresh from user {update.effective_user.id}")
    await update.message.reply_text("🔄 Обновление бота...\nОтправьте /start")

def main():
    logger.info("=" * 60)
    logger.info("🚀 STARTING USER BOT")
    logger.info("=" * 60)
    
    application = Application.builder().token(USER_BOT_TOKEN).build()
    
    # Обработчики
    logger.info("📝 Registering handlers...")
    application.add_handler(CommandHandler("start", user_start))
    application.add_handler(CommandHandler("refresh", force_refresh))
    logger.info("  ✅ CommandHandler: /start, /refresh")
    
    # InlineQueryHandler для поиска сур
    application.add_handler(InlineQueryHandler(inline_sura_search))
    logger.info("  ✅ InlineQueryHandler: inline_sura_search")
    
    # CallbackQueryHandler должен быть первым, чтобы обрабатывать все нажатия кнопок
    application.add_handler(CallbackQueryHandler(handle_user_callback))
    logger.info("  ✅ CallbackQueryHandler: handle_user_callback")
    
    # MessageHandler для текстовых сообщений и медиа (включая чат с админом)
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE | filters.Document.ALL) & ~filters.COMMAND,
        handle_user_message
    ))
    logger.info("  ✅ MessageHandler: handle_user_message (text + media)")
    
    application.add_error_handler(error_handler)
    logger.info("  ✅ ErrorHandler: error_handler")
    
    logger.info("=" * 60)
    logger.info("✅ User bot started successfully!")
    logger.info("📱 Send /start to your bot in Telegram")
    logger.info("=" * 60)
    
    application.run_polling()

if __name__ == '__main__':
    main()