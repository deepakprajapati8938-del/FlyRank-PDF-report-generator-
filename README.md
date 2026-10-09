# PDF Report Generator (BE-08 / A8)

A pipeline to query data, render it into an HTML template, convert it to a PDF using Playwright (headless Chromium), and serve it by link without passing the bytes directly in the JSON response.

## Dataset Chosen
Option A — The little shop. (Randomized orders data).

## How to run
1. **Seed the database:**
   ```bash
   python seed.py
   ```
2. **Start the API:**
   ```bash
   uvicorn main:app --reload
   ```
3. **Generate a Report:**
   ```bash
   curl -X POST http://localhost:8000/reports
   ```
4. **Download the PDF:**
   ```bash
   curl -o my-report.pdf http://localhost:8000/reports/<id>/file
   ```

## Aggregation SQL
```sql
-- Total number of orders
SELECT COUNT(*) FROM orders

-- Total revenue
SELECT SUM(amount) FROM orders

-- Top 5 products by revenue
SELECT product, SUM(amount) as rev FROM orders GROUP BY product ORDER BY rev DESC LIMIT 5

-- All orders
SELECT id, customer, product, amount, created_at FROM orders ORDER BY created_at DESC
```

## Proof of Execution
```json
// POST /reports
{
  "id": 1,
  "file": "/reports/1/file"
}
```

## Assignment Sentences

### Stage 4: Moving work out of the request
If this report generation took 15+ seconds or if thousands of users requested it simultaneously, we would move this work out of the request (using background jobs like Celery or Inngest) to avoid blocking the server and causing request timeouts.

### Stage 5: Ask twice, get one
The check protects against accidentally regenerating the same heavy PDF if a user double-clicks the "Generate" button, saving CPU/memory on the server. A real-world example where a missing idempotency check costs money is in payment processing: charging a customer's credit card twice for the same order because they double-clicked "Pay".

## Stage 7: AI vs Me
I built this primarily using AI. 
1. **What did the AI do better?** The AI instantly knew how to inject dynamic data into a beautifully formatted HTML template with print CSS (`break-inside: avoid`), which would have taken me an hour of trial and error.
2. **What did it get wrong or ignore?** It initially tried to use `reportlab` because I didn't specify Playwright correctly, but we corrected it to use `playwright` as required by the Python lane specs.
3. **What did it silently decide?** It decided to use a `reports/` folder and dynamically create it on startup to prevent FileNotFoundError, which is a very robust decision.
