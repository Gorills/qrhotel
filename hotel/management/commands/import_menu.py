"""
Management command для импорта меню из файла menu.txt
"""
import re
from django.core.management.base import BaseCommand
from hotel.models import Category, Product


class Command(BaseCommand):
    help = 'Импортирует меню из файла menu.txt'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='menu.txt',
            help='Путь к файлу с меню (по умолчанию menu.txt)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующие категории и продукты перед импортом',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        clear_existing = options['clear']
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Файл {file_path} не найден'))
            return
        
        if clear_existing:
            self.stdout.write('Очистка существующих данных...')
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Данные очищены'))
        
        # Парсинг файла
        current_category = None
        current_product = None
        product_description = []
        product_composition = []
        category_order = 0
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Пропускаем пустые строки
            if not line:
                i += 1
                continue
            
            # Проверка на категорию
            is_category = (
                not re.match(r'^\d+\)', line) and
                not line.startswith('·') and
                not line.startswith('Объем') and
                not line.startswith('Цена') and
                not line.startswith('Стоимость') and
                not line.lower().startswith('состав') and
                not line.startswith('Ассортимент') and
                not line.lower().startswith('подается') and
                not line.lower().startswith('сливочно') and
                len(line) > 2 and
                not re.search(r'\d+\s*(?:рублей?|₽|р|P)', line)  # Не содержит цену
            )
            
            if is_category:
                # Сохраняем предыдущий продукт
                if current_product:
                    self._save_product(current_product, product_description, product_composition)
                    current_product = None
                    product_description = []
                    product_composition = []
                
                category_name = line.strip()
                current_category, created = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'order_priority': category_order, 'is_active': True}
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Создана категория: {category_name}'))
                else:
                    self.stdout.write(f'Используется существующая категория: {category_name}')
                category_order += 10
                i += 1
                continue
            
            # Проверка на продукт с номером (1), 2), и т.д.)
            product_match = re.match(r'^(\d+)\)\s*(.+?)$', line)
            if product_match and current_category:
                # Сохраняем предыдущий продукт
                if current_product:
                    self._save_product(current_product, product_description, product_composition)
                
                # Парсим название, вес и цену
                num = product_match.group(1)
                rest = product_match.group(2).strip()
                
                # Извлекаем вес
                weight = ''
                weight_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(гр|г|мл|л|шт)\.?', rest, re.IGNORECASE)
                if weight_match:
                    weight = f"{weight_match.group(1)}{weight_match.group(2)}"
                    rest = rest.replace(weight_match.group(0), '').strip()
                
                # Извлекаем цену
                price = 0.0
                price_match = re.search(r'(\d+)\s*(?:рублей?|₽|р|P)', rest, re.IGNORECASE)
                if price_match:
                    price = float(price_match.group(1))
                    rest = rest.replace(price_match.group(0), '').strip()
                
                # Название - оставшаяся часть
                name = rest.strip()
                
                current_product = {
                    'name': name,
                    'weight': weight,
                    'price': price,
                    'category': current_category,
                    'order_priority': int(num)
                }
                product_description = []
                product_composition = []
                i += 1
                continue
            
            # Обработка описания и состава для текущего продукта
            if current_product:
                line_lower = line.lower()
                if line_lower.startswith('подается'):
                    product_description.append(line)
                elif line_lower.startswith('состав'):
                    comp_text = re.sub(r'^состав\s*:?\s*', '', line, flags=re.IGNORECASE).strip()
                    if comp_text:
                        product_composition.append(comp_text)
                elif 'состав' in line_lower and ':' in line:
                    comp_text = line.split(':', 1)[1].strip()
                    if comp_text:
                        product_composition.append(comp_text)
                elif not re.match(r'^\d+\)', line) and not line.startswith('·'):
                    # Дополнительное описание (если не начинается с номера и не маркер)
                    if line and len(line) > 3 and not re.search(r'^\d+\s*(?:рублей?|₽|р|P)', line):
                        product_description.append(line)
            
            # Обработка специальных форматов (чай, лимонады, кофе)
            if current_category:
                cat_name_upper = current_category.name.upper()
                if 'ЧАЙНАЯ КАРТА' in cat_name_upper or 'ЛИМОНАДЫ' in cat_name_upper or 'КОФЕ' in cat_name_upper or 'НАПИТКИ' in cat_name_upper:
                    # Обработка продуктов с маркерами ·
                    if line.startswith('·') and not any(x in line for x in ['Объем', 'Цена', 'Стоимость']):
                        product_name = line.replace('·', '').strip()
                        if product_name and len(product_name) > 2:
                            # Читаем следующие строки для этого продукта
                            weight = ''
                            price = 0.0
                            description = []
                            composition = []
                            
                            j = i + 1
                            while j < len(lines):
                                next_line = lines[j].strip()
                                if not next_line or (not next_line.startswith('·') and not any(x in next_line for x in ['Объем', 'Цена', 'Стоимость', 'Состав'])):
                                    break
                                
                                if 'Объем' in next_line:
                                    weight_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(л|мл)', next_line, re.IGNORECASE)
                                    if weight_match:
                                        weight = f"{weight_match.group(1)}{weight_match.group(2)}"
                                elif 'Цена' in next_line or 'Стоимость' in next_line:
                                    price_match = re.search(r'(\d+)\s*(?:₽|рублей?|р|P)', next_line, re.IGNORECASE)
                                    if price_match:
                                        price = float(price_match.group(1))
                                elif 'Состав' in next_line:
                                    comp_text = next_line.split(':', 1)[1].strip() if ':' in next_line else next_line.replace('Состав', '').strip()
                                    if comp_text:
                                        composition.append(comp_text)
                                
                                j += 1
                            
                            if product_name:
                                Product.objects.create(
                                    category=current_category,
                                    name=product_name,
                                    weight=weight,
                                    price=price,
                                    description='\n'.join(description) if description else '',
                                    composition='\n'.join(composition) if composition else '',
                                    order_priority=Product.objects.filter(category=current_category).count() + 1,
                                    is_available=True
                                )
                                self.stdout.write(f'  Создан продукт: {product_name}')
                                i = j - 1
            
            i += 1
        
        # Сохраняем последний продукт
        if current_product:
            self._save_product(current_product, product_description, product_composition)
        
        self.stdout.write(self.style.SUCCESS(f'\nИмпорт завершен!'))
        self.stdout.write(f'Категорий: {Category.objects.count()}')
        self.stdout.write(f'Продуктов: {Product.objects.count()}')

    def _save_product(self, product_data, description, composition):
        """Сохраняет продукт в базу данных"""
        description_text = '\n'.join(description) if description else ''
        composition_text = '\n'.join(composition) if composition else ''
        
        # Объединяем описание и состав
        full_description = description_text
        if composition_text:
            if full_description:
                full_description += '\n\n'
            full_description += f'Состав: {composition_text}'
        
        Product.objects.create(
            category=product_data['category'],
            name=product_data['name'],
            weight=product_data['weight'],
            price=product_data['price'],
            description=full_description,
            composition=composition_text,
            order_priority=product_data['order_priority'],
            is_available=True
        )
        self.stdout.write(f'  Создан продукт: {product_data["name"]} - {product_data["price"]} руб.')

