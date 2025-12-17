from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Prefetch
from django.utils import timezone
from datetime import timedelta
import json

from .models import Room, Category, Product, Order, OrderItem, Building, Floor, SiteSettings
from .utils import send_telegram_notification, update_order_status_telegram


def home(request):
    """Главная страница-заглушка"""
    return render(request, 'hotel/home.html')


def order_page(request, room_slug):
    """Страница меню для гостя"""
    room = get_object_or_404(Room, slug=room_slug, is_active=True)
    categories = Category.objects.filter(is_active=True).prefetch_related(
        Prefetch('products', queryset=Product.objects.filter(is_available=True))
    )
    
    # Получаем активные заказы для этой сессии
    session_key = request.session.session_key
    active_order = None
    if session_key:
        active_order = Order.objects.filter(
            room=room,
            session_key=session_key,
            is_archived=False,
            status__in=['new', 'cooking']
        ).first()
    
    context = {
        'room': room,
        'categories': categories,
        'active_order': active_order,
    }
    return render(request, 'hotel/order_page.html', context)


@csrf_exempt
def cart_add(request, room_slug):
    """Добавление товара в корзину (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            
            room = get_object_or_404(Room, slug=room_slug)
            product = get_object_or_404(Product, id=product_id, is_available=True)
            
            # Получаем или создаем корзину в сессии
            if 'cart' not in request.session:
                request.session['cart'] = {}
            
            cart = request.session['cart']
            cart_key = str(product_id)
            
            if cart_key in cart:
                cart[cart_key]['quantity'] += quantity
            else:
                cart[cart_key] = {
                    'product_id': product_id,
                    'quantity': quantity,
                    'price': str(product.price),
                }
            
            request.session.modified = True
            
            # Подсчитываем общую сумму
            total = sum(
                float(item['price']) * item['quantity']
                for item in cart.values()
            )
            
            return JsonResponse({
                'success': True,
                'total': total,
                'cart_count': sum(item['quantity'] for item in cart.values())
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False})


@csrf_exempt
def cart_remove(request, room_slug):
    """Удаление товара из корзины (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = str(data.get('product_id'))
            
            if 'cart' in request.session:
                cart = request.session['cart']
                if product_id in cart:
                    del cart[product_id]
                    request.session.modified = True
            
            # Подсчитываем общую сумму
            cart = request.session.get('cart', {})
            total = sum(
                float(item['price']) * item['quantity']
                for item in cart.values()
            )
            
            return JsonResponse({
                'success': True,
                'total': total,
                'cart_count': sum(item['quantity'] for item in cart.values())
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False})


@csrf_exempt
def cart_update(request, room_slug):
    """Обновление количества товара в корзине (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = str(data.get('product_id'))
            quantity = int(data.get('quantity', 1))
            
            if 'cart' in request.session:
                cart = request.session['cart']
                if product_id in cart:
                    if quantity > 0:
                        cart[product_id]['quantity'] = quantity
                    else:
                        del cart[product_id]
                    request.session.modified = True
            
            # Подсчитываем общую сумму
            cart = request.session.get('cart', {})
            total = sum(
                float(item['price']) * item['quantity']
                for item in cart.values()
            )
            
            return JsonResponse({
                'success': True,
                'total': total,
                'cart_count': sum(item['quantity'] for item in cart.values())
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False})


@csrf_exempt
def create_order(request, room_slug):
    """Создание заказа"""
    if request.method == 'POST':
        room = get_object_or_404(Room, slug=room_slug)
        cart = request.session.get('cart', {})
        
        if not cart:
            return JsonResponse({'success': False, 'error': 'Корзина пуста'})
        
        # Создаем заказ
        total_price = sum(
            float(item['price']) * item['quantity']
            for item in cart.values()
        )
        
        order = Order.objects.create(
            room=room,
            total_price=total_price,
            status='new',
            session_key=request.session.session_key or '',
            is_viewed=False,  # Новый заказ не просмотрен
        )
        
        # Создаем позиции заказа
        for item_data in cart.values():
            product = Product.objects.get(id=item_data['product_id'])
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item_data['quantity'],
                price_at_moment=product.price,
            )
        
        # Очищаем корзину
        request.session['cart'] = {}
        request.session.modified = True
        
        # Отправляем уведомление в Telegram
        send_telegram_notification(order)
        
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'redirect_url': f'/order/{room_slug}/status/{order.id}/'
        })
    
    return JsonResponse({'success': False})


def order_status(request, room_slug, order_id):
    """Страница статуса заказа"""
    room = get_object_or_404(Room, slug=room_slug)
    order = get_object_or_404(Order, id=order_id, room=room)
    
    context = {
        'room': room,
        'order': order,
    }
    return render(request, 'hotel/order_status.html', context)


def get_cart(request, room_slug):
    """Получение содержимого корзины (AJAX)"""
    cart = request.session.get('cart', {})
    products_data = []
    total = 0
    
    for item_data in cart.values():
        try:
            product = Product.objects.get(id=item_data['product_id'], is_available=True)
            quantity = item_data['quantity']
            price = float(item_data['price'])
            products_data.append({
                'id': product.id,
                'name': product.name,
                'quantity': quantity,
                'price': price,
                'total': price * quantity,
            })
            total += price * quantity
        except Product.DoesNotExist:
            continue
    
    return JsonResponse({
        'items': products_data,
        'total': total,
        'count': sum(item['quantity'] for item in products_data)
    })


# Dashboard views
@login_required
def dashboard_home(request):
    """Главная страница дашборда - Live мониторинг"""
    orders = Order.objects.filter(is_archived=False).select_related('room', 'room__floor', 'room__floor__building').prefetch_related('items__product').order_by('-created_at')[:50]
    
    # Статистика
    today = timezone.now().date()
    today_orders = Order.objects.filter(created_at__date=today)
    today_revenue = today_orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    stats = {
        'new_orders': Order.objects.filter(status='new', is_archived=False).count(),
        'cooking_orders': Order.objects.filter(status='cooking', is_archived=False).count(),
        'today_revenue': today_revenue,
        'today_orders_count': today_orders.count(),
    }
    
    context = {
        'orders': orders,
        'stats': stats,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def dashboard_rooms(request):
    """Управление номерами и QR-кодами"""
    buildings = Building.objects.prefetch_related('floors__rooms').all()
    floors_without_building = Floor.objects.filter(building__isnull=True).prefetch_related('rooms').all()
    
    # Подсчитываем общее количество номеров для каждого корпуса
    for building in buildings:
        total_rooms = 0
        for floor in building.floors.all():
            total_rooms += floor.rooms.count()
        building.total_rooms = total_rooms
    
    context = {
        'buildings': buildings,
        'floors': floors_without_building,
    }
    return render(request, 'dashboard/rooms.html', context)


@login_required
def dashboard_menu(request):
    """Управление меню"""
    categories = Category.objects.prefetch_related('products').all()
    
    context = {
        'categories': categories,
    }
    return render(request, 'dashboard/menu.html', context)


@login_required
def dashboard_statistics(request):
    """Статистика"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Популярные блюда
    popular_products = Product.objects.annotate(
        total_ordered=Count('orderitem')
    ).order_by('-total_ordered')[:10]
    
    # Статистика по дням
    daily_stats = Order.objects.filter(
        created_at__date__gte=week_ago
    ).extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(
        count=Count('id'),
        revenue=Sum('total_price')
    ).order_by('day')
    
    context = {
        'popular_products': popular_products,
        'daily_stats': daily_stats,
        'today_revenue': Order.objects.filter(created_at__date=today).aggregate(Sum('total_price'))['total_price__sum'] or 0,
        'week_revenue': Order.objects.filter(created_at__date__gte=week_ago).aggregate(Sum('total_price'))['total_price__sum'] or 0,
        'month_revenue': Order.objects.filter(created_at__date__gte=month_ago).aggregate(Sum('total_price'))['total_price__sum'] or 0,
    }
    return render(request, 'dashboard/statistics.html', context)


@login_required
@require_http_methods(["POST"])
def update_order_status(request, order_id):
    """Обновление статуса заказа (AJAX)"""
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        if new_status == 'archived':
            order.is_archived = True
        # Отмечаем заказ как просмотренный при смене статуса
        order.is_viewed = True
        order.save()
        
        # Обновляем статус в Telegram
        update_order_status_telegram(order)
        
        return JsonResponse({'success': True, 'status': order.status})
    
    return JsonResponse({'success': False, 'error': 'Invalid status'})


@login_required
@require_http_methods(["POST"])
def toggle_product_availability(request, product_id):
    """Быстрое переключение доступности товара (AJAX)"""
    product = get_object_or_404(Product, id=product_id)
    product.is_available = not product.is_available
    product.save()
    
    return JsonResponse({
        'success': True,
        'is_available': product.is_available
    })


# Management views
@login_required
def dashboard_building_add(request):
    """Добавление корпуса"""
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Building.objects.create(name=name)
            return redirect('dashboard_rooms')
    return render(request, 'dashboard/building_add.html')


@login_required
def dashboard_floor_add(request):
    """Добавление этажа"""
    buildings = Building.objects.all()
    if request.method == 'POST':
        building_id = request.POST.get('building')
        number = request.POST.get('number')
        if number:
            building = None
            if building_id:
                building = get_object_or_404(Building, id=building_id)
            Floor.objects.create(building=building, number=number)
            return redirect('dashboard_rooms')
    context = {'buildings': buildings}
    return render(request, 'dashboard/floor_add.html', context)


@login_required
def dashboard_room_add(request):
    """Добавление номера"""
    floors = Floor.objects.all()
    if request.method == 'POST':
        floor_id = request.POST.get('floor')
        number = request.POST.get('number')
        if floor_id and number:
            floor = get_object_or_404(Floor, id=floor_id)
            Room.objects.create(floor=floor, number=number)
            return redirect('dashboard_rooms')
    context = {'floors': floors}
    return render(request, 'dashboard/room_add.html', context)


@login_required
@require_http_methods(["POST"])
def dashboard_building_delete(request, building_id):
    """Удаление корпуса"""
    building = get_object_or_404(Building, id=building_id)
    
    # Подсчитываем связанные объекты для предупреждения
    floors_count = building.floors.count()
    rooms_count = Room.objects.filter(floor__building=building).count()
    
    building.delete()  # Каскадное удаление этажей и номеров
    
    return JsonResponse({
        'success': True,
        'message': f'Корпус "{building.name}" удален. Также удалено этажей: {floors_count}, номеров: {rooms_count}'
    })


@login_required
@require_http_methods(["POST"])
def dashboard_floor_delete(request, floor_id):
    """Удаление этажа"""
    floor = get_object_or_404(Floor, id=floor_id)
    
    # Подсчитываем связанные объекты для предупреждения
    rooms_count = floor.rooms.count()
    floor_name = f"{floor.building.name if floor.building else 'Без корпуса'} - Этаж {floor.number}"
    
    floor.delete()  # Каскадное удаление номеров
    
    return JsonResponse({
        'success': True,
        'message': f'Этаж "{floor_name}" удален. Также удалено номеров: {rooms_count}'
    })


@login_required
@require_http_methods(["POST"])
def dashboard_room_delete(request, room_id):
    """Удаление номера"""
    room = get_object_or_404(Room, id=room_id)
    room_name = str(room)
    
    # Проверяем наличие заказов
    orders_count = room.orders.count()
    
    if orders_count > 0:
        return JsonResponse({
            'success': False,
            'error': f'Невозможно удалить номер "{room_name}". У номера есть {orders_count} заказ(ов). Сначала удалите или архивируйте заказы.'
        })
    
    room.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'Номер "{room_name}" удален'
    })


