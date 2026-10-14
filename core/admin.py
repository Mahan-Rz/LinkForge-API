from django.contrib import admin

from django.contrib import admin
from .models import ShortenedURL, ClickEvent

@admin.register(ShortenedURL)
class ShortenedURLAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'shortened_code',
        'original_url',
        'is_active',
        'expires_at',
        'click_count',
    )

    list_filter = ('is_active', 'expires_at')
    search_fields = ('shortened_code', 'original_url')
    ordering = ('is_active', '-created_at')
    readonly_fields = ('click_count', 'last_clicked_at', 'created_at')
    list_editable = ('is_active',)
    date_hierarchy = 'created_at'
    list_per_page = 25

@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'shortened_url_code', 'created_at')

    @admin.display(description='Short code')
    def shortened_url_code(self, obj):
        return obj.shortened_url.shortened_code

    list_select_related = ('shortened_url',)