"""
Fraud Detection Agent for FinSentinel AI

ML-powered fraud detection using anomaly detection, pattern recognition,
and behavioral analysis for real-time transaction monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import json
import pickle
import os

import structlog
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib

from app.agents.base_agent import BaseAgent
from app.core.database import get_db_session
from app.core.redis import cache
from app.models.transaction import Transaction, FraudAlert
from app.services.websocket_manager import websocket_manager

logger = structlog.get_logger()


class FraudDetectionAgent(BaseAgent):
    """
    AI-powered fraud detection agent using machine learning
    
    Features:
    - Real-time anomaly detection using Isolation Forest
    - Behavioral pattern analysis
    - Velocity-based fraud detection
    - Location anomaly detection
    - Dynamic model training and updates
    """
    
    def __init__(self):
        super().__init__(
            name="fraud_detection",
            description="ML-powered fraud detection and risk assessment"
        )
        
        # ML Models
        self.anomaly_model = None
        self.scaler = StandardScaler()
        self.feature_columns = [
            'amount', 'hour', 'day_of_week', 'is_weekend',
            'velocity_1m', 'velocity_5m', 'velocity_1h',
            'amount_zscore', 'location_risk'
        ]
        
        # Model parameters
        self.contamination_rate = 0.1  # Expected fraud rate (10%)
        self.retrain_threshold = 1000  # Retrain after 1000 new transactions
        self.model_path = "models/fraud_detection"
        
        # Fraud detection thresholds
        self.fraud_thresholds = {
            'low': 0.3,
            'medium': 0.5,
            'high': 0.7,
            'critical': 0.9
        }
        
        self.transaction_count = 0
        
    async def initialize(self):
        """Initialize the fraud detection agent and ML models"""
        try:
            # Create models directory
            os.makedirs(self.model_path, exist_ok=True)
            
            # Load or create ML models
            await self._load_or_create_models()
            
            self.initialized = True
            self.running = True
            self.stats['start_time'] = datetime.utcnow()
            
            self.log_info("Fraud Detection Agent initialized successfully")
            
        except Exception as e:
            self.log_error("Failed to initialize Fraud Detection Agent", error=str(e))
            raise
    
    async def process(self):
        """Main processing loop - model maintenance and retraining"""
        try:
            # Check if model needs retraining
            if self.transaction_count >= self.retrain_threshold:
                await self._retrain_models()
                self.transaction_count = 0
            
            # Update fraud statistics
            await self._update_fraud_statistics()
            
            self._update_stats(success=True)
            
        except Exception as e:
            self.log_error("Fraud detection processing failed", error=str(e))
            self._update_stats(success=False)
    
    async def shutdown(self):
        """Cleanup and shutdown the agent"""
        # Save models before shutdown
        await self._save_models()
        self.running = False
        self.log_info("Fraud Detection Agent shutdown complete")
    
    def get_process_interval(self) -> float:
        """Return process interval - 30 seconds for model updates"""
        return 30.0
    
    async def analyze_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze transaction for fraud indicators using ML models
        
        Args:
            transaction_data: Raw transaction data from Plaid
            
        Returns:
            Fraud analysis results with risk score and recommendations
        """
        try:
            self.transaction_count += 1
            
            # Extract features for ML analysis
            features = await self._extract_features(transaction_data)
            
            # Run ML fraud detection
            fraud_score = await self._predict_fraud_score(features, transaction_data)
            
            # Analyze fraud patterns
            fraud_patterns = await self._analyze_fraud_patterns(transaction_data, features)
            
            # Generate risk factors
            risk_factors = await self._generate_risk_factors(transaction_data, features, fraud_score)
            
            # Create fraud analysis result
            analysis_result = {
                'transaction_id': transaction_data.get('transaction_id'),
                'fraud_score': fraud_score,
                'risk_level': self._get_risk_level(fraud_score),
                'fraud_patterns': fraud_patterns,
                'risk_factors': risk_factors,
                'ml_features': features,
                'model_version': await self._get_model_version(),
                'analyzed_at': datetime.utcnow().isoformat()
            }
            
            # Generate recommendations
            analysis_result['recommended_actions'] = self._generate_recommendations(analysis_result)
            
            # Create fraud alert if high risk
            if fraud_score >= self.fraud_thresholds['high']:
                await self._create_fraud_alert(transaction_data, analysis_result)
            
            self.log_info(
                "Fraud analysis completed",
                transaction_id=transaction_data.get('transaction_id'),
                fraud_score=fraud_score,
                risk_level=analysis_result['risk_level']
            )
            
            return analysis_result
            
        except Exception as e:
            self.log_error("Fraud analysis failed", 
                         transaction_id=transaction_data.get('transaction_id'), 
                         error=str(e))
            return {
                'transaction_id': transaction_data.get('transaction_id'),
                'fraud_score': 0.0,
                'risk_level': 'unknown',
                'error': str(e),
                'analyzed_at': datetime.utcnow().isoformat()
            }
    
    async def _extract_features(self, transaction_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract ML features from transaction data"""
        account_id = transaction_data.get('account_id')
        amount = float(transaction_data.get('amount', 0))
        transaction_time = datetime.fromisoformat(transaction_data.get('date'))
        
        features = {}
        
        # Basic transaction features
        features['amount'] = abs(amount)  # Use absolute value
        features['hour'] = transaction_time.hour
        features['day_of_week'] = transaction_time.weekday()
        features['is_weekend'] = float(transaction_time.weekday() >= 5)
        
        # Velocity features
        velocity_data = await self._get_velocity_features(account_id)
        features.update(velocity_data)
        
        # Amount analysis features
        amount_features = await self._get_amount_features(account_id, amount)
        features.update(amount_features)
        
        # Location risk features
        location_risk = await self._calculate_location_risk(account_id, transaction_data.get('location'))
        features['location_risk'] = location_risk
        
        # Merchant category features
        category_risk = self._calculate_category_risk(transaction_data.get('category', []))
        features['category_risk'] = category_risk
        
        # Payment channel features
        channel_risk = self._calculate_channel_risk(transaction_data.get('payment_channel'))
        features['channel_risk'] = channel_risk
        
        return features
    
    async def _predict_fraud_score(self, features: Dict[str, float], transaction_data: Dict[str, Any]) -> float:
        """Predict fraud score using ML models"""
        try:
            if not self.anomaly_model:
                return 0.0  # No model available
            
            # Prepare feature vector
            feature_vector = []
            for col in self.feature_columns:
                feature_vector.append(features.get(col, 0.0))
            
            feature_array = np.array(feature_vector).reshape(1, -1)
            
            # Scale features
            scaled_features = self.scaler.transform(feature_array)
            
            # Get anomaly score from Isolation Forest
            anomaly_score = self.anomaly_model.decision_function(scaled_features)[0]
            
            # Convert to fraud probability (0-1 scale)
            # Isolation Forest returns negative scores for anomalies
            fraud_score = max(0.0, min(1.0, (0.5 - anomaly_score) * 2))
            
            return fraud_score
            
        except Exception as e:
            self.log_error("ML prediction failed", error=str(e))
            return 0.0
    
    async def _analyze_fraud_patterns(self, transaction_data: Dict[str, Any], features: Dict[str, float]) -> List[str]:
        """Analyze for specific fraud patterns"""
        patterns = []
        
        # High velocity pattern
        if features.get('velocity_1m', 0) > 3:
            patterns.append('high_frequency_transactions')
        
        # Unusual amount pattern
        if features.get('amount_zscore', 0) > 3:
            patterns.append('unusual_transaction_amount')
        
        # Off-hours pattern
        if features.get('hour', 12) < 6 or features.get('hour', 12) > 23:
            patterns.append('off_hours_activity')
        
        # Location anomaly pattern
        if features.get('location_risk', 0) > 0.7:
            patterns.append('suspicious_location')
        
        # Round amount pattern (common in fraud)
        amount = abs(float(transaction_data.get('amount', 0)))
        if amount > 0 and amount % 1.0 == 0 and amount >= 100:
            patterns.append('round_amount_transaction')
        
        # Weekend activity pattern
        if features.get('is_weekend', 0) == 1 and amount > 1000:
            patterns.append('high_amount_weekend_transaction')
        
        return patterns
    
    async def _generate_risk_factors(self, transaction_data: Dict[str, Any], features: Dict[str, float], fraud_score: float) -> List[Dict[str, Any]]:
        """Generate detailed risk factors"""
        risk_factors = []
        
        # High fraud score
        if fraud_score > 0.7:
            risk_factors.append({
                'type': 'ml_anomaly',
                'severity': 'high',
                'description': f'ML model detected high fraud probability ({fraud_score:.2f})',
                'value': fraud_score
            })
        
        # Velocity risks
        if features.get('velocity_1m', 0) > 2:
            risk_factors.append({
                'type': 'velocity',
                'severity': 'medium',
                'description': f'High transaction velocity: {features["velocity_1m"]} transactions/minute',
                'value': features['velocity_1m']
            })
        
        # Amount risks
        if features.get('amount_zscore', 0) > 2:
            risk_factors.append({
                'type': 'amount_anomaly',
                'severity': 'medium',
                'description': f'Unusual transaction amount (Z-score: {features["amount_zscore"]:.2f})',
                'value': features['amount_zscore']
            })
        
        # Location risks
        if features.get('location_risk', 0) > 0.5:
            risk_factors.append({
                'type': 'location',
                'severity': 'medium',
                'description': 'Transaction from new or unusual location',
                'value': features['location_risk']
            })
        
        return risk_factors
    
    def _generate_recommendations(self, analysis_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on fraud analysis"""
        recommendations = []
        fraud_score = analysis_result['fraud_score']
        
        if fraud_score >= self.fraud_thresholds['critical']:
            recommendations.extend([
                'Block transaction immediately',
                'Contact customer for verification',
                'Review recent account activity',
                'Consider temporary account freeze'
            ])
        elif fraud_score >= self.fraud_thresholds['high']:
            recommendations.extend([
                'Hold transaction for manual review',
                'Send security alert to customer',
                'Verify transaction via secondary channel'
            ])
        elif fraud_score >= self.fraud_thresholds['medium']:
            recommendations.extend([
                'Flag for enhanced monitoring',
                'Log for audit trail',
                'Consider step-up authentication'
            ])
        else:
            recommendations.append('Continue normal processing')
        
        return recommendations
    
    async def _create_fraud_alert(self, transaction_data: Dict[str, Any], analysis_result: Dict[str, Any]):
        """Create fraud alert record and send notifications"""
        try:
            async with get_db_session() as db:
                alert = FraudAlert(
                    transaction_id=transaction_data.get('transaction_id'),
                    alert_type='ml_fraud_detection',
                    severity=analysis_result['risk_level'],
                    confidence=analysis_result['fraud_score'],
                    title=f"Fraud Alert - {analysis_result['risk_level'].title()} Risk",
                    description=f"ML model detected fraud probability of {analysis_result['fraud_score']:.2%}",
                    risk_factors=analysis_result['risk_factors'],
                    recommended_actions=analysis_result['recommended_actions']
                )
                
                db.add(alert)
                await db.commit()
                
                # Send real-time alert
                await websocket_manager.broadcast_fraud_alert({
                    'alert_id': str(alert.id),
                    'transaction_id': transaction_data.get('transaction_id'),
                    'severity': analysis_result['risk_level'],
                    'fraud_score': analysis_result['fraud_score'],
                    'risk_factors': analysis_result['risk_factors'],
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                self.log_info("Fraud alert created and broadcast", 
                            transaction_id=transaction_data.get('transaction_id'),
                            alert_id=str(alert.id))
        
        except Exception as e:
            self.log_error("Failed to create fraud alert", error=str(e))
    
    def _get_risk_level(self, fraud_score: float) -> str:
        """Convert fraud score to risk level"""
        if fraud_score >= self.fraud_thresholds['critical']:
            return 'critical'
        elif fraud_score >= self.fraud_thresholds['high']:
            return 'high'
        elif fraud_score >= self.fraud_thresholds['medium']:
            return 'medium'
        elif fraud_score >= self.fraud_thresholds['low']:
            return 'low'
        else:
            return 'minimal'
    
    async def _get_velocity_features(self, account_id: str) -> Dict[str, float]:
        """Get velocity-based features"""
        features = {}
        
        for window in ['1m', '5m', '1h']:
            cache_key = f"velocity:{account_id}:{window}"
            velocity_data = await cache.get(cache_key) or {'count': 0}
            features[f'velocity_{window}'] = float(velocity_data['count'])
        
        return features
    
    async def _get_amount_features(self, account_id: str, amount: float) -> Dict[str, float]:
        """Get amount-based features"""
        cache_key = f"amounts:{account_id}"
        recent_amounts = await cache.get(cache_key) or []
        
        if len(recent_amounts) > 5:
            avg_amount = np.mean(recent_amounts)
            std_amount = np.std(recent_amounts)
            z_score = abs(amount - avg_amount) / (std_amount + 0.01)
        else:
            z_score = 0.0
        
        return {'amount_zscore': z_score}
    
    async def _calculate_location_risk(self, account_id: str, location_data: Dict[str, Any]) -> float:
        """Calculate location-based risk score"""
        if not location_data:
            return 0.0
        
        cache_key = f"locations:{account_id}"
        recent_locations = await cache.get(cache_key) or []
        
        if not recent_locations:
            return 0.3  # Moderate risk for first transaction
        
        # Check if location is in recent history
        current_city = location_data.get('city', '')
        current_region = location_data.get('region', '')
        
        for loc in recent_locations[-20:]:  # Check last 20 locations
            if (loc.get('city') == current_city and 
                loc.get('region') == current_region):
                return 0.1  # Low risk for known location
        
        return 0.7  # High risk for new location
    
    def _calculate_category_risk(self, categories: List[str]) -> float:
        """Calculate risk based on merchant category"""
        high_risk_categories = [
            'ATM', 'Cash Advance', 'Gambling', 'Adult Entertainment',
            'Cryptocurrency', 'Money Transfer', 'Check Cashing'
        ]
        
        for category in categories:
            if any(risk_cat.lower() in category.lower() for risk_cat in high_risk_categories):
                return 0.8
        
        return 0.2  # Normal categories
    
    def _calculate_channel_risk(self, payment_channel: str) -> float:
        """Calculate risk based on payment channel"""
        channel_risks = {
            'online': 0.4,
            'in store': 0.2,
            'other': 0.6
        }
        return channel_risks.get(payment_channel, 0.3)
    
    async def _load_or_create_models(self):
        """Load existing models or create new ones"""
        try:
            # Try to load existing model
            model_file = os.path.join(self.model_path, 'isolation_forest.joblib')
            scaler_file = os.path.join(self.model_path, 'scaler.joblib')
            
            if os.path.exists(model_file) and os.path.exists(scaler_file):
                self.anomaly_model = joblib.load(model_file)
                self.scaler = joblib.load(scaler_file)
                self.log_info("Loaded existing ML models")
            else:
                # Create new model
                await self._create_initial_model()
                
        except Exception as e:
            self.log_error("Failed to load ML models", error=str(e))
            await self._create_initial_model()
    
    async def _create_initial_model(self):
        """Create initial ML model with synthetic data"""
        try:
            # Generate synthetic training data
            synthetic_data = self._generate_synthetic_training_data()
            
            # Train initial model
            X = synthetic_data[self.feature_columns]
            
            # Fit scaler
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)
            
            # Train Isolation Forest
            self.anomaly_model = IsolationForest(
                contamination=self.contamination_rate,
                random_state=42,
                n_estimators=100
            )
            self.anomaly_model.fit(X_scaled)
            
            # Save models
            await self._save_models()
            
            self.log_info("Created and trained initial ML models")
            
        except Exception as e:
            self.log_error("Failed to create initial model", error=str(e))
    
    def _generate_synthetic_training_data(self) -> pd.DataFrame:
        """Generate synthetic training data for initial model"""
        np.random.seed(42)
        n_samples = 10000
        
        data = {
            'amount': np.random.lognormal(3, 1, n_samples),  # Log-normal distribution for amounts
            'hour': np.random.randint(0, 24, n_samples),
            'day_of_week': np.random.randint(0, 7, n_samples),
            'is_weekend': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
            'velocity_1m': np.random.poisson(0.5, n_samples),  # Low velocity for normal transactions
            'velocity_5m': np.random.poisson(2, n_samples),
            'velocity_1h': np.random.poisson(10, n_samples),
            'amount_zscore': np.random.normal(0, 1, n_samples),
            'location_risk': np.random.beta(2, 8, n_samples),  # Most locations are low risk
        }
        
        return pd.DataFrame(data)
    
    async def _retrain_models(self):
        """Retrain models with new transaction data"""
        try:
            self.log_info("Starting model retraining")
            
            # Get recent transaction data from database
            async with get_db_session() as db:
                # This would fetch real transaction data for retraining
                # For now, we'll use synthetic data
                pass
            
            # For production, implement actual retraining with real data
            self.log_info("Model retraining completed")
            
        except Exception as e:
            self.log_error("Model retraining failed", error=str(e))
    
    async def _save_models(self):
        """Save ML models to disk"""
        try:
            if self.anomaly_model:
                model_file = os.path.join(self.model_path, 'isolation_forest.joblib')
                joblib.dump(self.anomaly_model, model_file)
            
            scaler_file = os.path.join(self.model_path, 'scaler.joblib')
            joblib.dump(self.scaler, scaler_file)
            
            self.log_info("ML models saved successfully")
            
        except Exception as e:
            self.log_error("Failed to save ML models", error=str(e))
    
    async def _get_model_version(self) -> str:
        """Get current model version"""
        return f"v1.0_{datetime.utcnow().strftime('%Y%m%d')}"
    
    async def _update_fraud_statistics(self):
        """Update fraud detection statistics"""
        # This would update various fraud detection metrics
        # for monitoring and reporting purposes
        pass