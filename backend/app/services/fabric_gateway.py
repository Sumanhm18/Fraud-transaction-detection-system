"""
Hyperledger Fabric Gateway Service
Connects to the real Hyperledger Fabric test network via subprocess calls
"""

import json
import subprocess
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class FabricGatewayService:
    """
    Service to interact with Hyperledger Fabric network
    Uses peer CLI commands to invoke chaincode
    """
    
    def __init__(self):
        self.enabled = os.getenv('BLOCKCHAIN_ENABLED', 'true').lower() == 'true'
        self.network_path = os.getenv('FABRIC_NETWORK_PATH', '/Users/sumanhm/Downloads/finance/fabric-samples/test-network')
        self.channel_name = os.getenv('BLOCKCHAIN_CHANNEL', 'finsentinel-channel')
        self.chaincode_name = os.getenv('BLOCKCHAIN_CHAINCODE', 'fraud-detector')
        self.org = "Org1"  # Default organization
        
        # Fabric bin path
        self.fabric_bin = f"{self.network_path}/../bin"
        self.peer_bin = f"{self.fabric_bin}/peer"
        
        logger.info(
            f"Fabric Gateway initialized: channel={self.channel_name}, "
            f"chaincode={self.chaincode_name}, enabled={self.enabled}"
        )
    
    def _set_org_env(self) -> Dict[str, str]:
        """Set environment variables for Org1"""
        env = os.environ.copy()
        env.update({
            'CORE_PEER_TLS_ENABLED': 'true',
            'CORE_PEER_LOCALMSPID': 'Org1MSP',
            'CORE_PEER_TLS_ROOTCERT_FILE': f'{self.network_path}/organizations/peerOrganizations/org1.example.com/tlsca/tlsca.org1.example.com-cert.pem',
            'CORE_PEER_MSPCONFIGPATH': f'{self.network_path}/organizations/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp',
            'CORE_PEER_ADDRESS': 'localhost:7051',
            'FABRIC_CFG_PATH': f'{self.network_path}/../config/',
        })
        return env
    
    async def record_transaction(
        self,
        transaction: Dict[str, Any],
        fraud_score: float,
        risk_factors: List[str]
    ) -> Dict[str, Any]:
        """
        Record transaction on Hyperledger Fabric blockchain with ML fraud detection results
        
        Args:
            transaction: Transaction data
            fraud_score: ML model fraud score
            risk_factors: Detected risk factors
            
        Returns:
            Blockchain record result
        """
        if not self.enabled:
            logger.info("Blockchain disabled - skipping record")
            return {"success": False, "message": "Blockchain disabled"}
        
        try:
            # Determine risk level
            if fraud_score > 0.7:
                risk_level = "HIGH"
            elif fraud_score > 0.4:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            
            # Determine if it's an anomaly
            is_anomaly = fraud_score > 0.6
            anomaly_type = "FRAUD_PATTERN" if is_anomaly else "NORMAL"
            
            # Prepare chaincode arguments
            category_json = json.dumps(transaction.get("category", []))
            risk_factors_json = json.dumps(risk_factors)
            
            # Build peer chaincode invoke command
            cmd = [
                self.peer_bin,
                'chaincode', 'invoke',
                '-o', 'localhost:7050',
                '--ordererTLSHostnameOverride', 'orderer.example.com',
                '--tls',
                '--cafile', f'{self.network_path}/organizations/ordererOrganizations/example.com/tlsca/tlsca.example.com-cert.pem',
                '-C', self.channel_name,
                '-n', self.chaincode_name,
                '--peerAddresses', 'localhost:7051',
                '--tlsRootCertFiles', f'{self.network_path}/organizations/peerOrganizations/org1.example.com/tlsca/tlsca.org1.example.com-cert.pem',
                '--peerAddresses', 'localhost:9051',
                '--tlsRootCertFiles', f'{self.network_path}/organizations/peerOrganizations/org2.example.com/tlsca/tlsca.org2.example.com-cert.pem',
                '-c', json.dumps({
                    "function": "RecordTransaction",
                    "Args": [
                        str(transaction.get("id")),
                        str(transaction.get("account_id")),
                        str(transaction.get("amount")),
                        str(transaction.get("merchant_name", "")),
                        category_json,
                        str(transaction.get("date", datetime.now().isoformat())),
                        str(transaction.get("transaction_type", "debit")),
                        str(transaction.get("location", "")),
                        str(transaction.get("payment_method", "card")),
                        str(fraud_score),
                        risk_level,
                        risk_factors_json,
                        "ML-Model-v1.0",  # ML model version
                        str(is_anomaly).lower(),
                        anomaly_type
                    ]
                })
            ]
            
            # Execute command
            env = self._set_org_env()
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Transaction {transaction.get('id')} recorded on Hyperledger Fabric blockchain")
                return {
                    "success": True,
                    "transaction_id": transaction.get("id"),
                    "channel": self.channel_name,
                    "chaincode": self.chaincode_name,
                    "fraud_score": fraud_score,
                    "risk_level": risk_level,
                    "is_anomaly": is_anomaly
                }
            else:
                logger.error(f"Failed to record transaction: {result.stderr}")
                return {"success": False, "error": result.stderr}
                
        except Exception as e:
            logger.error(f"Failed to record transaction on blockchain: {e}")
            return {"success": False, "error": str(e)}
    
    async def record_fraud_alert(
        self,
        alert: Dict[str, Any],
        transaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Record fraud alert on Hyperledger Fabric blockchain
        
        Args:
            alert: Fraud alert data
            transaction: Related transaction data
            
        Returns:
            Blockchain record result
        """
        if not self.enabled:
            logger.info("Blockchain disabled - skipping alert record")
            return {"success": False, "message": "Blockchain disabled"}
        
        try:
            risk_factors_json = json.dumps(transaction.get("risk_factors", []))
            
            # Build peer chaincode invoke command
            cmd = [
                self.peer_bin,
                'chaincode', 'invoke',
                '-o', 'localhost:7050',
                '--ordererTLSHostnameOverride', 'orderer.example.com',
                '--tls',
                '--cafile', f'{self.network_path}/organizations/ordererOrganizations/example.com/tlsca/tlsca.example.com-cert.pem',
                '-C', self.channel_name,
                '-n', self.chaincode_name,
                '--peerAddresses', 'localhost:7051',
                '--tlsRootCertFiles', f'{self.network_path}/organizations/peerOrganizations/org1.example.com/tlsca/tlsca.org1.example.com-cert.pem',
                '--peerAddresses', 'localhost:9051',
                '--tlsRootCertFiles', f'{self.network_path}/organizations/peerOrganizations/org2.example.com/tlsca/tlsca.org2.example.com-cert.pem',
                '-c', json.dumps({
                    "function": "RecordFraudAlert",
                    "Args": [
                        str(alert.get("id")),
                        str(alert.get("transaction_id")),
                        str(alert.get("alert_type")),
                        str(alert.get("severity")),
                        str(alert.get("message", "")),
                        str(transaction.get("fraud_score", 0)),
                        risk_factors_json
                    ]
                })
            ]
            
            # Execute command
            env = self._set_org_env()
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Fraud alert {alert.get('id')} recorded on Hyperledger Fabric blockchain")
                return {
                    "success": True,
                    "alert_id": alert.get("id"),
                    "channel": self.channel_name,
                    "chaincode": self.chaincode_name
                }
            else:
                logger.error(f"Failed to record alert: {result.stderr}")
                return {"success": False, "error": result.stderr}
                
        except Exception as e:
            logger.error(f"Failed to record alert on blockchain: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Query a transaction from the blockchain"""
        try:
            cmd = [
                self.peer_bin,
                'chaincode', 'query',
                '-C', self.channel_name,
                '-n', self.chaincode_name,
                '-c', json.dumps({
                    "function": "GetTransaction",
                    "Args": [transaction_id]
                })
            ]
            
            env = self._set_org_env()
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                logger.error(f"Failed to query transaction: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to query transaction: {e}")
            return None
    
    async def get_all_transactions(self) -> Optional[List[Dict[str, Any]]]:
        """Query all transactions from the blockchain"""
        try:
            cmd = [
                self.peer_bin,
                'chaincode', 'query',
                '-C', self.channel_name,
                '-n', self.chaincode_name,
                '-c', json.dumps({
                    "function": "GetAllTransactions",
                    "Args": []
                })
            ]
            
            env = self._set_org_env()
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                transactions = json.loads(result.stdout)
                logger.info(f"✅ Retrieved {len(transactions)} transactions from blockchain")
                return transactions
            else:
                logger.error(f"Failed to query all transactions: {result.stderr}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to query all transactions: {e}")
            return []


# Global service instance
fabric_gateway = FabricGatewayService()
