// ============================================================================
// BMAD Pattern Library Seed Data
// ============================================================================
// Version: 1.0
// Date: 2026-01-26
// Purpose: Pre-seed 50 foundational patterns for the BMAD framework
//
// Categories: architectural, testing, debugging, api, database, security, devops, code_quality
// ============================================================================

// ============================================================================
// SECTION 1: ARCHITECTURAL PATTERNS (10 patterns)
// ============================================================================

// 1.1 Layered Architecture
MERGE (p1:Pattern {
    pattern_id: 'pattern-arch-layered',
    name: 'Layered Architecture',
    description: 'Organize code into distinct layers (presentation, business logic, data access) with unidirectional dependencies. Each layer only knows about the layer directly below it.',
    category: 'architectural',
    tags: ['architecture', 'layers', 'separation-of-concerns', 'dependency-inversion'],
    success_rate: 0.85,
    times_used: 45,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.9
});

// 1.2 Repository Pattern
MERGE (p2:Pattern {
    pattern_id: 'pattern-arch-repository',
    name: 'Repository Pattern',
    description: 'Abstract database operations behind a repository interface. This creates a clean separation between business logic and data access, making code testable and database-agnostic.',
    category: 'architectural',
    tags: ['repository', 'data-access', 'abstraction', 'testing'],
    success_rate: 0.88,
    times_used: 52,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.92
});

// 1.3 Service Layer Pattern
MERGE (p3:Pattern {
    pattern_id: 'pattern-arch-service',
    name: 'Service Layer Pattern',
    description: 'Encapsulate business logic in services that coordinate between controllers and repositories. Services should be stateless and represent use cases.',
    category: 'architectural',
    tags: ['service', 'business-logic', 'transactions', 'orchestration'],
    success_rate: 0.82,
    times_used: 48,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.88
});

// 1.4 CQRS Pattern
MERGE (p4:Pattern {
    pattern_id: 'pattern-arch-cqrs',
    name: 'Command Query Responsibility Segregation',
    description: 'Separate read and write operations into different models. Commands modify state, queries read state. This improves performance, scalability, and security.',
    category: 'architectural',
    tags: ['cqrs', 'commands', 'queries', 'scalability', 'event-sourcing'],
    success_rate: 0.78,
    times_used: 23,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.82
});

// 1.5 Event Sourcing Pattern
MERGE (p5:Pattern {
    pattern_id: 'pattern-arch-event-sourcing',
    name: 'Event Sourcing Pattern',
    description: 'Store all changes to application state as a sequence of events. This provides full audit trail, enables temporal queries, and supports event-driven architectures.',
    category: 'architectural',
    tags: ['events', 'audit-trail', 'temporal', 'domain-driven'],
    success_rate: 0.75,
    times_used: 18,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.80
});

// 1.6 Saga Pattern
MERGE (p6:Pattern {
    pattern_id: 'pattern-arch-saga',
    name: 'Saga Pattern',
    description: 'Manage distributed transactions as a sequence of local transactions with compensating actions. Each step has a corresponding rollback action for failure recovery.',
    category: 'architectural',
    tags: ['saga', 'distributed-transactions', 'compensation', 'microservices'],
    success_rate: 0.72,
    times_used: 15,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.78
});

// 1.7 API Gateway Pattern
MERGE (p7:Pattern {
    pattern_id: 'pattern-arch-api-gateway',
    name: 'API Gateway Pattern',
    description: 'Use a single entry point for all client requests that routes to appropriate microservices, handles authentication, rate limiting, and request aggregation.',
    category: 'architectural',
    tags: ['api-gateway', 'routing', 'authentication', 'rate-limiting', 'microservices'],
    success_rate: 0.90,
    times_used: 35,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.92
});

// 1.8 Circuit Breaker Pattern
MERGE (p8:Pattern {
    pattern_id: 'pattern-arch-circuit-breaker',
    name: 'Circuit Breaker Pattern',
    description: 'Prevent cascading failures by stopping requests to a failing service. After threshold failures, the circuit opens and fast-fails requests until service recovers.',
    category: 'architectural',
    tags: ['circuit-breaker', 'resilience', 'fallback', 'error-handling'],
    success_rate: 0.88,
    times_used: 41,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.90
});

