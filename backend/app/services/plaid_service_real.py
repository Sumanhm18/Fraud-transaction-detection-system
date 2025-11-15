"""
Real Plaid service implementation for FinSentinel AI
"""
import os
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Plaid client imports
import plaid
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid.api import plaid_api
from plaid.configuration import Configuration
from plaid.api_client import ApiClient

load_dotenv()

class PlaidService:
    def __init__(self):
        # Plaid configuration
        self.client_id = os.getenv('PLAID_CLIENT_ID')
        self.secret = os.getenv('PLAID_SECRET')
        self.env = os.getenv('PLAID_ENV', 'sandbox')
        
        # Set up Plaid client
        if self.env == 'sandbox':
            host = plaid.Environment.Sandbox
        elif self.env == 'development':
            host = plaid.Environment.Development
        else:
            host = plaid.Environment.Production
            
        configuration = Configuration(
            host=host,
            api_key={
                'clientId': self.client_id,
                'secret': self.secret,
            }
        )
        
        api_client = ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)
        
        # In-memory storage for demo (replace with database in production)
        self.user_access_tokens: Dict[str, str] = {}
        self.user_items: Dict[str, Dict] = {}
    
    async def create_link_token(self, user_id: str) -> Dict:
        """Create a link token for Plaid Link"""
        try:
            request = LinkTokenCreateRequest(
                products=[Products('transactions'), Products('auth')],
                client_name="FinSentinel AI",
                country_codes=[CountryCode('US')],
                language='en',
                user=LinkTokenCreateRequestUser(
                    client_user_id=user_id
                )
            )
            
            response = self.client.link_token_create(request)
            return {
                'link_token': response['link_token'],
                'expiration': response['expiration'].isoformat()
            }
        except Exception as e:
            print(f"Error creating link token: {e}")
            return {'error': str(e)}
    
    async def exchange_public_token(self, public_token: str, user_id: str) -> Dict:
        """Exchange public token for access token"""
        try:
            request = ItemPublicTokenExchangeRequest(
                public_token=public_token
            )
            
            response = self.client.item_public_token_exchange(request)
            access_token = response['access_token']
            item_id = response['item_id']
            
            # Store access token for user
            self.user_access_tokens[user_id] = access_token
            self.user_items[user_id] = {
                'access_token': access_token,
                'item_id': item_id,
                'connected_at': datetime.utcnow().isoformat()
            }
            
            return {
                'success': True,
                'access_token': access_token,
                'item_id': item_id
            }
        except Exception as e:
            print(f"Error exchanging public token: {e}")
            return {'error': str(e)}
    
    async def get_accounts(self, user_id: str) -> List[Dict]:
        """Get user's accounts"""
        try:
            access_token = self.user_access_tokens.get(user_id)
            if not access_token:
                return []
            
            request = AccountsGetRequest(access_token=access_token)
            response = self.client.accounts_get(request)
            
            accounts = []
            for account in response['accounts']:
                accounts.append({
                    'account_id': account['account_id'],
                    'name': account['name'],
                    'type': account['type'],
                    'subtype': account['subtype'],
                    'balance': {
                        'available': account['balances']['available'],
                        'current': account['balances']['current'],
                        'currency': account['balances']['iso_currency_code']
                    }
                })
            
            return accounts
        except Exception as e:
            print(f"Error getting accounts: {e}")
            return []
    
    async def get_transactions(self, user_id: str, start_date: Optional[datetime] = None, 
                             end_date: Optional[datetime] = None, count: int = 100) -> List[Dict]:
        """Get user's transactions"""
        try:
            access_token = self.user_access_tokens.get(user_id)
            if not access_token:
                return []
            
            # Default to last 30 days
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date.date(),
                end_date=end_date.date(),
                count=count
            )
            
            response = self.client.transactions_get(request)
            
            transactions = []
            for transaction in response['transactions']:
                transactions.append({
                    'transaction_id': transaction['transaction_id'],
                    'account_id': transaction['account_id'],
                    'amount': float(transaction['amount']),
                    'date': transaction['date'].isoformat() if transaction['date'] else None,
                    'name': transaction['name'],
                    'merchant_name': transaction.get('merchant_name'),
                    'category': transaction.get('category', []),
                    'account_owner': transaction.get('account_owner'),
                })
            
            return transactions
        except Exception as e:
            print(f"Error getting transactions: {e}")
            return []
    
    async def get_connection_status(self, user_id: str) -> Dict:
        """Get user's Plaid connection status"""
        if user_id in self.user_access_tokens:
            item_info = self.user_items.get(user_id, {})
            return {
                'connected': True,
                'access_token': self.user_access_tokens[user_id],
                'connected_at': item_info.get('connected_at'),
                'accounts_count': len(await self.get_accounts(user_id))
            }
        else:
            return {
                'connected': False,
                'access_token': None,
                'connected_at': None,
                'accounts_count': 0
            }
    
    async def disconnect_user(self, user_id: str) -> Dict:
        """Disconnect user from Plaid"""
        if user_id in self.user_access_tokens:
            del self.user_access_tokens[user_id]
            if user_id in self.user_items:
                del self.user_items[user_id]
            return {'success': True, 'message': 'User disconnected'}
        else:
            return {'success': False, 'message': 'User not connected'}

# Global instance
plaid_service = PlaidService()