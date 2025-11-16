import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  List,
  ListItem,
  ListItemText,
  Avatar,
  Badge,
  LinearProgress,
  Paper,
  IconButton,
  Alert,
  Divider,
  Button,
  CircularProgress
} from '@mui/material';
import {
  Security as SecurityIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Block as BlockIcon,
  TrendingUp as TrendingUpIcon,
  Visibility as VisibilityIcon,
  NotificationsActive as NotificationsIcon,
  Shield as ShieldIcon,
  Analytics as AnalyticsIcon,
  Timeline as TimelineIcon,
  MonetizationOn as MoneyIcon,
  AccessTime as TimeIcon,
  Store as StoreIcon
} from '@mui/icons-material';
import { FinSentinelAPI } from '../services/api';

const FraudMonitoring = () => {
  const [fraudData, setFraudData] = useState({
    alerts: [],
    recentTransactions: [],
    riskStats: null,
    systemStatus: null
  });
  const [loading, setLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    loadFraudData();

    // WebSocket for real-time fraud alerts
    const wsCleanup = FinSentinelAPI.connectAlertsWebSocket(
      (data) => {
        console.log('🚨 New fraud alert:', data);
        if (data.type === 'fraud_alert') {
          setFraudData(prev => ({
            ...prev,
            alerts: [data.alert, ...prev.alerts.slice(0, 19)]
          }));
        }
      },
      (connected) => setWsConnected(connected)
    );

    const interval = setInterval(loadFraudData, 30000);

    return () => {
      if (wsCleanup) wsCleanup();
      clearInterval(interval);
    };
  }, []);

  const loadFraudData = async () => {
    try {
      const [alerts, transactions, analytics, health] = await Promise.allSettled([
        FinSentinelAPI.getFraudAlerts(),
        FinSentinelAPI.getTransactions(20),
        FinSentinelAPI.getAnalyticsSummary(),
        FinSentinelAPI.getHealth()
      ]);

      setFraudData({
        alerts: alerts.status === 'fulfilled' ? alerts.value : [],
        recentTransactions: transactions.status === 'fulfilled' ? transactions.value : [],
        riskStats: analytics.status === 'fulfilled' ? analytics.value : null,
        systemStatus: health.status === 'fulfilled' ? health.value : null
      });
    } catch (err) {
      console.error('Failed to load fraud data:', err);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (score) => {
    if (score >= 0.8) return 'error';
    if (score >= 0.6) return 'warning';
    if (score >= 0.4) return 'info';
    return 'success';
  };

  const getRiskLabel = (score) => {
    if (score >= 0.8) return 'CRITICAL';
    if (score >= 0.6) return 'HIGH';
    if (score >= 0.4) return 'MEDIUM';
    return 'LOW';
  };

  const getSeverityIcon = (severity) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
      case 'HIGH':
        return <ErrorIcon color="error" />;
      case 'MEDIUM':
        return <WarningIcon color="warning" />;
      default:
        return <CheckCircleIcon color="success" />;
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <CircularProgress size={60} />
        <Typography variant="h6" sx={{ ml: 2 }}>Loading Fraud Monitoring...</Typography>
      </Box>
    );
  }

  const alerts = Array.isArray(fraudData.alerts) ? fraudData.alerts : [];
  const transactions = Array.isArray(fraudData.recentTransactions) ? fraudData.recentTransactions : [];

  const highRiskAlerts = alerts.filter(a => 
    (a.severity === 'HIGH' || a.severity === 'CRITICAL') && !a.is_resolved
  );

  const recentHighRiskTransactions = transactions.filter(t => 
    t.fraud_score >= 0.6
  );

  return (
    <Box sx={{ p: 3, bgcolor: '#f5f7fa', minHeight: '100vh' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center">
            <ShieldIcon sx={{ fontSize: 40, color: '#1976d2', mr: 2 }} />
            <Box>
              <Typography variant="h4" fontWeight="bold" color="primary">
                Fraud Monitoring Center
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Real-time fraud detection and security monitoring
              </Typography>
            </Box>
          </Box>
          <Box display="flex" alignItems="center" gap={2}>
            <Chip 
              icon={wsConnected ? <NotificationsIcon /> : <BlockIcon />}
              label={wsConnected ? 'Live Monitoring' : 'Offline'}
              color={wsConnected ? 'success' : 'error'}
              variant="outlined"
            />
            <Chip 
              icon={<AnalyticsIcon />}
              label={`${alerts.length} Total Alerts`}
              color="primary"
              variant="outlined"
            />
          </Box>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Risk Overview Cards */}
        <Grid item xs={12} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9, mb: 1 }}>
                    Critical Alerts
                  </Typography>
                  <Typography variant="h3" fontWeight="bold">
                    {alerts.filter(a => a.severity === 'CRITICAL' && !a.is_resolved).length}
                  </Typography>
                </Box>
                <ErrorIcon sx={{ fontSize: 50, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', color: 'white' }}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9, mb: 1 }}>
                    High Risk Alerts
                  </Typography>
                  <Typography variant="h3" fontWeight="bold">
                    {highRiskAlerts.length}
                  </Typography>
                </Box>
                <WarningIcon sx={{ fontSize: 50, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', color: 'white' }}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9, mb: 1 }}>
                    Blocked Transactions
                  </Typography>
                  <Typography variant="h3" fontWeight="bold">
                    {alerts.filter(a => a.status === 'blocked').length}
                  </Typography>
                </Box>
                <BlockIcon sx={{ fontSize: 50, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={3}>
          <Card sx={{ background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', color: 'white' }}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9, mb: 1 }}>
                    Prevention Rate
                  </Typography>
                  <Typography variant="h3" fontWeight="bold">
                    {fraudData.riskStats?.fraud_prevention_rate 
                      ? `${(fraudData.riskStats.fraud_prevention_rate * 100).toFixed(0)}%`
                      : '95%'}
                  </Typography>
                </Box>
                <SecurityIcon sx={{ fontSize: 50, opacity: 0.3 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Active Alerts */}
        <Grid item xs={12} lg={8}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <WarningIcon color="error" sx={{ mr: 1 }} />
                <Typography variant="h6" fontWeight="bold">
                  Active Fraud Alerts
                </Typography>
                <Badge badgeContent={highRiskAlerts.length} color="error" sx={{ ml: 2 }} />
              </Box>
              <Divider sx={{ mb: 2 }} />
              
              {alerts.length === 0 ? (
                <Box textAlign="center" py={4}>
                  <CheckCircleIcon sx={{ fontSize: 60, color: '#43e97b', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    No Active Alerts
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    All transactions are secure
                  </Typography>
                </Box>
              ) : (
                <List sx={{ maxHeight: 500, overflow: 'auto' }}>
                  {alerts.slice(0, 10).map((alert, index) => (
                    <React.Fragment key={alert.id || index}>
                      <ListItem
                        sx={{
                          bgcolor: alert.is_resolved ? '#f5f5f5' : 'white',
                          borderLeft: `4px solid ${
                            alert.severity === 'CRITICAL' ? '#d32f2f' :
                            alert.severity === 'HIGH' ? '#f57c00' :
                            alert.severity === 'MEDIUM' ? '#fbc02d' : '#388e3c'
                          }`,
                          mb: 1,
                          borderRadius: 1,
                          '&:hover': { bgcolor: '#fafafa' }
                        }}
                      >
                        <Avatar sx={{ 
                          mr: 2, 
                          bgcolor: alert.severity === 'CRITICAL' ? '#d32f2f' :
                                   alert.severity === 'HIGH' ? '#f57c00' : '#fbc02d'
                        }}>
                          {getSeverityIcon(alert.severity)}
                        </Avatar>
                        <ListItemText
                          primary={
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="subtitle1" fontWeight="bold">
                                {alert.alert_type || 'Fraud Detection'}
                              </Typography>
                              <Chip 
                                label={alert.severity || 'MEDIUM'} 
                                size="small"
                                color={
                                  alert.severity === 'CRITICAL' ? 'error' :
                                  alert.severity === 'HIGH' ? 'warning' : 'info'
                                }
                              />
                              {alert.is_resolved && (
                                <Chip label="Resolved" size="small" color="success" variant="outlined" />
                              )}
                            </Box>
                          }
                          secondary={
                            <Box mt={1}>
                              <Typography variant="body2" color="text.secondary">
                                {alert.message || 'Suspicious transaction detected'}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" display="block">
                                Transaction ID: {alert.transaction_id}
                              </Typography>
                              {alert.client_ip && (
                                <Typography variant="caption" color="error.main" display="block" fontWeight="bold">
                                  🌐 Device IP: {alert.client_ip}
                                </Typography>
                              )}
                            </Box>
                          }
                        />
                        <IconButton 
                          size="small"
                        >
                          <VisibilityIcon />
                        </IconButton>
                      </ListItem>
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Risk Analytics */}
        <Grid item xs={12} lg={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <TimelineIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6" fontWeight="bold">
                  Risk Analytics
                </Typography>
              </Box>
              <Divider sx={{ mb: 3 }} />

              <Box mb={3}>
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Overall Risk Level
                </Typography>
                <LinearProgress 
                  variant="determinate" 
                  value={75} 
                  sx={{ 
                    height: 10, 
                    borderRadius: 5,
                    bgcolor: '#e0e0e0',
                    '& .MuiLinearProgress-bar': {
                      background: 'linear-gradient(90deg, #43e97b 0%, #fbc02d 50%, #f57c00 100%)'
                    }
                  }} 
                />
                <Box display="flex" justifyContent="space-between" mt={1}>
                  <Typography variant="caption" color="success.main">Low</Typography>
                  <Typography variant="caption" color="warning.main">Medium</Typography>
                  <Typography variant="caption" color="error.main">High</Typography>
                </Box>
              </Box>

              <Box mb={3}>
                <Typography variant="body2" color="text.secondary" mb={2}>
                  Risk Distribution
                </Typography>
                {[
                  { label: 'Critical Risk', value: alerts.filter(a => a.severity === 'CRITICAL').length, color: '#d32f2f' },
                  { label: 'High Risk', value: alerts.filter(a => a.severity === 'HIGH').length, color: '#f57c00' },
                  { label: 'Medium Risk', value: alerts.filter(a => a.severity === 'MEDIUM').length, color: '#fbc02d' },
                  { label: 'Low Risk', value: alerts.filter(a => a.severity === 'LOW').length, color: '#388e3c' }
                ].map((item, i) => (
                  <Box key={i} mb={2}>
                    <Box display="flex" justifyContent="space-between" mb={0.5}>
                      <Typography variant="body2">{item.label}</Typography>
                      <Typography variant="body2" fontWeight="bold">{item.value}</Typography>
                    </Box>
                    <LinearProgress 
                      variant="determinate" 
                      value={(item.value / Math.max(alerts.length, 1)) * 100} 
                      sx={{ 
                        height: 6, 
                        borderRadius: 3,
                        bgcolor: '#e0e0e0',
                        '& .MuiLinearProgress-bar': { bgcolor: item.color }
                      }} 
                    />
                  </Box>
                ))}
              </Box>

              <Alert severity="info" icon={<TrendingUpIcon />}>
                <Typography variant="body2">
                  <strong>24h Trend:</strong> Fraud attempts decreased by 12%
                </Typography>
              </Alert>
            </CardContent>
          </Card>
        </Grid>

        {/* High Risk Transactions */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <SecurityIcon color="error" sx={{ mr: 1 }} />
                <Typography variant="h6" fontWeight="bold">
                  High Risk Transactions
                </Typography>
                <Chip 
                  label={`${recentHighRiskTransactions.length} Flagged`} 
                  size="small" 
                  color="error" 
                  sx={{ ml: 2 }} 
                />
              </Box>
              <Divider sx={{ mb: 2 }} />

              {recentHighRiskTransactions.length === 0 ? (
                <Box textAlign="center" py={4}>
                  <CheckCircleIcon sx={{ fontSize: 60, color: '#43e97b', mb: 2 }} />
                  <Typography variant="h6" color="text.secondary">
                    No High Risk Transactions
                  </Typography>
                </Box>
              ) : (
                <Grid container spacing={2}>
                  {recentHighRiskTransactions.slice(0, 6).map((transaction, index) => (
                    <Grid item xs={12} md={6} lg={4} key={transaction.id || index}>
                      <Paper 
                        elevation={2} 
                        sx={{ 
                          p: 2, 
                          borderLeft: `4px solid ${getRiskColor(transaction.fraud_score) === 'error' ? '#d32f2f' : '#f57c00'}`,
                          '&:hover': { elevation: 4 }
                        }}
                      >
                        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                          <Chip 
                            label={getRiskLabel(transaction.fraud_score)} 
                            size="small"
                            color={getRiskColor(transaction.fraud_score)}
                          />
                          <Typography variant="h6" fontWeight="bold" color={getRiskColor(transaction.fraud_score) + '.main'}>
                            {(transaction.fraud_score * 100).toFixed(0)}%
                          </Typography>
                        </Box>

                        <Box display="flex" alignItems="center" mb={1}>
                          <MoneyIcon sx={{ fontSize: 18, mr: 1, color: 'text.secondary' }} />
                          <Typography variant="body1" fontWeight="bold">
                            ${Math.abs(transaction.amount || 0).toFixed(2)}
                          </Typography>
                        </Box>

                        <Box display="flex" alignItems="center" mb={1}>
                          <StoreIcon sx={{ fontSize: 18, mr: 1, color: 'text.secondary' }} />
                          <Typography variant="body2" noWrap>
                            {transaction.merchant_name || 'Unknown Merchant'}
                          </Typography>
                        </Box>

                        <Box display="flex" alignItems="center" mb={1}>
                          <TimeIcon sx={{ fontSize: 18, mr: 1, color: 'text.secondary' }} />
                          <Typography variant="caption" color="text.secondary">
                            {new Date(transaction.date).toLocaleString()}
                          </Typography>
                        </Box>

                        {transaction.risk_factors && transaction.risk_factors.length > 0 && (
                          <Box mt={2}>
                            <Typography variant="caption" color="text.secondary" fontWeight="bold">
                              Risk Factors:
                            </Typography>
                            <Box display="flex" flexWrap="wrap" gap={0.5} mt={0.5}>
                              {transaction.risk_factors.slice(0, 3).map((factor, i) => (
                                <Chip 
                                  key={i}
                                  label={factor} 
                                  size="small" 
                                  variant="outlined"
                                  color="warning"
                                />
                              ))}
                            </Box>
                          </Box>
                        )}

                        <Box mt={2}>
                          <Button 
                            fullWidth 
                            variant="outlined" 
                            size="small"
                            startIcon={<VisibilityIcon />}
                          >
                            Review Details
                          </Button>
                        </Box>
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default FraudMonitoring;