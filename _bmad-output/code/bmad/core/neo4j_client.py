"""
Async Neo4j Client for BMAD Agent Memory System

This module provides the foundational async connection layer for all BMAD agent
memory operations. It enforces multi-tenant isolation through mandatory group_id
filtering and provides connection pooling with automatic reconnection.

Architecture Reference: _bmad-output/docs/architecture/architecture.md
- Section: "Core Architectural Decisions" - Data Architecture
- Section: "Implementation Sequence" - Step 2

Author: Brooks (BMAD Dev Agent)
Created: 2026-01-26
Story: 1-2-async-neo4j-client-implementation
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import ServiceUnavailable, SessionExpired

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when security requirements are violated (e.g., missing group_id)"""
    pass


class Neo4jAsyncClient:
    """
    Async Neo4j client with connection pooling and multi-tenant isolation.
    
    Features:
    - Async connection pool with configurable size
    - Automatic reconnection with exponential backoff
    - Mandatory group_id filtering for multi-tenant isolation
    - Thread-safe for concurrent access
    - Health check support
    
    Usage:
        client = Neo4jAsyncClient()
        await client.initialize()
        
        # Execute query with group_id filtering
        results = await client.execute_query(
            "MATCH (a:AIAgent) WHERE a.group_id = $group_id RETURN a",
            {"group_id": "faith-meats"}
        )
        
        await client.close()
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        pool_size: Optional[int] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize Neo4j async client.
        
        Args:
            uri: Neo4j bolt URI (default: from NEO4J_URI env var)
            user: Neo4j username (default: from NEO4J_USER env var)
            password: Neo4j password (default: from NEO4J_PASSWORD env var)
            pool_size: Connection pool size (default: from NEO4J_POOL_SIZE or 10)
            max_retries: Maximum retry attempts for transient failures (default: 3)
            retry_delay: Initial retry delay in seconds (default: 1.0)
        """
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")
        self.pool_size = pool_size or int(os.getenv("NEO4J_POOL_SIZE", "10"))
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self._driver: Optional[AsyncDriver] = None
        self._initialized = False
        
        if not self.password:
            raise ValueError("NEO4J_PASSWORD must be set in environment or passed to constructor")
    
    async def initialize(self) -> None:
        """
        Initialize the async driver and connection pool.
        
        Raises:
            ServiceUnavailable: If unable to connect to Neo4j
        """
        if self._initialized:
            logger.warning("Client already initialized, skipping")
            return
        
        logger.info(f"Initializing Neo4j async client: {self.uri}")
        
        self._driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
            max_connection_pool_size=self.pool_size,
            connection_acquisition_timeout=30.0,
            max_transaction_retry_time=30.0
        )
        
        # Verify connection with health check
        await self.health_check()
        
        self._initialized = True
        logger.info(f"Neo4j async client initialized (pool_size={self.pool_size})")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check by querying Neo4j components.
        
        Returns:
            Dict with health check results including latency
            
        Raises:
            ServiceUnavailable: If health check fails
        """
        if not self._driver:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        
        import time
        start_time = time.perf_counter()
        
        try:
            async with self._driver.session() as session:
                result = await session.run("CALL dbms.components()")
                components = await result.single()
                
                latency_ms = (time.perf_counter() - start_time) * 1000
                
                return {
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2),
                    "components": dict(components) if components else {}
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise ServiceUnavailable(f"Neo4j health check failed: {e}")
    
    def _validate_group_id(self, query: str, parameters: Dict[str, Any]) -> None:
        """
        Validate that query includes group_id filtering for multi-tenant isolation.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            
        Raises:
            SecurityError: If group_id is missing from parameters
        """
        # Check if group_id is in parameters
        if "group_id" not in parameters:
            # Allow queries that don't touch tenant-scoped data
            # (e.g., schema queries, health checks)
            exempt_patterns = [
                "CALL dbms.",
                "SHOW CONSTRAINTS",
                "SHOW INDEXES",
                "CREATE CONSTRAINT",
                "CREATE INDEX"
            ]
            
            if not any(pattern in query for pattern in exempt_patterns):
                logger.warning(f"Query missing group_id parameter: {query[:100]}")
                raise SecurityError(
                    "Multi-tenant isolation violation: group_id parameter is required for data queries"
                )
    
    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        validate_group_id: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute a read query asynchronously.
        
        Args:
            query: Cypher query string
            parameters: Query parameters (must include group_id for tenant isolation)
            validate_group_id: Whether to enforce group_id validation (default: True)
            
        Returns:
            List of result records as dictionaries
            
        Raises:
            SecurityError: If group_id validation fails
            ServiceUnavailable: If connection fails after retries
        """
        if not self._driver:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        
        parameters = parameters or {}
        
        if validate_group_id:
            self._validate_group_id(query, parameters)
        
        return await self._execute_with_retry(query, parameters, read_only=True)
    
    async def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        validate_group_id: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute a write query in an explicit transaction.
        
        Args:
            query: Cypher query string
            parameters: Query parameters (must include group_id for tenant isolation)
            validate_group_id: Whether to enforce group_id validation (default: True)
            
        Returns:
            List of result records as dictionaries
            
        Raises:
            SecurityError: If group_id validation fails
            ServiceUnavailable: If connection fails after retries
        """
        if not self._driver:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        
        parameters = parameters or {}
        
        if validate_group_id:
            self._validate_group_id(query, parameters)
        
        return await self._execute_with_retry(query, parameters, read_only=False)
    
    async def _execute_with_retry(
        self,
        query: str,
        parameters: Dict[str, Any],
        read_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute query with exponential backoff retry logic.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            read_only: Whether this is a read-only query
            
        Returns:
            List of result records as dictionaries
            
        Raises:
            ServiceUnavailable: If all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                async with self._driver.session() as session:
                    if read_only:
                        result = await session.run(query, parameters)
                    else:
                        # Use explicit transaction for writes
                        async with session.begin_transaction() as tx:
                            result = await tx.run(query, parameters)
                            await tx.commit()
                    
                    # Convert to list of dicts
                    records = await result.data()
                    return records
                    
            except (ServiceUnavailable, SessionExpired) as e:
                last_exception = e
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Query failed (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Query failed after {self.max_retries} attempts: {e}")
        
        raise ServiceUnavailable(f"Query failed after {self.max_retries} retries: {last_exception}")
    
    @asynccontextmanager
    async def session(self) -> AsyncSession:
        """
        Context manager for manual session management.
        
        Usage:
            async with client.session() as session:
                result = await session.run("MATCH (n) RETURN n LIMIT 1")
                record = await result.single()
        """
        if not self._driver:
            raise RuntimeError("Client not initialized. Call initialize() first.")
        
        async with self._driver.session() as session:
            yield session
    
    async def close(self) -> None:
        """
        Close the driver and release all connections.
        """
        if self._driver:
            logger.info("Closing Neo4j async client")
            await self._driver.close()
            self._driver = None
            self._initialized = False
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
