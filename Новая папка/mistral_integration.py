# mistral_integration.py
import requests
import logging
import json
from config import MISTRAL_API_KEY

logger = logging.getLogger(__name__)

class MistralTranslator:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.mistral.ai/v1/chat/completions"
    
    def translate_text(self, text, target_lang):
        """Перевод текста через Mistral AI"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            lang_prompts = {
                'ar': f"Translate exactly to Arabic only the text without explanations: {text}",
                'uz': f"Translate exactly to Uzbek only the text without explanations: {text}", 
                'ru': f"Translate exactly to Russian only the text without explanations: {text}",
                'en': f"Translate exactly to English only the text without explanations: {text}"
            }
            
            data = {
                "model": "mistral-tiny",
                "messages": [{"role": "user", "content": lang_prompts[target_lang]}],
                "temperature": 0.1,
                "max_tokens": 100
            }
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            
            translated = response.json()['choices'][0]['message']['content'].strip()
            logger.info(f"Translated '{text}' to '{target_lang}': '{translated}'")
            return translated
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text  # Возвращаем оригинал при ошибке

    def translate_to_all_languages(self, text, source_lang='ru'):
        """
        Перевод текста на все поддерживаемые языки (ar, uz, ru, en)
        Возвращает dict с переводами или JSON-отчет с ошибками
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Определяем системный промпт для генерации всех переводов сразу
            system_prompt = f"""You are a professional translator. Translate the given text to Arabic, Uzbek, Russian, and English.
Return ONLY a valid JSON object in this exact format without any additional text or explanation:
{{"ar": "translation in Arabic", "uz": "translation in Uzbek", "ru": "translation in Russian", "en": "translation in English"}}

Rules:
- Return ONLY the JSON object, nothing else
- Keep names phonetically accurate
- For proper names, transliterate appropriately for each language
- Ensure all 4 languages are present in response"""

            user_prompt = f"Translate this text: {text}"
            
            data = {
                "model": "mistral-small-latest",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 300
            }
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=15)
            response.raise_for_status()
            
            result_text = response.json()['choices'][0]['message']['content'].strip()
            
            # Пытаемся распарсить JSON из ответа
            try:
                # Убираем возможные markdown обертки
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                    result_text = result_text.strip()
                
                translations = json.loads(result_text)
                
                # Валидация: проверяем что все языки присутствуют
                required_langs = ['ar', 'uz', 'ru', 'en']
                if not all(lang in translations for lang in required_langs):
                    raise ValueError("Not all languages present in translation")
                
                logger.info(f"Successfully translated '{text}' to all languages")
                return {
                    "status": "ok",
                    "action": "translate_name",
                    "translations": translations,
                    "needs_review": False
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse translation JSON: {e}")
                # Fallback: возвращаем одинаковый текст для всех языков
                return {
                    "status": "error",
                    "action": "translate_name",
                    "error": "Failed to parse AI response",
                    "translations": {'ar': text, 'uz': text, 'ru': text, 'en': text},
                    "needs_review": True
                }
            
        except Exception as e:
            logger.error(f"Translation API error: {e}")
            return {
                "status": "error",
                "action": "translate_name",
                "error": str(e),
                "translations": {'ar': text, 'uz': text, 'ru': text, 'en': text},
                "needs_review": True
            }
    
    def translate_broadcast_message(self, text, target_lang):
        """Перевод сообщения для рассылки на конкретный язык"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            lang_names = {
                'ar': 'Arabic',
                'uz': 'Uzbek',
                'ru': 'Russian',
                'en': 'English'
            }
            
            system_prompt = f"You are a professional translator. Translate the following message to {lang_names[target_lang]}. Preserve formatting, emojis, and line breaks. Return ONLY the translated text without any explanations."
            
            data = {
                "model": "mistral-small-latest",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.2,
                "max_tokens": 1000
            }
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=20)
            response.raise_for_status()
            
            translated = response.json()['choices'][0]['message']['content'].strip()
            logger.info(f"Translated broadcast message to '{target_lang}'")
            return translated
            
        except Exception as e:
            logger.error(f"Broadcast translation error for {target_lang}: {e}")
            return text  # Возвращаем оригинал при ошибке

# Глобальный экземпляр переводчика
translator = MistralTranslator(MISTRAL_API_KEY)