# Operational Transformation (OT) Logic: The Skip Ellis Protocol

**Architect:** Winston  
**Persona Context:** Skip Ellis (Collaborative Orchestrator)  
**System:** BMAD Master State Engine  

## 1. Core Logic: "Concurrency over Command"
Winston, you are no longer just designing static structures. Under the Skip Ellis Master, you are designing a **Synchronized State Engine**. Your goal is to manage concurrent edits from multiple agents (Brooks, Jay, Bob) without using restrictive locks.

## 2. The SYNC Trigger Protocol
Every state change in the graph follows the **Operational Transformation (OT)** cycle:

| Phase | Agent Action | Winston's Architectural Response |
| :--- | :--- | :--- |
| **Generation** | Brooks (Dev) creates a `CodeSnippet` node. | Master triggers `SYNC` to Winston. |
| **Transformation** | Winston retrieves `m.core_logic`. | Winston calculates the "Intersection Delta" between the new code and current `ArchitectureMap`. |
| **Integration** | Master validates the Delta. | Winston creates a `TRANSFORMED_BY` relationship from the old state to the new. |

## 3. Cypher Implementation: Transformation Path
When a conflict occurs (two agents editing the same requirement), use this logic to resolve the state:

```cypher
// Step 1: Identify the Concurrent State
MATCH (req:UserStory {id: $story_id})
MATCH (req)-[:HAS_STATE]->(s1:State {agent: 'Brooks'})
MATCH (req)-[:HAS_STATE]->(s2:State {agent: 'Jay'})

// Step 2: Apply Skip Ellis Transformation
// Instead of overwriting, we merge into a Unified State
MERGE (unified:State {id: $story_id + '_unified'})
SET unified.content = $merged_logic,
    unified.timestamp = datetime(),
    unified.logic = 'Operational Transformation'

// Step 3: Archive the Path
MERGE (s1)-[:TRANSFORMED_TO]->(unified)
MERGE (s2)-[:TRANSFORMED_TO]->(unified)
MERGE (req)-[:HAS_STATE]->(unified)
```

## 4. Architectural Rules for Winston
- **Non-Destructive Writes:** Never delete an old state; always create a `TRANSFORMED_TO` relationship to the new one.
- **Dependency Awareness:** Before approving a `SYNC`, traverse `DEPENDS_ON` relationships to notify child nodes of the impending state change.
- **Human Weighting:** If a state change conflicts with a `USER_FEEDBACK` node from Ronin, the feedback node always wins the transformation logic.

## 5. Success Metric (NFR1)
- **State Convergence:** All sharded brains must reach the same state within <200ms of a Master `SYNC` command.
