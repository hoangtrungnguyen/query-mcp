# Frequently Asked Questions

## General

**What is Query MCP?**  
Query MCP is an AI-powered tool that lets you ask questions about your business data in plain English and get immediate answers — without writing code or SQL. Connect it to your database, ask a question, get a result.

**Who is it for?**  
Business owners, operations leaders, sales managers, analysts — anyone who needs answers from their data without depending on a developer. If you've ever said "I just want to know X from our database," this is for you.

**Do I need to know SQL or coding?**  
No. That's the whole point. Ask naturally: "Which customers spent the most this quarter?" and Query MCP handles the technical translation.

**What kinds of questions can I ask?**  
Revenue, sales trends, customer behavior, inventory levels, order status, performance comparisons, segment analysis — anything that can be answered from your database.

---

## Getting Answers

**How do I ask a question?**  
Just type it in plain English. Good examples:
- "What were our top 5 revenue drivers last month?"
- "Show me customers who haven't ordered in 90 days"
- "Which product category has the highest average order value?"

**What if the answer seems wrong?**  
Rephrase with more specifics. Instead of "show me sales," try "show me total revenue by product category for Q1 2025, sorted highest to lowest."

**What if it asks me a clarifying question?**  
That's intentional. If your question is ambiguous, Query MCP will ask rather than guess and return a misleading result.

**Can I ask follow-up questions?**  
Yes. The conversation builds on context. After asking "Who are our top customers?" you can follow up with "Which of those haven't ordered this month?"

**Can I ask in my own language?**  
Yes. Ask in English, Spanish, French, Vietnamese, or any major language. Answers come back in the same language.

---

## Data & Safety

**Can Query MCP change or delete my data?**  
No. It is strictly read-only. It cannot insert, update, or delete any records. This is enforced at the system level.

**Is my data safe?**  
Your data stays in your database. The AI only sees your table structure and the specific results from the queries you ask — your full database is never exposed.

**Is everything logged?**  
Yes. Every question, every generated query, and every result is recorded in an audit log. You can always see who asked what and when.

**What gets sent to the AI?**  
Your table and column names (the structure), plus the rows returned by your query. Your credentials and full database contents are never sent to any AI provider.

---

## Data Access

**What databases does it work with?**  
Currently PostgreSQL. Support for MySQL and SQL Server is on the roadmap.

**Can it query any table in my database?**  
It can read any table it has been configured to access. Your IT team controls which tables and schemas are accessible.

**Can it access multiple databases at once?**  
Not simultaneously in a single query. You can run separate instances for different databases.

**How many rows can it return?**  
Default is 100 rows per query. Your technical team can raise this limit as needed.

---

## Performance

**How fast are the answers?**  
Typically 1–3 seconds from question to answer.

**Will it slow down our database?**  
Minimal impact. Query MCP only reads data and never holds locks.

---

## Setup & IT Questions

> These are for your IT or development team.

**How long does setup take?**  
About 5 minutes with Docker, 10–15 minutes for a manual install.

**Does it require changes to our database?**  
No. Query MCP reads from your existing tables without any schema changes.

**Can we run it on our own servers?**  
Yes. Runs on-premise, in your cloud environment, or via Docker. Nothing is hosted externally unless you choose it.

**What AI provider does it use?**  
Google Gemini by default (with a free tier). Your team can configure it to use Anthropic Claude or Z.ai GLM instead.

**What are the ongoing costs?**  
Only the AI provider API costs per query. Google Gemini offers a free tier. Typical cost with Z.ai is around $0.01–0.05 per question.

**Is there a free option?**  
Google Gemini's free tier is sufficient for moderate usage during evaluation and early rollout.

**Does it work with Claude?**  
Yes — both Claude Code and Claude Desktop, via the MCP integration. Business users can also access it through a REST API.

---

## Troubleshooting

**The answer doesn't match what I expected.**  
Try being more specific. Include the time period, metric, and how you want results sorted.

**It said it couldn't understand my question.**  
Rephrase it. Describe what you want in the simplest possible terms: "top 10 [X] by [Y] in [time period]."

**Results came back empty.**  
Either no data matches your criteria, or the table name may have been misidentified. Ask your technical team to verify which tables are connected.

---

## Limitations

**What can't it do?**
- Cannot write, update, or delete data (read-only by design)
- Cannot combine data across multiple databases in one query
- Does not stream real-time data
- Currently PostgreSQL only

**Will write access ever be added?**  
It's under consideration for a future version, with appropriate authorization controls. The current priority is making read access as useful and safe as possible.

---

## Getting Help

For a walkthrough of common questions with sample results, see [EXAMPLES.md](EXAMPLES.md).

For setup and deployment, see [QUICK_START.md](../QUICK_START.md) or [DEPLOYMENT.md](DEPLOYMENT.md).

For technical troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