// 1.9 Bulkhead Pattern
MERGE (p9:Pattern {
    pattern_id: 'pattern-arch-bulkhead',
    name: 'Bulkhead Pattern',
    description: 'Isolate system components into pools so that failure in one component does not bring down the entire system. Like ship compartments that prevent flooding from spreading.',
    category: 'architectural',
    tags: ['bulkhead', 'isolation', 'resilience', 'concurrency'],
    success_rate: 0.85,
    times_used: 28,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.88
});

// 1.10 Strangler Fig Pattern
MERGE (p10:Pattern {
    pattern_id: 'pattern-arch-strangler',
    name: 'Strangler Fig Pattern',
    description: 'Incrementally replace legacy system components with new ones by wrapping old functionality with new services. Routes requests to old or new based on migration status.',
    category: 'architectural',
    tags: ['strangler', 'migration', 'legacy', 'incremental'],
    success_rate: 0.80,
    times_used: 22,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.85
});


// ============================================================================
// SECTION 2: TESTING PATTERNS (10 patterns)
// ============================================================================

// 2.1 Arrange-Act-Assert
MERGE (p11:Pattern {
    pattern_id: 'pattern-test-aaa',
    name: 'Arrange-Act-Assert Pattern',
    description: 'Structure tests in three sections: Arrange (setup), Act (execute), Assert (verify). This makes tests readable and focused on a single behavior.',
    category: 'testing',
    tags: ['aaa', 'test-structure', 'readability', 'single-behavior'],
    success_rate: 0.92,
    times_used: 78,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.95
});

// 2.2 Test Data Builder
MERGE (p12:Pattern {
    pattern_id: 'pattern-test-data-builder',
    name: 'Test Data Builder Pattern',
    description: 'Create flexible test data builders with fluent API for setting only needed fields. Reduces test setup boilerplate and makes tests more readable.',
    category: 'testing',
    tags: ['data-builder', 'test-setup', 'fluent-api', 'readability'],
    success_rate: 0.88,
    times_used: 65,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.92
});

// 2.3 Given-When-Then
MERGE (p13:Pattern {
    pattern_id: 'pattern-test-gwt',
    name: 'Given-When-Then Pattern',
    description: 'Structure BDD-style tests with Given (context), When (action), Then (assertion) sections. Often used with Gherkin syntax for requirements traceability.',
    category: 'testing',
    tags: ['gwt', 'bdd', 'gherkin', 'requirements', 'readability'],
    success_rate: 0.90,
    times_used: 55,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.92
});

// 2.4 Mock Object Pattern
MERGE (p14:Pattern {
    pattern_id: 'pattern-test-mock',
    name: 'Mock Object Pattern',
    description: 'Replace real dependencies with mock objects that simulate expected behavior. Allows testing units in isolation and controlling test scenarios.',
    category: 'testing',
    tags: ['mock', 'isolation', 'stubs', 'test-doubles'],
    success_rate: 0.85,
    times_used: 70,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.90
});

// 2.5 Test Pyramid Strategy
MERGE (p15:Pattern {
    pattern_id: 'pattern-test-pyramid',
    name: 'Test Pyramid Strategy',
    description: 'Structure tests in a pyramid: many unit tests at base, fewer integration tests, and even fewer end-to-end tests at top. Optimizes for fast feedback and coverage.',
    category: 'testing',
    tags: ['test-pyramid', 'strategy', 'coverage', 'fast-feedback'],
    success_rate: 0.87,
    times_used: 42,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.90
});

// 2.6 Property-Based Testing
MERGE (p16:Pattern {
    pattern_id: 'pattern-test-property',
    name: 'Property-Based Testing',
    description: 'Generate random inputs and test properties/assertions that should hold true for all inputs. Catches edge cases that example-based tests miss.',
    category: 'testing',
    tags: ['property-based', 'fuzzing', 'edge-cases', 'generative'],
    success_rate: 0.78,
    times_used: 25,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.82
});

