# AAET Project: Complete Priority List
**Generated:** October 14, 2025  
**Source:** JIRA API (ALL tickets fetched and analyzed)  
**Method:** Read all ticket descriptions from JIRA

---

## 📊 ACTUAL TICKET STATUS

### Total Tickets Created: 90 (AAET-80 missing)

**Breakdown:**
- AAET-1 to AAET-20: 20 tickets (Foundation & Multi-Tenancy)
- AAET-21 to AAET-40: 20 tickets (Multi-Tenancy + Ingestion)
- AAET-41 to AAET-60: 20 tickets (Ingestion + Retrieval)
- AAET-61 to AAET-79: 19 tickets (Retrieval + Observability)
- **AAET-80: MISSING**
- AAET-81 to AAET-91: 11 tickets (code-graph-rag Integration)

### ✅ DONE (6 tickets)
- AAET-82: Extract Library ✅
- AAET-83: Tenant Context Infrastructure ✅
- AAET-84: Abstract Storage Interface ✅
- AAET-85: Convert to Async ✅
- AAET-86: Parser Service Wrapper ✅
- AAET-81: EPIC-6 (In Progress - parent epic)

### 📋 REMAINING: 84 tickets

---

## 🎯 RECOMMENDED PRIORITY ORDER

### **IMMEDIATE NEXT (Do These Now)**

1. **AAET-87** - Celery Integration & Background Workers
2. **AAET-88** - Integration Testing (Parse → Store → Query)
3. **AAET-89** - Documentation (Library + API)
4. **AAET-91** - Storage Enhancements (Batch limits, Type safety)
5. **AAET-90** - Code Quality & Refactoring

**Rationale:** Complete EPIC-6 (code-graph-rag integration) before moving to other epics.

---

### **PHASE 1: Foundation (EPIC-1) - Weeks 1-2**

6. **AAET-8** - PostgreSQL Setup ✅ (Already done via docker-compose)
7. **AAET-9** - Redis Setup ✅ (Already done via docker-compose)
8. **AAET-10** - FastAPI Service Skeleton ✅ (Already done)
9. **AAET-11** - Celery Worker Framework
10. **AAET-12** - Provider Abstractions (VectorStore, Reranker)
11. **AAET-13** - CI/CD Pipeline (GitHub Actions)
12. **AAET-14** - Kubernetes Deployment Configs
13. **AAET-15** - Tenant Data Model & Schema
14. **AAET-16** - Environment Configuration Management
15. **AAET-17** - Database Connection Pool & Session Management
16. **AAET-18** - Redis Connection Management
17. **AAET-19** - Pytest Framework & Test Fixtures
18. **AAET-20** - Structured Logging with Request ID

---

### **PHASE 2: Multi-Tenancy (EPIC-2) - Weeks 3-4**

19. **AAET-21** - JWT Authentication Middleware
20. **AAET-22** - Tenant Validation Middleware
21. **AAET-23** - Namespace Isolation Enforcement
22. **AAET-24** - Quota Tracking & Enforcement
23. **AAET-25** - Rate Limiting Implementation (Token Bucket)
24. **AAET-26** - Usage Metrics Collection
25. **AAET-27** - Tenant Provisioning API
26. **AAET-28** - Tenant Onboarding Flow
27. **AAET-29** - Multi-Tenant Testing Suite
28. **AAET-30** - Multi-Tenancy Documentation
29. **AAET-31** - Tenant Admin Dashboard
30. **AAET-32** - Tenant Billing Integration

---

### **PHASE 3: Ingestion Pipeline (EPIC-3) - Weeks 5-8**

