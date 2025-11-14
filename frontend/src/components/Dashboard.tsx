import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  Chip,
  IconButton,
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Warning as WarningIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  AccountBalance as AccountBalanceIcon,
  Security as SecurityIcon,
  Assessment as AssessmentIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar } from 'recharts';

interface Transaction {
  id: string;
  account_id: string;
  amount: number;
  date: string;
  merchant_name: string;
  category: string[];
  fraud_score?: number;
  risk_factors?: string[];
}

interface FraudAlert {
  id: string;
  transaction_id: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  fraud_score: number;
  risk_factors: string[];
  status: 'PENDING' | 'REVIEWED' | 'RESOLVED';
  created_at: string;
}

interface Account {
  id: string;
  name: string;
  type: string;
  balance: number;
  available_balance: number;
  currency_code: string;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8'];

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [fraudAlerts, setFraudAlerts] = useState<FraudAlert[]>([]);
  const [analytics, setAnalytics] = useState<any>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    loadDashboardData();
    setupWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Load accounts
      const accountsRes = await fetch('/api/v1/accounts');
      const accountsData = await accountsRes.json();
      setAccounts(accountsData);

      // Load recent transactions
      const transactionsRes = await fetch('/api/v1/transactions?limit=50');
      const transactionsData = await transactionsRes.json();
      setTransactions(transactionsData);

      // Load fraud alerts
      const fraudRes = await fetch('/api/v1/fraud/alerts');
      const fraudData = await fraudRes.json();
      setFraudAlerts(fraudData);

