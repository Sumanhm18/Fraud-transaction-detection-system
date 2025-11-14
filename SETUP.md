# FinSentinel AI - Complete Setup Guide

## 🚀 Quick Start with Plaid Sandbox

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Plaid Developer Account

### 1. Get Plaid Sandbox Credentials

1. **Sign up for Plaid** at https://plaid.com/
2. **Go to Dashboard** → Team Settings → Keys
3. **Copy your credentials:**
   ```
   Client ID: [Your Client ID]
   Sandbox Secret: [Your Sandbox Secret]
   ```

### 2. Environment Setup

```bash
# Clone or navigate to project
cd /Users/sumanhm/Downloads/finance

# Backend environment
cp backend/.env.example backend/.env
```

**Edit `backend/.env` with your Plaid credentials:**
```env
# Plaid Configuration
PLAID_CLIENT_ID=your_actual_client_id_here
PLAID_SECRET=your_actual_sandbox_secret_here
PLAID_ENV=sandbox
PLAID_PRODUCTS=transactions,auth,identity,assets,liabilities
PLAID_COUNTRY_CODES=US,CA

# Database (Docker defaults)
DATABASE_URL=postgresql+asyncpg://finsentinel:password@localhost:5432/finsentinel
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-super-secret-key-change-this-in-production-now

# Other settings (can use defaults)
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=finsentinel-token
INFLUXDB_ORG=finsentinel
INFLUXDB_BUCKET=transactions
```

### 3. Start Infrastructure Services

```bash
# Start databases and supporting services
docker-compose up -d postgres redis influxdb kafka zookeeper

# Wait for services to be ready (about 30 seconds)
docker-compose ps
```

### 4. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Backend will be available at:** http://localhost:8000
**API Documentation:** http://localhost:8000/docs

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start React development server
npm start
```

**Frontend will be available at:** http://localhost:3000

### 6. Test Plaid Integration

1. **Open Frontend**: http://localhost:3000
2. **Click "Connect Bank Account"**
3. **Use Plaid Sandbox Credentials:**
   ```
   Institution: Chase (or any test bank)
   Username: user_good
   Password: pass_good
   ```
4. **View Live Transaction Data** in real-time dashboard

### 7. Available Test Accounts

Plaid Sandbox provides several test scenarios:

**Normal User (Recommended for testing):**
- Username: `user_good`
- Password: `pass_good`
- Description: Clean transaction history, good for testing

**Custom Transactions:**
- Username: `user_custom`  
- Password: `pass_good`
- Description: Allows custom transaction scenarios

**Error Testing:**
- Username: `user_bad`
- Password: `pass_good`
- Description: Triggers various error conditions

## 🏗️ Architecture Overview

### Real-time Transaction Flow
```
Plaid Sandbox → FastAPI Backend → AI Agents → WebSocket → React Frontend
     ↓              ↓              ↓           ↓            ↓
Live Bank Data  ML Processing  Fraud Detection  Real-time UI  User Dashboard
```

### Multi-Agent System
- **Transaction Monitor**: Real-time processing
- **Fraud Detection**: ML-based anomaly detection
- **Forecast Agent**: Revenue/cashflow prediction
- **Audit Agent**: Automated compliance reports

### Key Features Enabled

✅ **Real-time Transaction Monitoring**
- Live transaction feeds via Plaid webhooks
- Instant fraud detection and alerts
- ML-powered risk scoring

✅ **Plaid Sandbox Integration**
- Test bank accounts with realistic data
- Multiple account types (checking, savings, credit)
- Webhook processing for real-time updates

✅ **AI-Powered Analysis**
- Anomaly detection using machine learning
- Pattern recognition for fraud prevention
- Predictive analytics for financial forecasting

✅ **Blockchain Verification**
- Immutable audit trails
- Smart contract integration ready
- Tamper-proof transaction records

## 🔧 Development Commands

### Backend
```bash
# Run tests
pytest

# Format code
black . && isort .

# Type checking
mypy .

# Database migration
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Frontend
```bash
# Run tests
npm test

# Build for production
npm run build

# Type checking
npm run type-check

# Format code
npm run format
```

### Docker (Full Stack)
```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop everything
docker-compose down
```

## 📊 Monitoring & Observability

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)
- **API Metrics**: http://localhost:8000/metrics

## 🔐 Security Notes

1. **Change default secrets** in production
2. **Use HTTPS** for webhook endpoints
3. **Validate webhook signatures** from Plaid
4. **Encrypt sensitive data** at rest and in transit
5. **Regular security audits** of dependencies

## 🚨 Troubleshooting

### Plaid Connection Issues
```bash
# Check Plaid credentials
curl -X POST http://localhost:8000/api/v1/plaid/link_token \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user"}'
```

### Database Connection Issues
```bash
# Check PostgreSQL
docker-compose exec postgres psql -U finsentinel -d finsentinel -c "\dt"

# Check Redis
docker-compose exec redis redis-cli ping
```

### Frontend/Backend Communication
```bash
# Test API endpoint
curl http://localhost:8000/health

# Check WebSocket connection in browser console
```

## 📈 Next Steps

1. **Add More Agents**: Tax optimization, KYC compliance
2. **Enhanced ML Models**: More sophisticated fraud detection
3. **Blockchain Integration**: Smart contracts for audit trails  
4. **Multi-tenant Support**: Support multiple organizations
5. **Mobile App**: React Native implementation

---

**🎉 You now have a fully functional FinSentinel AI system with live Plaid Sandbox integration!**

The system provides real-time transaction monitoring, AI-powered fraud detection, and autonomous financial intelligence - all powered by live banking data from Plaid's sandbox environment.