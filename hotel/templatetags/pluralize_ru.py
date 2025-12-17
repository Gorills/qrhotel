from django import template

register = template.Library()


@register.filter
def pluralize_ru(value, forms):
    """
    Склонение слова в зависимости от числа
    Использование: {{ count|pluralize_ru:"блюдо,блюда,блюд" }}
    """
    try:
        count = int(value)
    except (ValueError, TypeError):
        return forms.split(',')[2] if ',' in forms else ''
    
    forms_list = forms.split(',')
    if len(forms_list) != 3:
        return forms
    
    # Определяем правильную форму
    remainder_10 = count % 10
    remainder_100 = count % 100
    
    # Исключения для 11-14
    if 11 <= remainder_100 <= 14:
        return forms_list[2]
    
    # 1, 21, 31, 41... - именительный падеж
    if remainder_10 == 1:
        return forms_list[0]
    # 2, 3, 4, 22, 23, 24... - родительный падеж единственного числа
    elif 2 <= remainder_10 <= 4:
        return forms_list[1]
    # 5-9, 0, 10, 11-14, 15-19, 20, 25-29... - родительный падеж множественного числа
    else:
        return forms_list[2]


