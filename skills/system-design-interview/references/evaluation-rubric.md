# Evaluation Rubric

This rubric is for internal use during evaluation. Never reveal these criteria to the candidate during the interview.

## Level Definitions

### L5 (Senior) - "Build a Working System"

**Core Expectation:** Can design and build a working system for their team.

**Positive Signals:**
- Designs a correct solution that meets stated requirements
- Makes reasonable technology choices with basic justification
- Handles the happy path well
- Identifies major components and their interactions
- Can discuss basic scaling strategies (horizontal scaling, caching)

**Acceptable Gaps:**
- May not proactively identify edge cases
- May miss cross-team coordination concerns
- May not anticipate all failure modes
- Focus primarily on single-team ownership

**Red Flags:**
- Cannot produce a working design
- Major technical misconceptions
- Unable to explain their choices
- Ignores stated requirements

---

### L6 (Staff) - "Architect, Secure, and Scale"

**Core Expectation:** Can architect, secure, and scale a system that works across teams and over time, and reason explicitly about trade-offs and failure modes.

**Positive Signals:**
- Proactively scopes requirements before designing
- Asks about scale, SLOs, constraints, and business context
- Explicit trade-off reasoning: "I chose X over Y because..."
- Anticipates failure modes without prompting
- Considers security, compliance, and observability
- Discusses team boundaries and ownership
- Thinks about system evolution over 2-3 years
- Handles ambiguity gracefully
- Can discuss alternatives they considered

**Expected Depth:**
- Specific numbers for scale (QPS, storage, latency targets)
- Detailed data models and access patterns
- Clear consistency vs availability trade-offs
- Multi-region and disaster recovery considerations
- API versioning and backward compatibility
- Monitoring and alerting strategy

**Red Flags:**
- Jumps to solution without scoping
- Cannot articulate trade-offs
- Surprised by failure scenario questions
- No mention of security or compliance
- Single-team thinking only

---

### L7 (Senior Staff) - "Platform Thinking"

**Core Expectation:** Operates at org/platform level, defining standards and anticipating long-term risks.

**Positive Signals:**
- Designs platform-level abstractions others will build on
- Defines standards and patterns for the organization
- Industry context: references how similar systems work at scale
- Long-term technical strategy (3-5 year horizon)
- Identifies risks that affect multiple teams
- Considers second-order effects of design decisions
- Thinks about governance and operational burden
- Can discuss build vs buy trade-offs at org scale

**Expected Depth:**
- Platform primitives and extension points
- Organizational adoption strategy
- Migration paths from existing systems
- Cost modeling and resource planning
- Compliance across jurisdictions
- Vendor strategy and lock-in considerations

**Red Flags:**
- Thinks only at single-system level
- Cannot discuss organizational implications
- No awareness of industry patterns
- Short-term thinking only

---

## Signals Checklist

Track these during the interview:

### Scoping & Requirements
- [ ] Asked clarifying questions before designing
- [ ] Identified functional requirements
- [ ] Identified non-functional requirements (scale, latency, availability)
- [ ] Discussed SLOs/SLAs explicitly
- [ ] Asked about user patterns and access patterns

### Technical Depth
- [ ] Provided specific scale numbers
- [ ] Discussed data model in detail
- [ ] Explained consistency model choices
- [ ] Addressed caching strategy
- [ ] Covered API design

### Resilience & Scale
- [ ] Mentioned failure modes proactively
- [ ] Discussed retry and timeout strategies
- [ ] Addressed partial failures
- [ ] Covered multi-region/DR
- [ ] Discussed capacity planning

### Operational Excellence
- [ ] Considered security/compliance
- [ ] Discussed observability (metrics, logs, traces)
- [ ] Addressed deployment strategy
- [ ] Mentioned on-call and debugging

### Organizational Awareness (L6+)
- [ ] Thought about team ownership boundaries
- [ ] Discussed cross-team coordination
- [ ] Considered system evolution over time
- [ ] Addressed backward compatibility

### Platform Thinking (L7)
- [ ] Designed reusable abstractions
- [ ] Discussed standards for others to follow
- [ ] Referenced industry patterns
- [ ] Considered organizational adoption

---

## Scoring Guidance

**Strong L5:** Hits most L5 signals, some L6 signals emerging.

**Strong L6:** Consistently demonstrates L6 signals, may show some L7 thinking.

**Strong L7:** Demonstrates L6 signals as baseline, consistently shows platform-level thinking.

**Level Gap:** When target level is L6 but demonstrated level is L5, focus feedback on the specific L6 signals that were missing.
