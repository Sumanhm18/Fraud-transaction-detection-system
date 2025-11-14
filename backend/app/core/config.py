"""
Configuration management for FinSentinel AI
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Environment
    env: str = Field(default="development", alias="ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Database Configuration
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    influxdb_url: str = Field(alias="INFLUXDB_URL")
    influxdb_token: str = Field(alias="INFLUXDB_TOKEN")
    influxdb_org: str = Field(alias="INFLUXDB_ORG")
    influxdb_bucket: str = Field(alias="INFLUXDB_BUCKET")
    
    # Plaid Configuration
    plaid_client_id: str = Field(alias="PLAID_CLIENT_ID")
    plaid_secret: str = Field(alias="PLAID_SECRET")
    plaid_env: str = Field(default="sandbox", alias="PLAID_ENV")
    plaid_products: str = Field(
        default="transactions,auth,identity,assets,liabilities",
        alias="PLAID_PRODUCTS"
    )
    plaid_country_codes: str = Field(default="US,CA", alias="PLAID_COUNTRY_CODES")
    
    # Security
    secret_key: str = Field(alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, 
        alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    
    # Blockchain Configuration
    eth_private_key: Optional[str] = Field(default=None, alias="ETH_PRIVATE_KEY")
    eth_rpc_url: str = Field(
        default="https://polygon-rpc.com", 
        alias="ETH_RPC_URL"
    )
    contract_address: Optional[str] = Field(
        default=None, 
        alias="CONTRACT_ADDRESS"
    )
    
    # External Services
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        alias="KAFKA_BOOTSTRAP_SERVERS"
    )
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        alias="CELERY_RESULT_BACKEND"
    )
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")
    
    # WebSocket
    websocket_origins: List[str] = Field(
        default=["http://localhost:3000", "https://localhost:3000"],
        alias="WEBSOCKET_ORIGINS"
    )
    
    @property
    def plaid_products_list(self) -> List[str]:
        """Convert comma-separated products to list"""
        return [p.strip() for p in self.plaid_products.split(",")]
    
    @property
    def plaid_country_codes_list(self) -> List[str]:
        """Convert comma-separated country codes to list"""
        return [c.strip() for c in self.plaid_country_codes.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()