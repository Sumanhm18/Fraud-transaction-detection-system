import React, { useState } from 'react';
import {
  Container,
  Box,
  AppBar,
  Toolbar,
  Typography,
  Chip,
  Tab,
  Tabs,
  Paper
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  BugReport as TestIcon,
  AccountBalance as BankIcon,
  Receipt as ReceiptIcon,
  Security as SecurityIcon,
  Link as LinkIcon
} from '@mui/icons-material';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import ComprehensiveDashboard from './components/ComprehensiveDashboard';
import ApiTestDashboard from './components/ApiTestDashboard';
import PlaidIntegration from './components/PlaidIntegration';
import ManualTransactionEntry from './components/ManualTransactionEntry';
import FraudMonitoring from './components/FraudMonitoring';
import BlockchainViewer from './components/BlockchainViewer';
import './App.css';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00ff88',
    },
    secondary: {
      main: '#ff6b6b',
    },
    background: {
      default: '#0a0a0a',
      paper: '#1a1a1a',
    },
  },
  typography: {
    fontFamily: 'Monaco, "Courier New", monospace',
  },
});

function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`tabpanel-${index}`}
      aria-labelledby={`tab-${index}`}
      {...other}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

function App() {
  const [currentTab, setCurrentTab] = useState(0);

  const handleTabChange = (event, newValue) => {
    setCurrentTab(newValue);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      
      <AppBar position="static" sx={{ background: 'linear-gradient(45deg, #1a1a1a 30%, #2d2d2d 90%)' }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            🎯 FinSentinel AI - Autonomous Financial Intelligence System
          </Typography>
          <Chip 
            label="Backend: Online" 
            color="success" 
            size="small" 
            sx={{ mr: 1 }}
          />
          <Chip 
            label="Frontend: Ready" 
            color="success" 
            size="small"
          />
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 2, mb: 4 }}>
        <Paper elevation={3} sx={{ mb: 3 }}>
          <Tabs 
            value={currentTab} 
            onChange={handleTabChange}
            variant="fullWidth"
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab 
              icon={<DashboardIcon />} 
              label="Dashboard" 
              id="tab-0"
              aria-controls="tabpanel-0"
            />
            <Tab 
              icon={<SecurityIcon />} 
              label="Fraud Monitoring" 
              id="tab-1"
              aria-controls="tabpanel-1"
            />
            <Tab 
              icon={<BankIcon />} 
              label="Plaid Integration" 
              id="tab-2"
              aria-controls="tabpanel-2"
            />
            <Tab 
              icon={<ReceiptIcon />} 
              label="Manual Entry" 
              id="tab-3"
              aria-controls="tabpanel-3"
            />
            <Tab 
              icon={<TestIcon />} 
              label="API Test" 
              id="tab-4"
              aria-controls="tabpanel-4"
            />
            <Tab 
              icon={<LinkIcon />} 
              label="Blockchain" 
              id="tab-5"
              aria-controls="tabpanel-5"
            />
          </Tabs>
        </Paper>

        <TabPanel value={currentTab} index={0}>
          <ComprehensiveDashboard />
        </TabPanel>

        <TabPanel value={currentTab} index={1}>
          <FraudMonitoring />
        </TabPanel>

        <TabPanel value={currentTab} index={2}>
          <PlaidIntegration />
        </TabPanel>

        <TabPanel value={currentTab} index={3}>
          <ManualTransactionEntry />
        </TabPanel>

        <TabPanel value={currentTab} index={4}>
          <ApiTestDashboard />
        </TabPanel>

        <TabPanel value={currentTab} index={5}>
          <BlockchainViewer />
        </TabPanel>
      </Container>

      {/* Footer */}
      <Box 
        component="footer" 
        sx={{ 
          mt: 'auto', 
          py: 2, 
          textAlign: 'center',
          borderTop: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper'
        }}
      >
        <Typography variant="body2" color="text.secondary">
          🔐 FinSentinel AI - Multi-Agent Financial Intelligence | Frontend-Backend Integration Complete ✅
        </Typography>
      </Box>
    </ThemeProvider>
  );
}

export default App;