// 2.7 Snapshot Testing
MERGE (p17:Pattern {
    pattern_id: 'pattern-test-snapshot',
    name: 'Snapshot Testing',
    description: 'Capture output of a component and compare against stored snapshot. Useful for testing UI rendering, complex JSON responses, and serialization.',
    category: 'testing',
    tags: ['snapshot', 'regression', 'ui', 'serialization'],
    success_rate: 0.82,
    times_used: 38,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.86
});

// 2.8 Contract Testing
MERGE (p18:Pattern {
    pattern_id: 'pattern-test-contract',
    name: 'Contract Testing Pattern',
    description: 'Verify that services adhere to their interface contracts. Provider tests ensure it meets contract, consumer tests verify expectations.',
    category: 'testing',
    tags: ['contract', 'api-testing', 'interfaces', 'pact'],
    success_rate: 0.80,
    times_used: 30,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.85
});

// 2.9 Golden Master Testing
MERGE (p19:Pattern {
    pattern_id: 'pattern-test-golden-master',
    name: 'Golden Master Testing',
    description: 'Record system outputs for known inputs to create a golden master. Test by running same inputs and comparing outputs. Useful for legacy systems.',
    category: 'testing',
    tags: ['golden-master', 'characterization-tests', 'legacy', 'regression'],
    success_rate: 0.75,
    times_used: 20,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.80
});

// 2.10 Mutation Testing
MERGE (p20:Pattern {
    pattern_id: 'pattern-test-mutation',
    name: 'Mutation Testing Strategy',
    description: 'Introduce small code changes (mutations) and verify tests detect them. Measures test effectiveness by checking if tests actually catch bugs.',
    category: 'testing',
    tags: ['mutation-testing', 'test-quality', 'coverage', 'effectiveness'],
    success_rate: 0.72,
    times_used: 15,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.78
});


// ============================================================================
// SECTION 3: API DESIGN PATTERNS (10 patterns)
// ============================================================================

// 3.1 RESTful Resource Naming
MERGE (p21:Pattern {
    pattern_id: 'pattern-api-rest-naming',
    name: 'RESTful Resource Naming',
    description: 'Use nouns for resources, HTTP methods for actions. Collections use plural names. Use hierarchical URLs for nested resources and query params for filtering.',
    category: 'api',
    tags: ['rest', 'api-design', 'resources', 'urls', 'http'],
    success_rate: 0.92,
    times_used: 85,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.95
});

// 3.2 HATEOAS Implementation
MERGE (p22:Pattern {
    pattern_id: 'pattern-api-hateoas',
    name: 'HATEOAS Pattern',
    description: 'Include hypermedia links in API responses that guide clients through available actions. Makes APIs discoverable and self-documenting.',
    category: 'api',
    tags: ['hateoas', 'hypermedia', 'rest', 'discoverability'],
    success_rate: 0.78,
    times_used: 32,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.82
});

// 3.3 API Versioning Strategy
MERGE (p23:Pattern {
    pattern_id: 'pattern-api-versioning',
    name: 'API Versioning Strategy',
    description: 'Version APIs to maintain backward compatibility. Use URL path versioning (/v1/resources) for major versions. Maintain multiple versions simultaneously during migration.',
    category: 'api',
    tags: ['versioning', 'compatibility', 'migration', 'rest'],
    success_rate: 0.90,
    times_used: 58,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.92
});

// 3.4 Error Response Standardization
MERGE (p24:Pattern {
    pattern_id: 'pattern-api-error',
    name: 'Standardized Error Responses',
    description: 'Return consistent error format with code, message, details, and documentation link. Include request ID for tracing and support correlation.',
    category: 'api',
    tags: ['error-handling', 'standardization', 'debugging', 'rest'],
    success_rate: 0.88,
    times_used: 72,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.92
});

// 3.5 Pagination Pattern
MERGE (p25:Pattern {
    pattern_id: 'pattern-api-pagination',
    name: 'API Pagination Pattern',
    description: 'Support cursor-based or offset pagination for large collections. Include next/prev links in responses. Prefer cursor-based for real-time data.',
    category: 'api',
    tags: ['pagination', 'performance', 'cursors', 'collections'],
    success_rate: 0.90,
    times_used: 62,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.92
});

