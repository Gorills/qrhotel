from django.db import models
from django.utils.text import slugify
from django.urls import reverse
import uuid
import re
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image, ImageDraw, ImageFont


class Building(models.Model):
    """Корпус отеля"""
    name = models.CharField(max_length=100, verbose_name="Название корпуса")
    slug = models.SlugField(unique=True, blank=True, verbose_name="URL-адрес")
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name="QR-код")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="Токен")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    class Meta:
        verbose_name = "Корпус"
        verbose_name_plural = "Корпуса"
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Всегда пересоздаем slug из названия для нормализации
        # Сначала пробуем транслитерацию через unidecode, если доступен
        try:
            from unidecode import unidecode
            transliterated = unidecode(self.name)
            new_slug = slugify(transliterated, allow_unicode=False)
        except ImportError:
            # Если unidecode не установлен, используем встроенную транслитерацию
            # Словарь для транслитерации кириллицы
            translit_map = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
                'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
                'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
                'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
                'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
                'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
                'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
            }
            
            # Транслитерируем вручную
            transliterated = ''.join(translit_map.get(char, char) for char in self.name)
            new_slug = slugify(transliterated, allow_unicode=False)
        
        # Если slug пустой, используем ID
        if not new_slug:
            new_slug = f"building-{self.pk if self.pk else 'new'}"
        
        # Убеждаемся, что slug уникален
        original_slug = new_slug
        counter = 1
        while Building.objects.filter(slug=new_slug).exclude(pk=self.pk if self.pk else None).exists():
            new_slug = f"{original_slug}-{counter}"
            counter += 1
        
        self.slug = new_slug
        
        # Генерируем токен если его нет
        if not self.token:
            self.token = uuid.uuid4()
        super().save(*args, **kwargs)
        if not self.qr_code:
            self.generate_qr_code()
    
    def generate_qr_code(self):
        """Генерация QR-кода для корпуса"""
        from django.conf import settings
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        # Используем домен из настроек
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        # Убираем слэш в конце если есть
        site_url = site_url.rstrip('/')
        url = f"{site_url}/building/{self.slug}/"
        qr.add_data(url)
        qr.make(fit=True)
        
        # Создаем классический QR-код: черный на белом фоне
        img = qr.make_image(fill_color="black", back_color="white")
        # Убеждаемся, что изображение в режиме RGB (без альфа-канала)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Добавляем белую рамку вокруг QR-кода
        border_size = 20  # Размер рамки в пикселях
        qr_width, qr_height = img.size
        # Создаем новое изображение с рамкой
        bordered_img = Image.new('RGB', 
                               (qr_width + border_size * 2, qr_height + border_size * 2), 
                               'white')
        # Вставляем QR-код в центр (с рамкой вокруг)
        bordered_img.paste(img, (border_size, border_size))
        img = bordered_img
        
        # Добавляем текст с названием корпуса
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        text = f"Building {self.name}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        img_width, img_height = img.size
        position = ((img_width - text_width) // 2, img_height - text_height - 10)
        draw.text(position, text, fill="black", font=font)
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        self.qr_code.save(f'qr_building_{self.slug}.png', File(buffer), save=False)
        super().save()
    
    def get_absolute_url(self):
        return reverse('building_page', kwargs={'building_slug': self.slug})


class Floor(models.Model):
    """Этаж"""
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='floors', blank=True, null=True, verbose_name="Корпус")
    name = models.CharField(max_length=100, verbose_name="Название этажа", help_text="Например: Цоколь, 1 этаж, 2 этаж", default="")
    number = models.IntegerField(verbose_name="Номер этажа (для сортировки)", blank=True, null=True, help_text="Используется для сортировки, может быть пустым")
    slug = models.SlugField(unique=True, blank=True, verbose_name="URL-адрес")
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name="QR-код")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="Токен")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    class Meta:
        verbose_name = "Этаж"
        verbose_name_plural = "Этажи"
        unique_together = [['building', 'slug']]
        ordering = ['building', 'number']
    
    def __str__(self):
        if self.building:
            return f"{self.building.name} - {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        # Всегда пересоздаем slug из названия для нормализации
        # Сначала пробуем транслитерацию через unidecode, если доступен
        try:
            from unidecode import unidecode
            transliterated = unidecode(self.name)
            new_slug = slugify(transliterated, allow_unicode=False)
        except ImportError:
            # Если unidecode не установлен, используем встроенную транслитерацию
            # Словарь для транслитерации кириллицы
            translit_map = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
                'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
                'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
                'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
                'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
                'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
                'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
                'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
            }
            
            # Транслитерируем вручную
            transliterated = ''.join(translit_map.get(char, char) for char in self.name)
            new_slug = slugify(transliterated, allow_unicode=False)
        
        # Если slug пустой, используем ID
        if not new_slug:
            new_slug = f"floor-{self.pk if self.pk else 'new'}"
        
        # Убеждаемся, что slug уникален
        original_slug = new_slug
        counter = 1
        while Floor.objects.filter(slug=new_slug).exclude(pk=self.pk if self.pk else None).exists():
            new_slug = f"{original_slug}-{counter}"
            counter += 1
        
        self.slug = new_slug
        
        # Генерируем токен если его нет
        if not self.token:
            self.token = uuid.uuid4()
        super().save(*args, **kwargs)
        if not self.qr_code:
            self.generate_qr_code()
    
    def generate_qr_code(self):
        """Генерация QR-кода для этажа"""
        from django.conf import settings
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        # Используем домен из настроек
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        # Убираем слэш в конце если есть
        site_url = site_url.rstrip('/')
        url = f"{site_url}/floor/{self.slug}/"
        qr.add_data(url)
        qr.make(fit=True)
        
        # Создаем классический QR-код: черный на белом фоне
        img = qr.make_image(fill_color="black", back_color="white")
        # Убеждаемся, что изображение в режиме RGB (без альфа-канала)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Добавляем белую рамку вокруг QR-кода
        border_size = 20  # Размер рамки в пикселях
        qr_width, qr_height = img.size
        # Создаем новое изображение с рамкой
        bordered_img = Image.new('RGB', 
                               (qr_width + border_size * 2, qr_height + border_size * 2), 
                               'white')
        # Вставляем QR-код в центр (с рамкой вокруг)
        bordered_img.paste(img, (border_size, border_size))
        img = bordered_img
        
        # Добавляем текст с названием этажа
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        text = f"Floor {self.name}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        img_width, img_height = img.size
        position = ((img_width - text_width) // 2, img_height - text_height - 10)
        draw.text(position, text, fill="black", font=font)
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        self.qr_code.save(f'qr_floor_{self.slug}.png', File(buffer), save=False)
        super().save()
    
    def get_absolute_url(self):
        return reverse('floor_page', kwargs={'floor_slug': self.slug})


class Room(models.Model):
    """Номер отеля"""
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='rooms', verbose_name="Этаж")
    number = models.CharField(max_length=20, verbose_name="Номер комнаты")
    slug = models.SlugField(unique=True, blank=True, verbose_name="URL-адрес")
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name="QR-код")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name="Токен")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    class Meta:
        verbose_name = "Номер"
        verbose_name_plural = "Номера"
        unique_together = ['floor', 'number']
        ordering = ['floor__building', 'floor__number', 'number']
    
    def __str__(self):
        if self.floor.building:
            return f"{self.floor.building.name} - {self.number}"
        return f"Этаж {self.floor.number} - {self.number}"
    
    def save(self, *args, **kwargs):
        # Пересоздаем slug если его нет или если он содержит недопустимые символы (кириллица и т.д.)
        slug_pattern = re.compile(r'^[-a-zA-Z0-9_]+$')
        if not self.slug or not slug_pattern.match(self.slug):
            if self.floor.building:
                building_part = slugify(self.floor.building.name)
                self.slug = slugify(f"{building_part}-{self.floor.number}-floor-room-{self.number}")
            else:
                self.slug = slugify(f"{self.floor.number}-floor-room-{self.number}")
        super().save(*args, **kwargs)
        if not self.qr_code:
            self.generate_qr_code()
    
    def generate_qr_code(self):
        """Генерация QR-кода для номера"""
        from django.conf import settings
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        # Используем домен из настроек
        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        # Убираем слэш в конце если есть
        site_url = site_url.rstrip('/')
        url = f"{site_url}/order/{self.slug}/"
        qr.add_data(url)
        qr.make(fit=True)
        
        # Создаем классический QR-код: черный на белом фоне
        img = qr.make_image(fill_color="black", back_color="white")
        # Убеждаемся, что изображение в режиме RGB (без альфа-канала)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Добавляем белую рамку вокруг QR-кода
        border_size = 20  # Размер рамки в пикселях
        qr_width, qr_height = img.size
        # Создаем новое изображение с рамкой
        bordered_img = Image.new('RGB', 
                               (qr_width + border_size * 2, qr_height + border_size * 2), 
                               'white')
        # Вставляем QR-код в центр (с рамкой вокруг)
        bordered_img.paste(img, (border_size, border_size))
        img = bordered_img
        
        # Добавляем текст с номером комнаты
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        text = f"Room {self.number}"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        img_width, img_height = img.size
        position = ((img_width - text_width) // 2, img_height - text_height - 10)
        draw.text(position, text, fill="black", font=font)
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        self.qr_code.save(f'qr_{self.slug}.png', File(buffer), save=False)
        super().save()
    
    def get_absolute_url(self):
        return reverse('order_page', kwargs={'room_slug': self.slug})


class Category(models.Model):
    """Категория блюд"""
    name = models.CharField(max_length=100, verbose_name="Название")
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name="Изображение")
    order_priority = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    
    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['order_priority', 'name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Блюдо/товар"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name="Категория")
    name = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Изображение")
    is_available = models.BooleanField(default=True, verbose_name="Доступно (не в стоп-листе)")
    order_priority = models.IntegerField(default=0, verbose_name="Порядок сортировки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    
    # Дополнительные поля для еды
    weight = models.CharField(max_length=50, blank=True, verbose_name="Вес/Объем", help_text="Например: 250г, 500мл")
    composition = models.TextField(blank=True, verbose_name="Состав", help_text="Список ингредиентов")
    calories = models.IntegerField(blank=True, null=True, verbose_name="Калории (ккал)")
    cooking_time = models.CharField(max_length=50, blank=True, verbose_name="Время приготовления", help_text="Например: 15-20 мин")
    allergens = models.CharField(max_length=200, blank=True, verbose_name="Аллергены", help_text="Например: глютен, лактоза")
    nutritional_info = models.TextField(blank=True, verbose_name="Пищевая ценность", help_text="Белки, жиры, углеводы")
    
    class Meta:
        verbose_name = "Блюдо"
        verbose_name_plural = "Блюда"
        ordering = ['category__order_priority', 'order_priority', 'name']
    
    def __str__(self):
        return self.name


class Order(models.Model):
    """Заказ"""
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('cooking', 'Готовится'),
        ('done', 'Выполнен'),
        ('archived', 'Архив'),
    ]
    
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='orders', verbose_name="Номер", blank=True, null=True)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='orders', verbose_name="Корпус", blank=True, null=True)
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='orders', verbose_name="Этаж", blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Общая сумма")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлен")
    session_key = models.CharField(max_length=40, blank=True, verbose_name="Ключ сессии")
    is_archived = models.BooleanField(default=False, verbose_name="В архиве")
    is_viewed = models.BooleanField(default=False, verbose_name="Просмотрен в дашборде")
    telegram_message_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="ID сообщения в Telegram")
    
    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']
    
    def __str__(self):
        if self.room:
            return f"Заказ #{self.id} - {self.room} - {self.get_status_display()}"
        elif self.building:
            return f"Заказ #{self.id} - {self.building.name} - {self.get_status_display()}"
        elif self.floor:
            return f"Заказ #{self.id} - {self.floor.name} - {self.get_status_display()}"
        return f"Заказ #{self.id} - {self.get_status_display()}"
    
    def get_status_color(self):
        """Возвращает цвет статуса для UI"""
        colors = {
            'new': 'bg-yellow-100 text-yellow-800',
            'cooking': 'bg-blue-100 text-blue-800',
            'done': 'bg-green-100 text-green-800',
            'archived': 'bg-gray-100 text-gray-800',
        }
        return colors.get(self.status, 'bg-gray-100 text-gray-800')


