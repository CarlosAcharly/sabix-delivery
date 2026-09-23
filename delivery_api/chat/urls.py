from django.urls import path
from .views import (
    # Conversaciones
    ConversationListView,
    ConversationDetailView,
    ConversationByOrderView,
    
    # Mensajes
    MessageListView,
    MessageCreateView,
    MessageReplyView,
    MarkMessageReadView,
    MessageDeleteView,
    UnreadCountView,
    TotalUnreadCountView,
    
    # Soporte
    RequestSupportView,
    CloseConversationView,
    
    # Admin
    AdminSupportRequestListView,
    AdminSupportRequestDetailView,
    AdminJoinConversationView,
    AdminConversationListView,
)

urlpatterns = [
    # =============================================
    # CONVERSACIONES
    # =============================================
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/<int:id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/by-order/<int:order_id>/', ConversationByOrderView.as_view(), name='conversation-by-order'),
    
    # =============================================
    # MENSAJES
    # =============================================
    path('conversations/<int:conversation_id>/messages/', MessageListView.as_view(), name='message-list'),
    path('conversations/<int:conversation_id>/messages/send/', MessageCreateView.as_view(), name='message-create'),
    path('conversations/<int:conversation_id>/messages/<int:message_id>/reply/', MessageReplyView.as_view(), name='message-reply'),
    path('conversations/<int:conversation_id>/messages/<int:message_id>/read/', MarkMessageReadView.as_view(), name='message-read'),
    path('conversations/<int:conversation_id>/messages/<int:message_id>/', MessageDeleteView.as_view(), name='message-delete'),
    path('conversations/<int:conversation_id>/unread/', UnreadCountView.as_view(), name='conversation-unread'),
    path('unread/total/', TotalUnreadCountView.as_view(), name='total-unread'),
    
    # =============================================
    # SOPORTE
    # =============================================
    path('conversations/<int:conversation_id>/request-support/', RequestSupportView.as_view(), name='request-support'),
    path('conversations/<int:conversation_id>/close/', CloseConversationView.as_view(), name='close-conversation'),
    
    # =============================================
    # ADMIN
    # =============================================
    path('admin/support-requests/', AdminSupportRequestListView.as_view(), name='admin-support-list'),
    path('admin/support-requests/<int:id>/', AdminSupportRequestDetailView.as_view(), name='admin-support-detail'),
    path('admin/conversations/', AdminConversationListView.as_view(), name='admin-conversation-list'),
    path('admin/conversations/<int:conversation_id>/join/', AdminJoinConversationView.as_view(), name='admin-join-conversation'),
]