-- FinSentinel AI Database Initialization
-- This file sets up the database schema for the financial intelligence system

-- Create the database if it doesn't exist
-- Note: This is handled by the POSTGRES_DB environment variable in Docker

-- Create necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE finsentinel_db TO finsentinel;

-- The tables will be created automatically by the Python application
-- This file serves as documentation and can contain any additional setup