@login_required
@require_http_methods(["POST"])
def dashboard_room_regenerate_qr(request, room_id):
    """Перегенерация QR-кода для номера"""
    room = get_object_or_404(Room, id=room_id)
    room_name = str(room)
    
    try:
        # Удаляем старый QR-код если есть
        if room.qr_code:
            room.qr_code.delete(save=False)
        
        # Генерируем новый QR-код
        room.generate_qr_code()
        
        return JsonResponse({
            'success': True,
            'message': f'QR-код для номера "{room_name}" успешно перегенерирован'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка при перегенерации QR-кода: {str(e)}'
        })


@login_required
def dashboard_category_add(request):
    """Добавление категории"""
    if request.method == 'POST':
        name = request.POST.get('name')
        order_priority = int(request.POST.get('order_priority', 0))
        is_active = request.POST.get('is_active') == 'on'
        if name:
            category = Category.objects.create(
                name=name,
                order_priority=order_priority,
                is_active=is_active
            )
            if 'image' in request.FILES:
                category.image = request.FILES['image']
                category.save()
            return redirect('dashboard_menu')
    return render(request, 'dashboard/category_add.html')


@login_required
def dashboard_category_edit(request, category_id):
    """Редактирование категории"""
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.order_priority = int(request.POST.get('order_priority', 0))
        category.is_active = request.POST.get('is_active') == 'on'
        if 'image' in request.FILES:
            category.image = request.FILES['image']
        category.save()
        return redirect('dashboard_menu')
    context = {'category': category}
    return render(request, 'dashboard/category_edit.html', context)


