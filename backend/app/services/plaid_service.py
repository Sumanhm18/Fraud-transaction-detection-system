"""
Plaid Integration Service for FinSentinel AI

Handles all Plaid API interactions for real-time transaction monitoring,
account management, and webhook processing for live financial data.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
from plaid.api import plaid_api
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.model.webhook_verification_key_get_request import WebhookVerificationKeyGetRequest
from plaid.configuration import Configuration
from plaid.api_client import ApiClient

from app.core.config import get_settings
from app.core.redis import cache
from app.models.transaction import Transaction, Account, PlaidItem
from app.services.websocket_manager import websocket_manager

logger = structlog.get_logger()


class PlaidService:
    """
    Plaid integration service for real-time financial data
    
    Provides methods for:
    - Link token creation for frontend integration
    - Public token exchange for permanent access
    - Real-time transaction fetching
    - Account information retrieval
    - Webhook verification and processing
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.client = self._create_client()
        self._webhook_cache_ttl = 300  # 5 minutes
    
    def _create_client(self) -> plaid_api.PlaidApi:
        """Create and configure Plaid API client"""
        configuration = Configuration(
            host=self._get_plaid_host(),
            api_key={
                'clientId': self.settings.plaid_client_id,
                'secret': self.settings.plaid_secret,
            }
        )
        api_client = ApiClient(configuration)
        return plaid_api.PlaidApi(api_client)
    
    def _get_plaid_host(self) -> str:
        """Get Plaid host based on environment"""
        hosts = {
            'sandbox': 'https://sandbox.plaid.com',
            'development': 'https://development.plaid.com',
            'production': 'https://production.plaid.com'
        }
        return hosts.get(self.settings.plaid_env, hosts['sandbox'])
    
    async def create_link_token(
        self, 
        user_id: str, 
        client_name: str = "FinSentinel AI"
    ) -> Dict[str, Any]:
        """
        Create a link token for Plaid Link initialization
        
        Args:
            user_id: Unique user identifier
            client_name: Application name displayed to user
            
        Returns:
            Dict containing link_token and expiration
        """
        try:
            # Cache check
            cache_key = f"link_token:{user_id}"
            cached_token = await cache.get(cache_key)
            if cached_token:
                return cached_token
            
            request = LinkTokenCreateRequest(
                products=[getattr(Products, p) for p in self.settings.plaid_products_list],
                client_name=client_name,
                country_codes=[
                    getattr(CountryCode, cc) for cc in self.settings.plaid_country_codes_list
                ],
                language='en',
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
                webhook='https://your-webhook-url.com/plaid/webhook'  # Configure in production
            )
            
            response = self.client.link_token_create(request)
            
            result = {
                'link_token': response['link_token'],
                'expiration': response['expiration'],
                'request_id': response['request_id']
            }
            
            # Cache for 4 hours (Plaid tokens expire after 4 hours)
            await cache.set(cache_key, result, expire=14400)
            
            logger.info("Link token created", user_id=user_id, request_id=result['request_id'])
            return result
            
        except Exception as e:
            logger.error("Failed to create link token", user_id=user_id, error=str(e))
            raise
    
    async def exchange_public_token(
        self, 
        public_token: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Exchange public token for access token and item ID
        
        Args:
            public_token: Public token from Plaid Link
            user_id: User identifier
            
        Returns:
            Dict containing access_token, item_id, and accounts
        """
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)
            
            access_token = response['access_token']
            item_id = response['item_id']
            
            # Fetch initial account data
            accounts = await self.get_accounts(access_token)
            
            result = {
                'access_token': access_token,
                'item_id': item_id,
                'accounts': accounts,
                'request_id': response['request_id']
            }
            
            # Cache access token for user
            await cache.set(f"access_token:{user_id}", access_token, expire=86400)  # 24 hours
            
            logger.info(
                "Public token exchanged", 
                user_id=user_id, 
                item_id=item_id,
                account_count=len(accounts)
            )
            
            return result
            
        except Exception as e:
            logger.error("Failed to exchange public token", user_id=user_id, error=str(e))
            raise
    
    async def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """
        Fetch account information
        
        Args:
            access_token: Plaid access token
            
        Returns:
            List of account dictionaries
        """
        try:
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)
            
            accounts = []
            for account in response['accounts']:
                account_data = {
                    'account_id': account['account_id'],
                    'name': account['name'],
                    'official_name': account.get('official_name'),
                    'type': account['type'],
                    'subtype': account['subtype'],
                    'balances': {
                        'available': account['balances'].get('available'),
                        'current': account['balances'].get('current'),
                        'limit': account['balances'].get('limit'),
                        'iso_currency_code': account['balances'].get('iso_currency_code', 'USD')
                    },
                    'mask': account.get('mask'),
                    'verification_status': account.get('verification_status')
                }
                accounts.append(account_data)
            
            logger.info("Accounts fetched", count=len(accounts))
            return accounts
            
        except Exception as e:
            logger.error("Failed to fetch accounts", error=str(e))
            raise
    
    async def get_transactions(
        self, 
        access_token: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        account_ids: Optional[List[str]] = None,
        count: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Fetch transactions for real-time monitoring
        
        Args:
            access_token: Plaid access token
            start_date: Start date for transaction range
            end_date: End date for transaction range
            account_ids: Specific accounts to fetch (optional)
            count: Number of transactions to fetch
            offset: Offset for pagination
            
        Returns:
            Dict containing transactions and metadata
        """
        try:
            # Default to last 30 days if no dates provided
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date.date(),
                end_date=end_date.date(),
                count=count,
                offset=offset
            )
            
            if account_ids:
                request.account_ids = account_ids
            
            response = self.client.transactions_get(request)
            
            transactions = []
            for txn in response['transactions']:
                transaction_data = {
                    'transaction_id': txn['transaction_id'],
                    'account_id': txn['account_id'],
                    'amount': float(txn['amount']),
                    'iso_currency_code': txn.get('iso_currency_code', 'USD'),
                    'date': txn['date'].isoformat(),
                    'authorized_date': txn.get('authorized_date').isoformat() if txn.get('authorized_date') else None,
                    'name': txn['name'],
                    'merchant_name': txn.get('merchant_name'),
                    'category': txn.get('category', []),
                    'category_id': txn.get('category_id'),
                    'location': {
                        'address': txn.get('location', {}).get('address'),
                        'city': txn.get('location', {}).get('city'),
                        'region': txn.get('location', {}).get('region'),
                        'postal_code': txn.get('location', {}).get('postal_code'),
                        'country': txn.get('location', {}).get('country'),
                        'lat': txn.get('location', {}).get('lat'),
                        'lon': txn.get('location', {}).get('lon'),
                    } if txn.get('location') else None,
                    'payment_channel': txn.get('payment_channel'),
                    'account_owner': txn.get('account_owner'),
                    'transaction_code': txn.get('transaction_code'),
                    'pending': txn.get('pending', False),
                    'created_at': datetime.now().isoformat()
                }
                transactions.append(transaction_data)
            
            result = {
                'transactions': transactions,
                'total_transactions': response['total_transactions'],
                'accounts': [
                    {
                        'account_id': acc['account_id'],
                        'name': acc['name'],
                        'type': acc['type'],
                        'subtype': acc['subtype']
                    } for acc in response['accounts']
                ],
                'request_id': response['request_id']
            }
            
            logger.info(
                "Transactions fetched",
                count=len(transactions),
                total=response['total_transactions'],
                start_date=start_date.date().isoformat(),
                end_date=end_date.date().isoformat()
            )
            
            # Send real-time updates via WebSocket
            await websocket_manager.broadcast({
                'type': 'transactions_update',
                'data': {
                    'new_transactions': len(transactions),
                    'latest_transaction': transactions[0] if transactions else None
                }
            })
            
            return result
            
        except Exception as e:
            logger.error("Failed to fetch transactions", error=str(e))
            raise
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """
        Process incoming Plaid webhooks for real-time updates
        
        Args:
            webhook_data: Webhook payload from Plaid
            
        Returns:
            True if processed successfully
        """
        try:
            webhook_type = webhook_data.get('webhook_type')
            webhook_code = webhook_data.get('webhook_code')
            item_id = webhook_data.get('item_id')
            
            logger.info(
                "Processing webhook",
                type=webhook_type,
                code=webhook_code,
                item_id=item_id
            )
            
            if webhook_type == 'TRANSACTIONS':
                await self._handle_transaction_webhook(webhook_data)
            elif webhook_type == 'ITEM':
                await self._handle_item_webhook(webhook_data)
            elif webhook_type == 'AUTH':
                await self._handle_auth_webhook(webhook_data)
            else:
                logger.warning("Unknown webhook type", type=webhook_type)
            
            return True
            
        except Exception as e:
            logger.error("Failed to process webhook", error=str(e))
            return False
    
    async def _handle_transaction_webhook(self, webhook_data: Dict[str, Any]):
        """Handle transaction-related webhooks"""
        webhook_code = webhook_data.get('webhook_code')
        item_id = webhook_data.get('item_id')
        
        if webhook_code == 'DEFAULT_UPDATE':
            # New transactions available
            new_transactions = webhook_data.get('new_transactions', 0)
            
            # Broadcast real-time update
            await websocket_manager.broadcast({
                'type': 'new_transactions',
                'data': {
                    'item_id': item_id,
                    'new_transactions': new_transactions,
                    'timestamp': datetime.now().isoformat()
                }
            })
            
        elif webhook_code == 'INITIAL_UPDATE':
            # Historical transactions ready
            logger.info("Historical transactions ready", item_id=item_id)
            
        elif webhook_code == 'HISTORICAL_UPDATE':
            # Historical data update complete
            logger.info("Historical update complete", item_id=item_id)
    
    async def _handle_item_webhook(self, webhook_data: Dict[str, Any]):
        """Handle item-related webhooks"""
        webhook_code = webhook_data.get('webhook_code')
        
        if webhook_code == 'ERROR':
            error = webhook_data.get('error')
            logger.error("Item error webhook", error=error)
            
            # Broadcast error to frontend
            await websocket_manager.broadcast({
                'type': 'item_error',
                'data': {
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                }
            })
    
    async def _handle_auth_webhook(self, webhook_data: Dict[str, Any]):
        """Handle auth-related webhooks"""
        webhook_code = webhook_data.get('webhook_code')
        
        if webhook_code == 'AUTOMATICALLY_VERIFIED':
            logger.info("Account automatically verified")
        elif webhook_code == 'VERIFICATION_EXPIRED':
            logger.warning("Account verification expired")


# Global Plaid service instance
plaid_service = PlaidService()