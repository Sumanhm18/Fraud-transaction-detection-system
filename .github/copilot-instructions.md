# FinSentinel AI - Project Instructions

## Project Overview
FinSentinel AI is an autonomous financial intelligence system with multi-agent architecture, real-time transaction monitoring via Plaid Sandbox, ML-based fraud detection, and blockchain verification.

## Architecture
- **Backend**: FastAPI (Python) with async processing
- **Database**: PostgreSQL + Redis + InfluxDB
- **ML/AI**: PyTorch, Scikit-learn, XGBoost for fraud detection
- **Blockchain**: Web3.py integration for audit trails
- **Frontend**: React with TypeScript
- **Real-time**: WebSockets + Plaid webhooks
- **Agents**: Modular agent system (Transaction, Fraud, Audit, Forecast)

## Development Guidelines
- Use async/await patterns for all I/O operations
- Implement proper error handling and logging
- Follow clean architecture principles
- Use type hints throughout Python code
- Implement comprehensive testing
- Follow security best practices for financial data