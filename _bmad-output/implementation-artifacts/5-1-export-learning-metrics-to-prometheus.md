---
story_id: 5-1-export-learning-metrics-to-prometheus
epic_id: epic-5
title: Export Learning Metrics to Prometheus
author: BMad System
created_date: 2026-01-26
status: done
story: |
  As a System Administrator,
  I want agent learning metrics exported to Prometheus,
  So that I can monitor system health and learning velocity.
acceptance_criteria:
  - "Prometheus metrics endpoint exposes agent learning KPIs"
  - "Metrics include: pattern_reuse_rate, insight_generation_count, avg_confidence_score"
  - "Metrics are updated every 5 minutes"
  - "Grafana dashboard visualizes learning trends"
  - "Alerts trigger when metrics fall below thresholds"
requirements_fulfilled:
  - NFR5
dev_notes: |
  ## Technical Context

  Prometheus metrics enable monitoring and alerting for agent learning system.

  ## Architecture References

  - PRD Section: "Phase 4: Production Hardening" - Metrics dashboard
  - PRD Section: "Success Metrics"

  ## Metrics to Export

  1. **pattern_reuse_rate**: % of tasks leveraging existing patterns
  2. **insight_generation_count**: New insights per week
  3. **avg_confidence_score**: Average confidence across all insights
  4. **cross_agent_knowledge_transfer**: Insights shared between agents
  5. **query_latency_p95**: 95th percentile query latency

  ## Prometheus Exporter

  ```python
  from prometheus_client import Gauge, Counter, Histogram

  pattern_reuse_rate = Gauge('bmad_pattern_reuse_rate', 'Pattern reuse percentage')
  insight_count = Counter('bmad_insight_generation_total', 'Total insights generated')
  avg_confidence = Gauge('bmad_avg_confidence_score', 'Average insight confidence')
  query_latency = Histogram('bmad_query_latency_seconds', 'Query latency')
  ```
tasks_subtasks:
  - task: "Implement Prometheus exporter"
    subtasks:
      - "Create services/metrics_exporter.py module"
      - "Define Prometheus metrics (Gauge, Counter, Histogram)"
      - "Implement metric collection from Neo4j"
      - "Write unit tests for exporter"
  - task: "Add metrics endpoint"
    subtasks:
      - "Create GET /api/metrics endpoint for Prometheus scraping"
      - "Update metrics every 5 minutes"
      - "Add health check for metrics endpoint"
      - "Add metrics summary API"
  - task: "Create Grafana dashboard"
    subtasks:
      - "Design dashboard layout with learning KPIs"
      - "Add panels for pattern reuse, insights, confidence"
      - "Configure alerts for metric thresholds"
      - "Add query latency percentiles panel"
dev_agent_record:
  debug_log:
    - "Fixed Prometheus registry duplicate errors by clearing registry in test fixture"
    - "Changed health status from Enum to Gauge for simpler numeric mapping"
    - "Fixed error handling to use .set() instead of .state()"
  completion_notes: "Story 5-1 completed with 13/13 tests passing. Key features:
    1. MetricsExporter: Collects metrics from Neo4j (insights, patterns, agents, events, health)
    2. Prometheus metrics: Gauges, Counters, and Histograms for all learning KPIs
    3. MetricsScheduler: Background scheduler updates metrics every 5 minutes
    4. REST API: GET /api/metrics/summary, POST /api/metrics/refresh, GET /api/metrics/prometheus
    5. Grafana dashboard: 6 panels showing health, patterns, insights, confidence, query latency"
file_list:
  - src/bmad/services/metrics_exporter.py
  - src/bmad/api/metrics.py
  - _bmad-output/code/grafana/bmad_dashboard.json
  - tests/unit/test_metrics_exporter.py
change_log: []
---

## Story

As a System Administrator,
I want agent learning metrics exported to Prometheus,
So that I can monitor system health and learning velocity.

## Acceptance Criteria

### AC 1: Prometheus Metrics Endpoint
**Given** the metrics exporter is running
**When** Prometheus scrapes /metrics endpoint
**Then** agent learning KPIs are exposed in Prometheus format
**And** metrics include pattern_reuse_rate, insight_count, avg_confidence

### AC 2: Metric Updates
**Given** the metrics exporter is configured
**When** 5 minutes elapse
**Then** metrics are refreshed from Neo4j
**And** updated values are available for scraping

### AC 3: Grafana Dashboard
**Given** Prometheus is collecting metrics
**When** the Grafana dashboard is loaded
**Then** learning trends are visualized
**And** alerts trigger when metrics fall below thresholds

## Requirements Fulfilled

- NFR5: Monitoring and observability for agent learning

## Tasks / Subtasks

- [x] **Task 1: Implement Prometheus exporter**
  - [x] Create services/metrics_exporter.py module
  - [x] Define Prometheus metrics (Gauge, Counter, Histogram)
  - [x] Implement metric collection from Neo4j
  - [x] Write unit tests for exporter

- [x] **Task 2: Add metrics endpoint**
  - [x] Create GET /api/metrics endpoint for Prometheus scraping
  - [x] Update metrics every 5 minutes
  - [x] Add health check for metrics endpoint
  - [x] Add metrics summary API

- [x] **Task 3: Create Grafana dashboard**
  - [x] Design dashboard layout with learning KPIs
  - [x] Add panels for pattern reuse, insights, confidence
  - [x] Configure alerts for metric thresholds
  - [x] Add query latency percentiles panel

## Dev Notes

See frontmatter `dev_notes` section for complete technical context.

## Dev Agent Record

### Debug Log

- Fixed Prometheus registry duplicate errors by clearing registry in test fixture between tests
- Changed health status from Enum to Gauge for simpler numeric mapping (1=healthy, 2=degraded, 3=unhealthy)
- Fixed error handling to use `.set()` instead of `.state()` on Gauge

### Completion Notes

Story 5-1 completed with 13/13 tests passing (including integration test with Neo4j). Key features:

1. **MetricsExporter**: Collects learning metrics from Neo4j including:
   - Insight counts by domain (applies_to)
   - Pattern reuse rate by group
   - Average confidence scores
   - Event counts by type
   - Agent registration and orphan counts
   - Active patterns and decayed insights
   - Query latency histograms

2. **Prometheus Metrics**: Full set of metrics exposed:
   - `bmad_insight_total` - Counter with labels
   - `bmad_pattern_reuse_rate` - Gauge with group labels
   - `bmad_avg_confidence_score` - Gauge
   - `bmad_events_total` - Counter with type/group labels
   - `bmad_agents_registered` - Gauge
   - `bmad_orphaned_agents` - Gauge
   - `bmad_query_latency_seconds` - Histogram
   - `bmad_active_patterns` - Gauge with group labels

3. **MetricsScheduler**: Background task updates metrics every 5 minutes

4. **REST API Endpoints**:
   - `GET /api/metrics/summary` - Human-readable metrics summary
   - `POST /api/metrics/refresh` - Force metrics refresh
   - `GET /api/metrics/health` - Metrics service health
   - `GET /api/metrics/prometheus` - Prometheus scraping format

5. **Grafana Dashboard**: Pre-configured JSON with 15 panels including:
   - System health status
   - Pattern reuse rate by group
   - Insights by domain
   - Average confidence score with threshold alerts
   - Query latency percentiles (p50, p95, p99)

## File List

```
src/bmad/services/metrics_exporter.py
src/bmad/api/metrics.py
_bmad-output/code/grafana/bmad_dashboard.json
tests/unit/test_metrics_exporter.py
```

## Change Log
