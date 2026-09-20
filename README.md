# 🤖 Agentic Customer Support Associate

## Final Year Major Project

An AI-powered customer support system that uses an **agentic architecture** to understand customer queries, retrieve relevant support information, interact with controlled backend tools, maintain conversational context, and provide transparent agent activity.

The system combines:

- ReAct-style agent routing
- Retrieval-Augmented Generation (RAG)
- Semantic search
- Conversation memory
- Controlled backend tools
- PostgreSQL database
- Order management
- Product search
- Support ticket management
- Knowledge-base policies
- Agent activity tracing
- React-based customer support interface

---

# 📌 Project Overview

Traditional customer-support systems usually depend on static FAQs or manually operated support dashboards.

Our system provides an AI-powered support assistant that can:

1. Understand the customer's request.
2. Determine what type of request it is.
3. Check conversation memory.
4. Select an appropriate controlled tool.
5. Retrieve information from the database or knowledge base.
6. Generate a response using the obtained information.
7. Maintain context for follow-up questions.
8. Display the agent's processing activity to the user.

### Example

Customer:

> Where is my order ORD1002?

The agent identifies this as an **order-status query** and calls the controlled order tool.

Customer:

> When will it arrive?

Instead of treating this as a completely new question, the system uses conversation memory to remember:

```text
Previous order: ORD1002