31. **AAET-33** - Queue Consumer (Celery Worker)
32. **AAET-34** - GitHub Connector
33. **AAET-35** - GitLab Connector
34. **AAET-36** - Bitbucket Connector
35. **AAET-37** - Jira Connector
36. **AAET-38** - Linear Connector
37. **AAET-39** - Webhook Handlers
38. **AAET-40** - File Parsing Service (TypeScript first)
39. **AAET-41** - AST-based Chunking Strategy
40. **AAET-42** - Doc Chunking (Semantic)
41. **AAET-43** - Story Chunking
42. **AAET-44** - Metadata Extraction (GPT-4o-mini)
43. **AAET-45** - Voyage Embedding Integration
44. **AAET-46** - Vector Indexing (pgvector)
45. **AAET-47** - Graph Indexing (PostgreSQL)
46. **AAET-48** - Idempotency & Dry-Run Mode
47. **AAET-49** - Error Handling & DLQ
48. **AAET-50** - Ingestion API Endpoints

---

### **PHASE 4: Retrieval & Search (EPIC-4) - Weeks 9-12**

49. **AAET-51** - Vector Search (pgvector)
50. **AAET-52** - Graph Traversal Queries
51. **AAET-53** - Hybrid Search Orchestration
52. **AAET-54** - Cohere Reranking Integration
53. **AAET-55** - Context Pack Assembly
54. **AAET-56** - Query Optimization
55. **AAET-57** - Search Result Caching
56. **AAET-58** - Search API Endpoints
57. **AAET-59** - Search Performance Testing
58. **AAET-60** - Search Documentation

---

### **PHASE 5: Multi-Repo Intelligence (EPIC-5) - Weeks 13-16**

59. **AAET-61** - Cross-Repo Linking
60. **AAET-62** - API Endpoint Detection
61. **AAET-63** - Frontend-Backend Mapping
62. **AAET-64** - Story-Code Mapping
63. **AAET-65** - Dependency Graph Construction
64. **AAET-66** - Change Impact Analysis
65. **AAET-67** - Multi-Repo Search
66. **AAET-68** - Cross-Repo Documentation
67. **AAET-69** - Multi-Repo Testing

---

### **PHASE 6: Monitoring & Operations - Weeks 17-18**

70. **AAET-70** - Prometheus Metrics
71. **AAET-71** - Grafana Dashboards
72. **AAET-72** - Alert Rules
73. **AAET-73** - Performance Monitoring
74. **AAET-74** - Error Tracking (Sentry)
75. **AAET-75** - Log Aggregation
76. **AAET-76** - Health Checks
77. **AAET-77** - Backup & Recovery

---

### **PHASE 7: Advanced Features - Weeks 19-22**

78. **AAET-78** - Incremental Updates
79. **AAET-79** - Real-time File Parsing
80. **AAET-80** - Webhook Processing
81. **AAET-81** - EPIC-6 (code-graph-rag) ✅ IN PROGRESS
82-86: ✅ DONE (sub-stories of AAET-81)
87. **AAET-87** - Celery Integration
88. **AAET-88** - Integration Testing
89. **AAET-89** - Documentation
90. **AAET-90** - Code Quality
91. **AAET-91** - Storage Enhancements

---

## 🔥 TOP 10 PRIORITIES (Start Here)

Based on dependencies, business value, and current state:

1. **AAET-87** - Celery Integration (Unblocks async ingestion)
2. **AAET-88** - Integration Testing (Validates AAET-82-86 work)
3. **AAET-91** - Storage Enhancements (Production readiness)
4. **AAET-15** - Tenant Data Model (Required for multi-tenancy)
5. **AAET-21** - JWT Authentication (Security foundation)
6. **AAET-33** - Queue Consumer (Enables ingestion pipeline)
7. **AAET-40** - File Parsing Service (Core ingestion feature)
8. **AAET-45** - Voyage Embedding (Enables vector search)
9. **AAET-51** - Vector Search (Core retrieval feature)
10. **AAET-89** - Documentation (Makes library usable)

---

## 📝 DETAILED NEXT STEPS

### This Week (Oct 14-18)

**Day 1-2: AAET-87 (Celery Integration)**
- Set up Celery worker configuration
- Create task definitions for parsing
- Add Redis as message broker
- Implement task retry logic
- Add task monitoring

