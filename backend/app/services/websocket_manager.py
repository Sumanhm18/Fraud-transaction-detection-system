"""
WebSocket Manager for Real-time Communication

Manages WebSocket connections for real-time transaction updates,
fraud alerts, and system notifications.
"""

import json
from typing import Dict, List, Set, Any, Optional

from fastapi import WebSocket, WebSocketDisconnect
import structlog

logger = structlog.get_logger()


class WebSocketManager:
    """
    WebSocket connection manager for real-time updates
    
    Supports multiple channels:
    - transactions: Real-time transaction updates
    - alerts: Fraud detection alerts
    - system: System notifications and health updates
    """
    
    def __init__(self):
        # Store active connections by channel
        self.connections: Dict[str, Set[WebSocket]] = {
            'transactions': set(),
            'alerts': set(),
            'system': set(),
        }
        self.user_connections: Dict[str, Dict[str, WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, channel: str = "transactions", user_id: Optional[str] = None):
        """Accept WebSocket connection and add to channel"""
        await websocket.accept()
        
        # Add to channel connections
        if channel not in self.connections:
            self.connections[channel] = set()
        self.connections[channel].add(websocket)
        
        # Track user-specific connections
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = {}
            self.user_connections[user_id][channel] = websocket
        
        logger.info(
            "WebSocket connected",
            channel=channel,
            user_id=user_id,
            total_connections=len(self.connections[channel])
        )
        
        # Send welcome message
        await self.send_to_connection(websocket, {
            'type': 'connection_established',
            'channel': channel,
            'message': f'Connected to FinSentinel AI {channel} channel'
        })
    
    def disconnect(self, websocket: WebSocket, channel: str = "transactions", user_id: Optional[str] = None):
        """Remove WebSocket connection from channel"""
        if channel in self.connections:
            self.connections[channel].discard(websocket)
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].pop(channel, None)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(
            "WebSocket disconnected",
            channel=channel,
            user_id=user_id,
            remaining_connections=len(self.connections.get(channel, []))
        )
    
    async def send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.error("Failed to send WebSocket message", error=str(e))
    
    async def broadcast(self, message: Dict[str, Any], channel: str = "transactions"):
        """Broadcast message to all connections in channel"""
        if channel not in self.connections:
            logger.warning("Invalid WebSocket channel", channel=channel)
            return
        
        disconnected = []
        
        for websocket in self.connections[channel].copy():
            try:
                await websocket.send_text(json.dumps(message, default=str))
            except WebSocketDisconnect:
                disconnected.append(websocket)
            except Exception as e:
                logger.error("WebSocket broadcast error", error=str(e))
                disconnected.append(websocket)
        
        # Remove disconnected websockets
        for websocket in disconnected:
            self.connections[channel].discard(websocket)
        
        logger.info(
            "WebSocket message broadcasted",
            channel=channel,
            message_type=message.get('type'),
            recipients=len(self.connections[channel]),
            disconnected=len(disconnected)
        )
    
    async def send_to_user(self, user_id: str, message: Dict[str, Any], channel: str = "transactions"):
        """Send message to specific user's WebSocket"""
        if user_id not in self.user_connections or channel not in self.user_connections[user_id]:
            logger.warning("User WebSocket not found", user_id=user_id, channel=channel)
            return
        
        websocket = self.user_connections[user_id][channel]
        await self.send_to_connection(websocket, message)
    
    async def broadcast_transaction_update(self, transaction_data: Dict[str, Any]):
        """Broadcast real-time transaction update"""
        message = {
            'type': 'transaction_update',
            'data': transaction_data,
            'timestamp': transaction_data.get('created_at')
        }
        await self.broadcast(message, channel='transactions')
    
    async def broadcast_fraud_alert(self, alert_data: Dict[str, Any]):
        """Broadcast fraud detection alert"""
        message = {
            'type': 'fraud_alert',
            'data': alert_data,
            'severity': alert_data.get('severity', 'medium'),
            'timestamp': alert_data.get('timestamp')
        }
        await self.broadcast(message, channel='alerts')
    
    async def broadcast_system_notification(self, notification: Dict[str, Any]):
        """Broadcast system notification"""
        message = {
            'type': 'system_notification',
            'data': notification,
            'timestamp': notification.get('timestamp')
        }
        await self.broadcast(message, channel='system')
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        return {
            'total_connections': sum(len(connections) for connections in self.connections.values()),
            'connections_by_channel': {
                channel: len(connections) 
                for channel, connections in self.connections.items()
            },
            'total_users': len(self.user_connections),
            'channels': list(self.connections.keys())
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()