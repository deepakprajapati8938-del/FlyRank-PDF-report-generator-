import sqlite3
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from playwright.async_api import async_playwright

app = FastAPI()

# Ensure reports dir exists
os.makedirs("reports", exist_ok=True)

def getReportData():
    conn = sqlite3.connect('report.db')
    c = conn.cursor()
    
    # 1. Total number of orders
    c.execute('SELECT COUNT(*) FROM orders')
    total_orders = c.fetchone()[0]
    
    # 2. Total revenue
    c.execute('SELECT SUM(amount) FROM orders')
    total_revenue = c.fetchone()[0] or 0
    
    # 3. Top 5 products by revenue
    c.execute('SELECT product, SUM(amount) as rev FROM orders GROUP BY product ORDER BY rev DESC LIMIT 5')
    top_products = [{"product": row[0], "revenue": row[1]} for row in c.fetchall()]
    
    # 4. All orders (for the long table)
    c.execute('SELECT id, customer, product, amount, created_at FROM orders ORDER BY created_at DESC')
    all_orders = [{"id": r[0], "customer": r[1], "product": r[2], "amount": r[3], "date": r[4]} for r in c.fetchall()]
    
    conn.close()
    
    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "top_products": top_products,
        "all_orders": all_orders
    }

async def render_pdf(html_content: str, output_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_content)
        await page.pdf(path=output_path, format="A4", print_background=True)
        await browser.close()

def build_html(data):
    today = datetime.now().strftime('%Y-%m-%d')
    
    top_products_html = "".join([f"<tr><td>{p['product']}</td><td>${p['revenue']:.2f}</td></tr>" for p in data['top_products']])
    all_orders_html = "".join([f"<tr><td>{o['id']}</td><td>{o['customer']}</td><td>{o['product']}</td><td>${o['amount']}</td><td>{o['date']}</td></tr>" for o in data['all_orders']])
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
            h1 {{ color: #2c3e50; }}
            .summary {{ display: flex; gap: 40px; margin-bottom: 30px; }}
            .card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border: 1px solid #dee2e6; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #2c3e50; color: white; }}
            tr {{ break-inside: avoid; }}
            thead {{ display: table-header-group; }}
        </style>
    </head>
    <body>
        <h1>Sales Report - {today}</h1>
        
        <div class="summary">
            <div class="card">
                <h3>Total Orders</h3>
                <p style="font-size: 24px; font-weight: bold;">{data['total_orders']}</p>
            </div>
            <div class="card">
                <h3>Total Revenue</h3>
                <p style="font-size: 24px; font-weight: bold;">${data['total_revenue']}</p>
            </div>
        </div>
        
        <h2>Top 5 Products</h2>
        <table>
            <thead><tr><th>Product</th><th>Revenue</th></tr></thead>
            <tbody>{top_products_html}</tbody>
        </table>
        
        <h2>All Orders</h2>
        <table>
            <thead><tr><th>ID</th><th>Customer</th><th>Product</th><th>Amount</th><th>Date</th></tr></thead>
            <tbody>{all_orders_html}</tbody>
        </table>
    </body>
    </html>
    """
    return html

@app.get("/health")
def health():
    return {"status": "ok"}

class GenerateRequest(BaseModel):
    force: bool = False

@app.post("/reports", status_code=201)
async def generate_report(req: GenerateRequest = GenerateRequest()):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('report.db')
    c = conn.cursor()
    
    # Idempotency check
    if not req.force:
        c.execute('SELECT id, path FROM reports WHERE created_at = ?', (today,))
        existing = c.fetchone()
        if existing:
            conn.close()
            # Return 200 for existing
            return {"id": existing[0], "file": f"/reports/{existing[0]}/file"}
            
    # Generate new
    data = getReportData()
    html = build_html(data)
    
    c.execute('INSERT INTO reports (path, created_at) VALUES (?, ?)', ('', today))
    report_id = c.lastrowid
    
    filename = f"report_{report_id}_{today}.pdf"
    filepath = f"reports/{filename}"
    
    c.execute('UPDATE reports SET path = ? WHERE id = ?', (filepath, report_id))
    conn.commit()
    conn.close()
    
    await render_pdf(html, filepath)
    
    return {"id": report_id, "file": f"/reports/{report_id}/file"}

@app.get("/reports/{report_id}")
def get_report(report_id: int):
    conn = sqlite3.connect('report.db')
    c = conn.cursor()
    c.execute('SELECT id, path, created_at FROM reports WHERE id = ?', (report_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
        
    return {"id": row[0], "path": row[1], "created_at": row[2], "file": f"/reports/{row[0]}/file"}

@app.get("/reports/{report_id}/file")
def download_report(report_id: int):
    conn = sqlite3.connect('report.db')
    c = conn.cursor()
    c.execute('SELECT path FROM reports WHERE id = ?', (report_id,))
    row = c.fetchone()
    conn.close()
    
    if not row or not os.path.exists(row[0]):
        raise HTTPException(status_code=404, detail="File not found")
        
    return FileResponse(row[0], media_type='application/pdf', filename=os.path.basename(row[0]))