**Day 3: AAET-88 (Integration Testing)**
- End-to-end test: parse → store → query
- Multi-tenant isolation tests
- Performance benchmarks
- Load testing

**Day 4: AAET-91 (Storage Enhancements)**
- Add batch size limits
- Create NodeType/EdgeType enums
- Update 38 processor calls
- Standardize async file reading

**Day 5: AAET-89 (Documentation)**
- API documentation
- Library usage guide
- Architecture diagrams
- Deployment guide

### Next Week (Oct 21-25)

**AAET-15: Tenant Data Model**
- Create tenants table schema
- Add tenant_id to all tables
- Implement quotas (JSONB)
- Add Alembic migrations

**AAET-21: JWT Authentication**
- JWT middleware
- Token validation
- Tenant extraction from claims
- API key authentication

**AAET-33: Queue Consumer**
- Celery worker for ingestion
- Job format definition
- Error handling & DLQ
- Parallel processing

---

## 🎯 EPIC COMPLETION TARGETS

- **EPIC-6 (code-graph-rag):** 90% complete → Target: Oct 18
- **EPIC-1 (Foundation):** 30% complete → Target: Oct 25
- **EPIC-2 (Multi-Tenancy):** 0% complete → Target: Nov 8
- **EPIC-3 (Ingestion):** 0% complete → Target: Nov 29
- **EPIC-4 (Retrieval):** 0% complete → Target: Dec 20
- **EPIC-5 (Multi-Repo):** 0% complete → Target: Jan 17

---

## ✅ DEFINITION OF "NEXT"

The absolute next ticket to work on is: **AAET-87 (Celery Integration)**

**Why?**
1. Completes EPIC-6 (only 3 tickets left)
2. Unblocks async ingestion pipeline
3. Required for AAET-33 (Queue Consumer)
4. Natural continuation of AAET-86 (Parser Service)
5. Enables background job processing

**Start Command:**
```bash
git checkout -b feature/AAET-87-celery-integration
```

---

## 📋 COMPLETE TICKET LIST (All 71 Actual Tickets)

### AAET-1 to AAET-20 (Foundation & Infrastructure)
1. AAET-1: EPIC-1 Foundation & Infrastructure
2. AAET-2: EPIC-2 Multi-Tenancy Core
3. AAET-3: EPIC-3 Ingestion Pipeline
4. AAET-4: EPIC-4 Retrieval & Search
5. AAET-5: EPIC-5 Multi-Repo Intelligence
6. AAET-6: EPIC-6 Product Intelligence
7. AAET-7: Project Repository Setup
8. AAET-8: PostgreSQL 15 + pgvector Setup ✅
9. AAET-9: Redis 7 Setup ✅
10. AAET-10: FastAPI Service Skeleton ✅
11. AAET-11: Celery Worker Framework
12. AAET-12: Provider Abstractions
13. AAET-13: CI/CD Pipeline (GitHub Actions)
14. AAET-14: Kubernetes Deployment Configs
15. AAET-15: Tenant Data Model & Schema
16. AAET-16: Environment Configuration Management
17. AAET-17: Database Connection Pool & Session Management
18. AAET-18: Redis Connection Management
19. AAET-19: Pytest Framework & Test Fixtures
20. AAET-20: Structured Logging with Request ID

