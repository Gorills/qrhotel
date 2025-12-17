from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Room, Building
import qrcode
from PIL import Image
from io import BytesIO
import zipfile


@login_required
def generate_qr_images(request):
    """Генерация PNG файлов с QR-кодами для всех номеров (каждый отдельным файлом)"""
    building_id = request.GET.get('building_id')
    
    if building_id:
        rooms = Room.objects.filter(floor__building_id=building_id, is_active=True)
    else:
        rooms = Room.objects.filter(is_active=True)
    
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
            url = request.build_absolute_uri(room.get_absolute_url())
            qr.add_data(url)
            qr.make(fit=True)
            
            # Создаем изображение QR-кода
            # Используем make_image с минимальными настройками для точного размера
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Убеждаемся, что изображение точно по размеру QR-кода
            # Размер будет равен: (version * 4 + 17) * box_size пикселей
            # Но так как border=0, размер будет точно по QR-коду
            
            # Сохраняем в BytesIO как PNG без сжатия для максимального качества
            img_buffer = BytesIO()
            qr_img.save(img_buffer, format='PNG', optimize=False)
            img_buffer.seek(0)
            
            # Формируем имя файла (безопасное для файловой системы)
            if room.floor.building:
                building_name = room.floor.building.name.replace(' ', '_').replace('/', '_')
                filename = f"qr_{building_name}_floor_{room.floor.number}_room_{room.number}.png"
            else:
                filename = f"qr_floor_{room.floor.number}_room_{room.number}.png"
            
            # Добавляем в ZIP
            zip_file.writestr(filename, img_buffer.getvalue())
    
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="qr_codes.zip"'
    return response