class OrderItem(models.Model):
    """Позиция в заказе"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Заказ")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Блюдо")
    quantity = models.IntegerField(verbose_name="Количество")
    price_at_moment = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена на момент заказа")
    
    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказов"
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
    
    def get_total(self):
        return self.quantity * self.price_at_moment


class SiteSettings(models.Model):
    """Настройки сайта"""
    logo = models.ImageField(upload_to='settings/', blank=True, null=True, verbose_name="Логотип")
    site_name = models.CharField(max_length=100, default="QR Hotel Service", verbose_name="Название сайта")
    telegram_bot_token = models.CharField(max_length=200, blank=True, verbose_name="Telegram Bot Token", help_text="Токен бота от @BotFather")
    telegram_chat_id = models.CharField(max_length=100, blank=True, verbose_name="Telegram Chat ID", help_text="ID группы или канала для уведомлений")
    notification_sound = models.FileField(upload_to='settings/sounds/', blank=True, null=True, verbose_name="Звук уведомления", help_text="Загрузите свой звук уведомления (MP3, WAV, OGG). Если не загружен, будет использован звук по умолчанию.")
    
    class Meta:
        verbose_name = "Настройки сайта"
        verbose_name_plural = "Настройки сайта"
    
    def __str__(self):
        return "Настройки сайта"
    
    def save(self, *args, **kwargs):
        # Обеспечиваем единственную запись настроек
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Получить настройки (создать если не существует)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

