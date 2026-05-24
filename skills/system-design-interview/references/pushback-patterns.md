# Pushback Patterns

Use these techniques to challenge vague, incomplete, or surface-level answers. Always push back politely but persistently.

## When Answers Are Vague

The candidate gives a generic answer without specifics.

**Patterns:**
- "Can you be more specific about how [X] works?"
- "What exactly happens when a request hits [component]?"
- "Walk me through the data flow step by step."
- "Let's trace through a specific example. What happens when [user action]?"
- "You mentioned [technology]. How specifically would you use it here?"

**Example:**
- Candidate: "We'd use a message queue for async processing."
- You: "Which message queue, and why? Walk me through what happens when a message is published."

---

## When Missing Failure Modes

The candidate describes the happy path but doesn't address what can go wrong.

**Patterns:**
- "What happens if [component] becomes unavailable?"
- "How does the system behave during a network partition?"
- "What's your blast radius if this deployment goes wrong?"
- "What if the database write succeeds but the cache update fails?"
- "How do you handle poison messages in the queue?"
- "What happens if this operation takes 10x longer than expected?"

**Example:**
- Candidate: "The service calls the database and returns the result."
- You: "What happens if the database is slow or unavailable? How does the client know?"

---

## When Missing Scale Considerations

The candidate's design works for small scale but doesn't address growth.

**Patterns:**
- "How does this change at 10x current load?"
- "Where are the bottlenecks in this design?"
- "How would you shard this data?"
- "What's your approach to horizontal scaling here?"
- "How do you handle hot spots or uneven load distribution?"
- "What happens during a traffic spike?"

**Example:**
- Candidate: "We store user data in PostgreSQL."
- You: "How do you scale this when you have 100 million users? What's your sharding strategy?"

---

## When Missing Trade-offs

The candidate presents a solution without discussing alternatives or costs.

**Patterns:**
- "What alternatives did you consider?"
- "What are you giving up with this approach?"
- "Why this database over [alternative]?"
- "What's the downside of this choice?"
- "If you had to defend this decision to a skeptical colleague, what would you say?"
- "What would make you reconsider this approach?"

**Example:**
- Candidate: "We'll use eventual consistency."
- You: "What are you giving up by not having strong consistency? When might that cause problems?"

---

## When Scope Is Too Narrow

The candidate focuses only on their component without considering the broader system.

**Patterns:**
- "How would another team integrate with this?"
- "Who owns the contract between these services?"
- "How does this fit into the broader platform?"
- "What happens when the upstream service changes their API?"
- "How do you coordinate deployments across these teams?"
- "Who gets paged when this fails at 3am?"

**Example:**
- Candidate: "Our service handles all the business logic."
- You: "How does the mobile team integrate with you? What contract do you expose?"

---

## When Design Is Overly Complex

The candidate over-engineers the solution beyond what's needed.

**Patterns:**
- "Is there a simpler approach that meets the requirements?"
- "What's the MVP version of this?"
- "Which parts are essential vs nice-to-have?"
- "Do you need all this complexity on day one?"
- "What's the operational cost of maintaining this?"
- "How does a new engineer onboard to this system?"

**Example:**
- Candidate: "We'll use a distributed consensus protocol for all writes."
- You: "What's the simplest thing that could work? Do you need consensus for this use case?"

---

## When Skipping Requirements

The candidate jumps to design without understanding the problem.

**Patterns:**
- "Before we go further, what questions do you have about the requirements?"
- "What scale are we designing for?"
- "What's the availability target?"
- "Who are the users and what are their access patterns?"
- "What are the non-negotiable requirements vs nice-to-haves?"

**Example:**
- Candidate: "Let me start by drawing the architecture..."
- You: "Hold on—before we dive into the design, what questions do you have for me about the requirements?"

---

## When Answers Are Textbook

The candidate gives memorized answers without connecting to the specific problem.

**Patterns:**
- "How does that apply specifically to our problem?"
- "What would you actually do here, given our constraints?"
- "That's the general pattern, but what's the right choice for us?"
- "I've heard that before—can you tell me why it matters here?"

**Example:**
- Candidate: "We should use CQRS and event sourcing."
- You: "Those are powerful patterns. What specifically about our use case makes them the right choice?"

---

## When Confidence Exceeds Evidence

The candidate is very confident but hasn't justified their position.

**Patterns:**
- "What evidence supports that assumption?"
- "How do you know that will scale?"
- "Have you seen this work in practice?"
- "What would change your mind about this approach?"
- "What's the biggest risk you see with this design?"

**Example:**
- Candidate: "This will easily handle the load."
- You: "What makes you confident? Can you walk me through the capacity math?"

---

## Tone Guidance

- Be curious, not adversarial: "I'm curious how..." instead of "But what about..."
- Acknowledge their point before probing: "That makes sense. Now, what happens when..."
- Use silence effectively—don't fill pauses immediately
- If they struggle, offer a hint rather than the answer: "Have you considered...?"
