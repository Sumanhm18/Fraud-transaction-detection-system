import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Alert,
  Button,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress
} from '@mui/material';
import {
  AccountBalance as AccountBalanceIcon,
  Security as SecurityIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Speed as SpeedIcon,
  Analytics as AnalyticsIcon,
  SwapHoriz as TransactionIcon,
  Shield as ShieldIcon
} from '@mui/icons-material';
import { FinSentinelAPI } from '../services/api';

const ComprehensiveDashboard = () => {
  const [dashboardData, setDashboardData] = useState({
    health: null,
    accounts: [],
    transactions: [],
    fraudAlerts: [],
    analytics: null,
    agents: null,
    wsStatus: null
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [realtimeUpdates, setRealtimeUpdates] = useState([]);
  const [simulating, setSimulating] = useState(false);

  useEffect(() => {
    loadDashboardData();
    
    // Setup WebSocket for real-time updates
    const wsCleanup = FinSentinelAPI.connectGeneralWebSocket(
      (data) => {
        console.log('📨 Real-time update:', data);
        setRealtimeUpdates(prev => [...prev.slice(-9), { ...data, timestamp: new Date() }]);
        // Refresh relevant data based on update type
        if (data.type === 'transaction' || data.type === 'fraud_alert') {
          refreshTransactionData();
        }
      },
      (connected) => {
        setWsConnected(connected);
        console.log('🔗 WebSocket status:', connected ? 'Connected' : 'Disconnected');
      }
    );

    const interval = setInterval(() => {
      refreshData();
    }, 30000); // Refresh every 30 seconds

    return () => {
      if (wsCleanup) wsCleanup();
      clearInterval(interval);
    };
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('🔄 Loading comprehensive dashboard data...');
      
      const [health, accounts, transactions, fraudAlerts, analytics, agents, wsStatus] = await Promise.allSettled([
        FinSentinelAPI.getHealth(),
        FinSentinelAPI.getAccounts(),
        FinSentinelAPI.getTransactions(20),
        FinSentinelAPI.getFraudAlerts(),
        FinSentinelAPI.getAnalyticsSummary(),
        FinSentinelAPI.getAgentsStatus(),
        FinSentinelAPI.getWebSocketStatus()
      ]);

      setDashboardData({
        health: health.status === 'fulfilled' ? health.value : null,
        accounts: accounts.status === 'fulfilled' ? accounts.value : [],
        transactions: transactions.status === 'fulfilled' ? transactions.value : [],
        fraudAlerts: fraudAlerts.status === 'fulfilled' ? fraudAlerts.value : [],
        analytics: analytics.status === 'fulfilled' ? analytics.value : null,
        agents: agents.status === 'fulfilled' ? agents.value : null,
        wsStatus: wsStatus.status === 'fulfilled' ? wsStatus.value : null
      });

      console.log('✅ Dashboard data loaded successfully');
    } catch (err) {
      console.error('❌ Failed to load dashboard data:', err);
      setError('Failed to load dashboard data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const refreshData = async () => {
    try {
      const [transactions, fraudAlerts, analytics] = await Promise.all([
        FinSentinelAPI.getTransactions(20),
        FinSentinelAPI.getFraudAlerts(),
        FinSentinelAPI.getAnalyticsSummary()
      ]);
      
      setDashboardData(prev => ({
        ...prev,
        transactions,
        fraudAlerts,
        analytics
      }));
    } catch (err) {
      console.error('❌ Failed to refresh data:', err);
    }
  };

  const refreshTransactionData = async () => {
    try {
      const [transactions, fraudAlerts] = await Promise.all([
        FinSentinelAPI.getTransactions(20),
        FinSentinelAPI.getFraudAlerts()
      ]);
      
      setDashboardData(prev => ({
        ...prev,
        transactions,
        fraudAlerts
      }));
    } catch (err) {
      console.error('❌ Failed to refresh transaction data:', err);
    }
  };

  const simulateTransaction = async () => {
    if (simulating) return; // Prevent double-clicks
    
    try {
      setSimulating(true);
      console.log('🎯 Simulating transaction...');
      setError(null); // Clear any previous errors
      
      const result = await FinSentinelAPI.simulateTransaction();
      console.log('✅ Transaction simulated:', result);
      
      // Show success message with correct data structure
      if (result && result.transaction) {
        const tx = result.transaction;
        setError(`✅ Transaction simulated! ID: ${tx.id}, Merchant: ${tx.merchant_name}, Amount: $${Math.abs(tx.amount || 0).toFixed(2)}, Fraud Score: ${(tx.fraud_score || 0).toFixed(2)}`);
      } else if (result && result.success) {
        setError(`✅ ${result.message || 'Transaction simulated successfully!'}`);
      } else {
        setError('✅ Transaction created successfully!');
      }
      
      // Refresh data immediately to show new transaction
      await refreshTransactionData();
      
      // Clear success message after 4 seconds
      setTimeout(() => {
        setError(null);
      }, 4000);
    } catch (err) {
      console.error('❌ Transaction simulation failed:', err);
      setError('❌ Transaction simulation failed: ' + err.message);
    } finally {
      setSimulating(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ ml: 2 }}>Loading FinSentinel Dashboard...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={loadDashboardData}>
            Retry
          </Button>
        }>
          {error}
        </Alert>
      </Box>
    );
  }

  const { health, accounts, transactions, fraudAlerts, analytics, agents, wsStatus } = dashboardData;

  return (
    <Box p={3}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          🎯 FinSentinel AI Comprehensive Dashboard
        </Typography>
        <Box>
          <Chip 
            label={wsConnected ? 'Real-time Connected' : 'Real-time Disconnected'}
            color={wsConnected ? 'success' : 'error'}
            icon={wsConnected ? <CheckCircleIcon /> : <ErrorIcon />}
            sx={{ mr: 2 }}
          />
          <Button 
            variant="contained" 
            color="primary" 
            onClick={simulateTransaction}
            disabled={simulating}
            startIcon={simulating ? <CircularProgress size={20} /> : <TransactionIcon />}
          >
            {simulating ? 'Simulating...' : 'Simulate Transaction'}
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* System Health Overview */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <SpeedIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">System Health</Typography>
              </Box>
              {health ? (
                <Box>
                  <Chip 
                    label={health.status || 'Unknown'} 
                    color={health.status === 'healthy' ? 'success' : 'error'} 
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="body2" color="text.secondary">
                    API: {health.api_status || 'Unknown'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Plaid: {health.plaid_configured ? 'Configured' : 'Not Configured'}
                  </Typography>
                </Box>
              ) : (
                <Typography color="error">Health data unavailable</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Analytics Summary */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <AnalyticsIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Analytics Summary</Typography>
              </Box>
              {analytics ? (
                <Box>
                  <Typography variant="h4" color="primary">
                    {analytics.total_transactions || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Transactions
                  </Typography>
                  <Typography variant="h5" color="error" sx={{ mt: 1 }}>
                    {analytics.fraud_alerts || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Fraud Alerts
                  </Typography>
                  <Typography variant="h5" color="success.main" sx={{ mt: 1 }}>
                    {analytics.ml_model_accuracy || 0}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    ML Model Accuracy
                  </Typography>
                </Box>
              ) : (
                <Typography color="error">Analytics data unavailable</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Agent Status */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <ShieldIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">AI Agents Status</Typography>
              </Box>
              {agents ? (
                <Box>
                  {Object.entries(agents).map(([agentName, status]) => (
                    <Box key={agentName} display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                      <Typography variant="body2">{agentName}</Typography>
                      <Chip 
                        label={status ? 'Active' : 'Inactive'} 
                        color={status ? 'success' : 'default'}
                        size="small"
                      />
                    </Box>
                  ))}
                </Box>
              ) : (
                <Typography color="error">Agent data unavailable</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Accounts Overview */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <AccountBalanceIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Accounts ({accounts.length})</Typography>
              </Box>
              {accounts.length > 0 ? (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Account ID</TableCell>
                        <TableCell>Name</TableCell>
                        <TableCell>Type</TableCell>
                        <TableCell align="right">Balance</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {accounts.slice(0, 5).map((account) => (
                        <TableRow key={account.id || account.account_id}>
                          <TableCell>{account.id || account.account_id}</TableCell>
                          <TableCell>{account.name || 'Unknown'}</TableCell>
                          <TableCell>{account.type || 'Unknown'}</TableCell>
                          <TableCell align="right">
                            ${account.balance?.toFixed(2) || '0.00'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography color="text.secondary">No accounts found</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Fraud Alerts */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <WarningIcon color="error" sx={{ mr: 1 }} />
                <Typography variant="h6">Recent Fraud Alerts ({fraudAlerts.length})</Typography>
              </Box>
              {fraudAlerts.length > 0 ? (
                <List dense>
                  {fraudAlerts.slice(0, 5).map((alert, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <SecurityIcon color="error" />
                      </ListItemIcon>
                      <ListItemText
                        primary={alert.message || alert.description || 'Fraud detected'}
                        secondary={`Risk Score: ${alert.risk_score || alert.score || 'Unknown'} | ${alert.timestamp || alert.created_at || 'Unknown time'}`}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography color="text.secondary">No fraud alerts</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Transactions */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <TrendingUpIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Recent Transactions ({transactions.length})</Typography>
              </Box>
              {transactions.length > 0 ? (
                <TableContainer component={Paper} variant="outlined">
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>ID</TableCell>
                        <TableCell>Account</TableCell>
                        <TableCell>Amount</TableCell>
                        <TableCell>Description</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell>Timestamp</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {transactions.slice(0, 10).map((transaction) => (
                        <TableRow key={transaction.id || transaction.transaction_id}>
                          <TableCell>{transaction.id || transaction.transaction_id}</TableCell>
                          <TableCell>{transaction.account_id || 'Unknown'}</TableCell>
                          <TableCell>
                            <Typography 
                              color={transaction.amount > 0 ? 'success.main' : 'error.main'}
                            >
                              ${Math.abs(transaction.amount || 0).toFixed(2)}
                            </Typography>
                          </TableCell>
                          <TableCell>{transaction.description || transaction.merchant_name || 'Unknown'}</TableCell>
                          <TableCell>
                            <Chip 
                              label={transaction.status || 'processed'} 
                              color={transaction.is_fraud ? 'error' : 'success'}
                              size="small"
                            />
                          </TableCell>
                          <TableCell>{transaction.timestamp || transaction.date || 'Unknown'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography color="text.secondary">No transactions found</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Real-time Updates */}
        {realtimeUpdates.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  🔴 Real-time Updates ({realtimeUpdates.length})
                </Typography>
                <List dense>
                  {realtimeUpdates.slice(-5).reverse().map((update, index) => (
                    <ListItem key={index}>
                      <ListItemText
                        primary={JSON.stringify(update, null, 2)}
                        secondary={update.timestamp?.toLocaleTimeString()}
                      />
                    </ListItem>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default ComprehensiveDashboard;