@login_required
def dashboard_product_add(request):
    """Добавление блюда"""
    categories = Category.objects.all()
    if request.method == 'POST':
        category_id = request.POST.get('category')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        price = request.POST.get('price')
        order_priority = int(request.POST.get('order_priority', 0))
        is_available = request.POST.get('is_available') == 'on'
        weight = request.POST.get('weight', '')
        composition = request.POST.get('composition', '')
        calories = request.POST.get('calories') or None
        cooking_time = request.POST.get('cooking_time', '')
        allergens = request.POST.get('allergens', '')
        nutritional_info = request.POST.get('nutritional_info', '')
        
        if category_id and name and price:
            from decimal import Decimal, InvalidOperation
            try:
                price_decimal = Decimal(price)
            except (InvalidOperation, ValueError):
                # Если цена невалидна, возвращаем ошибку
                context = {'categories': categories, 'error': 'Неверный формат цены'}
                return render(request, 'dashboard/product_add.html', context)
            
            category = get_object_or_404(Category, id=category_id)
            product = Product.objects.create(
                category=category,
                name=name,
                description=description,
                price=price_decimal,
                order_priority=order_priority,
                is_available=is_available,
                weight=weight,
                composition=composition,
                calories=int(calories) if calories else None,
                cooking_time=cooking_time,
                allergens=allergens,
                nutritional_info=nutritional_info
            )
            if 'image' in request.FILES:
                product.image = request.FILES['image']
                product.save()
            return redirect('dashboard_menu')
    context = {'categories': categories}
    return render(request, 'dashboard/product_add.html', context)


