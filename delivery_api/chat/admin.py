from django.contrib import admin
from .models import (
    Conversation, ConversationParticipant,
    Message, MessageRead, SupportRequest
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'is_active', 'is_support_requested', 'created_at']
    list_filter = ['is_active', 'is_support_requested', 'created_at']
    search_fields = ['order__id', 'order__client__username']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['order', 'support_requested_by']


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'user', 'role', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active', 'joined_at']
    search_fields = ['user__username', 'conversation__order__id']
    raw_id_fields = ['conversation', 'user']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'message_type', 'content_preview', 'created_at']
    list_filter = ['message_type', 'is_deleted', 'created_at']
    search_fields = ['content', 'sender__username']
    raw_id_fields = ['conversation', 'sender', 'reply_to']
    readonly_fields = ['created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Contenido'


@admin.register(MessageRead)
class MessageReadAdmin(admin.ModelAdmin):
    list_display = ['id', 'message', 'user', 'read_at']
    list_filter = ['read_at']
    raw_id_fields = ['message', 'user']


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'requested_by', 'priority', 'status', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['reason', 'requested_by__username']
    raw_id_fields = ['conversation', 'requested_by', 'assigned_to']
    readonly_fields = ['created_at', 'updated_at']