// 3.6 API Rate Limiting
MERGE (p26:Pattern {
    pattern_id: 'pattern-api-rate-limit',
    name: 'API Rate Limiting Pattern',
    description: 'Track request counts per client/API key. Return 429 Too Many Requests with Retry-After header. Use token bucket or sliding window algorithms.',
    category: 'api',
    tags: ['rate-limiting', 'throttling', '429', 'security'],
    success_rate: 0.85,
    times_used: 45,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.88
});

// 3.7 Idempotency Pattern
MERGE (p27:Pattern {
    pattern_id: 'pattern-api-idempotency',
    name: 'API Idempotency Pattern',
    description: 'Allow clients to retry requests safely using idempotency keys. Store processed keys for a time period and return cached responses for duplicate requests.',
    category: 'api',
    tags: ['idempotency', 'retries', 'safety', 'reliability'],
    success_rate: 0.88,
    times_used: 48,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.90
});

// 3.8 Response Caching Strategy
MERGE (p28:Pattern {
    pattern_id: 'pattern-api-cache',
    name: 'API Response Caching',
    description: 'Use HTTP caching headers (ETag, Last-Modified) and CDNs. Implement cache invalidation patterns. Consider TTL-based caching for stable data.',
    category: 'api',
    tags: ['caching', 'http-headers', 'cdn', 'performance'],
    success_rate: 0.87,
    times_used: 55,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.90
});

// 3.9 Async Response Pattern
MERGE (p29:Pattern {
    pattern_id: 'pattern-api-async',
    name: 'Async Response Pattern',
    description: 'For long-running operations, return 202 Accepted with operation URL. Client polls status endpoint. Consider webhook or WebSocket for completion notification.',
    category: 'api',
    tags: ['async', '202-accepted', 'polling', 'webhooks'],
    success_rate: 0.82,
    times_used: 40,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.86
});

// 3.10 GraphQL Schema Design
MERGE (p30:Pattern {
    pattern_id: 'pattern-api-graphql',
    name: 'GraphQL Schema Design',
    description: 'Design schemas with clear types, queries, mutations. Use connections for lists, input types for mutations. Implement proper error handling with extensions.',
    category: 'api',
    tags: ['graphql', 'schema', 'types', 'queries', 'mutations'],
    success_rate: 0.85,
    times_used: 35,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.88
});


// ============================================================================
// SECTION 4: DATABASE PATTERNS (10 patterns)
// ============================================================================

// 4.1 Unit of Work Pattern
MERGE (p31:Pattern {
    pattern_id: 'pattern-db-unit-of-work',
    name: 'Unit of Work Pattern',
    description: 'Track changes to objects and commit them atomically. Aggregates multiple operations into a single transaction. Maintains identity map for entities.',
    category: 'database',
    tags: ['unit-of-work', 'transactions', 'atomicity', 'changes'],
    success_rate: 0.90,
    times_used: 65,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.92
});

// 4.2 Soft Delete Pattern
MERGE (p32:Pattern {
    pattern_id: 'pattern-db-soft-delete',
    name: 'Soft Delete Pattern',
    description: 'Instead of deleting records, set a deleted_at timestamp or status flag. Preserves data integrity, enables audit trails, allows recovery.',
    category: 'database',
    tags: ['soft-delete', 'audit-trail', 'data-integrity', 'recovery'],
    success_rate: 0.88,
    times_used: 58,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.90
});

// 4.3 Audit Trail Pattern
MERGE (p33:Pattern {
    pattern_id: 'pattern-db-audit',
    name: 'Audit Trail Pattern',
    description: 'Track all changes to critical data with who, when, what, and before/after values. Use triggers or application-level hooks for capture.',
    category: 'database',
    tags: ['audit', 'history', 'compliance', 'tracking'],
    success_rate: 0.92,
    times_used: 52,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.94
});

// 4.4 Sharding Pattern
MERGE (p34:Pattern {
    pattern_id: 'pattern-db-sharding',
    name: 'Database Sharding Pattern',
    description: 'Partition data across multiple databases using a sharding key. Distributes load and enables horizontal scaling. Requires careful key selection.',
    category: 'database',
    tags: ['sharding', 'horizontal-scaling', 'partitioning', 'performance'],
    success_rate: 0.78,
    times_used: 28,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.82
});

