import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { motion } from 'framer-motion';

import Dashboard from './components/Dashboard/Dashboard';
import PlaidConnection from './components/PlaidConnection/PlaidConnection';
import Transactions from './components/Transactions/Transactions';
import FraudAlerts from './components/FraudAlerts/FraudAlerts';
import Analytics from './components/Analytics/Analytics';
import AuditReports from './components/AuditReports/AuditReports';
import Navbar from './components/Layout/Navbar';
import Sidebar from './components/Layout/Sidebar';
import { WebSocketProvider } from './contexts/WebSocketContext';
import './App.css';

// FinSentinel AI Dark Theme
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00d4aa',
      dark: '#00a085',
      light: '#4de0c1',
    },
    secondary: {
      main: '#ff6b35',
      dark: '#cc5429',
      light: '#ff8a5c',
    },
    background: {
      default: '#0a0e1a',
      paper: '#1a1f35',
    },
    text: {
      primary: '#ffffff',
      secondary: '#a0a9c1',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 700,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'linear-gradient(135deg, #1a1f35 0%, #252b45 100%)',
          border: '1px solid rgba(0, 212, 170, 0.1)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
  },
});

function App() {
  const [sidebarOpen, setSidebarOpen] = React.useState(true);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <WebSocketProvider>
        <Router>
          <div className="App">
            <Navbar 
              onSidebarToggle={() => setSidebarOpen(!sidebarOpen)}
            />
            <div style={{ display: 'flex' }}>
              <Sidebar open={sidebarOpen} />
              <motion.main 
                style={{ 
                  flexGrow: 1, 
                  padding: '24px',
                  marginLeft: sidebarOpen ? '240px' : '60px',
                  transition: 'margin-left 0.3s ease',
                  minHeight: 'calc(100vh - 64px)',
                  backgroundColor: '#0a0e1a'
                }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
              >
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/connect" element={<PlaidConnection />} />
                  <Route path="/transactions" element={<Transactions />} />
                  <Route path="/fraud-alerts" element={<FraudAlerts />} />
                  <Route path="/analytics" element={<Analytics />} />
                  <Route path="/audit" element={<AuditReports />} />
                </Routes>
              </motion.main>
            </div>
          </div>
        </Router>
      </WebSocketProvider>
    </ThemeProvider>
  );
}

export default App;