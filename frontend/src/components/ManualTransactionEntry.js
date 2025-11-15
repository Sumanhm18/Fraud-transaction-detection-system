import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Alert,
  Grid,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  IconButton,
  Tooltip,
  InputAdornment,
  CircularProgress
} from '@mui/material';
import {
  Add as AddIcon,
  Receipt as ReceiptIcon,
  AttachMoney as MoneyIcon,
  Store as StoreIcon,
  Category as CategoryIcon,
  CalendarToday as DateIcon,
  AccountBalance as AccountIcon,
  Save as SaveIcon,
  Clear as ClearIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Warning as WarningIcon,
  CheckCircle as SuccessIcon
} from '@mui/icons-material';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import FinSentinelAPI from '../services/api.js';

const ManualTransactionEntry = () => {
  const [transactions, setTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [openDialog, setOpenDialog] = useState(false);
  const [editingTransaction, setEditingTransaction] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    account_id: '',
    amount: '',
    merchant_name: '',
    category: '',
    date: new Date(),
    description: '',
    transaction_type: 'debit',
    location: '',
    payment_method: 'card'
  });

  // Predefined categories for dropdown
  const categories = [
    'Food & Dining',
    'Shopping',
    'Transportation', 
    'Bills & Utilities',
    'Entertainment',
    'Healthcare',
    'Travel',
    'Groceries',
    'Gas Stations',
    'ATM & Cash',
    'Transfer',
    'Salary',
    'Investment',
    'Other'
  ];

  const paymentMethods = [
    'card',
    'cash',
    'check',
    'online',
    'mobile',
    'wire_transfer'
  ];

  const transactionTypes = [
    { value: 'debit', label: 'Expense (Debit)', color: 'error' },
    { value: 'credit', label: 'Income (Credit)', color: 'success' }
  ];

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Load accounts and recent manual transactions
      const [accountsResult, transactionsResult] = await Promise.all([
        FinSentinelAPI.getAccounts(),
        FinSentinelAPI.getTransactions(50)
      ]);
      
      setAccounts(accountsResult || []);
      // Filter for manual transactions if they have a flag
      setTransactions(transactionsResult || []);
      
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load accounts and transactions');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const validateForm = () => {
    const errors = [];
    
    if (!formData.account_id) errors.push('Account is required');
    if (!formData.amount || parseFloat(formData.amount) <= 0) errors.push('Valid amount is required');
    if (!formData.merchant_name.trim()) errors.push('Merchant/Description is required');
    if (!formData.category) errors.push('Category is required');
    
    return errors;
  };

  const handleSubmit = async () => {
    const validationErrors = validateForm();
    
    if (validationErrors.length > 0) {
      setError('Please fix the following errors:\n• ' + validationErrors.join('\n• '));
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      const transactionData = {
        ...formData,
        amount: formData.transaction_type === 'debit' 
          ? -Math.abs(parseFloat(formData.amount))
          : Math.abs(parseFloat(formData.amount)),
        date: formData.date.toISOString().split('T')[0],
        manual_entry: true,
        entry_timestamp: new Date().toISOString()
      };

      let result;
      if (editingTransaction) {
        // Update existing transaction
        result = await FinSentinelAPI.updateManualTransaction(editingTransaction.id, transactionData);
        setSuccess('✅ Transaction updated successfully!');
      } else {
        // Create new transaction
        result = await FinSentinelAPI.createManualTransaction(transactionData);
        setSuccess('✅ Transaction added successfully!');
      }
      
      console.log('Transaction submitted:', result);
      
      // Reset form and refresh data
      resetForm();
      setOpenDialog(false);
      setEditingTransaction(null);
      await loadData();
      
      // Clear success message after 5 seconds
      setTimeout(() => setSuccess(null), 5000);
      
    } catch (err) {
      console.error('Failed to submit transaction:', err);
      setError('Failed to save transaction: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      account_id: '',
      amount: '',
      merchant_name: '',
      category: '',
      date: new Date(),
      description: '',
      transaction_type: 'debit',
      location: '',
      payment_method: 'card'
    });
  };

  const handleEdit = (transaction) => {
    setEditingTransaction(transaction);
    setFormData({
      account_id: transaction.account_id,
      amount: Math.abs(transaction.amount).toString(),
      merchant_name: transaction.merchant_name || '',
      category: transaction.category?.[0] || '',
      date: new Date(transaction.date),
      description: transaction.description || '',
      transaction_type: transaction.amount < 0 ? 'debit' : 'credit',
      location: transaction.location || '',
      payment_method: transaction.payment_method || 'card'
    });
    setOpenDialog(true);
  };

  const handleDelete = async (transactionId) => {
    if (window.confirm('Are you sure you want to delete this transaction?')) {
      try {
        await FinSentinelAPI.deleteTransaction(transactionId);
        setSuccess('✅ Transaction deleted successfully!');
        await loadData();
        setTimeout(() => setSuccess(null), 3000);
      } catch (err) {
        setError('Failed to delete transaction: ' + err.message);
      }
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(Math.abs(amount));
  };

  const getAccountName = (accountId) => {
    const account = accounts.find(acc => acc.id === accountId);
    return account ? account.account_name || account.name : 'Unknown Account';
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box p={3}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h4" component="h1">
            💳 Manual Transaction Entry
          </Typography>
          <Button
            variant="contained"
            color="primary"
            onClick={() => {
              resetForm();
              setEditingTransaction(null);
              setOpenDialog(true);
            }}
            startIcon={<AddIcon />}
          >
            Add Transaction
          </Button>
        </Box>

        {/* Status Messages */}
        {error && (
          <Alert 
            severity="error" 
            sx={{ mb: 3, whiteSpace: 'pre-line' }}
            onClose={() => setError(null)}
          >
            {error}
          </Alert>
        )}
        
        {success && (
          <Alert 
            severity="success" 
            sx={{ mb: 3 }}
            onClose={() => setSuccess(null)}
          >
            {success}
          </Alert>
        )}

        {/* Statistics Cards */}
        <Grid container spacing={3} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <ReceiptIcon color="primary" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h6" color="primary">
                      {transactions.length}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Transactions
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <AccountIcon color="success" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h6" color="success.main">
                      {accounts.length}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Connected Accounts
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <MoneyIcon color="error" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h6" color="error.main">
                      {formatCurrency(
                        transactions
                          .filter(t => t.amount < 0)
                          .reduce((sum, t) => sum + Math.abs(t.amount), 0)
                      )}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Expenses
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center">
                  <MoneyIcon color="success" sx={{ mr: 2 }} />
                  <Box>
                    <Typography variant="h6" color="success.main">
                      {formatCurrency(
                        transactions
                          .filter(t => t.amount > 0)
                          .reduce((sum, t) => sum + t.amount, 0)
                      )}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Income
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Transaction Table */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Transaction History
            </Typography>
            
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Merchant/Description</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Account</TableCell>
                    <TableCell align="right">Amount</TableCell>
                    <TableCell align="center">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {transactions
                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                    .map((transaction) => (
                      <TableRow key={transaction.id}>
                        <TableCell>
                          {new Date(transaction.date).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          <Box display="flex" alignItems="center">
                            <StoreIcon sx={{ mr: 1, fontSize: 16 }} />
                            {transaction.merchant_name || transaction.name || 'N/A'}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip 
                            size="small" 
                            label={transaction.category?.[0] || 'Uncategorized'}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          {getAccountName(transaction.account_id)}
                        </TableCell>
                        <TableCell align="right">
                          <Typography 
                            color={transaction.amount < 0 ? 'error' : 'success'}
                            fontWeight="medium"
                          >
                            {transaction.amount < 0 ? '-' : '+'}{formatCurrency(Math.abs(transaction.amount))}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Tooltip title="View Details">
                            <IconButton size="small">
                              <ViewIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Edit">
                            <IconButton 
                              size="small" 
                              onClick={() => handleEdit(transaction)}
                            >
                              <EditIcon />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete">
                            <IconButton 
                              size="small" 
                              onClick={() => handleDelete(transaction.id)}
                              color="error"
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </TableContainer>
            
            <TablePagination
              rowsPerPageOptions={[5, 10, 25]}
              component="div"
              count={transactions.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
            />
          </CardContent>
        </Card>

        {/* Transaction Entry Dialog */}
        <Dialog 
          open={openDialog} 
          onClose={() => setOpenDialog(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>
            {editingTransaction ? 'Edit Transaction' : 'Add New Transaction'}
          </DialogTitle>
          <DialogContent>
            <Grid container spacing={3} sx={{ mt: 1 }}>
              {/* Account Selection */}
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Account</InputLabel>
                  <Select
                    value={formData.account_id}
                    label="Account"
                    onChange={(e) => handleInputChange('account_id', e.target.value)}
                  >
                    {accounts.map((account) => (
                      <MenuItem key={account.id} value={account.id}>
                        <Box display="flex" alignItems="center">
                          <AccountIcon sx={{ mr: 1 }} />
                          {account.account_name || account.name} ({account.account_type})
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {/* Transaction Type */}
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Transaction Type</InputLabel>
                  <Select
                    value={formData.transaction_type}
                    label="Transaction Type"
                    onChange={(e) => handleInputChange('transaction_type', e.target.value)}
                  >
                    {transactionTypes.map((type) => (
                      <MenuItem key={type.value} value={type.value}>
                        <Chip 
                          size="small" 
                          label={type.label} 
                          color={type.color}
                          sx={{ minWidth: 120 }}
                        />
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {/* Amount */}
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Amount"
                  type="number"
                  value={formData.amount}
                  onChange={(e) => handleInputChange('amount', e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <MoneyIcon />
                      </InputAdornment>
                    )
                  }}
                  inputProps={{
                    min: 0,
                    step: 0.01
                  }}
                />
              </Grid>

              {/* Date */}
              <Grid item xs={12} sm={6}>
                <DatePicker
                  label="Transaction Date"
                  value={formData.date}
                  onChange={(newValue) => handleInputChange('date', newValue)}
                  renderInput={(params) => (
                    <TextField 
                      {...params} 
                      fullWidth
                      InputProps={{
                        ...params.InputProps,
                        startAdornment: (
                          <InputAdornment position="start">
                            <DateIcon />
                          </InputAdornment>
                        )
                      }}
                    />
                  )}
                />
              </Grid>

              {/* Merchant Name */}
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Merchant/Description"
                  value={formData.merchant_name}
                  onChange={(e) => handleInputChange('merchant_name', e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <StoreIcon />
                      </InputAdornment>
                    )
                  }}
                />
              </Grid>

              {/* Category */}
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Category</InputLabel>
                  <Select
                    value={formData.category}
                    label="Category"
                    onChange={(e) => handleInputChange('category', e.target.value)}
                  >
                    {categories.map((category) => (
                      <MenuItem key={category} value={category}>
                        <Box display="flex" alignItems="center">
                          <CategoryIcon sx={{ mr: 1 }} />
                          {category}
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {/* Payment Method */}
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Payment Method</InputLabel>
                  <Select
                    value={formData.payment_method}
                    label="Payment Method"
                    onChange={(e) => handleInputChange('payment_method', e.target.value)}
                  >
                    {paymentMethods.map((method) => (
                      <MenuItem key={method} value={method}>
                        {method.replace('_', ' ').toUpperCase()}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {/* Location */}
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Location (Optional)"
                  value={formData.location}
                  onChange={(e) => handleInputChange('location', e.target.value)}
                />
              </Grid>

              {/* Description */}
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Additional Notes (Optional)"
                  multiline
                  rows={3}
                  value={formData.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button 
              onClick={() => setOpenDialog(false)}
              startIcon={<ClearIcon />}
            >
              Cancel
            </Button>
            <Button 
              onClick={handleSubmit}
              variant="contained"
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : <SaveIcon />}
            >
              {loading ? 'Saving...' : (editingTransaction ? 'Update' : 'Save Transaction')}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
};

export default ManualTransactionEntry;