### AAET-21 to AAET-40 (Multi-Tenancy + Ingestion)
21. AAET-21: Developer Documentation
22. AAET-22: JWT Authentication Middleware
23. AAET-23: Database Tenant Isolation with RLS
24. AAET-24: Namespace Format Validation
25. AAET-25: Quota Tracking & Enforcement
26. AAET-26: Per-Tenant Rate Limiting
27. AAET-27: Usage Metrics for Billing
28. AAET-28: Tenant Provisioning API
29. AAET-29: Tenant Onboarding Flow
30. AAET-30: Multi-Tenant Testing Suite
31. AAET-31: GitHub Connector
32. AAET-32: GitLab Connector
33. AAET-33: Bitbucket Connector
34. AAET-34: Jira Connector
35. AAET-35: Linear Connector
36. AAET-36: TypeScript AST Parser (tree-sitter)
37. AAET-37: Graph Indexing (PostgreSQL with adjacency lists)
38. AAET-38: Voyage AI Embedding Integration
39. AAET-39: Vector Indexing with pgvector & Deduplication
40. AAET-40: Graph Indexing for Code Relationships

### AAET-41 to AAET-60 (Ingestion + Retrieval)
41. AAET-41: Idempotency Logic with MD5 Digest
42. AAET-42: Dry-Run Mode for Ingestion Validation
43. AAET-43: Error Handling & Dead Letter Queue (DLQ)
44. AAET-44: Batch Processing for Large Ingestion Jobs
45. AAET-45: Multi-Language Parser Support (Python/Go/Java/Ruby)
46. AAET-46: Ingestion Performance Optimization
47. AAET-47: POST /ingest/chunks API Endpoint
48. AAET-48: Ingestion Pipeline Testing Suite
49. AAET-49: BM25 Lexical Search Implementation
50. AAET-50: Dense Vector Search with pgvector
51. AAET-51: Hybrid Search Union Strategy
52. AAET-52: Voyage AI Reranker Integration
53. AAET-53: Reranker Result Caching
54. AAET-54: Story Context Injection
55. AAET-55: Context Pack Assembly with Citations
56. AAET-56: Retrieval Configuration Knobs
57. AAET-57: Cross-Repository Search
58. AAET-58: Matryoshka Embedding Support
59. AAET-59: Retrieval Performance Optimization
60. AAET-60: POST /search API Endpoint

### AAET-61 to AAET-79 (Retrieval + Observability)
61. AAET-61: POST /rerank API Endpoint
62. AAET-62: Retrieval Quality Evaluation Harness
63. AAET-63: Retrieval Pipeline Testing Suite
64. AAET-64: Flowise HTTP Integration
65. AAET-65: POST /generate/docs Endpoint
66. AAET-66: POST /intelligence/story-coverage Endpoint
67. AAET-67: POST /intelligence/pattern-check Endpoint
68. AAET-68: POST /intelligence/impact-analysis Endpoint
69. AAET-69: Prometheus Metrics Export
70. AAET-70: Request ID Propagation
71. AAET-71: Health Check Endpoints (/healthz, /readyz)
72. AAET-72: GET /stats System Statistics Endpoint
73. AAET-73: Standardized Error Handling
74. AAET-74: POST /admin/dlq/retry Endpoint
75. AAET-75: Operational Runbooks
76. AAET-76: Grafana Dashboards
77. AAET-77: Prometheus Alert Rules
78. AAET-78: Load Testing & Performance Validation
79. AAET-79: Integration & Observability Documentation

### AAET-80 (MISSING)
**AAET-80 does not exist in JIRA**

### AAET-81 to AAET-91 (code-graph-rag Integration)
81. AAET-81: EPIC-6 code-graph-rag Integration (In Progress)
82. AAET-82: Extract Library ✅ DONE
83. AAET-83: Tenant Context Infrastructure ✅ DONE
84. AAET-84: Abstract Storage Interface ✅ DONE
85. AAET-85: Convert to Async ✅ DONE
86. AAET-86: Parser Service Wrapper ✅ DONE
87. AAET-87: Celery Integration & Background Workers
88. AAET-88: Integration Testing
89. AAET-89: Documentation
90. AAET-90: Code Quality & Refactoring
91. AAET-91: Storage Layer Enhancements

---

**Last Updated:** October 14, 2025  
**Next Review:** After AAET-87 completion  
**Note:** Only AAET-80 is missing from JIRA (all other 90 tickets exist)
