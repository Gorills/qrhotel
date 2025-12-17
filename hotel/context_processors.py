from .models import SiteSettings


def site_settings(request):
    """Context processor для добавления настроек сайта во все шаблоны"""
    try:
        return {
            'site_settings': SiteSettings.get_settings()
        }
    except Exception:
        # Если БД еще не готова, возвращаем None
        return {
            'site_settings': None
        }


