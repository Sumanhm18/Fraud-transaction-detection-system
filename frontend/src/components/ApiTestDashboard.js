import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Box,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
  PlayArrow as PlayArrowIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { FinSentinelAPI } from '../services/api';

const ApiTestDashboard = () => {
  const [testResults, setTestResults] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [wsStatus, setWsStatus] = useState({
    transactions: false,
    alerts: false,
    general: false
  });
  const [realtimeData, setRealtimeData] = useState({
    transactions: [],
    alerts: [],
    general: []
  });
  const [wsConnections, setWsConnections] = useState({});

  useEffect(() => {
    // Initialize WebSocket connections
    const connections = {};
    
    // Transactions WebSocket
    connections.transactions = FinSentinelAPI.connectTransactionWebSocket(
      (data) => {
        setRealtimeData(prev => ({
          ...prev,
          transactions: [...prev.transactions.slice(-9), { ...data, timestamp: new Date() }]
        }));
      },
      (status) => setWsStatus(prev => ({ ...prev, transactions: status }))
    );

    // Alerts WebSocket
    connections.alerts = FinSentinelAPI.connectAlertsWebSocket(
      (data) => {
        setRealtimeData(prev => ({
          ...prev,
          alerts: [...prev.alerts.slice(-9), { ...data, timestamp: new Date() }]
        }));
      },
      (status) => setWsStatus(prev => ({ ...prev, alerts: status }))
    );

    // General WebSocket
    connections.general = FinSentinelAPI.connectGeneralWebSocket(
      (data) => {
        setRealtimeData(prev => ({
          ...prev,
          general: [...prev.general.slice(-9), { ...data, timestamp: new Date() }]
        }));
      },
      (status) => setWsStatus(prev => ({ ...prev, general: status }))
    );

    setWsConnections(connections);

    // Cleanup on unmount
    return () => {
      Object.values(connections).forEach(cleanup => cleanup && cleanup());
    };
  }, []);

  const runAllTests = async () => {
    setIsLoading(true);
    try {
      const results = await FinSentinelAPI.testAllEndpoints();
      setTestResults(results);
    } catch (error) {
      console.error('Failed to run tests:', error);
      setTestResults({ error: error.message });
    } finally {
      setIsLoading(false);
    }
  };

  const simulateTransaction = async () => {
    try {
      console.log('🎯 Starting transaction simulation...');
      const result = await FinSentinelAPI.simulateTransaction();
      console.log('✅ Transaction simulated successfully:', result);
      
      // Show success alert
      alert(`✅ Transaction Simulated!\n\nID: ${result.transaction_id || 'N/A'}\nAmount: ${result.amount || 'N/A'}\nMerchant: ${result.merchant_name || 'N/A'}\nFraud Score: ${result.fraud_score || 'N/A'}`);
      
      // Force refresh test results
      runAllTests();
    } catch (error) {
      console.error('❌ Simulation failed:', error);
      alert('❌ Transaction simulation failed: ' + error.message);
    }
  };

  const renderTestResult = (name, result) => {
    if (!result) return null;

    return (
      <Card key={name} sx={{ mb: 2 }}>
        <CardContent>
          <Box display="flex" alignItems="center" mb={1}>
            {result.success ? (
              <CheckCircleIcon color="success" sx={{ mr: 1 }} />
            ) : (
              <ErrorIcon color="error" sx={{ mr: 1 }} />
            )}
            <Typography variant="h6">{name}</Typography>
            <Chip 
              label={result.success ? 'PASS' : 'FAIL'} 
              color={result.success ? 'success' : 'error'}
              size="small"
              sx={{ ml: 'auto' }}
            />
          </Box>
          {result.error ? (
            <Alert severity="error" sx={{ mt: 1 }}>
              {result.error}
            </Alert>
          ) : (
            <Typography variant="body2" color="text.secondary">
              {typeof result.data === 'object' ? JSON.stringify(result.data, null, 2) : result.data}
            </Typography>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderWebSocketStatus = (type, status) => (
    <Box display="flex" alignItems="center" mb={1}>
      {status ? (
        <WifiIcon color="success" sx={{ mr: 1 }} />
      ) : (
        <WifiOffIcon color="error" sx={{ mr: 1 }} />
      )}
      <Typography variant="body2">
        {type.charAt(0).toUpperCase() + type.slice(1)}: {status ? 'Connected' : 'Disconnected'}
      </Typography>
    </Box>
  );

  const renderRealtimeData = (type, data) => (
    <Box mb={2}>
      <Typography variant="h6" gutterBottom>
        {type.charAt(0).toUpperCase() + type.slice(1)} Data ({data.length})
      </Typography>
      <List dense>
        {data.slice(-3).map((item, index) => (
          <ListItem key={index}>
            <ListItemText
              primary={typeof item === 'object' ? JSON.stringify(item, null, 2) : item}
              secondary={item.timestamp ? item.timestamp.toLocaleTimeString() : ''}
            />
          </ListItem>
        ))}
        {data.length === 0 && (
          <ListItem>
            <ListItemText primary="No data received yet" />
          </ListItem>
        )}
      </List>
    </Box>
  );

  return (
    <Box p={3}>
      <Typography variant="h4" gutterBottom>
        🔧 FinSentinel API Integration Test Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        {/* API Test Controls */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                API Endpoint Testing
              </Typography>
              <Box mb={2}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={isLoading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
                  onClick={runAllTests}
                  disabled={isLoading}
                  sx={{ mr: 2 }}
                >
                  {isLoading ? 'Testing...' : 'Test All Endpoints'}
                </Button>
                <Button
                  variant="outlined"
                  color="secondary"
                  startIcon={<RefreshIcon />}
                  onClick={simulateTransaction}
                >
                  Simulate Transaction
                </Button>
              </Box>
              
              {Object.keys(testResults).length > 0 && (
                <Box>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="h6" gutterBottom>
                    Test Results
                  </Typography>
                  {Object.entries(testResults).map(([name, result]) => renderTestResult(name, result))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* WebSocket Status */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                WebSocket Connections
              </Typography>
              {renderWebSocketStatus('transactions', wsStatus.transactions)}
              {renderWebSocketStatus('alerts', wsStatus.alerts)}
              {renderWebSocketStatus('general', wsStatus.general)}
              
              <Divider sx={{ my: 2 }} />
              
              {renderRealtimeData('transactions', realtimeData.transactions)}
              {renderRealtimeData('alerts', realtimeData.alerts)}
              {renderRealtimeData('general', realtimeData.general)}
            </CardContent>
          </Card>
        </Grid>

        {/* System Status */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h5" gutterBottom>
                System Integration Status
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Box textAlign="center">
                    <Typography variant="h6" color="primary">Backend API</Typography>
                    <Chip 
                      label="Ready" 
                      color="success" 
                      icon={<CheckCircleIcon />}
                    />
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box textAlign="center">
                    <Typography variant="h6" color="primary">WebSocket</Typography>
                    <Chip 
                      label={Object.values(wsStatus).some(s => s) ? 'Connected' : 'Disconnected'} 
                      color={Object.values(wsStatus).some(s => s) ? 'success' : 'error'}
                      icon={Object.values(wsStatus).some(s => s) ? <WifiIcon /> : <WifiOffIcon />}
                    />
                  </Box>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Box textAlign="center">
                    <Typography variant="h6" color="primary">Frontend</Typography>
                    <Chip 
                      label="Ready" 
                      color="success" 
                      icon={<CheckCircleIcon />}
                    />
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ApiTestDashboard;