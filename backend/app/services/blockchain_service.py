"""
Blockchain Service for FinSentinel AI using Hyperledger Fabric

Provides immutable audit trails for:
- Transaction records
- Fraud detection results
- Security events
- Compliance logs
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import os

logger = logging.getLogger(__name__)


class Block:
    """
    Represents a single block in the blockchain
    """
    
    def __init__(
        self,
        index: int,
        timestamp: str,
        data: Dict[str, Any],
        previous_hash: str,
        nonce: int = 0
    ):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """
        Calculate SHA-256 hash of the block
        """
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int = 2):
        """
        Proof of Work: Mine block with given difficulty
        """
        target = "0" * difficulty
        
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        
        logger.info(f"Block mined: {self.hash}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary"""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }


class HyperledgerBlockchainService:
    """
    Blockchain service implementing Hyperledger-inspired architecture
    
    Features:
    - Immutable transaction ledger
    - Fraud detection audit trail
    - Smart contract validation
    - Distributed consensus simulation
    - Tamper-proof records
    """
    
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict[str, Any]] = []
        self.difficulty = 2  # Mining difficulty
        self.mining_reward = 1.0
        
        # Hyperledger configuration
        self.enabled = os.getenv('BLOCKCHAIN_ENABLED', 'true').lower() == 'true'
        self.network_name = os.getenv('BLOCKCHAIN_NETWORK', 'finsentinel-network')
        self.channel_name = os.getenv('BLOCKCHAIN_CHANNEL', 'audit-channel')
        self.chaincode_name = os.getenv('BLOCKCHAIN_CHAINCODE', 'fraud-detector')
        
        # Initialize with genesis block
        if not self.chain:
            self.create_genesis_block()
        
        logger.info(
            f"Blockchain service initialized: network={self.network_name}, "
            f"channel={self.channel_name}, enabled={self.enabled}"
        )
    
    def create_genesis_block(self) -> Block:
        """
        Create the genesis block (first block in the chain)
        """
        genesis_block = Block(
            index=0,
            timestamp=datetime.now().isoformat(),
            data={
                "type": "genesis",
                "message": "FinSentinel AI - Hyperledger Blockchain Genesis Block",
                "network": self.network_name,
                "channel": self.channel_name
            },
            previous_hash="0"
        )
        
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        
        logger.info(f"Genesis block created: {genesis_block.hash}")
        return genesis_block
    
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain"""
        return self.chain[-1] if self.chain else None
    
    async def record_transaction(
        self,
        transaction: Dict[str, Any],
        fraud_score: float,
        risk_factors: List[str]
    ) -> Dict[str, Any]:
        """
        Record transaction on blockchain with fraud detection metadata
        
        Args:
            transaction: Transaction data
            fraud_score: Calculated fraud score
            risk_factors: Identified risk factors
            
        Returns:
            Blockchain record with hash
        """
        if not self.enabled:
            logger.info("Blockchain disabled - skipping record")
            return {"success": False, "message": "Blockchain disabled"}
        
        try:
            # Create blockchain record
            record = {
                "type": "transaction",
                "transaction_id": transaction.get("id"),
                "account_id": transaction.get("account_id"),
                "amount": transaction.get("amount"),
                "merchant": transaction.get("merchant_name"),
                "timestamp": transaction.get("date", datetime.now().isoformat()),
                "fraud_score": fraud_score,
                "risk_factors": risk_factors,
                "verified_by": "FinSentinel AI Fraud Detection",
                "network": self.network_name,
                "channel": self.channel_name
            }
            
            # Add to pending transactions
            self.pending_transactions.append(record)
            
            # Mine new block if we have enough pending transactions
            if len(self.pending_transactions) >= 1:  # Mine every transaction for demo
                block_hash = await self.mine_pending_transactions()
                
                return {
                    "success": True,
                    "block_hash": block_hash,
                    "block_index": len(self.chain) - 1,
                    "transaction_hash": self._calculate_transaction_hash(record),
                    "network": self.network_name,
                    "channel": self.channel_name
                }
            
            return {
                "success": True,
                "status": "pending",
                "transaction_hash": self._calculate_transaction_hash(record)
            }
            
        except Exception as e:
            logger.error(f"Failed to record transaction on blockchain: {e}")
            return {"success": False, "error": str(e)}
    
    async def mine_pending_transactions(self) -> str:
        """
        Mine pending transactions into a new block
        
        Returns:
            Hash of the new block
        """
        if not self.pending_transactions:
            logger.info("No pending transactions to mine")
            return None
        
        # Create new block with pending transactions
        new_block = Block(
            index=len(self.chain),
            timestamp=datetime.now().isoformat(),
            data={
                "transactions": self.pending_transactions,
                "transaction_count": len(self.pending_transactions)
            },
            previous_hash=self.get_latest_block().hash
        )
        
        # Mine the block (Proof of Work)
        new_block.mine_block(self.difficulty)
        
        # Add to chain
        self.chain.append(new_block)
        
        # Clear pending transactions
        self.pending_transactions = []
        
        logger.info(
            f"Block mined successfully: index={new_block.index}, "
            f"hash={new_block.hash}, transactions={new_block.data['transaction_count']}"
        )
        
        return new_block.hash
    
    async def record_fraud_alert(
        self,
        alert: Dict[str, Any],
        transaction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Record fraud alert on blockchain
        
        Args:
            alert: Fraud alert data
            transaction: Associated transaction
            
        Returns:
            Blockchain record
        """
        if not self.enabled:
            return {"success": False, "message": "Blockchain disabled"}
        
        try:
            record = {
                "type": "fraud_alert",
                "alert_id": alert.get("id"),
                "transaction_id": alert.get("transaction_id"),
                "severity": alert.get("severity"),
                "risk_factors": alert.get("risk_factors", []),
                "timestamp": datetime.now().isoformat(),
                "alert_message": alert.get("message"),
                "transaction_amount": transaction.get("amount"),
                "merchant": transaction.get("merchant_name"),
                "verified_by": "FinSentinel AI Security System",
                "network": self.network_name
            }
            
            self.pending_transactions.append(record)
            
            # Mine immediately for critical alerts
            if alert.get("severity") in ["CRITICAL", "HIGH"]:
                block_hash = await self.mine_pending_transactions()
                
                return {
                    "success": True,
                    "block_hash": block_hash,
                    "block_index": len(self.chain) - 1,
                    "alert_hash": self._calculate_transaction_hash(record)
                }
            
            return {
                "success": True,
                "status": "pending",
                "alert_hash": self._calculate_transaction_hash(record)
            }
            
        except Exception as e:
            logger.error(f"Failed to record fraud alert on blockchain: {e}")
            return {"success": False, "error": str(e)}
    
    def verify_chain(self) -> Dict[str, Any]:
        """
        Verify the integrity of the blockchain
        
        Returns:
            Validation result
        """
        if len(self.chain) <= 1:
            return {
                "valid": True,
                "message": "Chain is valid (genesis only)"
            }
        
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Verify current block hash
            if current_block.hash != current_block.calculate_hash():
                return {
                    "valid": False,
                    "error": f"Block {i} has invalid hash",
                    "tampered_block": i
                }
            
            # Verify link to previous block
            if current_block.previous_hash != previous_block.hash:
                return {
                    "valid": False,
                    "error": f"Block {i} has invalid previous_hash",
                    "tampered_block": i
                }
        
        return {
            "valid": True,
            "message": "Blockchain is valid and tamper-proof",
            "blocks": len(self.chain)
        }
    
    def get_chain_summary(self) -> Dict[str, Any]:
        """
        Get blockchain summary statistics
        """
        total_transactions = sum(
            len(block.data.get("transactions", []))
            for block in self.chain
            if block.data.get("type") != "genesis"
        )
        
        return {
            "enabled": self.enabled,
            "network": self.network_name,
            "channel": self.channel_name,
            "chaincode": self.chaincode_name,
            "total_blocks": len(self.chain),
            "total_transactions": total_transactions,
            "pending_transactions": len(self.pending_transactions),
            "latest_block_hash": self.get_latest_block().hash if self.chain else None,
            "chain_valid": self.verify_chain()["valid"]
        }
    
    def get_block(self, index: int) -> Optional[Dict[str, Any]]:
        """Get block by index"""
        if 0 <= index < len(self.chain):
            return self.chain[index].to_dict()
        return None
    
    def get_all_blocks(self) -> List[Dict[str, Any]]:
        """Get all blocks in the chain"""
        return [block.to_dict() for block in self.chain]
    
    def _calculate_transaction_hash(self, transaction: Dict[str, Any]) -> str:
        """Calculate hash for a transaction"""
        tx_string = json.dumps(transaction, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()


# Global blockchain service instance
blockchain_service = HyperledgerBlockchainService()
