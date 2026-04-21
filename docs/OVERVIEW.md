# Query MCP — Overview

## The Problem It Solves

Business leaders and operators need answers from their data every day. But getting those answers typically means:

- Filing a request with a developer or analyst
- Waiting hours or days for a report
- Getting a result that may not quite match what you needed
- Repeating the cycle when you have a follow-up question

Query MCP eliminates this cycle. It sits between you and your database, letting you ask questions the same way you'd ask a colleague — in plain English — and getting back clear, accurate answers in seconds.

---

## Who It's For

**Business owners** who want to understand what's happening in their business without depending on a developer every time.

**Operations leaders** who need to monitor performance, spot anomalies, and make fast decisions.

**Sales and marketing teams** who want to pull customer segments, track campaigns, and identify trends without technical help.

**Anyone with a question** about data in a database, who doesn't want to learn SQL to get the answer.

---

## What You Can Ask

### Revenue & Sales
- "What was total revenue last month?"
- "Which product categories are growing fastest?"
- "Show me our top 20 customers by lifetime value"
- "Which sales rep closed the most deals this quarter?"

### Operations & Inventory
- "How many units of Product X do we have in stock?"
- "Which products are below reorder level?"
- "Show me all orders that haven't shipped in over 5 days"
- "What's our average order fulfillment time?"

### Customer Insights
- "Which customers placed more than 3 orders this year?"
- "How many new customers signed up last week?"
- "Which customers haven't purchased in 60+ days?"
- "What's our customer retention rate this quarter?"

### Financial Analysis
- "What's the average order value by region?"
- "Show me all transactions over $10,000 this month"
- "Which product has the highest profit margin?"
- "How does this month compare to the same month last year?"

---

## How It Works

You don't need to understand the technical details to use Query MCP. Here's a plain-English explanation:

1. **You ask a question** — in your own words, in any language
2. **The AI reads your database structure** — it learns what data you have available
3. **The AI writes the precise query** — translating your question into exact database instructions
4. **Your database runs the query** — against your real, live data
5. **You get a clear answer** — summarized in plain language, with the supporting data

The entire process takes 1–3 seconds.

---

## Business Use Cases

### Daily Operations Check
Instead of manually building reports each morning, ask:
- "Show me yesterday's order volume and revenue"
- "Any orders with issues or delays?"
- "How does today's pipeline look versus last Monday?"

### Weekly Business Review
Pull the numbers you need without waiting for anyone:
- "Revenue by product line this week vs. last week"
- "New customers acquired this week by channel"
- "Top 10 deals closed this week"

### Ad-Hoc Investigation
When something looks off, dig in immediately:
- "Why did sales drop on Tuesday? Show me order volume by hour"
- "Which customers made large purchases this month but not last month?"
- "Find all refunds issued in the past 30 days"

### Executive Reporting
Prepare for board meetings or investor updates by pulling the exact numbers you need:
- "Revenue, growth rate, and average order value for each quarter this year"
- "Customer count, churn rate, and net new customers by month"
- "Top 5 markets by revenue growth"

---

## What Makes It Safe

Business leaders often worry about giving teams access to live data. Query MCP is designed with safety as a core principle:

**Read-only by design.** Query MCP can only read data — it cannot insert, update, or delete anything. This is enforced at the system level, not just by policy.

**Full audit trail.** Every question asked, every query run, and every result returned is logged. You know exactly who asked what, and when.

**Your data stays yours.** Data lives in your own database. The AI only sees your table structure and the results of specific queries — not your full database.

**Clarifies before guessing.** If your question is ambiguous, Query MCP asks a clarifying question rather than guessing and returning wrong results.

---

## Response Quality

Query MCP is tuned to give direct, useful answers — not just raw data tables.

**Example question:** *"Who are our best customers?"*

**Instead of:** A raw table of 10,000 rows

**You get:** *"Your top 5 customers by total spend this year are: [Customer A] at $142,000, [Customer B] at $98,500..."*

You can always ask for more detail, a different time period, or a different metric — it's a conversation.

---

## Languages

Ask in English, Spanish, Vietnamese, French, Japanese, or any other major language. Responses come back in the same language you asked in.

---

## Technical Overview

> For IT teams evaluating or deploying Query MCP.

**Architecture:** A lightweight server that connects to your existing PostgreSQL database. No changes to your database schema required. Runs on-premise, in your cloud, or via Docker.

**AI Providers:** Configurable. Google Gemini (default, free tier available), Anthropic Claude, or Z.ai GLM. Your team chooses the provider; end users don't need to think about it.

**Integration:** Works with Claude Code and Claude Desktop via the Model Context Protocol (MCP), or as a standalone HTTP REST API.

**Deployment:** Docker Compose for quick setup; Cloud Run or any container platform for production. See [DEPLOYMENT.md](DEPLOYMENT.md).

**Performance:** 1–3 seconds per query end-to-end. Handles 20–30 concurrent requests per instance; scales horizontally.

---

## Getting Started

For a 5-minute setup, see [QUICK_START.md](../QUICK_START.md).

For deployment to production, see [DEPLOYMENT.md](DEPLOYMENT.md).

For example questions and results, see [EXAMPLES.md](EXAMPLES.md).

For common questions, see [FAQ.md](FAQ.md).
