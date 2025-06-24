from django.apps import AppConfig


class InternshipsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'internships'

    def ready(self):
        import internships.signals
        # Warm up model when Django starts
        from .utils import generate_embedding
        generate_embedding("warmup")  # Initial load
        print("✅ Semantic model preloaded")
