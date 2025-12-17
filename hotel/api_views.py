from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import Order
from .utils import update_order_status_telegram


@csrf_exempt
@require_http_methods(["POST"])
def telegram_webhook(request):
    """Webhook для обработки callback от Telegram бота"""
    try:
        data = json.loads(request.body)
        callback_query = data.get('callback_query')
        
        if not callback_query:
            return JsonResponse({'ok': True})
        
        callback_data = callback_query.get('data', '')
        user = callback_query.get('from', {})
        
        # Обработка callback данных
        if callback_data.startswith('order_'):
            parts = callback_data.split('_')
            if len(parts) >= 3:
                action = parts[1]  # accept, cooking, done
                order_id = int(parts[2])
                
                order = Order.objects.get(id=order_id)
                
                status_map = {
                    'accept': 'cooking',
                    'cooking': 'cooking',
                    'done': 'done',
                }
                
                new_status = status_map.get(action)
                if new_status:
                    order.status = new_status
                    if new_status == 'done':
                        order.is_archived = True
                    order.save()
                    
                    # Обновляем сообщение в Telegram
                    update_order_status_telegram(order)
                    
                    # Отвечаем на callback
                    from django.conf import settings
                    import requests
                    
                    bot_token = settings.TELEGRAM_BOT_TOKEN
                    callback_id = callback_query.get('id')
                    
                    if bot_token and callback_id:
                        url = f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery"
                        requests.post(url, json={
                            "callback_query_id": callback_id,
                            "text": f"Статус изменен на: {order.get_status_display()}"
                        })
        
        return JsonResponse({'ok': True})
    except Exception as e:
        print(f"Error processing Telegram webhook: {e}")
        return JsonResponse({'ok': False, 'error': str(e)})


@require_http_methods(["GET"])
def orders_live(request):
    """API для получения списка заказов в реальном времени"""
    from django.contrib.auth.decorators import login_required
    from django.utils.decorators import method_decorator
    
    if not request.user.is_authenticated:
        return JsonResponse({'orders': []})
    
    status_filter = request.GET.get('status', '')
    
    orders = Order.objects.filter(is_archived=False).select_related('room', 'room__floor', 'room__floor__building').prefetch_related('items__product').order_by('-created_at')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    orders = orders[:50]
    
    orders_data = []
    for order in orders:
        room_info = f"{order.room.number}"
        if order.room.floor.building:
            room_info += f" ({order.room.floor.building.name}, Этаж {order.room.floor.number})"
        else:
            room_info += f" (Этаж {order.room.floor.number})"
        
        items_data = []
        for item in order.items.all():
            items_data.append({
                'name': item.product.name,
                'quantity': item.quantity,
                'price': float(item.price_at_moment),
            })
        
        orders_data.append({
            'id': order.id,
            'room': room_info,
            'room_number': order.room.number,
            'building': order.room.floor.building.name if order.room.floor.building else None,
            'floor': order.room.floor.number,
            'total_price': float(order.total_price),
            'status': order.status,
            'status_display': order.get_status_display(),
            'created_at': order.created_at.strftime('%H:%M:%S'),
            'items': items_data,
            'items_count': len(items_data),
        })
    
    return JsonResponse({'orders': orders_data})


@require_http_methods(["GET"])
def unviewed_orders(request):
    """API для получения непросмотренных заказов"""
    if not request.user.is_authenticated:
        return JsonResponse({'notifications': [], 'count': 0})
    
    orders = Order.objects.filter(
        is_archived=False,
        is_viewed=False
    ).select_related('room', 'room__floor', 'room__floor__building').prefetch_related('items__product').order_by('-created_at')[:20]
    
    notifications = []
    for order in orders:
        room_info = f"{order.room.number}"
        if order.room.floor.building:
            room_info += f" ({order.room.floor.building.name}, Этаж {order.room.floor.number})"
        else:
            room_info += f" (Этаж {order.room.floor.number})"
        
        items_summary = []
        for item in order.items.all()[:3]:
            items_summary.append(f"{item.product.name} x{item.quantity}")
        if order.items.count() > 3:
            items_summary.append(f"+{order.items.count() - 3} еще")
        
        notifications.append({
            'order_id': order.id,
            'title': f'Новый заказ #{order.id}',
            'message': f'Комната {room_info} • {order.total_price} ₽',
            'items': items_summary,
            'time': order.created_at.strftime('%H:%M:%S'),
            'status': order.status,
            'created_at_timestamp': int(order.created_at.timestamp()),
        })
    
    return JsonResponse({
        'notifications': notifications,
        'count': len(notifications)
    })


@require_http_methods(["POST"])
def mark_order_viewed(request, order_id):
    """Отметить заказ как просмотренный"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    
    try:
        order = Order.objects.get(id=order_id)
        order.is_viewed = True
        order.save()
        return JsonResponse({'success': True})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'})

