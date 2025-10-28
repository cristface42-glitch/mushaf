# text_resources.py
"""Текстовые ресурсы на всех языках (ar, uz, ru, en)"""

TEXTS = {
    # Главное меню
    'main_menu': {
        'ar': '🌸 ماذا نستمع اليوم؟',
        'uz': '🌸 Bugun nimani tinglaymiz?',
        'ru': '🌸 Что сегодня послушаем?',
        'en': '🌸 What shall we listen to today?'
    },
    'welcome': {
        'ar': 'مرحباً بك في بوت القرآن الكريم 🌸',
        'uz': 'Quron botiga xush kelibsiz 🌸', 
        'ru': 'Добро пожаловать в Коран бот 🌸',
        'en': 'Welcome to Quran bot 🌸'
    },
    
    # Кнопки главного меню
    'btn_listen_quran': {
        'ar': '📖 استماع القرآن',
        'uz': '📖 Quronni tinglash',
        'ru': '📖 Слушать Коран',
        'en': '📖 Listen to Quran'
    },
    'btn_listen_nasheed': {
        'ar': '🎵 استماع الأناشيد',
        'uz': '🎵 Nasheedlar tinglash',
        'ru': '🎵 Слушать Нашиды',
        'en': '🎵 Listen to Nasheeds'
    },
    'btn_sura_of_day': {
        'ar': '🌙 سورة اليوم',
        'uz': '🌙 Kun surasi',
        'ru': '🌙 Сура дня',
        'en': '🌙 Surah of the day'
    },
    'btn_nasheed_of_day': {
        'ar': '⭐ نشيد اليوم',
        'uz': '⭐ Kun nasheedi',
        'ru': '⭐ Нашид дня',
        'en': '⭐ Nasheed of the day'
    },
    'btn_favorite_suras': {
        'ar': '❤️ السور المفضلة',
        'uz': '❤️ Sevimli suralar',
        'ru': '❤️ Избранные суры',
        'en': '❤️ Favorite Surahs'
    },
    'btn_favorite_nasheeds': {
        'ar': '💝 الأناشيد المفضلة',
        'uz': '💝 Sevimli nasheedlar',
        'ru': '💝 Избранные нашиды',
        'en': '💝 Favorite Nasheeds'
    },
    'btn_chat_admin': {
        'ar': '💬 الدردشة مع المسؤول',
        'uz': '💬 Admin bilan chat',
        'ru': '💬 Чат с админом',
        'en': '💬 Chat with admin'
    },
    'btn_language': {
        'ar': '🌍 اللغة',
        'uz': '🌍 Til',
        'ru': '🌍 Язык',
        'en': '🌍 Language'
    },
    
    # Выбор чтеца
    'choose_reciter': {
        'ar': '🎙 اختر القارئ',
        'uz': '🎙 Qorini tanlang',
        'ru': '🎙 Выберите чтеца',
        'en': '🎙 Choose reciter'
    },
    'no_reciters': {
        'ar': '❌ لا يوجد قراء متاحون حالياً',
        'uz': '❌ Hozircha qorilar mavjud emas',
        'ru': '❌ Пока нет доступных чтецов',
        'en': '❌ No reciters available yet'
    },
    
    # Суры
    'choose_surah': {
        'ar': '🎙 {} - اختر السورة',
        'uz': '🎙 {} - Surani tanlang',
        'ru': '🎙 {} - Выберите суру',
        'en': '🎙 {} - Choose surah'
    },
    'no_suras': {
        'ar': '❌ لا توجد سور لهذا القارئ',
        'uz': '❌ Bu qori uchun suralar yo\'q',
        'ru': '❌ Для этого чтеца пока нет сур',
        'en': '❌ No surahs for this reciter yet'
    },
    'sura_not_found': {
        'ar': '❌ السورة غير موجودة',
        'uz': '❌ Sura topilmadi',
        'ru': '❌ Сура не найдена',
        'en': '❌ Surah not found'
    },
    'btn_search_sura': {
        'ar': '🔍 البحث عن سورة',
        'uz': '🔍 Sura qidirish',
        'ru': '🔍 Поиск суры',
        'en': '🔍 Search surah'
    },
    
    # Нашиды
    'no_nasheeds': {
        'ar': '🎵 لا توجد أناشيد حالياً',
        'uz': '🎵 Hozircha nasheedlar yo\'q',
        'ru': '🎵 Нашидов пока нет',
        'en': '🎵 No nasheeds available yet'
    },
    'nasheed_not_found': {
        'ar': '❌ النشيد غير موجود',
        'uz': '❌ Nasheed topilmadi',
        'ru': '❌ Нашид не найден',
        'en': '❌ Nasheed not found'
    },
    
    # Контент дня
    'no_sura_of_day': {
        'ar': '🌙 لم يتم تحديد سورة اليوم\n\nجرب سورة عشوائية!',
        'uz': '🌙 Kun surasi hali belgilanmagan\n\nTasodifiy surani sinab ko\'ring!',
        'ru': '🌙 Сура дня сегодня еще не установлена\n\nПопробуйте случайную суру!',
        'en': '🌙 Surah of the day not set yet\n\nTry a random surah!'
    },
    'no_nasheed_of_day': {
        'ar': '⭐ لم يتم تحديد نشيد اليوم\n\nجرب نشيداً عشوائياً!',
        'uz': '⭐ Kun nasheedi hali belgilanmagan\n\nTasodifiy nasheedni sinab ko\'ring!',
        'en': '⭐ Nasheed of the day not set yet\n\nTry a random nasheed!',
        'ru': '⭐ Нашид дня сегодня еще не установлен\n\nПопробуйте случайный нашид!'
    },
    'btn_random_sura': {
        'ar': '🎲 سورة عشوائية',
        'uz': '🎲 Tasodifiy sura',
        'ru': '🎲 Случайная сура',
        'en': '🎲 Random surah'
    },
    'btn_random_nasheed': {
        'ar': '🎲 نشيد عشوائي',
        'uz': '🎲 Tasodifiy nasheed',
        'ru': '🎲 Случайный нашид',
        'en': '🎲 Random nasheed'
    },
    'btn_another_random': {
        'ar': '🎲 آخر عشوائي',
        'uz': '🎲 Yana bir tasodifiy',
        'ru': '🎲 Еще одна случайная',
        'en': '🎲 Another random'
    },
    
    # Избранное
    'no_favorite_suras': {
        'ar': '❌ لا توجد سور مفضلة',
        'uz': '❌ Sevimli suralar yo\'q',
        'ru': '❌ У вас пока нет избранных сур',
        'en': '❌ No favorite surahs yet'
    },
    'no_favorite_nasheeds': {
        'ar': '❌ لا توجد أناشيد مفضلة',
        'uz': '❌ Sevimli nasheedlar yo\'q',
        'ru': '❌ У вас пока нет избранных нашидов',
        'en': '❌ No favorite nasheeds yet'
    },
    'favorite_suras_title': {
        'ar': '❤️ سورك المفضلة',
        'uz': '❤️ Sizning sevimli suralaringiz',
        'ru': '❤️ Ваши избранные суры',
        'en': '❤️ Your favorite surahs'
    },
    'favorite_nasheeds_title': {
        'ar': '💝 أناشيدك المفضلة',
        'uz': '💝 Sizning sevimli nasheedlaringiz',
        'ru': '💝 Ваши избранные нашиды',
        'en': '💝 Your favorite nasheeds'
    },
    'btn_add_favorite': {
        'ar': '❤️ أضف إلى المفضلة',
        'uz': '❤️ Sevimliga qo\'shish',
        'ru': '❤️ Добавить в избранное',
        'en': '❤️ Add to favorites'
    },
    'btn_remove_favorite': {
        'ar': '💔 إزالة من المفضلة',
        'uz': '💔 Sevimlilardan o\'chirish',
        'ru': '💔 Удалить из избранного',
        'en': '💔 Remove from favorites'
    },
    
    # Чат с админом
    'chat_with_admin_msg': {
        'ar': '💬 أنت الآن في محادثة مع المسؤول. اكتب رسالتك',
        'uz': '💬 Siz admin bilan chatdasiz. Xabaringizni yozing',
        'ru': '💬 Вы в чате с администратором. Напишите ваше сообщение',
        'en': '💬 You are chatting with admin. Write your message'
    },
    'btn_exit_chat': {
        'ar': '🚪 الخروج من المحادثة',
        'uz': '🚪 Chatdan chiqish',
        'ru': '🚪 Выйти из чата',
        'en': '🚪 Exit chat'
    },
    'btn_notify_admin': {
        'ar': '📬 إبلاغ المسؤول',
        'uz': '📬 Adminga xabar berish',
        'ru': '📬 Сообщить админу',
        'en': '📬 Notify admin'
    },
    
    # Смена языка
    'select_language': {
        'ar': '🌍 اختر اللغة',
        'uz': '🌍 Tilni tanlang',
        'ru': '🌍 Выберите язык',
        'en': '🌍 Select language'
    },
    'language_changed': {
        'ar': '✅ تم تغيير اللغة إلى {}',
        'uz': '✅ Til {} ga o\'zgartirildi',
        'ru': '✅ Язык изменен на {}',
        'en': '✅ Language changed to {}'
    },
    
    # Общие
    'back': {
        'ar': '⬅️ رجوع',
        'uz': '⬅️ Orqaga',
        'ru': '⬅️ Назад',
        'en': '⬅️ Back'
    },
    'home': {
        'ar': '🏠 الصفحة الرئيسية',
        'uz': '🏠 Bosh sahifa',
        'ru': '🏠 Главное меню',
        'en': '🏠 Home'
    },
    'next': {
        'ar': 'التالي ▶️',
        'uz': 'Keyingi ▶️',
        'ru': 'Следующие ▶️',
        'en': 'Next ▶️'
    },
    'previous': {
        'ar': '◀️ السابق',
        'uz': '◀️ Oldingi',
        'ru': '◀️ Предыдущие',
        'en': '◀️ Previous'
    },
    'error_occurred': {
        'ar': '❌ حدث خطأ',
        'uz': '❌ Xatolik yuz berdi',
        'ru': '❌ Произошла ошибка',
        'en': '❌ An error occurred'
    },
    'use_menu_buttons': {
        'ar': 'للتنقل، يرجى استخدام أزرار القائمة. اضغط /start لرؤية القائمة الرئيسية',
        'uz': 'Navigatsiya uchun menyu tugmalaridan foydalaning. Asosiy menyuni ko\'rish uchun /start bosing',
        'ru': 'Для навигации, пожалуйста, используйте кнопки меню. Нажмите /start, чтобы увидеть главное меню',
        'en': 'Please use menu buttons for navigation. Press /start to see the main menu'
    },
    
    # Имена языков
    'lang_ar': {
        'ar': 'العربية',
        'uz': 'Arabcha',
        'ru': 'Арабский',
        'en': 'Arabic'
    },
    'lang_uz': {
        'ar': 'الأوزبكية',
        'uz': 'O\'zbekcha',
        'ru': 'Узбекский',
        'en': 'Uzbek'
    },
    'lang_ru': {
        'ar': 'الروسية',
        'uz': 'Ruscha',
        'ru': 'Русский',
        'en': 'Russian'
    },
    'lang_en': {
        'ar': 'الإنجليزية',
        'uz': 'Inglizcha',
        'ru': 'Английский',
        'en': 'English'
    }
}

def get_text(key, language='ru', format_args=None):
    """Получить текст на нужном языке"""
    text = TEXTS.get(key, {}).get(language, TEXTS.get(key, {}).get('ru', key))
    if format_args:
        if isinstance(format_args, (list, tuple)):
            text = text.format(*format_args)
        else:
            text = text.format(format_args)
    return text