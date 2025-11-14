import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import io, { Socket } from 'socket.io-client';
import toast from 'react-hot-toast';

interface WebSocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  transactionCount: number;
  fraudAlerts: any[];
}

interface WebSocketProviderProps {
  children: ReactNode;
}

const WebSocketContext = createContext<WebSocketContextType>({
  socket: null,
  isConnected: false,
  transactionCount: 0,
  fraudAlerts: []
});

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [transactionCount, setTransactionCount] = useState(0);
  const [fraudAlerts, setFraudAlerts] = useState<any[]>([]);

  useEffect(() => {
    // Initialize socket connection
    const newSocket = io('ws://localhost:8000', {
      transports: ['websocket', 'polling'],
      timeout: 20000,
    });

    // Connection event handlers
    newSocket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      toast.success('Connected to real-time monitoring', {
        duration: 3000,
        position: 'bottom-right'
      });
    });

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      toast.error('Real-time connection lost. Attempting to reconnect...', {
        duration: 5000,
        position: 'bottom-right'
      });
    });

    newSocket.on('reconnect', () => {
      console.log('WebSocket reconnected');
      setIsConnected(true);
      toast.success('Reconnected to real-time monitoring', {
        duration: 3000,
        position: 'bottom-right'
      });
    });

    // Transaction event handlers
    newSocket.on('new_transaction', (data: any) => {
      console.log('New transaction received:', data);
      setTransactionCount(prev => prev + 1);
      
      // Show notification for high-value transactions
      if (Math.abs(data.transaction.amount) > 1000) {
        toast(`💰 Large transaction: ${formatCurrency(data.transaction.amount)}`, {
          duration: 5000,
          position: 'top-right'
        });
      }
    });

    // Fraud alert handlers
    newSocket.on('fraud_alert', (data: any) => {
      console.log('Fraud alert received:', data);
      setFraudAlerts(prev => [data.alert, ...prev.slice(0, 9)]);
      
      // Show different notifications based on risk level
      const { alert } = data;
      const riskColor = getRiskColor(alert.risk_level);
      const icon = getRiskIcon(alert.risk_level);
      
      toast(`${icon} ${alert.risk_level} Risk Alert - Score: ${(alert.fraud_score * 100).toFixed(1)}%`, {
        duration: alert.risk_level === 'CRITICAL' ? 0 : 7000, // Critical alerts stay until dismissed
        position: 'top-center',
        style: {
          background: riskColor,
          color: 'white',
          fontWeight: 'bold',
          border: '2px solid rgba(255,255,255,0.3)',
          borderRadius: '8px'
        }
      });
    });

    // Analytics updates
    newSocket.on('analytics_update', (data: any) => {
      console.log('Analytics update received:', data);
    });

    // Agent status updates
    newSocket.on('agent_status', (data: any) => {
      console.log('Agent status update:', data);
    });

    // System alerts
    newSocket.on('system_alert', (data: any) => {
      console.log('System alert:', data);
      toast(`🔧 System: ${data.message}`, {
        duration: 4000,
        position: 'bottom-left'
      });
    });

    // Error handling
    newSocket.on('error', (error: any) => {
      console.error('WebSocket error:', error);
      toast.error(`Connection error: ${error.message || 'Unknown error'}`, {
        duration: 5000,
        position: 'bottom-right'
      });
    });

    setSocket(newSocket);

    // Cleanup on unmount
    return () => {
      newSocket.close();
    };
  }, []);

  // Helper functions
  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency
    }).format(amount);
  };

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'LOW': return '#4caf50';
      case 'MEDIUM': return '#ff9800';
      case 'HIGH': return '#f44336';
      case 'CRITICAL': return '#d32f2f';
      default: return '#2196f3';
    }
  };

  const getRiskIcon = (riskLevel: string) => {
    switch (riskLevel) {
      case 'LOW': return '🟢';
      case 'MEDIUM': return '🟡';
      case 'HIGH': return '🔴';
      case 'CRITICAL': return '🚨';
      default: return '🔵';
    }
  };

  const value: WebSocketContextType = {
    socket,
    isConnected,
    transactionCount,
    fraudAlerts
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};