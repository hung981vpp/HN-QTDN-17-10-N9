# -*- coding: utf-8 -*-
"""
Telegram Bot API Wrapper
Wrapper cho Telegram Bot API (api.telegram.org)
"""
import requests
import logging
import json

_logger = logging.getLogger(__name__)


class TelegramBotAPI:
    """Wrapper class cho Telegram Bot API"""

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, bot_token):
        self.bot_token = bot_token

    def _make_request(self, method, data=None):
        url = self.BASE_URL.format(token=self.bot_token, method=method)

        try:
            _logger.info(f"Telegram API Request: {method}")
            response = requests.post(url, json=data, timeout=35)
            response.raise_for_status()

            result = response.json()
            _logger.info(f"Telegram API Response: {method} - ok: {result.get('ok')}")
            return result

        except requests.exceptions.Timeout:
            _logger.error(f"Telegram API Timeout: {method}")
            return None
        except requests.exceptions.RequestException as e:
            _logger.error(f"Telegram API Request Error: {method} - {str(e)}")
            return None
        except json.JSONDecodeError as e:
            _logger.error(f"Telegram API JSON Decode Error: {method} - {str(e)}")
            return None
        except Exception as e:
            _logger.error(f"Telegram API Unexpected Error: {method} - {str(e)}")
            return None

    def get_me(self):
        """Lấy thông tin bot"""
        return self._make_request('getMe')

    def get_updates(self, offset=None, timeout=30):
        """
        Lấy tin nhắn mới (long polling)
        - offset: update_id + 1 của update cuối đã xử lý
        - Telegram trả về list updates (khác Zalo)
        """
        data = {'timeout': timeout}
        if offset is not None:
            data['offset'] = offset
        return self._make_request('getUpdates', data)

    def send_message(self, chat_id, text, parse_mode='HTML'):
        """Gửi tin nhắn text đến user"""
        data = {
            'chat_id': str(chat_id),
            'text': str(text),
        }
        if parse_mode:
            data['parse_mode'] = parse_mode
        return self._make_request('sendMessage', data)

    def send_photo(self, chat_id, photo_url, caption=None):
        """Gửi ảnh đến user"""
        data = {
            'chat_id': str(chat_id),
            'photo': photo_url,
        }
        if caption:
            data['caption'] = caption
        return self._make_request('sendPhoto', data)

    def send_chat_action(self, chat_id, action='typing'):
        """Gửi trạng thái 'typing...' hoặc 'upload_photo...' cho user"""
        data = {
            'chat_id': str(chat_id),
            'action': action,
        }
        return self._make_request('sendChatAction', data)
