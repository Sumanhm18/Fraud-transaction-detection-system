import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  CircularProgress,
  Grid,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  AccountBalance as BankIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Link as LinkIcon,
  Security as SecurityIcon,
  Sync as SyncIcon,
  Timeline as TimelineIcon,
  TrendingUp as TrendingUpIcon
} from '@mui/icons-material';
import { usePlaidLink } from 'react-plaid-link';
import FinSentinelAPI from '../services/api.js';

const PlaidIntegration = () => {
  const [accounts, setAccounts] = useState([]);
  const [linkToken, setLinkToken] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [syncProgress, setSyncProgress] = useState(0);
  const [showLinkDialog, setShowLinkDialog] = useState(false);
  const [plaidStats, setPlaidStats] = useState({
    totalAccounts: 0,
    totalTransactions: 0,
    lastSync: null,
    syncStatus: 'idle'
  });

  // Initialize Plaid Link
  const { open, ready } = usePlaidLink({
    token: linkToken,
    onSuccess: async (public_token, metadata) => {
      try {
        console.log('🔗 Plaid Link successful:', metadata);
        setError(null);
        
        // Exchange public token for access token
        const result = await FinSentinelAPI.exchangePublicToken(public_token, metadata);
        console.log('✅ Token exchange successful:', result);
        
        setAccessToken(result.access_token);
        setConnectionStatus('connected');
        setShowLinkDialog(false);
        
        // Start monitoring sync progress
        monitorSyncProgress();
        
        // Refresh data
        await loadPlaidData();
        
        setError('✅ Bank account connected successfully! Syncing transactions...');
        setTimeout(() => setError(null), 5000);
        
      } catch (err) {
        console.error('❌ Token exchange failed:', err);
        setError('Failed to connect bank account: ' + err.message);
      }
    },
    onExit: (err, metadata) => {
      if (err) {
        console.error('Plaid Link error:', err);
        setError('Bank connection cancelled or failed');
      }
      setShowLinkDialog(false);
    },
    onEvent: (eventName, metadata) => {
      console.log('Plaid event:', eventName, metadata);
    }
  });

  // Debug Plaid Link state and auto-open when ready
  useEffect(() => {
    console.log('🔍 Plaid Link state - ready:', ready, 'linkToken:', linkToken ? 'exists' : 'null');
    
    // Auto-open Plaid Link when it becomes ready with a token
    if (ready && linkToken && connectionStatus === 'disconnected' && !loading) {
      console.log('🚀 Plaid Link is ready! Opening automatically...');
      setTimeout(() => {
        if (open) {
          open();
        }
      }, 100);
    }
  }, [ready, linkToken, connectionStatus, loading, open]);

  useEffect(() => {
    initializePlaid();
  }, []);



  const initializePlaid = async () => {
    try {
      setLoading(true);
      console.log('🔄 Initializing Plaid integration...');
      
      // Check if user already has Plaid connection
      const status = await FinSentinelAPI.getPlaidConnectionStatus('demo_user');
      console.log('📊 Plaid connection status:', status);
      
      if (status.connected) {
        console.log('✅ User already connected to Plaid');
        setAccessToken(status.access_token);
        setConnectionStatus('connected');
        await loadPlaidData();
      } else {
        console.log('❌ User not connected to Plaid');
        setConnectionStatus('disconnected');
      }
      
    } catch (err) {
      console.error('❌ Plaid initialization failed:', err);
      setError('Failed to initialize Plaid integration: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const createLinkToken = async () => {
    try {
      setError(null);
      setLoading(true);
      console.log('🔗 Creating Plaid link token...');
      
      const result = await FinSentinelAPI.createLinkToken('demo_user');
      console.log('✅ Link token created:', result);
      
      setLinkToken(result.link_token);
      return result.link_token;
      
    } catch (err) {
      console.error('❌ Failed to create link token:', err);
      setError('Failed to initialize bank connection: ' + err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleConnectBank = async () => {
    try {
      console.log('🖱️ Connect Bank Account button clicked');
      const token = await createLinkToken();
      
      if (token) {
        console.log('🎯 Link token ready, waiting for Plaid Link to initialize...');
        // The usePlaidLink hook will automatically become ready when linkToken is set
      }
    } catch (err) {
      console.error('❌ Failed to initiate bank connection:', err);
    }
  };

  const loadPlaidData = async () => {
    if (!accessToken) return;
    
    try {
      setLoading(true);
      
      // Load accounts and recent transactions in parallel
      const [accountsResult, transactionsResult] = await Promise.all([
        FinSentinelAPI.getPlaidAccounts('demo_user'),
        FinSentinelAPI.getPlaidTransactions('demo_user', 30)
      ]);
      
      setAccounts(accountsResult.accounts || []);
      setTransactions(transactionsResult.transactions || []);
      
      setPlaidStats({
        totalAccounts: accountsResult.accounts?.length || 0,
        totalTransactions: transactionsResult.total_transactions || 0,
        lastSync: new Date().toISOString(),
        syncStatus: 'completed'
      });
      
    } catch (err) {
      console.error('Failed to load Plaid data:', err);
      setError('Failed to load bank data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const monitorSyncProgress = () => {
    setSyncProgress(0);
    setPlaidStats(prev => ({ ...prev, syncStatus: 'syncing' }));
    
    // Simulate sync progress
    const interval = setInterval(() => {
      setSyncProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setPlaidStats(prevStats => ({ ...prevStats, syncStatus: 'completed' }));
          return 100;
        }
        return prev + 10;
      });
    }, 500);
  };

  const refreshTransactions = async () => {
    if (!accessToken) return;
    
    try {
      setLoading(true);
      setPlaidStats(prev => ({ ...prev, syncStatus: 'syncing' }));
      
      const result = await FinSentinelAPI.getPlaidTransactions({
        access_token: accessToken,
        count: 100
      });
      
      setTransactions(result.transactions || []);
      setPlaidStats(prev => ({
        ...prev,
        totalTransactions: result.total_transactions || 0,
        lastSync: new Date().toISOString(),
        syncStatus: 'completed'
      }));
      
      setError('✅ Transactions refreshed successfully!');
      setTimeout(() => setError(null), 3000);
      
    } catch (err) {
      console.error('Failed to refresh transactions:', err);
      setError('Failed to refresh transactions: ' + err.message);
      setPlaidStats(prev => ({ ...prev, syncStatus: 'error' }));
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(Math.abs(amount));
  };

  const getAccountTypeIcon = (type) => {
    const icons = {
      'checking': <BankIcon color="primary" />,
      'savings': <SecurityIcon color="success" />,
      'credit': <TimelineIcon color="warning" />,
      'investment': <TrendingUpIcon color="info" />
    };
    return icons[type] || <BankIcon />;
  };

  const getConnectionStatusColor = (status) => {
    const colors = {
      'connected': 'success',
      'disconnected': 'error',
      'connecting': 'warning'
    };
    return colors[status] || 'default';
  };

  if (loading && !accounts.length) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="h6" sx={{ ml: 2 }}>
          Loading Plaid Integration...
        </Typography>
      </Box>
    );
  }

  return (
    <Box p={3}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          🏦 Plaid Banking Integration
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          <Chip 
            label={connectionStatus === 'connected' ? 'Connected' : 'Not Connected'}
            color={getConnectionStatusColor(connectionStatus)}
            icon={connectionStatus === 'connected' ? <CheckIcon /> : <ErrorIcon />}
          />
          {connectionStatus === 'connected' && (
            <Button
              variant="outlined"
              onClick={refreshTransactions}
              startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
              disabled={loading}
            >
              Refresh Data
            </Button>
          )}
        </Box>
      </Box>

      {/* Error Display */}
      {error && (
        <Alert 
          severity={error.includes('✅') ? 'success' : 'error'} 
          sx={{ mb: 3 }}
          onClose={() => setError(null)}
        >
          {error}
        </Alert>
      )}

      {/* Connection Status */}
      {connectionStatus === 'disconnected' && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box textAlign="center" py={4}>
              <BankIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h5" gutterBottom>
                Connect Your Bank Account
              </Typography>
              <Typography variant="body1" color="text.secondary" mb={3}>
                Securely connect your bank account to enable real-time transaction monitoring and fraud detection.
              </Typography>
              <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleConnectBank}
                  startIcon={loading ? <CircularProgress size={20} /> : <LinkIcon />}
                  disabled={loading}
                >
                  {loading ? 'Creating Link Token...' : 'Connect Bank Account'}
                </Button>
                
                {linkToken && ready && (
                  <Button
                    variant="outlined"
                    onClick={() => {
                      console.log('🔘 Manual Plaid Link open triggered');
                      if (open) open();
                    }}
                    startIcon={<SecurityIcon />}
                    disabled={!open}
                  >
                    Open Bank Connection (Manual)
                  </Button>
                )}
                
                {linkToken && !ready && (
                  <Typography variant="body2" color="warning.main">
                    ⏳ Preparing secure connection...
                  </Typography>
                )}
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Plaid Statistics */}
      {connectionStatus === 'connected' && (
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="primary">
                  {plaidStats.totalAccounts}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Connected Accounts
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="success.main">
                  {plaidStats.totalTransactions.toLocaleString()}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Transactions
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="info.main">
                  {plaidStats.syncStatus === 'syncing' ? 'Syncing...' : 'Up to Date'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Sync Status
                </Typography>
                {plaidStats.syncStatus === 'syncing' && (
                  <LinearProgress variant="determinate" value={syncProgress} sx={{ mt: 1 }} />
                )}
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" color="text.primary">
                  {plaidStats.lastSync ? new Date(plaidStats.lastSync).toLocaleDateString() : 'Never'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Last Sync
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Connected Accounts */}
      {accounts.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Connected Accounts ({accounts.length})
            </Typography>
            <List>
              {accounts.map((account, index) => (
                <React.Fragment key={account.account_id}>
                  <ListItem>
                    <ListItemIcon>
                      {getAccountTypeIcon(account.subtype || account.type)}
                    </ListItemIcon>
                    <ListItemText
                      primary={account.name}
                      secondary={`${account.type} • ${account.subtype || 'N/A'} • ${account.mask || ''}`}
                    />
                    <Typography variant="h6" color="primary">
                      {formatCurrency(account.balances?.current || 0)}
                    </Typography>
                  </ListItem>
                  {index < accounts.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Recent Transactions */}
      {transactions.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Recent Plaid Transactions ({transactions.length})
            </Typography>
            <List>
              {transactions.slice(0, 10).map((transaction, index) => (
                <React.Fragment key={transaction.transaction_id}>
                  <ListItem>
                    <ListItemText
                      primary={transaction.merchant_name || transaction.name}
                      secondary={`${new Date(transaction.date).toLocaleDateString()} • ${transaction.category?.join(', ') || 'Uncategorized'}`}
                    />
                    <Box textAlign="right">
                      <Typography 
                        variant="body1" 
                        color={transaction.amount > 0 ? 'error' : 'success'}
                        fontWeight="medium"
                      >
                        {transaction.amount > 0 ? '-' : '+'}{formatCurrency(Math.abs(transaction.amount))}
                      </Typography>
                      {transaction.fraud_score > 0.5 && (
                        <Chip 
                          size="small" 
                          label="High Risk" 
                          color="error" 
                          sx={{ ml: 1 }} 
                        />
                      )}
                    </Box>
                  </ListItem>
                  {index < Math.min(transactions.length, 10) - 1 && <Divider />}
                </React.Fragment>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Plaid Link Dialog */}
      <Dialog open={showLinkDialog} onClose={() => setShowLinkDialog(false)}>
        <DialogTitle>Connect Your Bank Account</DialogTitle>
        <DialogContent>
          <Typography variant="body1" mb={2}>
            You'll be redirected to Plaid's secure interface to connect your bank account.
            FinSentinel AI will use this connection to:
          </Typography>
          <List dense>
            <ListItem>
              <ListItemIcon><CheckIcon color="success" /></ListItemIcon>
              <ListItemText primary="Monitor transactions in real-time" />
            </ListItem>
            <ListItem>
              <ListItemIcon><CheckIcon color="success" /></ListItemIcon>
              <ListItemText primary="Detect fraudulent activity" />
            </ListItem>
            <ListItem>
              <ListItemIcon><CheckIcon color="success" /></ListItemIcon>
              <ListItemText primary="Provide account insights and analytics" />
            </ListItem>
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowLinkDialog(false)}>
            Cancel
          </Button>
          <Button 
            onClick={open} 
            variant="contained" 
            disabled={!ready}
            startIcon={<SecurityIcon />}
          >
            Connect Securely with Plaid
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PlaidIntegration;