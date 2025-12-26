from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Room, Building, Floor
import qrcode
from PIL import Image
from io import BytesIO
import zipfile
import re


def sanitize_filename(name):
    """Очищает имя от недопустимых символов для файловой системы"""
    if name is None:
        return ''
    # Заменяем пробелы и специальные символы на подчеркивания
    name = re.sub(r'[^\w\-_\.]', '_', str(name))
    # Убираем множественные подчеркивания
    name = re.sub(r'_+', '_', name)
    return name.strip('_')


@login_required
def generate_qr_images(request):
    """Генерация PNG файлов с QR-кодами для всех номеров, корпусов и этажей (каждый отдельным файлом)"""
    building_id = request.GET.get('building_id')
    # По умолчанию включаем все типы QR-кодов
    include_buildings = request.GET.get('include_buildings', 'true').lower() == 'true'
    include_floors = request.GET.get('include_floors', 'true').lower() == 'true'
    
    # Используем select_related для оптимизации запросов и загрузки связанных объектов
    if building_id:
        rooms = Room.objects.filter(floor__building_id=building_id, is_active=True).select_related('floor', 'floor__building')
        buildings = Building.objects.filter(id=building_id, is_active=True) if include_buildings else Building.objects.none()
        floors = Floor.objects.filter(building_id=building_id, is_active=True) if include_floors else Floor.objects.none()
    else:
        rooms = Room.objects.filter(is_active=True).select_related('floor', 'floor__building')
        buildings = Building.objects.filter(is_active=True) if include_buildings else Building.objects.none()
        floors = Floor.objects.filter(is_active=True) if include_floors else Floor.objects.none()
    
    # Создаем ZIP архив в памяти
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for room in rooms:
            # Генерируем QR-код без отступов (border=0)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=0,  # Без отступов - размер точно по QR-коду
            )
            # Используем домен из настроек или из request
            from django.conf import settings
            from django.urls import NoReverseMatch
            site_url = getattr(settings, 'SITE_URL', None)
            try:
                if site_url:
                    site_url = site_url.rstrip('/')
                    url = f"{site_url}{room.get_absolute_url()}"
                else:
                    url = request.build_absolute_uri(room.get_absolute_url())
            except NoReverseMatch:
                # Если slug некорректный, пересоздаем его и используем новый URL
                from django.utils.text import slugify
                if room.floor.building:
                    building_part = slugify(room.floor.building.name)
                    room.slug = slugify(f"{building_part}-{room.floor.number}-floor-room-{room.number}")
                else:
                    room.slug = slugify(f"{room.floor.number}-floor-room-{room.number}")
                room.save(update_fields=['slug'])
                # Теперь формируем URL снова
                if site_url:
                    url = f"{site_url}{room.get_absolute_url()}"
                else:
                    url = request.build_absolute_uri(room.get_absolute_url())
            qr.add_data(url)
            qr.make(fit=True)
            
            # Создаем классический QR-код: черный на белом фоне
            qr_img = qr.make_image(fill_color="black", back_color="white")
            # Убеждаемся, что изображение в режиме RGB (без альфа-канала)
            if qr_img.mode != 'RGB':
                qr_img = qr_img.convert('RGB')
            
            # Добавляем белую рамку вокруг QR-кода
            border_size = 20  # Размер рамки в пикселях
            qr_width, qr_height = qr_img.size
            # Создаем новое изображение с рамкой
            bordered_img = Image.new('RGB', 
                                   (qr_width + border_size * 2, qr_height + border_size * 2), 
                                   'white')
            # Вставляем QR-код в центр (с рамкой вокруг)
            bordered_img.paste(qr_img, (border_size, border_size))
            qr_img = bordered_img
            
            # Сохраняем в BytesIO как PNG без сжатия для максимального качества
            img_buffer = BytesIO()
            qr_img.save(img_buffer, format='PNG', optimize=False)
            img_buffer.seek(0)
            
            # Собираем части имени файла с всеми доступными данными
            parts = ['qr']
            
            # Добавляем корпус, если есть (явно указываем в имени файла)
            try:
                building = room.floor.building
                if building and building.name:
                    building_name = sanitize_filename(building.name)
                    if building_name:
                        parts.append(f'building_{building_name}')
            except (AttributeError, TypeError):
                pass  # Корпус отсутствует, пропускаем
            
            # Добавляем этаж (используем название этажа, если есть)
            if room.floor.name:
                floor_name = sanitize_filename(room.floor.name)
                if floor_name:
                    parts.append(f'floor_{floor_name}')
            elif room.floor.number is not None:
                floor_number = sanitize_filename(str(room.floor.number))
                if floor_number:
                    parts.append(f'floor_{floor_number}')
            
            # Добавляем номер комнаты (всегда есть, явно указываем в имени файла)
            room_number = sanitize_filename(str(room.number))
            if room_number:
                parts.append(f'room_{room_number}')
            
            # Формируем итоговое имя файла
            filename = '_'.join(parts) + '.png'
            
            # Добавляем в ZIP в папку rooms/
            zip_file.writestr(f'rooms/{filename}', img_buffer.getvalue())
        
        # Добавляем QR-коды корпусов, если запрошено
        if include_buildings:
            for building in buildings:
                # Генерируем QR-код без отступов (border=0)
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=0,  # Без отступов - размер точно по QR-коду
                )
                # Используем домен из настроек или из request
                from django.conf import settings
                from django.urls import NoReverseMatch
                site_url = getattr(settings, 'SITE_URL', None)
                try:
                    if site_url:
                        site_url = site_url.rstrip('/')
                        url = f"{site_url}{building.get_absolute_url()}"
                    else:
                        url = request.build_absolute_uri(building.get_absolute_url())
                except NoReverseMatch:
                    # Если slug некорректный, пересоздаем его
                    from django.utils.text import slugify
                    building.slug = slugify(building.name)
                    building.save(update_fields=['slug'])
                    if site_url:
                        url = f"{site_url}{building.get_absolute_url()}"
                    else:
                        url = request.build_absolute_uri(building.get_absolute_url())
                qr.add_data(url)
                qr.make(fit=True)
                
                # Создаем классический QR-код: черный на белом фоне
                qr_img = qr.make_image(fill_color="black", back_color="white")
                # Убеждаемся, что изображение в режиме RGB (без альфа-канала)
                if qr_img.mode != 'RGB':
                    qr_img = qr_img.convert('RGB')
                
                # Добавляем белую рамку вокруг QR-кода
                border_size = 20  # Размер рамки в пикселях
                qr_width, qr_height = qr_img.size
                # Создаем новое изображение с рамкой
                bordered_img = Image.new('RGB', 
                                       (qr_width + border_size * 2, qr_height + border_size * 2), 
                                       'white')
                # Вставляем QR-код в центр (с рамкой вокруг)
                bordered_img.paste(qr_img, (border_size, border_size))
                qr_img = bordered_img
                
                # Сохраняем в BytesIO как PNG без сжатия для максимального качества
                img_buffer = BytesIO()
                qr_img.save(img_buffer, format='PNG', optimize=False)
                img_buffer.seek(0)
                
                # Формируем имя файла для корпуса
                building_name = sanitize_filename(building.name)
                filename = f'qr_building_{building_name}.png' if building_name else f'qr_building_{building.id}.png'
                
                # Добавляем в ZIP в папку buildings/
                zip_file.writestr(f'buildings/{filename}', img_buffer.getvalue())
        
        # Добавляем QR-коды этажей, если запрошено
        if include_floors:
            for floor in floors:
                # Генерируем QR-код без отступов (border=0)
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=0,  # Без отступов - размер точно по QR-коду
                )
                # Используем домен из настроек или из request
                from django.conf import settings
                from django.urls import NoReverseMatch
                site_url = getattr(settings, 'SITE_URL', None)
                try:
                    if site_url:
                        site_url = site_url.rstrip('/')
                        url = f"{site_url}{floor.get_absolute_url()}"
                    else:
                        url = request.build_absolute_uri(floor.get_absolute_url())
                except NoReverseMatch:
                    # Если slug некорректный, пересоздаем его
                    from django.utils.text import slugify
                    floor.slug = slugify(floor.name)
                    floor.save(update_fields=['slug'])
                    if site_url:
                        url = f"{site_url}{floor.get_absolute_url()}"
                    else:
                        url = request.build_absolute_uri(floor.get_absolute_url())
                qr.add_data(url)
                qr.make(fit=True)
                
                # Создаем классический QR-код: черный на белом фоне
                qr_img = qr.make_image(fill_color="black", back_color="white")
                # Убеждаемся, что изображение в режиме RGB (без альфа-канала)
                if qr_img.mode != 'RGB':
                    qr_img = qr_img.convert('RGB')
                
                # Добавляем белую рамку вокруг QR-кода
                border_size = 20  # Размер рамки в пикселях
                qr_width, qr_height = qr_img.size
                # Создаем новое изображение с рамкой
                bordered_img = Image.new('RGB', 
                                       (qr_width + border_size * 2, qr_height + border_size * 2), 
                                       'white')
                # Вставляем QR-код в центр (с рамкой вокруг)
                bordered_img.paste(qr_img, (border_size, border_size))
                qr_img = bordered_img
                
                # Сохраняем в BytesIO как PNG без сжатия для максимального качества
                img_buffer = BytesIO()
                qr_img.save(img_buffer, format='PNG', optimize=False)
                img_buffer.seek(0)
                
                # Формируем имя файла для этажа
                floor_name = sanitize_filename(floor.name)
                filename = f'qr_floor_{floor_name}.png' if floor_name else f'qr_floor_{floor.id}.png'
                
                # Добавляем в ZIP в папку floors/
                zip_file.writestr(f'floors/{filename}', img_buffer.getvalue())
    
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="qr_codes.zip"'
    return response
