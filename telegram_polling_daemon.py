#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Long Polling Daemon
Chạy script này trong terminal riêng để bot phản hồi gần như tức thì.

Usage:
    cd /home/hwungg/Business-Internship
    source venv/bin/activate
    python3 telegram_polling_daemon.py
"""

import requests
import json
import time
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
_logger = logging.getLogger('TelegramDaemon')

# ─── Cấu hình ────────────────────────────────────────────────────────────────
BOT_TOKEN     = '8626565906:AAGYCeNn4PZT15CPx5Dacd57HBNH_Uy6tEQ'
ODOO_URL      = 'http://localhost:8069'
ODOO_DB       = 'QLNS'
ODOO_USER     = 'admin'
ODOO_PASSWORD = 'admin'          # đổi nếu mật khẩu admin khác
TELEGRAM_API  = f'https://api.telegram.org/bot{BOT_TOKEN}'
LONG_POLL_TIMEOUT = 25           # giây chờ Telegram (gần như tức thì khi có tin)
# ─────────────────────────────────────────────────────────────────────────────


def get_odoo_session(max_retries=10, retry_delay=5):
    """Đăng nhập Odoo, trả về session requests. Retry nếu Odoo chưa sẵn sàng."""
    for attempt in range(1, max_retries + 1):
        try:
            session = requests.Session()
            auth = session.post(f'{ODOO_URL}/web/session/authenticate', json={
                'jsonrpc': '2.0',
                'method': 'call',
                'params': {
                    'db': ODOO_DB,
                    'login': ODOO_USER,
                    'password': ODOO_PASSWORD,
                }
            }, timeout=10)

            result = auth.json()
            uid = result.get('result', {}).get('uid')
            if uid:
                _logger.info(f"✅ Đăng nhập Odoo thành công (uid={uid})")
                return session
            else:
                _logger.warning(f"Đăng nhập Odoo thất bại (attempt {attempt}): {result.get('error', 'unknown')}")
        except Exception as e:
            _logger.warning(f"Odoo chưa sẵn sàng (attempt {attempt}/{max_retries}): {e}")

        if attempt < max_retries:
            _logger.info(f"Thử lại sau {retry_delay}s...")
            time.sleep(retry_delay)

    _logger.error("❌ Không thể kết nối Odoo sau nhiều lần thử.")
    return None


def call_odoo(session, model, method, args=None, kwargs=None):
    """Gọi một method Odoo qua JSON-RPC."""
    try:
        resp = session.post(f'{ODOO_URL}/web/dataset/call_kw', json={
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'model': model,
                'method': method,
                'args': args or [],
                'kwargs': kwargs or {}
            }
        }, timeout=30)
        result = resp.json()
        if 'error' in result:
            _logger.error(f"Odoo error: {result['error']}")
            return None
        return result.get('result')
    except Exception as e:
        _logger.error(f"Odoo RPC error: {e}")
        return None


def get_telegram_updates(offset=None):
    """Long polling Telegram — block tới LONG_POLL_TIMEOUT giây."""
    params = {'timeout': LONG_POLL_TIMEOUT, 'allowed_updates': ['message']}
    if offset is not None:
        params['offset'] = offset
    try:
        resp = requests.get(f'{TELEGRAM_API}/getUpdates',
                            params=params,
                            timeout=LONG_POLL_TIMEOUT + 5)
        data = resp.json()
        if data.get('ok'):
            return data.get('result', [])
    except requests.exceptions.Timeout:
        pass   # Normal timeout, không có tin mới
    except Exception as e:
        _logger.error(f"Telegram API error: {e}")
        time.sleep(5)
    return []


def process_update_in_odoo(session, update):
    """Gửi update lên Odoo để xử lý command."""
    message = update.get('message') or update.get('edited_message')
    if not message:
        return

    chat_id = str(message.get('chat', {}).get('id', ''))
    text = (message.get('text') or '').strip()
    location = message.get('location')

    if not chat_id or (not text and not location):
        return

    _logger.info(f"📨 [{chat_id}] text='{text}', location={bool(location)}")

    # Tìm config trong Odoo và xử lý update
    # Dùng execute_kw để gọi poll_updates vs _handle_update trực tiếp
    # (poll_updates bên Odoo sẽ gọi getUpdates lần nữa — bỏ qua)
    # Thay vào đó, gọi _handle_message_direct nếu có, hoặc dùng workaround:
    call_odoo(session,
              'telegram.bot.config',
              'handle_message_from_daemon',
              kwargs={'chat_id': chat_id, 'text': text,
                      'message': json.dumps(message)})


def main():
    _logger.info("🚀 Telegram Polling Daemon đang khởi động...")
    _logger.info(f"   Bot token: ...{BOT_TOKEN[-10:]}")
    _logger.info(f"   Odoo URL: {ODOO_URL}")

    # Kiểm tra kết nối Telegram
    try:
        me = requests.get(f'{TELEGRAM_API}/getMe', timeout=10).json()
        if me.get('ok'):
            bot = me['result']
            _logger.info(f"✅ Telegram Bot: @{bot['username']} ({bot['first_name']})")
        else:
            _logger.error("❌ Không kết nối được Telegram Bot!")
            sys.exit(1)
    except Exception as e:
        _logger.error(f"❌ Lỗi kết nối Telegram: {e}")
        sys.exit(1)

    # Đăng nhập Odoo
    session = get_odoo_session()
    if not session:
        _logger.warning("⚠️  Không đăng nhập được Odoo. Daemon vẫn chạy nhưng dùng Odoo built-in xử lý.")

    offset = None
    _logger.info("✅ Bắt đầu long polling... (Ctrl+C để dừng)\n")

    while True:
        try:
            updates = get_telegram_updates(offset)

            for update in updates:
                update_id = update.get('update_id', 0)

                if session:
                    # Xử lý qua Odoo RPC
                    process_update_in_odoo(session, update)
                else:
                    # Fallback: log để debug
                    msg = update.get('message', {})
                    _logger.info(f"Update [{update_id}]: {msg.get('text', '')}")

                # Advance offset để không nhận lại update này
                offset = update_id + 1

        except KeyboardInterrupt:
            _logger.info("\n👋 Daemon đã dừng.")
            break
        except Exception as e:
            _logger.error(f"Loop error: {e}")
            time.sleep(5)


if __name__ == '__main__':
    main()
