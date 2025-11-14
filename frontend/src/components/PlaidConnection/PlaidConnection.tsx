import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Alert,
  CircularProgress,
  Stepper,
  Step,
  StepLabel,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  LinearProgress
} from '@mui/material';
import {
  AccountBalance as BankIcon,
  Security as SecurityIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { usePlaidLink } from 'react-plaid-link';

interface Account {
  id: string;
  name: string;
  type: string;
  subtype: string;
  balance: number;
  currency_code: string;
  mask: string;
}

interface PlaidConnectionProps {}

const PlaidConnection: React.FC<PlaidConnectionProps> = () => {
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [connectionStep, setConnectionStep] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connecting' | 'success' | 'error'>('idle');

  // Fetch link token from backend
  const fetchLinkToken = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/v1/plaid/link_token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: 'demo_user', // In production, this would be the actual user ID
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create link token');
      }

      const data = await response.json();
      setLinkToken(data.link_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Handle successful Plaid Link flow
  const onSuccess = useCallback(async (public_token: string, metadata: any) => {
    try {
      setConnectionStatus('connecting');
      setConnectionStep(1);

      // Exchange public token for access token
      const response = await fetch('/api/v1/plaid/exchange_token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          public_token,
          account_ids: metadata.accounts.map((account: any) => account.id),
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to exchange tokens');
      }

      const data = await response.json();
      setConnectionStep(2);

      // Fetch initial accounts and transactions
      setTimeout(async () => {
        await loadAccounts();
        setConnectionStep(3);
        setConnectionStatus('success');
      }, 2000);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
      setConnectionStatus('error');
    }
  }, []);

  // Handle Plaid Link errors
  const onExit = useCallback((err: any, metadata: any) => {
    if (err) {
      setError(`Plaid Link Error: ${err.error_message || 'Connection cancelled'}`);
      setConnectionStatus('error');
    }
  }, []);

  // Load connected accounts
  const loadAccounts = async () => {
    try {
      const response = await fetch('/api/v1/accounts');
      if (response.ok) {
        const accountsData = await response.json();
        setAccounts(accountsData);
      }
    } catch (err) {
      console.error('Failed to load accounts:', err);
    }
  };

  // Configure Plaid Link
  const config = {
    token: linkToken,
    onSuccess,
    onExit,
  };

  const { open, ready } = usePlaidLink(config);

  // Load accounts on component mount
  useEffect(() => {
    loadAccounts();
  }, []);

  const steps = [
    'Connect Bank Account',
    'Verify Connection',
    'Sync Transactions',
    'Complete Setup'
  ];

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  };

  const getAccountIcon = (type: string) => {
    return <BankIcon color="primary" />;
  };

  return (
    <Box maxWidth="800px" mx="auto">
      {/* Header */}
      <Box mb={4}>
        <Typography variant="h4" component="h1" gutterBottom>
          Bank Account Connection
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Securely connect your bank accounts to start monitoring transactions with FinSentinel AI
        </Typography>
      </Box>

      {/* Connection Steps */}
      {connectionStatus !== 'idle' && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Connection Progress
            </Typography>
            <Stepper activeStep={connectionStep} alternativeLabel>
              {steps.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>
            {connectionStatus === 'connecting' && (
              <Box mt={2}>
                <LinearProgress />
                <Typography variant="body2" color="textSecondary" align="center" mt={1}>
                  Setting up your secure connection...
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Success Message */}
      {connectionStatus === 'success' && (
        <Alert severity="success" sx={{ mb: 3 }}>
          <Box display="flex" alignItems="center">
            <CheckIcon sx={{ mr: 1 }} />
            Bank account connected successfully! Your transactions are now being monitored.
          </Box>
        </Alert>
      )}

      {/* Connected Accounts */}
      {accounts.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">
                Connected Accounts ({accounts.length})
              </Typography>
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={loadAccounts}
                size="small"
              >
                Refresh
              </Button>
            </Box>
            <List>
              {accounts.map((account) => (
                <ListItem key={account.id} divider>
                  <ListItemIcon>
                    {getAccountIcon(account.type)}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="subtitle1">
                          {account.name}
                        </Typography>
                        <Chip 
                          label={account.type.toUpperCase()} 
                          size="small" 
                          color="primary" 
                          variant="outlined"
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Typography variant="body2" color="textSecondary">
                          {account.subtype} • ••••{account.mask}
                        </Typography>
                        <Typography variant="h6" color="primary" mt={0.5}>
                          {formatCurrency(account.balance, account.currency_code)}
                        </Typography>
                      </Box>
                    }
                  />
                  <Chip
                    icon={<CheckIcon />}
                    label="Connected"
                    color="success"
                    size="small"
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* Connect New Account */}
      <Card>
        <CardContent>
          <Box textAlign="center" py={4}>
            <SecurityIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom>
              {accounts.length > 0 ? 'Connect Additional Account' : 'Connect Your First Bank Account'}
            </Typography>
            <Typography variant="body1" color="textSecondary" mb={3} maxWidth="400px" mx="auto">
              FinSentinel AI uses bank-level security to protect your data. 
              Your credentials are encrypted and never stored on our servers.
            </Typography>

            {/* Security Features */}
            <Box mb={4}>
              <Typography variant="subtitle1" gutterBottom>
                🔒 Bank-Level Security
              </Typography>
              <Box display="flex" justifyContent="center" gap={2} flexWrap="wrap">
                <Chip label="256-bit Encryption" variant="outlined" size="small" />
                <Chip label="Read-Only Access" variant="outlined" size="small" />
                <Chip label="SOC 2 Certified" variant="outlined" size="small" />
                <Chip label="No Credential Storage" variant="outlined" size="small" />
              </Box>
            </Box>

            {/* Connection Button */}
            <Box>
              {!linkToken ? (
                <Button
                  variant="contained"
                  size="large"
                  onClick={fetchLinkToken}
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={20} /> : <BankIcon />}
                  sx={{ minWidth: 200 }}
                >
                  {loading ? 'Preparing...' : 'Get Started'}
                </Button>
              ) : (
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => open()}
                  disabled={!ready || connectionStatus === 'connecting'}
                  startIcon={connectionStatus === 'connecting' ? <CircularProgress size={20} /> : <BankIcon />}
                  sx={{ minWidth: 200 }}
                >
                  {connectionStatus === 'connecting' ? 'Connecting...' : 'Connect Bank Account'}
                </Button>
              )}
            </Box>

            {linkToken && !ready && (
              <Typography variant="body2" color="textSecondary" mt={2}>
                Preparing secure connection...
              </Typography>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Information Cards */}
      <Box mt={4}>
        <Typography variant="h6" gutterBottom>
          What happens after you connect?
        </Typography>
        <Box display="grid" gridTemplateColumns={{ xs: '1fr', md: '1fr 1fr' }} gap={2}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom color="primary">
                🔍 Real-Time Monitoring
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Your transactions are analyzed in real-time for fraud detection and pattern recognition.
              </Typography>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle1" gutterBottom color="primary">
                🤖 AI-Powered Insights
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Get intelligent forecasts, spending analytics, and automated audit reports.
              </Typography>
            </CardContent>
          </Card>
        </Box>
      </Box>
    </Box>
  );
};

export default PlaidConnection;