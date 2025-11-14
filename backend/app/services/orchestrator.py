"""
Multi-Agent Orchestrator for FinSentinel AI

Coordinates multiple AI agents for transaction monitoring, fraud detection,
forecasting, and audit intelligence.
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import structlog

from app.agents.base_agent import BaseAgent
from app.agents.transaction_monitor import TransactionMonitorAgent
from app.agents.fraud_detection import FraudDetectionAgent
from app.agents.forecast_agent import ForecastAgent
from app.agents.audit_agent import AuditAgent
from app.core.redis import cache
from app.services.websocket_manager import websocket_manager

logger = structlog.get_logger()


class AgentOrchestrator:
    """
    Central orchestrator for the multi-agent system
    
    Manages agent lifecycle, coordinates communication between agents,
    and provides hot-swappable agent registration for extensibility.
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        self._agent_stats = {}
    
    async def initialize(self):
        """Initialize all agents and start orchestration"""
        logger.info("Initializing FinSentinel AI Agent Orchestrator")
        
        try:
            # Register core agents
            await self._register_core_agents()
            
            # Start agent monitoring
            self.running = True
            await self._start_agent_monitoring()
            
            logger.info(
                "Agent orchestrator initialized",
                agent_count=len(self.agents),
                agents=list(self.agents.keys())
            )
            
        except Exception as e:
            logger.error("Failed to initialize orchestrator", error=str(e))
            raise
    
    async def shutdown(self):
        """Shutdown all agents and cleanup"""
        logger.info("Shutting down agent orchestrator")
        
        self.running = False
        
        # Cancel all agent tasks
        for agent_name, task in self.agent_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info("Agent task cancelled", agent=agent_name)
        
        # Shutdown individual agents
        for agent_name, agent in self.agents.items():
            try:
                await agent.shutdown()
                logger.info("Agent shutdown complete", agent=agent_name)
            except Exception as e:
                logger.error("Agent shutdown failed", agent=agent_name, error=str(e))
        
        logger.info("Agent orchestrator shutdown complete")
    
    async def _register_core_agents(self):
        """Register the core FinSentinel AI agents"""
        # Transaction Monitor Agent - Real-time transaction processing
        transaction_agent = TransactionMonitorAgent()
        await self.register_agent("transaction_monitor", transaction_agent)
        
        # Fraud Detection Agent - ML-based anomaly detection
        fraud_agent = FraudDetectionAgent()
        await self.register_agent("fraud_detection", fraud_agent)
        
        # Forecast Agent - Predictive analytics
        forecast_agent = ForecastAgent()
        await self.register_agent("forecast", forecast_agent)
        
        # Audit Agent - Automated audit intelligence
        audit_agent = AuditAgent()
        await self.register_agent("audit", audit_agent)
    
    async def register_agent(self, name: str, agent: BaseAgent):
        """
        Register a new agent with the orchestrator
        
        Supports hot-swappable agent registration for extensibility.
        New agents (Tax AI, KYC AI, DeFi AI) can be added without system redesign.
        """
        try:
            # Initialize the agent
            await agent.initialize()
            
            # Store agent
            self.agents[name] = agent
            
            # Start agent task if orchestrator is running
            if self.running:
                task = asyncio.create_task(self._run_agent(name, agent))
                self.agent_tasks[name] = task
            
            # Initialize agent stats
            self._agent_stats[name] = {
                'status': 'active',
                'processed_items': 0,
                'last_activity': datetime.utcnow(),
                'errors': 0
            }
            
            logger.info("Agent registered successfully", agent=name, type=type(agent).__name__)
            
        except Exception as e:
            logger.error("Failed to register agent", agent=name, error=str(e))
            raise
    
    async def unregister_agent(self, name: str):
        """Unregister and shutdown an agent"""
        if name not in self.agents:
            logger.warning("Agent not found for unregistration", agent=name)
            return
        
        try:
            # Cancel agent task
            if name in self.agent_tasks:
                self.agent_tasks[name].cancel()
                try:
                    await self.agent_tasks[name]
                except asyncio.CancelledError:
                    pass
                del self.agent_tasks[name]
            
            # Shutdown agent
            await self.agents[name].shutdown()
            del self.agents[name]
            del self._agent_stats[name]
            
            logger.info("Agent unregistered successfully", agent=name)
            
        except Exception as e:
            logger.error("Failed to unregister agent", agent=name, error=str(e))
    
    async def _start_agent_monitoring(self):
        """Start monitoring tasks for all registered agents"""
        for name, agent in self.agents.items():
            task = asyncio.create_task(self._run_agent(name, agent))
            self.agent_tasks[name] = task
    
    async def _run_agent(self, name: str, agent: BaseAgent):
        """Run an individual agent with error handling and monitoring"""
        logger.info("Starting agent", agent=name)
        
        while self.running:
            try:
                # Process agent work
                await agent.process()
                
                # Update stats
                self._agent_stats[name]['processed_items'] += 1
                self._agent_stats[name]['last_activity'] = datetime.utcnow()
                
                # Agent-specific sleep interval
                await asyncio.sleep(agent.get_process_interval())
                
            except Exception as e:
                logger.error("Agent processing error", agent=name, error=str(e))
                self._agent_stats[name]['errors'] += 1
                self._agent_stats[name]['status'] = 'error'
                
                # Send error notification
                await websocket_manager.broadcast_system_notification({
                    'type': 'agent_error',
                    'agent': name,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Wait before retry
                await asyncio.sleep(30)
        
        logger.info("Agent stopped", agent=name)
    
    async def process_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a transaction through the agent pipeline
        
        Args:
            transaction_data: Raw transaction data from Plaid
            
        Returns:
            Processed transaction with all agent analysis
        """
        results = {}
        
        # Process through transaction monitor
        if 'transaction_monitor' in self.agents:
            try:
                monitor_result = await self.agents['transaction_monitor'].analyze_transaction(transaction_data)
                results['monitoring'] = monitor_result
            except Exception as e:
                logger.error("Transaction monitoring failed", error=str(e))
        
        # Fraud detection analysis
        if 'fraud_detection' in self.agents:
            try:
                fraud_result = await self.agents['fraud_detection'].analyze_transaction(transaction_data)
                results['fraud_analysis'] = fraud_result
                
                # Generate alert if high risk
                if fraud_result.get('fraud_score', 0) > 0.7:
                    await self._generate_fraud_alert(transaction_data, fraud_result)
                    
            except Exception as e:
                logger.error("Fraud detection failed", error=str(e))
        
        # Update agent stats
        for agent_name in results.keys():
            if agent_name.replace('_analysis', '').replace('ing', '') in self._agent_stats:
                self._agent_stats[agent_name.replace('_analysis', '').replace('ing', '')]['processed_items'] += 1
        
        return results
    
    async def _generate_fraud_alert(self, transaction_data: Dict[str, Any], fraud_result: Dict[str, Any]):
        """Generate and broadcast fraud alert"""
        alert = {
            'transaction_id': transaction_data.get('transaction_id'),
            'fraud_score': fraud_result.get('fraud_score'),
            'risk_factors': fraud_result.get('risk_factors', []),
            'severity': self._calculate_alert_severity(fraud_result.get('fraud_score', 0)),
            'timestamp': datetime.utcnow().isoformat(),
            'recommended_actions': fraud_result.get('recommended_actions', [])
        }
        
        await websocket_manager.broadcast_fraud_alert(alert)
        
        # Cache alert for audit trail
        await cache.set(
            f"fraud_alert:{transaction_data.get('transaction_id')}", 
            alert, 
            expire=86400  # 24 hours
        )
    
    def _calculate_alert_severity(self, fraud_score: float) -> str:
        """Calculate alert severity based on fraud score"""
        if fraud_score >= 0.9:
            return 'critical'
        elif fraud_score >= 0.7:
            return 'high'
        elif fraud_score >= 0.5:
            return 'medium'
        else:
            return 'low'
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get current status of all agents"""
        status = {}
        
        for name, stats in self._agent_stats.items():
            status[name] = {
                'status': stats['status'],
                'processed_items': stats['processed_items'],
                'last_activity': stats['last_activity'].isoformat() if stats['last_activity'] else None,
                'errors': stats['errors'],
                'uptime_seconds': (datetime.utcnow() - stats['last_activity']).total_seconds() if stats['last_activity'] else None
            }
        
        return status
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        total_agents = len(self.agents)
        active_agents = sum(1 for stats in self._agent_stats.values() if stats['status'] == 'active')
        total_processed = sum(stats['processed_items'] for stats in self._agent_stats.values())
        total_errors = sum(stats['errors'] for stats in self._agent_stats.values())
        
        return {
            'total_agents': total_agents,
            'active_agents': active_agents,
            'health_percentage': (active_agents / total_agents * 100) if total_agents > 0 else 0,
            'total_processed_items': total_processed,
            'total_errors': total_errors,
            'error_rate': (total_errors / total_processed * 100) if total_processed > 0 else 0,
            'orchestrator_status': 'running' if self.running else 'stopped'
        }
    
    async def trigger_forecast_update(self) -> Dict[str, Any]:
        """Manually trigger forecast agent update"""
        if 'forecast' not in self.agents:
            return {'error': 'Forecast agent not available'}
        
        try:
            result = await self.agents['forecast'].generate_forecasts()
            return {'success': True, 'result': result}
        except Exception as e:
            logger.error("Manual forecast update failed", error=str(e))
            return {'error': str(e)}
    
    async def generate_audit_report(self) -> Dict[str, Any]:
        """Generate comprehensive audit report"""
        if 'audit' not in self.agents:
            return {'error': 'Audit agent not available'}
        
        try:
            result = await self.agents['audit'].generate_audit_report()
            return {'success': True, 'result': result}
        except Exception as e:
            logger.error("Audit report generation failed", error=str(e))
            return {'error': str(e)}