      // Load analytics
      const analyticsRes = await fetch('/api/v1/analytics/summary');
      const analyticsData = await analyticsRes.json();
      setAnalytics(analyticsData);

    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const setupWebSocket = () => {
    const websocket = new WebSocket('ws://localhost:8000/ws/transactions');
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'new_transaction') {
        setTransactions(prev => [data.transaction, ...prev.slice(0, 49)]);
      } else if (data.type === 'fraud_alert') {
        setFraudAlerts(prev => [data.alert, ...prev]);
      }
    };

    websocket.onopen = () => {
      console.log('WebSocket connected');
    };

    websocket.onclose = () => {
      console.log('WebSocket disconnected');
      // Reconnect after 5 seconds
      setTimeout(setupWebSocket, 5000);
    };

    setWs(websocket);
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'LOW': return 'success';
      case 'MEDIUM': return 'warning';
      case 'HIGH': return 'error';
      case 'CRITICAL': return 'error';
      default: return 'default';
    }
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
        <CircularProgress size={60} />
      </Box>
    );
  }

  const totalBalance = accounts.reduce((sum, account) => sum + account.balance, 0);
  const highRiskAlerts = fraudAlerts.filter(alert => alert.risk_level === 'HIGH' || alert.risk_level === 'CRITICAL').length;
  const pendingAlerts = fraudAlerts.filter(alert => alert.status === 'PENDING').length;

  return (
    <Box p={3}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          FinSentinel AI Dashboard
        </Typography>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={loadDashboardData}
        >
          Refresh
        </Button>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Total Balance
                  </Typography>
                  <Typography variant="h5" component="div">
                    {formatCurrency(totalBalance)}
                  </Typography>
                </Box>
                <AccountBalanceIcon color="primary" fontSize="large" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Active Accounts
                  </Typography>
                  <Typography variant="h5" component="div">
                    {accounts.length}
                  </Typography>
                </Box>
                <AccountBalanceIcon color="success" fontSize="large" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    High Risk Alerts
                  </Typography>
                  <Typography variant="h5" component="div" color={highRiskAlerts > 0 ? 'error' : 'success'}>
                    {highRiskAlerts}
                  </Typography>
                </Box>
                <SecurityIcon color={highRiskAlerts > 0 ? 'error' : 'success'} fontSize="large" />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="textSecondary" gutterBottom>
                    Pending Reviews
                  </Typography>
                  <Typography variant="h5" component="div" color={pendingAlerts > 0 ? 'warning' : 'success'}>
                    {pendingAlerts}
                  </Typography>
                </Box>
                <AssessmentIcon color={pendingAlerts > 0 ? 'warning' : 'success'} fontSize="large" />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Transaction Volume (Last 7 Days)
              </Typography>
              {analytics?.transaction_volume && (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={analytics.transaction_volume}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <RechartsTooltip />
                    <Line type="monotone" dataKey="count" stroke="#8884d8" strokeWidth={2} />
                    <Line type="monotone" dataKey="amount" stroke="#82ca9d" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Spending by Category
              </Typography>
              {analytics?.category_breakdown && (
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={Object.entries(analytics.category_breakdown).map(([name, value]) => ({ name, value }))}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {Object.keys(analytics.category_breakdown).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Fraud Alerts */}
      {fraudAlerts.length > 0 && (
        <Card mb={4}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Recent Fraud Alerts
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Time</TableCell>
                    <TableCell>Risk Level</TableCell>
                    <TableCell>Fraud Score</TableCell>
                    <TableCell>Risk Factors</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {fraudAlerts.slice(0, 10).map((alert) => (
                    <TableRow key={alert.id}>
                      <TableCell>{formatDate(alert.created_at)}</TableCell>
                      <TableCell>
                        <Chip
                          label={alert.risk_level}
                          color={getRiskLevelColor(alert.risk_level) as any}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{(alert.fraud_score * 100).toFixed(1)}%</TableCell>
                      <TableCell>
                        <Box>
                          {alert.risk_factors.slice(0, 2).map((factor, idx) => (
                            <Chip key={idx} label={factor} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                          ))}
                          {alert.risk_factors.length > 2 && (
                            <Tooltip title={alert.risk_factors.slice(2).join(', ')}>
                              <Chip label={`+${alert.risk_factors.length - 2} more`} size="small" />
                            </Tooltip>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={alert.status}
                          color={alert.status === 'PENDING' ? 'warning' : 'success'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <IconButton size="small">
                          <InfoIcon />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Recent Transactions */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Transactions
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Merchant</TableCell>
                  <TableCell>Category</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell>Risk Score</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {transactions.slice(0, 20).map((transaction) => (
                  <TableRow key={transaction.id}>
                    <TableCell>{formatDate(transaction.date)}</TableCell>
                    <TableCell>{transaction.merchant_name || 'Unknown'}</TableCell>
                    <TableCell>
                      {transaction.category?.slice(0, 2).map((cat, idx) => (
                        <Chip key={idx} label={cat} size="small" sx={{ mr: 0.5 }} />
                      ))}
                    </TableCell>
                    <TableCell align="right">
                      <Box display="flex" alignItems="center" justifyContent="flex-end">
                        {transaction.amount > 0 ? (
                          <TrendingUpIcon color="success" fontSize="small" sx={{ mr: 1 }} />
                        ) : (
                          <TrendingDownIcon color="error" fontSize="small" sx={{ mr: 1 }} />
                        )}
                        {formatCurrency(Math.abs(transaction.amount))}
                      </Box>
                    </TableCell>
                    <TableCell>
                      {transaction.fraud_score && (
                        <Chip
                          label={`${(transaction.fraud_score * 100).toFixed(1)}%`}
                          color={transaction.fraud_score > 0.7 ? 'error' : transaction.fraud_score > 0.4 ? 'warning' : 'success'}
                          size="small"
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      <IconButton 
                        size="small"
                        onClick={() => setSelectedTransaction(transaction)}
                      >
                        <InfoIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Transaction Detail Dialog */}
      <Dialog
        open={!!selectedTransaction}
        onClose={() => setSelectedTransaction(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Transaction Details</DialogTitle>
        <DialogContent>
          {selectedTransaction && (
            <Box>
              <Typography variant="body1" gutterBottom>
                <strong>Merchant:</strong> {selectedTransaction.merchant_name || 'Unknown'}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Amount:</strong> {formatCurrency(selectedTransaction.amount)}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Date:</strong> {formatDate(selectedTransaction.date)}
              </Typography>
              <Typography variant="body1" gutterBottom>
                <strong>Categories:</strong> {selectedTransaction.category?.join(', ') || 'None'}
              </Typography>
              {selectedTransaction.fraud_score && (
                <Typography variant="body1" gutterBottom>
                  <strong>Fraud Score:</strong> {(selectedTransaction.fraud_score * 100).toFixed(1)}%
                </Typography>
              )}
              {selectedTransaction.risk_factors && selectedTransaction.risk_factors.length > 0 && (
                <Box>
                  <Typography variant="body1" gutterBottom>
                    <strong>Risk Factors:</strong>
                  </Typography>
                  {selectedTransaction.risk_factors.map((factor, idx) => (
                    <Chip key={idx} label={factor} size="small" sx={{ mr: 0.5, mb: 0.5 }} />
                  ))}
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSelectedTransaction(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}