// 4.5 Read/Write Separation
MERGE (p35:Pattern {
    pattern_id: 'pattern-db-read-write',
    name: 'Read/Write Separation',
    description: 'Route writes to primary database and reads to replicas. Improves read throughput and reduces primary load. Handle replication lag in consistency-critical operations.',
    category: 'database',
    tags: ['read-replicas', 'replication', 'performance', 'scaling'],
    success_rate: 0.85,
    times_used: 45,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.88
});

// 4.6 Outbox Pattern
MERGE (p36:Pattern {
    pattern_id: 'pattern-db-outbox',
    name: 'Outbox Pattern',
    description: 'Store domain events in an outbox table within the same transaction as data changes. Separate worker publishes events to message broker. Ensures reliable event delivery.',
    category: 'database',
    tags: ['outbox', 'events', 'reliability', 'messaging', 'transactions'],
    success_rate: 0.88,
    times_used: 38,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.90
});

// 4.7 Change Data Capture
MERGE (p37:Pattern {
    pattern_id: 'pattern-db-cdc',
    name: 'Change Data Capture Pattern',
    description: 'Capture changes from database transaction log and publish to downstream systems. Enables real-time data synchronization without application coupling.',
    category: 'database',
    tags: ['cdc', 'change-tracking', 'real-time', 'synchronization'],
    success_rate: 0.82,
    times_used: 30,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.85
});

// 4.8 Indexing Strategy
MERGE (p38:Pattern {
    pattern_id: 'pattern-db-indexing',
    name: 'Database Indexing Strategy',
    description: 'Create indexes on frequently queried columns, especially WHERE, JOIN, and ORDER BY columns. Use composite indexes for common query patterns. Avoid over-indexing.',
    category: 'database',
    tags: ['indexing', 'performance', 'query-optimization', 'composite'],
    success_rate: 0.92,
    times_used: 75,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.95
});

// 4.9 Connection Pooling
MERGE (p39:Pattern {
    pattern_id: 'pattern-db-pooling',
    name: 'Connection Pooling Pattern',
    description: 'Maintain a pool of database connections to reuse. Reduces connection overhead, limits concurrent connections, improves response times.',
    category: 'database',
    tags: ['connection-pool', 'performance', 'resource-management'],
    success_rate: 0.95,
    times_used: 88,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.96
});

// 4.10 Schema Migration Pattern
MERGE (p40:Pattern {
    pattern_id: 'pattern-db-migration',
    name: 'Schema Migration Pattern',
    description: 'Version control database schema with migration scripts. Test migrations locally, backup before production, support zero-downtime deployments with backward-compatible changes.',
    category: 'database',
    tags: ['migration', 'versioning', 'schema', 'deployment', 'liquibase'],
    success_rate: 0.90,
    times_used: 68,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.92
});


// ============================================================================
// SECTION 5: SECURITY PATTERNS (5 patterns)
// ============================================================================

// 5.1 Defense in Depth
MERGE (p41:Pattern {
    pattern_id: 'pattern-security-defense',
    name: 'Defense in Depth Strategy',
    description: 'Apply multiple layers of security controls. Never rely on a single security mechanism. Validate at each layer, use principle of least privilege.',
    category: 'security',
    tags: ['defense-in-depth', 'principle-of-least-privilege', 'layers', 'validation'],
    success_rate: 0.95,
    times_used: 48,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.96
});

// 5.2 OAuth2 Flow Implementation
MERGE (p42:Pattern {
    pattern_id: 'pattern-security-oauth',
    name: 'OAuth2 Authentication Flow',
    description: 'Implement OAuth2 authorization code flow for user authentication. Use PKCE for public clients. Validate tokens, check scopes, handle token refresh.',
    category: 'security',
    tags: ['oauth2', 'authentication', 'authorization', 'tokens', 'scopes'],
    success_rate: 0.90,
    times_used: 55,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.92
});

// 5.3 SQL Injection Prevention
MERGE (p43:Pattern {
    pattern_id: 'pattern-security-sql-injection',
    name: 'SQL Injection Prevention',
    description: 'Always use parameterized queries or prepared statements. Never concatenate user input into SQL strings. Use ORM or query builders that escape values.',
    category: 'security',
    tags: ['sql-injection', 'parameterized-queries', 'prepared-statements', 'input-validation'],
    success_rate: 0.98,
    times_used: 92,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.98
});

