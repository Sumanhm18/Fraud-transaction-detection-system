"""
Base Agent Class for FinSentinel AI Multi-Agent System

Abstract base class that defines the interface for all agents in the system.
Supports hot-swappable agent registration and modular architecture.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

logger = structlog.get_logger()


class BaseAgent(ABC):
    """
    Abstract base class for all FinSentinel AI agents
    
    Provides common functionality and interface for:
    - Transaction Monitor Agent
    - Fraud Detection Agent  
    - Forecast Agent
    - Audit Agent
    - Tax AI Agent (extensible)
    - KYC AI Agent (extensible)
    - DeFi AI Agent (extensible)
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.initialized = False
        self.running = False
        self.stats = {
            'processed_count': 0,
            'error_count': 0,
            'start_time': None,
            'last_activity': None
        }
    
    @abstractmethod
    async def initialize(self):
        """Initialize the agent - load models, connect to services, etc."""
        pass
    
    @abstractmethod
    async def process(self):
        """Main processing loop - called repeatedly by orchestrator"""
        pass
    
    @abstractmethod
    async def shutdown(self):
        """Cleanup and shutdown the agent"""
        pass
    
    @abstractmethod
    def get_process_interval(self) -> float:
        """Return the sleep interval between process() calls in seconds"""
        pass
    
    async def analyze_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single transaction (optional override)
        
        Args:
            transaction_data: Transaction data from Plaid
            
        Returns:
            Analysis results specific to this agent
        """
        return {'status': 'not_implemented', 'agent': self.name}
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get agent health and statistics"""
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            'name': self.name,
            'description': self.description,
            'initialized': self.initialized,
            'running': self.running,
            'processed_count': self.stats['processed_count'],
            'error_count': self.stats['error_count'],
            'uptime_seconds': uptime,
            'last_activity': self.stats['last_activity'].isoformat() if self.stats['last_activity'] else None,
            'error_rate': (self.stats['error_count'] / max(self.stats['processed_count'], 1)) * 100
        }
    
    def _update_stats(self, success: bool = True):
        """Update agent statistics"""
        self.stats['processed_count'] += 1
        if not success:
            self.stats['error_count'] += 1
        self.stats['last_activity'] = datetime.utcnow()
    
    async def _safe_execute(self, func, *args, **kwargs):
        """
        Safely execute a function with error handling and stats tracking
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or None if error occurred
        """
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._update_stats(success=True)
            return result
        except Exception as e:
            logger.error(
                "Agent execution error",
                agent=self.name,
                function=func.__name__,
                error=str(e)
            )
            self._update_stats(success=False)
            return None
    
    def log_info(self, message: str, **kwargs):
        """Log info message with agent context"""
        logger.info(message, agent=self.name, **kwargs)
    
    def log_error(self, message: str, **kwargs):
        """Log error message with agent context"""
        logger.error(message, agent=self.name, **kwargs)
        self._update_stats(success=False)
    
    def log_warning(self, message: str, **kwargs):
        """Log warning message with agent context"""
        logger.warning(message, agent=self.name, **kwargs)