@login_required
def dashboard_product_edit(request, product_id):
    """Редактирование блюда"""
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()
    if request.method == 'POST':
        product.category = get_object_or_404(Category, id=request.POST.get('category'))
        product.name = request.POST.get('name')
        product.description = request.POST.get('description', '')
        
        # Правильная обработка цены
        price_str = request.POST.get('price', '').strip()
        if price_str:
            from decimal import Decimal, InvalidOperation
            try:
                product.price = Decimal(price_str)
            except (InvalidOperation, ValueError):
                # Если не удалось преобразовать, оставляем текущую цену
                pass
        
        product.order_priority = int(request.POST.get('order_priority', 0))
        product.is_available = request.POST.get('is_available') == 'on'
        product.weight = request.POST.get('weight', '')
        product.composition = request.POST.get('composition', '')
        calories = request.POST.get('calories') or None
        product.calories = int(calories) if calories else None
        product.cooking_time = request.POST.get('cooking_time', '')
        product.allergens = request.POST.get('allergens', '')
        product.nutritional_info = request.POST.get('nutritional_info', '')
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        product.save()
        return redirect('dashboard_menu')
    context = {'product': product, 'categories': categories}
    return render(request, 'dashboard/product_edit.html', context)


@login_required
def dashboard_category_delete(request, category_id):
    """Удаление категории"""
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        # Удаляем все товары в категории
        category.products.all().delete()
        # Удаляем категорию
        category.delete()
        return redirect('dashboard_menu')
    context = {'category': category}
    return render(request, 'dashboard/category_delete.html', context)


@login_required
def dashboard_product_delete(request, product_id):
    """Удаление товара"""
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product.delete()
        return redirect('dashboard_menu')
    context = {'product': product}
    return render(request, 'dashboard/product_delete.html', context)


@login_required
def dashboard_settings(request):
    """Настройки сайта"""
    settings = SiteSettings.get_settings()
    
    if request.method == 'POST':
        settings.site_name = request.POST.get('site_name', 'QR Hotel Service')
        settings.telegram_bot_token = request.POST.get('telegram_bot_token', '')
        settings.telegram_chat_id = request.POST.get('telegram_chat_id', '')
        
        # Обработка логотипа
        if request.POST.get('remove_logo') == 'true':
            # Удаляем старый логотип если есть
            if settings.logo:
                settings.logo.delete(save=False)
            settings.logo = None
        elif 'logo' in request.FILES:
            # Удаляем старый логотип перед загрузкой нового
            if settings.logo:
                settings.logo.delete(save=False)
            settings.logo = request.FILES['logo']
        
        # Обработка звука уведомления
        if 'notification_sound' in request.FILES:
            # Удаляем старый звук перед загрузкой нового
            if settings.notification_sound:
                settings.notification_sound.delete(save=False)
            settings.notification_sound = request.FILES['notification_sound']
        # Если нужно удалить звук (оставить пустым для использования по умолчанию)
        if request.POST.get('remove_notification_sound') == 'true':
            if settings.notification_sound:
                settings.notification_sound.delete(save=False)
            settings.notification_sound = None
        
        settings.save()
        return redirect('dashboard_settings')
    
    context = {'settings': settings}
    return render(request, 'dashboard/settings.html', context)

