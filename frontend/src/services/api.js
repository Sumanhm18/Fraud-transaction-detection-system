const API_BASE_URL = 'http://localhost:8000';

class APIService {
  // Health & Status
  async getHealth() {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.json();
  }

  async getConnectionStatus() {
    const response = await fetch(`${API_BASE_URL}/api/v1/connection_status`);
    return response.json();
  }

  async getDatabaseStats() {
    const response = await fetch(`${API_BASE_URL}/api/v1/database_stats`);
    return response.json();
  }

  async getAdminStats() {
    const response = await fetch(`${API_BASE_URL}/api/v1/admin/stats`);
    return response.json();
  }

  // Accounts & Transactions
  async getAccounts() {
    const response = await fetch(`${API_BASE_URL}/api/v1/accounts`);
    return response.json();
  }

  async getTransactions(limit = 100) {
    const response = await fetch(`${API_BASE_URL}/api/v1/transactions?limit=${limit}`);
    return response.json();
  }

  // Fraud Detection
  async getFraudAlerts() {
    const response = await fetch(`${API_BASE_URL}/api/v1/fraud/alerts`);
    return response.json();
  }

  // Simulation & Manual Entry
  async simulateTransaction() {
    const response = await fetch(`${API_BASE_URL}/api/v1/simulate_transaction`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    return response.json();
  }

  // Plaid Integration
  async createLinkToken(userId) {
    const response = await fetch(`${API_BASE_URL}/api/v1/plaid/create_link_token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId })
    });
    return response.json();
  }

  async exchangePublicToken(publicToken, metadata) {
    const response = await fetch(`${API_BASE_URL}/api/v1/plaid/exchange_public_token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        public_token: publicToken, 
        user_id: 'demo_user',
        metadata 
      })
    });
    return response.json();
  }

  async getPlaidAccounts(userId) {
    const response = await fetch(`${API_BASE_URL}/api/v1/plaid/accounts/${userId}`);
    return response.json();
  }

  async getPlaidTransactions(userId, days = 30) {
    const response = await fetch(`${API_BASE_URL}/api/v1/plaid/transactions/${userId}?days=${days}`);
    return response.json();
  }

  async getPlaidConnectionStatus(userId) {
    const response = await fetch(`${API_BASE_URL}/api/v1/plaid/connection_status/${userId}`);
    return response.json();
  }

  // Manual Transaction Entry
  async createManualTransaction(transactionData) {
    const response = await fetch(`${API_BASE_URL}/api/v1/manual_transaction`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(transactionData)
    });
    return response.json();
  }

  async updateManualTransaction(transactionId, transactionData) {
    const response = await fetch(`${API_BASE_URL}/api/v1/manual_transaction/${transactionId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(transactionData)
    });
    return response.json();
  }

  async deleteTransaction(transactionId) {
    const response = await fetch(`${API_BASE_URL}/api/v1/transactions/${transactionId}`, {
      method: 'DELETE'
    });
    return response.json();
  }

  async getManualTransactions(limit = 50) {
    const response = await fetch(`${API_BASE_URL}/api/v1/manual_transactions?limit=${limit}`);
    return response.json();
  }

  // Individual Account & Transaction endpoints
  async getAccount(accountId) {
    const response = await fetch(`${API_BASE_URL}/api/v1/accounts/${accountId}`);
    return response.json();
  }

  async getTransaction(transactionId) {
    const response = await fetch(`${API_BASE_URL}/api/v1/transactions/${transactionId}`);
    return response.json();
  }

  // Fraud Detection - Enhanced
  async getFraudScore(transactionId) {
    const response = await fetch(`${API_BASE_URL}/api/v1/fraud/score/${transactionId}`);
    return response.json();
  }

  // Analytics Dashboard
  async getAnalyticsSummary() {
    const response = await fetch(`${API_BASE_URL}/api/v1/analytics/summary`);
    return response.json();
  }

  // System Status & Monitoring
  async getWebSocketStatus() {
    const response = await fetch(`${API_BASE_URL}/api/v1/ws/status`);
    return response.json();
  }

  async getAgentsStatus() {
    const response = await fetch(`${API_BASE_URL}/api/v1/agents/status`);
    return response.json();
  }

  // WebSocket connections with auto-reconnect
  connectTransactionWebSocket(onMessage, onStatusChange) {
    return this._connectWebSocket('ws://localhost:8000/ws/transactions', 'transactions', onMessage, onStatusChange);
  }

  connectAlertsWebSocket(onMessage, onStatusChange) {
    return this._connectWebSocket('ws://localhost:8000/ws/alerts', 'alerts', onMessage, onStatusChange);
  }

  connectGeneralWebSocket(onMessage, onStatusChange) {
    return this._connectWebSocket('ws://localhost:8000/ws', 'general', onMessage, onStatusChange);
  }

  // Private WebSocket connection method
  _connectWebSocket(url, type, onMessage, onStatusChange) {
    let ws = null;
    let reconnectTimer = null;

    const connect = () => {
      try {
        console.log(`🔄 Attempting ${type} WebSocket connection to ${url}`);
        ws = new WebSocket(url);
        
        ws.onopen = () => {
          console.log(`🔗 ${type} WebSocket connected successfully to ${url}`);
          console.log(`🎯 FinSentinel AI ${type} real-time connection established`);
          if (onStatusChange) onStatusChange(true);
          
          // Clear any existing reconnect timer
          if (reconnectTimer) {
            clearTimeout(reconnectTimer);
            reconnectTimer = null;
          }
          
          // Start keepalive ping every 25 seconds
          const pingInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send('ping');
            } else {
              clearInterval(pingInterval);
            }
          }, 25000);
        };
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log(`📨 ${type} WebSocket message received:`, data);
            onMessage(data);
          } catch (error) {
            console.error(`❌ ${type} WebSocket message parsing error:`, error, 'Raw data:', event.data);
          }
        };
        
        ws.onclose = (event) => {
          console.log(`❌ ${type} WebSocket connection closed:`, event.code, event.reason);
          if (onStatusChange) onStatusChange(false);
          
          // Auto-reconnect after 3 seconds
          if (!reconnectTimer) {
            reconnectTimer = setTimeout(() => {
              console.log(`🔄 Attempting ${type} WebSocket reconnection...`);
              connect();
            }, 3000);
          }
        };
        
        ws.onerror = (error) => {
          console.error(`WebSocket ${type} error:`, error);
          if (onStatusChange) onStatusChange(false);
        };
      } catch (error) {
        console.error(`❌ ${type} WebSocket connection failed:`, error);
        console.error('📍 Error details:', error.message, error.stack);
        if (onStatusChange) onStatusChange(false);
      }
    };

    // Initial connection
    connect();

    // Return cleanup function
    return () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      if (ws) {
        ws.close();
      }
    };
  }

  // Legacy method for backward compatibility
  connectWebSocket(onMessage, onStatusChange) {
    return this.connectGeneralWebSocket(onMessage, onStatusChange);
  }

  // API Testing - Test all endpoints
  async testAllEndpoints() {
    const results = {};
    console.log('🧪 Testing all API endpoints...');
    
    const endpoints = [
      { name: 'Health Check', fn: () => this.getHealth() },
      { name: 'Accounts List', fn: () => this.getAccounts() },
      { name: 'Transactions List', fn: () => this.getTransactions(10) },
      { name: 'Fraud Alerts', fn: () => this.getFraudAlerts() },
      { name: 'Analytics Summary', fn: () => this.getAnalyticsSummary() },
      { name: 'Agents Status', fn: () => this.getAgentsStatus() },
      { name: 'WebSocket Status', fn: () => this.getWebSocketStatus() }
    ];

    for (const endpoint of endpoints) {
      try {
        console.log(`🔍 Testing ${endpoint.name}...`);
        const result = await endpoint.fn();
        results[endpoint.name] = { success: true, data: result };
        console.log(`✅ ${endpoint.name}:`, result);
      } catch (error) {
        results[endpoint.name] = { success: false, error: error.message };
        console.error(`❌ ${endpoint.name} failed:`, error);
      }
    }
    
    console.log('🎉 API endpoint testing complete!', results);
    return results;
  }
}

const FinSentinelAPI = new APIService();
export { FinSentinelAPI };
export default FinSentinelAPI;