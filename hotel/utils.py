from django.conf import settings
import requests
from .models import Order, SiteSettings


def send_telegram_notification(order):
    """Отправка уведомления о новом заказе в Telegram"""
    site_settings = SiteSettings.get_settings()
    
    # Используем настройки из БД, если они есть, иначе из settings.py
    bot_token = site_settings.telegram_bot_token or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = site_settings.telegram_chat_id or getattr(settings, 'TELEGRAM_CHAT_ID', '')
    
    if not bot_token or not chat_id:
        return None
    
    # Формируем текст сообщения
    items_text = "\n".join([
        f"• {item.product.name} x{item.quantity} - {item.price_at_moment * item.quantity} ₽"
        for item in order.items.all()
    ])
    
    message = f"""
🆕 Новый заказ #{order.id}

📍 Номер: {order.room}
💰 Сумма: {order.total_price} ₽
🕐 Время: {order.created_at.strftime('%H:%M')}

📋 Состав:
{items_text}

Статус: {order.get_status_display()}
"""
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                message_id = result.get('result', {}).get('message_id')
                order.telegram_message_id = str(message_id)
                order.save()
                return message_id
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")
    
    return None


def update_order_status_telegram(order):
    """Обновление сообщения в Telegram при изменении статуса"""
    site_settings = SiteSettings.get_settings()
    
    # Используем настройки из БД, если они есть, иначе из settings.py
    bot_token = site_settings.telegram_bot_token or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = site_settings.telegram_chat_id or getattr(settings, 'TELEGRAM_CHAT_ID', '')
    
    if not bot_token or not chat_id or not order.telegram_message_id:
        return
    
    items_text = "\n".join([
        f"• {item.product.name} x{item.quantity} - {item.price_at_moment * item.quantity} ₽"
        for item in order.items.all()
    ])
    
    status_emoji = {
        'new': '🆕',
        'cooking': '🍳',
        'done': '✅',
        'archived': '📦'
    }
    
    emoji = status_emoji.get(order.status, '📋')
    
    message = f"""
{emoji} Заказ #{order.id}

📍 Номер: {order.room}
💰 Сумма: {order.total_price} ₽
🕐 Время: {order.created_at.strftime('%H:%M')}

📋 Состав:
{items_text}

Статус: {order.get_status_display()}
"""
    
    url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
    data = {
        "chat_id": chat_id,
        "message_id": int(order.telegram_message_id),
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(url, json=data)
    except Exception as e:
        print(f"Error updating Telegram message: {e}")

