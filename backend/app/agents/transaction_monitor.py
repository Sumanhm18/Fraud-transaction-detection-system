"""
Transaction Monitor Agent for FinSentinel AI

Real-time transaction processing and monitoring with Plaid integration.
Processes live transaction streams and prepares data for ML analysis.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

import structlog
import numpy as np
from sqlalchemy import select, func

from app.agents.base_agent import BaseAgent
from app.core.database import get_db_session
from app.core.redis import cache
from app.models.transaction import Transaction, Account, PlaidItem
from app.services.websocket_manager import websocket_manager

logger = structlog.get_logger()


class TransactionMonitorAgent(BaseAgent):
    """
    Real-time transaction monitoring and processing agent
    
    Responsibilities:
    - Process incoming Plaid transactions
    - Real-time transaction validation
    - Transaction enrichment and normalization
    - Velocity and pattern monitoring
    - Data preparation for ML analysis
    """
    
    def __init__(self):
        super().__init__(
            name="transaction_monitor",
            description="Real-time transaction processing and monitoring"
        )
        self.processing_queue = asyncio.Queue()
        self.velocity_windows = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '1h': timedelta(hours=1),
            '1d': timedelta(days=1)
        }
        
    async def initialize(self):
        """Initialize the transaction monitor agent"""
        try:
            self.initialized = True
            self.running = True
            self.stats['start_time'] = datetime.utcnow()
            
            # Initialize velocity tracking cache
            await self._initialize_velocity_cache()
            
            self.log_info("Transaction Monitor Agent initialized successfully")
            
        except Exception as e:
            self.log_error("Failed to initialize Transaction Monitor Agent", error=str(e))
            raise
    
    async def process(self):
        """Main processing loop - handles queued transactions"""
        try:
            # Process queued transactions
            while not self.processing_queue.empty():
                transaction_data = await self.processing_queue.get()
                await self._process_transaction(transaction_data)
            
            # Periodic cleanup and maintenance
            await self._periodic_maintenance()
            
            self._update_stats(success=True)
            
        except Exception as e:
            self.log_error("Transaction processing failed", error=str(e))
            self._update_stats(success=False)
    
    async def shutdown(self):
        """Cleanup and shutdown the agent"""
        self.running = False
        self.log_info("Transaction Monitor Agent shutdown complete")
    
    def get_process_interval(self) -> float:
        """Return process interval - 1 second for real-time processing"""
        return 1.0
    
    async def analyze_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single transaction for monitoring metrics
        
        Args:
            transaction_data: Raw transaction data from Plaid
            
        Returns:
            Transaction analysis results
        """
        try:
            # Add to processing queue for async handling
            await self.processing_queue.put(transaction_data)
            
            # Immediate analysis for real-time response
            analysis_result = await self._analyze_transaction_immediate(transaction_data)
            
            return analysis_result
            
        except Exception as e:
            self.log_error("Transaction analysis failed", error=str(e))
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def _analyze_transaction_immediate(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Immediate transaction analysis for real-time response"""
        transaction_id = transaction_data.get('transaction_id')
        account_id = transaction_data.get('account_id')
        amount = float(transaction_data.get('amount', 0))
        
        analysis = {
            'transaction_id': transaction_id,
            'processed_at': datetime.utcnow().isoformat(),
            'monitoring_metrics': {},
            'flags': [],
            'risk_score': 0.0
        }
        
        try:
            # Velocity analysis
            velocity_metrics = await self._analyze_velocity(account_id, amount)
            analysis['monitoring_metrics']['velocity'] = velocity_metrics
            
            # Amount analysis
            amount_metrics = await self._analyze_amount(account_id, amount)
            analysis['monitoring_metrics']['amount'] = amount_metrics
            
            # Time pattern analysis
            time_metrics = await self._analyze_time_patterns(transaction_data)
            analysis['monitoring_metrics']['time_patterns'] = time_metrics
            
            # Location analysis (if available)
            if transaction_data.get('location'):
                location_metrics = await self._analyze_location(account_id, transaction_data['location'])
                analysis['monitoring_metrics']['location'] = location_metrics
            
            # Calculate overall risk score
            analysis['risk_score'] = self._calculate_monitoring_risk_score(analysis['monitoring_metrics'])
            
            # Generate flags based on analysis
            analysis['flags'] = self._generate_monitoring_flags(analysis['monitoring_metrics'])
            
            self.log_info(
                "Transaction analyzed",
                transaction_id=transaction_id,
                risk_score=analysis['risk_score'],
                flags_count=len(analysis['flags'])
            )
            
            return analysis
            
        except Exception as e:
            self.log_error("Immediate analysis failed", transaction_id=transaction_id, error=str(e))
            analysis['status'] = 'partial_analysis'
            analysis['error'] = str(e)
            return analysis
    
    async def _process_transaction(self, transaction_data: Dict[str, Any]):
        """Process transaction for database storage and enrichment"""
        try:
            async with get_db_session() as db:
                # Check if transaction already exists
                existing = await db.execute(
                    select(Transaction).where(
                        Transaction.transaction_id == transaction_data.get('transaction_id')
                    )
                )
                if existing.scalar():
                    return  # Already processed
                
                # Create new transaction record
                transaction = Transaction(
                    transaction_id=transaction_data.get('transaction_id'),
                    account_id=transaction_data.get('account_id'),
                    amount=float(transaction_data.get('amount', 0)),
                    iso_currency_code=transaction_data.get('iso_currency_code', 'USD'),
                    date=datetime.fromisoformat(transaction_data.get('date')),
                    authorized_date=datetime.fromisoformat(transaction_data.get('authorized_date')) if transaction_data.get('authorized_date') else None,
                    name=transaction_data.get('name', ''),
                    merchant_name=transaction_data.get('merchant_name'),
                    category=transaction_data.get('category', []),
                    category_id=transaction_data.get('category_id'),
                    location_data=transaction_data.get('location'),
                    payment_channel=transaction_data.get('payment_channel'),
                    account_owner=transaction_data.get('account_owner'),
                    transaction_code=transaction_data.get('transaction_code'),
                    pending=transaction_data.get('pending', False)
                )
                
                db.add(transaction)
                await db.commit()
                
                # Update velocity cache
                await self._update_velocity_cache(
                    transaction_data.get('account_id'),
                    float(transaction_data.get('amount', 0)),
                    datetime.utcnow()
                )
                
                self.log_info("Transaction processed and stored", 
                            transaction_id=transaction_data.get('transaction_id'))
                
        except Exception as e:
            self.log_error("Transaction processing failed", 
                         transaction_id=transaction_data.get('transaction_id'), 
                         error=str(e))
    
    async def _analyze_velocity(self, account_id: str, amount: float) -> Dict[str, Any]:
        """Analyze transaction velocity patterns"""
        velocity_metrics = {}
        
        for window_name, window_duration in self.velocity_windows.items():
            cache_key = f"velocity:{account_id}:{window_name}"
            
            # Get current velocity data
            velocity_data = await cache.get(cache_key) or {'count': 0, 'total_amount': 0.0}
            
            velocity_metrics[window_name] = {
                'transaction_count': velocity_data['count'],
                'total_amount': velocity_data['total_amount'],
                'average_amount': velocity_data['total_amount'] / max(velocity_data['count'], 1)
            }
        
        return velocity_metrics
    
    async def _analyze_amount(self, account_id: str, amount: float) -> Dict[str, Any]:
        """Analyze transaction amount patterns"""
        # Get recent transaction amounts for comparison
        cache_key = f"amounts:{account_id}"
        recent_amounts = await cache.get(cache_key) or []
        
        if recent_amounts:
            avg_amount = np.mean(recent_amounts)
            std_amount = np.std(recent_amounts)
            
            # Calculate z-score
            z_score = abs(amount - avg_amount) / (std_amount + 0.01)  # Avoid division by zero
        else:
            avg_amount = amount
            std_amount = 0
            z_score = 0
        
        return {
            'current_amount': amount,
            'historical_average': float(avg_amount),
            'historical_std': float(std_amount),
            'z_score': float(z_score),
            'is_outlier': z_score > 2.0  # 2 standard deviations
        }
    
    async def _analyze_time_patterns(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze transaction timing patterns"""
        transaction_time = datetime.fromisoformat(transaction_data.get('date'))
        
        return {
            'hour_of_day': transaction_time.hour,
            'day_of_week': transaction_time.weekday(),
            'is_weekend': transaction_time.weekday() >= 5,
            'is_business_hours': 9 <= transaction_time.hour <= 17,
            'is_late_night': transaction_time.hour >= 22 or transaction_time.hour <= 6
        }
    
    async def _analyze_location(self, account_id: str, location_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze transaction location patterns"""
        if not location_data:
            return {}
        
        # Get recent locations for this account
        cache_key = f"locations:{account_id}"
        recent_locations = await cache.get(cache_key) or []
        
        current_location = {
            'city': location_data.get('city'),
            'region': location_data.get('region'),
            'country': location_data.get('country'),
            'lat': location_data.get('lat'),
            'lon': location_data.get('lon')
        }
        
        # Check for location anomalies
        is_new_location = True
        if recent_locations:
            for loc in recent_locations[-10:]:  # Check last 10 locations
                if (loc.get('city') == current_location['city'] and 
                    loc.get('region') == current_location['region']):
                    is_new_location = False
                    break
        
        return {
            'current_location': current_location,
            'is_new_location': is_new_location,
            'recent_location_count': len(recent_locations)
        }
    
    def _calculate_monitoring_risk_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall risk score from monitoring metrics"""
        risk_score = 0.0
        
        # Velocity risk
        velocity_metrics = metrics.get('velocity', {})
        for window_name, window_metrics in velocity_metrics.items():
            if window_metrics['transaction_count'] > self._get_velocity_threshold(window_name):
                risk_score += 0.2
        
        # Amount risk
        amount_metrics = metrics.get('amount', {})
        if amount_metrics.get('is_outlier', False):
            risk_score += 0.3
        
        # Time pattern risk
        time_metrics = metrics.get('time_patterns', {})
        if time_metrics.get('is_late_night', False):
            risk_score += 0.1
        
        # Location risk
        location_metrics = metrics.get('location', {})
        if location_metrics.get('is_new_location', False):
            risk_score += 0.2
        
        return min(risk_score, 1.0)  # Cap at 1.0
    
    def _generate_monitoring_flags(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate monitoring flags based on metrics"""
        flags = []
        
        # High velocity flags
        velocity_metrics = metrics.get('velocity', {})
        for window_name, window_metrics in velocity_metrics.items():
            if window_metrics['transaction_count'] > self._get_velocity_threshold(window_name):
                flags.append(f"high_velocity_{window_name}")
        
        # Amount flags
        amount_metrics = metrics.get('amount', {})
        if amount_metrics.get('is_outlier', False):
            flags.append("amount_outlier")
        
        # Time pattern flags
        time_metrics = metrics.get('time_patterns', {})
        if time_metrics.get('is_late_night', False):
            flags.append("late_night_transaction")
        
        # Location flags
        location_metrics = metrics.get('location', {})
        if location_metrics.get('is_new_location', False):
            flags.append("new_location")
        
        return flags
    
    def _get_velocity_threshold(self, window_name: str) -> int:
        """Get velocity threshold for different time windows"""
        thresholds = {
            '1m': 5,    # 5 transactions per minute
            '5m': 15,   # 15 transactions per 5 minutes
            '1h': 50,   # 50 transactions per hour
            '1d': 200   # 200 transactions per day
        }
        return thresholds.get(window_name, 10)
    
    async def _update_velocity_cache(self, account_id: str, amount: float, timestamp: datetime):
        """Update velocity tracking cache"""
        for window_name, window_duration in self.velocity_windows.items():
            cache_key = f"velocity:{account_id}:{window_name}"
            
            # Get current data
            velocity_data = await cache.get(cache_key) or {'count': 0, 'total_amount': 0.0}
            
            # Update counters
            velocity_data['count'] += 1
            velocity_data['total_amount'] += amount
            velocity_data['last_update'] = timestamp.isoformat()
            
            # Set with expiration based on window
            expire_seconds = int(window_duration.total_seconds())
            await cache.set(cache_key, velocity_data, expire=expire_seconds)
    
    async def _initialize_velocity_cache(self):
        """Initialize velocity tracking structures"""
        self.log_info("Initializing velocity tracking cache")
        # Cache initialization is handled dynamically
    
    async def _periodic_maintenance(self):
        """Perform periodic maintenance tasks"""
        # Clean up old cache entries, update statistics, etc.
        # This runs periodically to maintain system health
        pass