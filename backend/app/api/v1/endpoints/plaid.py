"""
Plaid Integration API Endpoints

Handles Plaid Link token creation, public token exchange,
and webhook processing for real-time financial data.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from pydantic import BaseModel, Field
import structlog

from app.services.plaid_service import plaid_service
from app.services.orchestrator import AgentOrchestrator
from app.core.database import get_db
from app.core.redis import cache
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

router = APIRouter()

# Pydantic models for request/response
class LinkTokenRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    client_name: str = Field(default="FinSentinel AI", description="Application name")

class LinkTokenResponse(BaseModel):
    link_token: str
    expiration: str
    request_id: str

class PublicTokenExchangeRequest(BaseModel):
    public_token: str = Field(..., description="Public token from Plaid Link")
    user_id: str = Field(..., description="User identifier")

class PublicTokenExchangeResponse(BaseModel):
    access_token: str
    item_id: str
    accounts: List[Dict[str, Any]]
    request_id: str

class TransactionsRequest(BaseModel):
    access_token: str = Field(..., description="Plaid access token")
    start_date: Optional[datetime] = Field(default=None, description="Start date for transactions")
    end_date: Optional[datetime] = Field(default=None, description="End date for transactions")
    account_ids: Optional[List[str]] = Field(default=None, description="Specific account IDs")
    count: int = Field(default=100, ge=1, le=500, description="Number of transactions")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


@router.post("/link_token", response_model=LinkTokenResponse)
async def create_link_token(
    request: LinkTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Plaid Link token for frontend integration
    
    This endpoint creates a link_token that the frontend uses to initialize
    Plaid Link for connecting user bank accounts.
    """
    try:
        logger.info("Creating Plaid Link token", user_id=request.user_id)
        
        result = await plaid_service.create_link_token(
            user_id=request.user_id,
            client_name=request.client_name
        )
        
        return LinkTokenResponse(**result)
        
    except Exception as e:
        logger.error("Failed to create link token", user_id=request.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create link token: {str(e)}")


@router.post("/exchange_token", response_model=PublicTokenExchangeResponse)
async def exchange_public_token(
    request: PublicTokenExchangeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange public token for access token and fetch initial account data
    
    This is called after successful Plaid Link connection to get permanent
    access to the user's financial data.
    """
    try:
        logger.info("Exchanging public token", user_id=request.user_id)
        
        result = await plaid_service.exchange_public_token(
            public_token=request.public_token,
            user_id=request.user_id
        )
        
        # Start initial transaction sync in background
        background_tasks.add_task(
            _sync_initial_transactions,
            result['access_token'],
            request.user_id
        )
        
        return PublicTokenExchangeResponse(**result)
        
    except Exception as e:
        logger.error("Failed to exchange token", user_id=request.user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to exchange token: {str(e)}")


@router.get("/accounts/{user_id}")
async def get_user_accounts(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all accounts for a user"""
    try:
        # Get cached access token
        access_token = await cache.get(f"access_token:{user_id}")
        if not access_token:
            raise HTTPException(status_code=404, detail="User not found or not connected")
        
        accounts = await plaid_service.get_accounts(access_token)
        
        return {
            "user_id": user_id,
            "accounts": accounts,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch accounts", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch accounts: {str(e)}")


@router.post("/transactions")
async def get_transactions(
    request: TransactionsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch transactions with real-time processing through agent pipeline
    
    Returns transactions processed through FinSentinel AI's multi-agent system
    for fraud detection, anomaly analysis, and risk scoring.
    """
    try:
        logger.info("Fetching transactions", count=request.count, offset=request.offset)
        
        # Fetch transactions from Plaid
        result = await plaid_service.get_transactions(
            access_token=request.access_token,
            start_date=request.start_date,
            end_date=request.end_date,
            account_ids=request.account_ids,
            count=request.count,
            offset=request.offset
        )
        
        # Process through agent orchestrator for AI analysis
        orchestrator = AgentOrchestrator()
        enhanced_transactions = []
        
        for transaction in result['transactions']:
            # Run through multi-agent analysis pipeline
            agent_analysis = await orchestrator.process_transaction(transaction)
            
            # Enhance transaction with AI insights
            enhanced_transaction = {
                **transaction,
                'ai_analysis': agent_analysis,
                'processed_at': datetime.utcnow().isoformat()
            }
            
            enhanced_transactions.append(enhanced_transaction)
        
        return {
            **result,
            'transactions': enhanced_transactions,
            'ai_processed': True,
            'processing_timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to fetch transactions", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch transactions: {str(e)}")


@router.post("/webhook")
async def plaid_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle Plaid webhooks for real-time transaction updates
    
    Processes webhooks for:
    - New transactions (DEFAULT_UPDATE)
    - Historical data sync (INITIAL_UPDATE, HISTORICAL_UPDATE)
    - Item errors and status changes
    """
    try:
        webhook_data = await request.json()
        
        logger.info(
            "Received Plaid webhook",
            webhook_type=webhook_data.get('webhook_type'),
            webhook_code=webhook_data.get('webhook_code'),
            item_id=webhook_data.get('item_id')
        )
        
        # Process webhook in background to avoid blocking
        background_tasks.add_task(
            plaid_service.process_webhook,
            webhook_data
        )
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/connection_status/{user_id}")
async def get_connection_status(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get Plaid connection status for a user"""
    try:
        # Check if user has active access token
        access_token = await cache.get(f"access_token:{user_id}")
        
        if not access_token:
            return {
                "user_id": user_id,
                "connected": False,
                "status": "not_connected"
            }
        
        # Verify connection by fetching accounts
        try:
            accounts = await plaid_service.get_accounts(access_token)
            return {
                "user_id": user_id,
                "connected": True,
                "status": "active",
                "account_count": len(accounts),
                "last_verified": datetime.utcnow().isoformat()
            }
        except Exception:
            return {
                "user_id": user_id,
                "connected": False,
                "status": "connection_error"
            }
        
    except Exception as e:
        logger.error("Failed to check connection status", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to check connection status")


# Background task functions
async def _sync_initial_transactions(access_token: str, user_id: str):
    """Background task to sync initial historical transactions"""
    try:
        logger.info("Starting initial transaction sync", user_id=user_id)
        
        # Fetch last 90 days of transactions
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        result = await plaid_service.get_transactions(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            count=500  # Get more transactions for initial sync
        )
        
        # Process through agent pipeline
        orchestrator = AgentOrchestrator()
        processed_count = 0
        
        for transaction in result['transactions']:
            await orchestrator.process_transaction(transaction)
            processed_count += 1
        
        logger.info(
            "Initial transaction sync completed",
            user_id=user_id,
            processed_count=processed_count
        )
        
        # Cache sync completion
        await cache.set(
            f"initial_sync:{user_id}",
            {
                'completed': True,
                'processed_count': processed_count,
                'completion_time': datetime.utcnow().isoformat()
            },
            expire=86400  # 24 hours
        )
        
    except Exception as e:
        logger.error("Initial transaction sync failed", user_id=user_id, error=str(e))