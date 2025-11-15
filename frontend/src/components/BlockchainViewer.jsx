import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Link as LinkIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  FilterList as FilterIcon
} from '@mui/icons-material';

const API_BASE = 'http://localhost:8000/api/v1';

function BlockchainViewer() {
  const [transactions, setTransactions] = useState([]);
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [blockchainStatus, setBlockchainStatus] = useState(null);
  const [filterRiskLevel, setFilterRiskLevel] = useState('ALL');
  const [filterMinScore, setFilterMinScore] = useState('');
  const [stats, setStats] = useState({
    total: 0,
    high_risk: 0,
    medium_risk: 0,
    low_risk: 0,
    avg_fraud_score: 0
  });

  const fetchBlockchainStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/blockchain/status`);
      const data = await response.json();
      setBlockchainStatus(data);
    } catch (err) {
      console.error('Failed to fetch blockchain status:', err);
    }
  };

  const fetchTransactions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/blockchain/transactions/all`);
      const data = await response.json();
      
      if (data.success) {
        setTransactions(data.transactions || []);
        calculateStats(data.transactions || []);
      } else {
        setError('Failed to fetch blockchain transactions');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const calculateStats = (txns) => {
    const total = txns.length;
    const high_risk = txns.filter(t => t.risk_level === 'HIGH').length;
    const medium_risk = txns.filter(t => t.risk_level === 'MEDIUM').length;
    const low_risk = txns.filter(t => t.risk_level === 'LOW').length;
    const avg_fraud_score = total > 0 
      ? (txns.reduce((sum, t) => sum + (t.fraud_score || 0), 0) / total).toFixed(3)
      : 0;

    setStats({ total, high_risk, medium_risk, low_risk, avg_fraud_score });
  };

  useEffect(() => {
    fetchBlockchainStatus();
    fetchTransactions();
  }, []);

  useEffect(() => {
    let filtered = [...transactions];

    // Filter by risk level
    if (filterRiskLevel !== 'ALL') {
      filtered = filtered.filter(t => t.risk_level === filterRiskLevel);
    }

    // Filter by minimum fraud score
    if (filterMinScore !== '') {
      const minScore = parseFloat(filterMinScore);
      filtered = filtered.filter(t => (t.fraud_score || 0) >= minScore);
    }

    setFilteredTransactions(filtered);
  }, [transactions, filterRiskLevel, filterMinScore]);

  const getRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case 'HIGH': return 'error';
      case 'MEDIUM': return 'warning';
      case 'LOW': return 'success';
      default: return 'default';
    }
  };

  const formatAmount = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(Math.abs(amount));
  };

  return (
    <Box>
      {/* Header */}
      <Paper elevation={3} sx={{ p: 3, mb: 3, background: 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)' }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={8}>
            <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              ⛓️ Blockchain Transaction Viewer
            </Typography>
            <Typography variant="body2" color="text.secondary">
              View all transactions stored on Hyperledger Fabric blockchain with immutable audit trail
            </Typography>
          </Grid>
          <Grid item xs={12} md={4} sx={{ textAlign: 'right' }}>
            <Button
              variant="contained"
              startIcon={<RefreshIcon />}
              onClick={() => {
                fetchBlockchainStatus();
                fetchTransactions();
              }}
              disabled={loading}
            >
              Refresh
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Blockchain Status */}
      {blockchainStatus && (
        <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <LinkIcon /> Blockchain Status
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={3}>
              <Chip
                icon={blockchainStatus.connected ? <CheckCircleIcon /> : <ErrorIcon />}
                label={blockchainStatus.connected ? 'Connected' : 'Disconnected'}
                color={blockchainStatus.connected ? 'success' : 'error'}
                sx={{ width: '100%' }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="body2">
                <strong>Channel:</strong> {blockchainStatus.channel || 'N/A'}
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="body2">
                <strong>Chaincode:</strong> {blockchainStatus.chaincode || 'N/A'}
              </Typography>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="body2">
                <strong>Network:</strong> {blockchainStatus.network || 'N/A'}
              </Typography>
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* Statistics Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)' }}>
            <CardContent>
              <Typography variant="h4" sx={{ fontWeight: 'bold' }}>{stats.total}</Typography>
              <Typography variant="body2" color="text.secondary">Total Transactions</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ background: 'linear-gradient(135deg, #d32f2f 0%, #f44336 100%)' }}>
            <CardContent>
              <Typography variant="h4" sx={{ fontWeight: 'bold' }}>{stats.high_risk}</Typography>
              <Typography variant="body2" color="text.secondary">High Risk</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ background: 'linear-gradient(135deg, #f57c00 0%, #ff9800 100%)' }}>
            <CardContent>
              <Typography variant="h4" sx={{ fontWeight: 'bold' }}>{stats.medium_risk}</Typography>
              <Typography variant="body2" color="text.secondary">Medium Risk</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ background: 'linear-gradient(135deg, #388e3c 0%, #4caf50 100%)' }}>
            <CardContent>
              <Typography variant="h4" sx={{ fontWeight: 'bold' }}>{stats.low_risk}</Typography>
              <Typography variant="body2" color="text.secondary">Low Risk</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <Card sx={{ background: 'linear-gradient(135deg, #7b1fa2 0%, #9c27b0 100%)' }}>
            <CardContent>
              <Typography variant="h4" sx={{ fontWeight: 'bold' }}>{stats.avg_fraud_score}</Typography>
              <Typography variant="body2" color="text.secondary">Avg Fraud Score</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FilterIcon /> Filters
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <InputLabel>Risk Level</InputLabel>
              <Select
                value={filterRiskLevel}
                label="Risk Level"
                onChange={(e) => setFilterRiskLevel(e.target.value)}
              >
                <MenuItem value="ALL">All Levels</MenuItem>
                <MenuItem value="HIGH">High Risk</MenuItem>
                <MenuItem value="MEDIUM">Medium Risk</MenuItem>
                <MenuItem value="LOW">Low Risk</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="Minimum Fraud Score"
              type="number"
              inputProps={{ min: 0, max: 1, step: 0.1 }}
              value={filterMinScore}
              onChange={(e) => setFilterMinScore(e.target.value)}
              placeholder="e.g., 0.5"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <Button
              fullWidth
              variant="outlined"
              onClick={() => {
                setFilterRiskLevel('ALL');
                setFilterMinScore('');
              }}
              sx={{ height: '56px' }}
            >
              Clear Filters
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Error Message */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Transactions Table */}
      {!loading && filteredTransactions.length > 0 && (
        <TableContainer component={Paper} elevation={3}>
          <Table>
            <TableHead>
              <TableRow sx={{ backgroundColor: 'primary.dark' }}>
                <TableCell><strong>Transaction ID</strong></TableCell>
                <TableCell><strong>Merchant</strong></TableCell>
                <TableCell align="right"><strong>Amount</strong></TableCell>
                <TableCell><strong>Date</strong></TableCell>
                <TableCell align="center"><strong>Fraud Score</strong></TableCell>
                <TableCell align="center"><strong>Risk Level</strong></TableCell>
                <TableCell><strong>Anomaly</strong></TableCell>
                <TableCell><strong>Recorded At</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredTransactions.map((tx) => (
                <TableRow
                  key={tx.id}
                  hover
                  sx={{
                    '&:hover': { backgroundColor: 'action.hover' },
                    backgroundColor: tx.is_anomaly ? 'rgba(255, 107, 107, 0.1)' : 'inherit'
                  }}
                >
                  <TableCell>
                    <Tooltip title={tx.id}>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                        {tx.id.substring(0, 20)}...
                      </Typography>
                    </Tooltip>
                  </TableCell>
                  <TableCell>{tx.merchant_name}</TableCell>
                  <TableCell align="right">
                    <Typography
                      variant="body2"
                      sx={{ color: tx.amount < 0 ? 'error.main' : 'success.main', fontWeight: 'bold' }}
                    >
                      {formatAmount(tx.amount)}
                    </Typography>
                  </TableCell>
                  <TableCell>{tx.date}</TableCell>
                  <TableCell align="center">
                    <Chip
                      label={tx.fraud_score?.toFixed(3) || '0.000'}
                      size="small"
                      color={tx.fraud_score > 0.7 ? 'error' : tx.fraud_score > 0.4 ? 'warning' : 'success'}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={tx.risk_level}
                      color={getRiskColor(tx.risk_level)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {tx.is_anomaly ? (
                      <Chip label={tx.anomaly_type} color="error" size="small" />
                    ) : (
                      <Chip label="NORMAL" color="success" size="small" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontSize: '0.75rem' }}>
                      {new Date(tx.recorded_at).toLocaleString()}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* No Data Message */}
      {!loading && filteredTransactions.length === 0 && !error && (
        <Paper elevation={2} sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No transactions found on the blockchain
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {filterRiskLevel !== 'ALL' || filterMinScore !== '' 
              ? 'Try adjusting your filters or add some transactions to view them here.'
              : 'Add some transactions to view them here.'}
          </Typography>
        </Paper>
      )}
    </Box>
  );
}

export default BlockchainViewer;
