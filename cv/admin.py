from django.contrib import admin
from .models import CV

@admin.register(CV)
class CVAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at', 'shared_on_social')
    list_filter = ('created_at', 'shared_on_social')
    search_fields = ('user__username', 'original_text')
    readonly_fields = ('created_at', 'updated_at')
    fields = ('user', 'original_text', 'optimized_text', 'shared_on_social', 'shared_platforms', 'created_at', 'updated_at')