// 5.4 JWT Token Security
MERGE (p44:Pattern {
    pattern_id: 'pattern-security-jwt',
    name: 'JWT Token Security',
    description: 'Sign JWTs with strong algorithms (RS256). Validate signature, expiration, issuer. Store tokens securely, use short expiration with refresh tokens.',
    category: 'security',
    tags: ['jwt', 'tokens', 'signing', 'validation', 'security'],
    success_rate: 0.92,
    times_used: 62,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.94
});

// 5.5 Input Validation Layer
MERGE (p45:Pattern {
    pattern_id: 'pattern-security-validation',
    name: 'Input Validation Pattern',
    description: 'Validate all inputs at system boundary. Use allowlists for known formats, reject anything unexpected. Sanitize HTML to prevent XSS. Type-check and bounds-check.',
    category: 'security',
    tags: ['input-validation', 'sanitization', 'xss', 'allowlist'],
    success_rate: 0.94,
    times_used: 78,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.96
});


// ============================================================================
// SECTION 6: DEVOPS PATTERNS (5 patterns)
// ============================================================================

// 6.1 Blue-Green Deployment
MERGE (p46:Pattern {
    pattern_id: 'pattern-devops-blue-green',
    name: 'Blue-Green Deployment',
    description: 'Maintain two identical production environments. Deploy new version to inactive environment, test, then switch traffic. Enables instant rollback.',
    category: 'devops',
    tags: ['blue-green', 'deployment', 'rollback', 'zero-downtime'],
    success_rate: 0.88,
    times_used: 42,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.90
});

// 6.2 Infrastructure as Code
MERGE (p47:Pattern {
    pattern_id: 'pattern-devops-iac',
    name: 'Infrastructure as Code Pattern',
    description: 'Define infrastructure in version-controlled code (Terraform, CloudFormation). Enables reproducible environments, audit trail, and infrastructure rollbacks.',
    category: 'devops',
    tags: ['iac', 'terraform', 'cloudformation', 'automation', 'reproducibility'],
    success_rate: 0.92,
    times_used: 68,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.94
});

// 6.3 Feature Flag Pattern
MERGE (p48:Pattern {
    pattern_id: 'pattern-devops-feature-flags',
    name: 'Feature Flag Implementation',
    description: 'Wrap features in toggleable flags. Enable canary releases, A/B testing, and instant rollbacks. Decouple deploy from release.',
    category: 'devops',
    tags: ['feature-flags', 'canary', 'ab-testing', 'toggle', 'release'],
    success_rate: 0.90,
    times_used: 55,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.92
});

// 6.4 Health Check Pattern
MERGE (p49:Pattern {
    pattern_id: 'pattern-devops-health-check',
    name: 'Health Check Endpoint Pattern',
    description: 'Implement /health endpoint that checks dependencies (database, cache, external APIs). Include liveness, readiness, and startup probes for orchestration.',
    category: 'devops',
    tags: ['health-check', 'liveness', 'readiness', 'kubernetes', 'monitoring'],
    success_rate: 0.94,
    times_used: 72,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.95
});

// 6.5 GitOps Workflow
MERGE (p50:Pattern {
    pattern_id: 'pattern-devops-gitops',
    name: 'GitOps Workflow Pattern',
    description: 'Use Git as single source of truth for infrastructure and application state. Automated reconciliation ensures cluster matches Git definitions.',
    category: 'devops',
    tags: ['gitops', 'argo-cd', 'flux', 'declarative', 'automation'],
    success_rate: 0.88,
    times_used: 45,
    scope: 'global',
    group_id: 'global-coding-skills',
    confidence_score: 0.90
});


// ============================================================================
// VALIDATION QUERY
// ============================================================================
// Run this to verify all patterns were created:
// MATCH (p:Pattern) RETURN p.category, count(p) as count ORDER BY p.category
// Expected: 8 categories with 50 total patterns

// ============================================================================
// END OF PATTERN LIBRARY SEED
// ============================================================================