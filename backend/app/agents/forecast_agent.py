"""
Forecast Agent for FinSentinel AI

Predictive analytics agent for revenue forecasting, cashflow prediction,
and financial trend analysis using time series models.
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
from app.models.transaction import Transaction, Account

logger = structlog.get_logger()


class ForecastAgent(BaseAgent):
    """
    Predictive analytics and forecasting agent
    
    Capabilities:
    - Revenue forecasting (30/90/365 days)
    - Cashflow prediction
    - Spending pattern analysis
    - Seasonal trend detection
    - Risk exposure forecasting
    """
    
    def __init__(self):
        super().__init__(
            name="forecast",
            description="Financial forecasting and predictive analytics"
        )
        self.forecast_horizons = [30, 90, 365]  # Days
        self.min_data_points = 30  # Minimum transactions for forecasting
        
    async def initialize(self):
        """Initialize the forecast agent"""
        try:
            self.initialized = True
            self.running = True
            self.stats['start_time'] = datetime.utcnow()
            
            self.log_info("Forecast Agent initialized successfully")
            
        except Exception as e:
            self.log_error("Failed to initialize Forecast Agent", error=str(e))
            raise
    
    async def process(self):
        """Main processing loop - generate periodic forecasts"""
        try:
            # Generate daily forecasts for active accounts
            await self._generate_daily_forecasts()
            
            self._update_stats(success=True)
            
        except Exception as e:
            self.log_error("Forecast processing failed", error=str(e))
            self._update_stats(success=False)
    
    async def shutdown(self):
        """Cleanup and shutdown the agent"""
        self.running = False
        self.log_info("Forecast Agent shutdown complete")
    
    def get_process_interval(self) -> float:
        """Return process interval - 1 hour for forecast updates"""
        return 3600.0  # 1 hour
    
    async def generate_forecasts(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive financial forecasts
        
        Args:
            account_id: Specific account ID or None for all accounts
            
        Returns:
            Forecast results including revenue, expenses, and trends
        """
        try:
            forecasts = {
                'generated_at': datetime.utcnow().isoformat(),
                'forecast_horizons': self.forecast_horizons,
                'accounts': {}
            }
            
            async with get_db_session() as db:
                # Get accounts to forecast
                if account_id:
                    accounts = [account_id]
                else:
                    # Get active accounts with sufficient transaction history
                    result = await db.execute(
                        select(Transaction.account_id, func.count(Transaction.id).label('count'))
                        .where(Transaction.date >= datetime.utcnow() - timedelta(days=90))
                        .group_by(Transaction.account_id)
                        .having(func.count(Transaction.id) >= self.min_data_points)
                    )
                    accounts = [row.account_id for row in result.fetchall()]
                
                # Generate forecasts for each account
                for acc_id in accounts:
                    account_forecast = await self._generate_account_forecast(db, acc_id)
                    forecasts['accounts'][acc_id] = account_forecast
            
            # Generate aggregate forecasts
            if len(forecasts['accounts']) > 1:
                forecasts['aggregate'] = await self._generate_aggregate_forecast(forecasts['accounts'])
            
            # Cache forecasts
            await cache.set(
                f"forecasts:latest", 
                forecasts, 
                expire=3600  # 1 hour
            )
            
            self.log_info("Forecasts generated", account_count=len(forecasts['accounts']))
            return forecasts
            
        except Exception as e:
            self.log_error("Forecast generation failed", error=str(e))
            return {
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat()
            }
    
    async def _generate_account_forecast(self, db, account_id: str) -> Dict[str, Any]:
        """Generate forecast for a specific account"""
        # Get transaction history
        result = await db.execute(
            select(Transaction)
            .where(
                Transaction.account_id == account_id,
                Transaction.date >= datetime.utcnow() - timedelta(days=365)
            )
            .order_by(Transaction.date)
        )
        transactions = result.fetchall()
        
        if len(transactions) < self.min_data_points:
            return {'error': 'Insufficient data for forecasting'}
        
        # Prepare transaction data
        transaction_data = []
        for txn in transactions:
            transaction_data.append({
                'date': txn.date,
                'amount': txn.amount,
                'category': txn.category,
                'merchant_name': txn.merchant_name
            })
        
        # Generate forecasts
        forecast_result = {
            'account_id': account_id,
            'data_points': len(transaction_data),
            'analysis_period': {
                'start': transaction_data[0]['date'].isoformat(),
                'end': transaction_data[-1]['date'].isoformat()
            }
        }
        
        # Revenue forecasting (incoming transactions)
        revenue_forecast = await self._forecast_revenue(transaction_data)
        forecast_result['revenue'] = revenue_forecast
        
        # Expense forecasting (outgoing transactions)
        expense_forecast = await self._forecast_expenses(transaction_data)
        forecast_result['expenses'] = expense_forecast
        
        # Cash flow forecasting
        cashflow_forecast = await self._forecast_cashflow(revenue_forecast, expense_forecast)
        forecast_result['cashflow'] = cashflow_forecast
        
        # Trend analysis
        trend_analysis = await self._analyze_trends(transaction_data)
        forecast_result['trends'] = trend_analysis
        
        return forecast_result
    
    async def _forecast_revenue(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Forecast revenue (negative amounts in Plaid = money in)"""
        # Filter for revenue transactions (negative amounts)
        revenue_txns = [txn for txn in transactions if txn['amount'] < 0]
        
        if not revenue_txns:
            return {'forecasts': {}, 'confidence': 'low', 'note': 'No revenue transactions found'}
        
        # Calculate daily revenue amounts
        daily_revenue = self._aggregate_daily_amounts(revenue_txns)
        
        forecasts = {}
        for horizon in self.forecast_horizons:
            # Simple moving average forecast
            recent_period = min(horizon, len(daily_revenue))
            if recent_period > 0:
                recent_avg = np.mean(list(daily_revenue.values())[-recent_period:])
                forecasts[f'{horizon}_days'] = {
                    'predicted_total': abs(recent_avg * horizon),
                    'daily_average': abs(recent_avg),
                    'confidence': self._calculate_confidence(recent_period, horizon)
                }
        
        return {
            'forecasts': forecasts,
            'historical_average': abs(np.mean([txn['amount'] for txn in revenue_txns])),
            'transaction_count': len(revenue_txns)
        }
    
    async def _forecast_expenses(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Forecast expenses (positive amounts in Plaid = money out)"""
        # Filter for expense transactions (positive amounts)
        expense_txns = [txn for txn in transactions if txn['amount'] > 0]
        
        if not expense_txns:
            return {'forecasts': {}, 'confidence': 'low', 'note': 'No expense transactions found'}
        
        # Calculate daily expense amounts
        daily_expenses = self._aggregate_daily_amounts(expense_txns)
        
        # Category-based forecasting
        category_forecasts = await self._forecast_by_category(expense_txns)
        
        forecasts = {}
        for horizon in self.forecast_horizons:
            recent_period = min(horizon, len(daily_expenses))
            if recent_period > 0:
                recent_avg = np.mean(list(daily_expenses.values())[-recent_period:])
                forecasts[f'{horizon}_days'] = {
                    'predicted_total': recent_avg * horizon,
                    'daily_average': recent_avg,
                    'confidence': self._calculate_confidence(recent_period, horizon),
                    'category_breakdown': category_forecasts.get(f'{horizon}_days', {})
                }
        
        return {
            'forecasts': forecasts,
            'historical_average': np.mean([txn['amount'] for txn in expense_txns]),
            'transaction_count': len(expense_txns),
            'categories': category_forecasts
        }
    
    async def _forecast_cashflow(self, revenue_forecast: Dict[str, Any], expense_forecast: Dict[str, Any]) -> Dict[str, Any]:
        """Forecast net cash flow"""
        cashflow_forecasts = {}
        
        for horizon in self.forecast_horizons:
            horizon_key = f'{horizon}_days'
            
            revenue_data = revenue_forecast.get('forecasts', {}).get(horizon_key, {})
            expense_data = expense_forecast.get('forecasts', {}).get(horizon_key, {})
            
            if revenue_data and expense_data:
                predicted_revenue = revenue_data.get('predicted_total', 0)
                predicted_expenses = expense_data.get('predicted_total', 0)
                net_cashflow = predicted_revenue - predicted_expenses
                
                cashflow_forecasts[horizon_key] = {
                    'predicted_revenue': predicted_revenue,
                    'predicted_expenses': predicted_expenses,
                    'net_cashflow': net_cashflow,
                    'cashflow_ratio': predicted_revenue / predicted_expenses if predicted_expenses > 0 else 0,
                    'outlook': 'positive' if net_cashflow > 0 else 'negative'
                }
        
        return {'forecasts': cashflow_forecasts}
    
    async def _analyze_trends(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze spending and revenue trends"""
        # Group by month for trend analysis
        monthly_data = {}
        for txn in transactions:
            month_key = txn['date'].strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {'revenue': 0, 'expenses': 0, 'count': 0}
            
            monthly_data[month_key]['count'] += 1
            if txn['amount'] < 0:  # Revenue
                monthly_data[month_key]['revenue'] += abs(txn['amount'])
            else:  # Expenses
                monthly_data[month_key]['expenses'] += txn['amount']
        
        # Calculate trends
        months = sorted(monthly_data.keys())
        if len(months) >= 3:
            # Revenue trend
            revenue_values = [monthly_data[month]['revenue'] for month in months[-3:]]
            revenue_trend = 'increasing' if revenue_values[-1] > revenue_values[0] else 'decreasing'
            
            # Expense trend
            expense_values = [monthly_data[month]['expenses'] for month in months[-3:]]
            expense_trend = 'increasing' if expense_values[-1] > expense_values[0] else 'decreasing'
            
            return {
                'revenue_trend': revenue_trend,
                'expense_trend': expense_trend,
                'monthly_data': {month: monthly_data[month] for month in months[-6:]},  # Last 6 months
                'volatility': {
                    'revenue': np.std(revenue_values) if len(revenue_values) > 1 else 0,
                    'expenses': np.std(expense_values) if len(expense_values) > 1 else 0
                }
            }
        
        return {'note': 'Insufficient data for trend analysis'}
    
    async def _forecast_by_category(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate forecasts by spending category"""
        category_data = {}
        
        for txn in transactions:
            categories = txn.get('category', [])
            if categories:
                main_category = categories[0]  # Use first category
                if main_category not in category_data:
                    category_data[main_category] = []
                category_data[main_category].append(txn['amount'])
        
        category_forecasts = {}
        for horizon in self.forecast_horizons:
            horizon_forecasts = {}
            for category, amounts in category_data.items():
                if len(amounts) >= 5:  # Minimum transactions for category forecast
                    avg_amount = np.mean(amounts)
                    frequency = len(amounts) / 30  # Transactions per day (assuming 30-day period)
                    horizon_forecasts[category] = avg_amount * frequency * horizon
            
            category_forecasts[f'{horizon}_days'] = horizon_forecasts
        
        return category_forecasts
    
    def _aggregate_daily_amounts(self, transactions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate transaction amounts by day"""
        daily_amounts = {}
        
        for txn in transactions:
            date_key = txn['date'].strftime('%Y-%m-%d')
            if date_key not in daily_amounts:
                daily_amounts[date_key] = 0
            daily_amounts[date_key] += abs(txn['amount'])
        
        return daily_amounts
    
    def _calculate_confidence(self, data_points: int, horizon: int) -> str:
        """Calculate forecast confidence based on data availability"""
        if data_points >= horizon:
            return 'high'
        elif data_points >= horizon / 2:
            return 'medium'
        else:
            return 'low'
    
    async def _generate_daily_forecasts(self):
        """Generate and cache daily forecast updates"""
        try:
            # Check if daily forecasts need updating
            last_update = await cache.get("forecasts:last_update")
            if last_update:
                last_update_time = datetime.fromisoformat(last_update)
                if datetime.utcnow() - last_update_time < timedelta(hours=6):
                    return  # Skip if updated within 6 hours
            
            # Generate new forecasts
            forecasts = await self.generate_forecasts()
            
            # Update timestamp
            await cache.set(
                "forecasts:last_update", 
                datetime.utcnow().isoformat(),
                expire=86400  # 24 hours
            )
            
            self.log_info("Daily forecasts updated")
            
        except Exception as e:
            self.log_error("Daily forecast update failed", error=str(e))
    
    async def _generate_aggregate_forecast(self, account_forecasts: Dict[str, Any]) -> Dict[str, Any]:
        """Generate aggregate forecast across multiple accounts"""
        aggregate = {
            'total_accounts': len(account_forecasts),
            'revenue': {},
            'expenses': {},
            'cashflow': {}
        }
        
        for horizon in self.forecast_horizons:
            horizon_key = f'{horizon}_days'
            total_revenue = 0
            total_expenses = 0
            
            for account_id, forecast in account_forecasts.items():
                revenue_data = forecast.get('revenue', {}).get('forecasts', {}).get(horizon_key, {})
                expense_data = forecast.get('expenses', {}).get('forecasts', {}).get(horizon_key, {})
                
                total_revenue += revenue_data.get('predicted_total', 0)
                total_expenses += expense_data.get('predicted_total', 0)
            
            aggregate['revenue'][horizon_key] = total_revenue
            aggregate['expenses'][horizon_key] = total_expenses
            aggregate['cashflow'][horizon_key] = total_revenue - total_expenses
        
        return aggregate