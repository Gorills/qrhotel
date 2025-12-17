import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Order


class OrderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add("orders", self.channel_name)
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("orders", self.channel_name)
    
    async def receive(self, text_data):
        pass
    
    async def order_update(self, event):
        """Отправка обновления заказа клиенту"""
        await self.send(text_data=json.dumps({
            'type': 'order_update',
            'order': event['order']
        }))


