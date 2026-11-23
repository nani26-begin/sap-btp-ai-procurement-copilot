from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import yfinance as yf
import os
import time

app = FastAPI(
    title="SAP BTP AI Procurement & Real-Time Market Intelligence Copilot",
    description="Hybrid Live-DB + RAG + Real-Time Market Engine — Created by Ajit babu kakumanu",
    version="3.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load procurement policies
POLICY_FILE = os.path.join(os.path.dirname(__file__), "policies.txt")
with open(POLICY_FILE, "r", encoding="utf-8") as f:
    POLICY_CHUNKS = [chunk.strip() for chunk in f.read().split("\n\n") if chunk.strip()]

vectorizer = TfidfVectorizer(stop_words="english")
POLICY_VECTORS = vectorizer.fit_transform(POLICY_CHUNKS)

# 60-second smart cache for live trending ticker
TRENDING_CACHE = {"timestamp": 0, "data": None}
CACHE_TTL_SECONDS = 60

# Keyword-to-Ticker mapping for instant natural-language queries
SYMBOL_MAP = {
    "gold": ("GC=F", "Gold Futures (USD/oz)"),
    "silver": ("SI=F", "Silver Futures (USD/oz)"),
    "usd": ("INR=X", "USD to INR"),
    "inr": ("INR=X", "USD to INR"),
    "dollar": ("INR=X", "USD to INR"),
    "bitcoin": ("BTC-USD", "Bitcoin (BTC/USD)"),
    "btc": ("BTC-USD", "Bitcoin (BTC/USD)"),
    "oil": ("CL=F", "Crude Oil (USD/bbl)"),
    "crude": ("CL=F", "Crude Oil (USD/bbl)"),
    "nvidia": ("NVDA", "NVIDIA Corp (AI/GPU)"),
    "gpu": ("NVDA", "NVIDIA Corp (AI/GPU)"),
    "ai": ("NVDA", "NVIDIA Corp (AI/GPU)"),
    "aws": ("AMZN", "Amazon / AWS"),
    "amazon": ("AMZN", "Amazon / AWS"),
    "sap": ("SAP", "SAP SE"),
    "microsoft": ("MSFT", "Microsoft / Azure"),
    "azure": ("MSFT", "Microsoft / Azure"),
    "google": ("GOOGL", "Alphabet / Google Cloud"),
    "cloud": ("GOOGL", "Alphabet / Google Cloud"),
    "apple": ("AAPL", "Apple Inc."),
    "tesla": ("TSLA", "Tesla Inc."),
    "tcs": ("TCS.NS", "TCS (NSE India)"),
    "infosys": ("INFY.NS", "Infosys (NSE India)"),
}


def resolve_symbol(topic: str):
    q = topic.lower().strip()
    for key, val in SYMBOL_MAP.items():
        if key in q:
            return val
    # Fallback: treat user input as direct ticker (e.g., META, IBM, RELIANCE.NS)
    clean_ticker = topic.strip().upper().split()[0]
    return (clean_ticker, clean_ticker)


def retrieve_policies(query: str, top_k: int = 2):
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, POLICY_VECTORS).flatten()
    top_indices = scores.argsort()[::-1][:top_k]
    return [
        {"policy": POLICY_CHUNKS[i], "relevance_score": round(float(scores[i]), 3)}
        for i in top_indices
        if scores[i] > 0.05
    ]


class PurchaseOrderRequest(BaseModel):
    poNumber: str
    title: str
    description: str = ""
    department: str
    amount: float
    vendorName: str = "Unknown"
    vendorApproved: bool = True
    vendorRating: float = 4.0


class PolicyQuery(BaseModel):
    question: str
    orders: Optional[List[Dict[str, Any]]] = []
    vendors: Optional[List[Dict[str, Any]]] = []


class MarketQuery(BaseModel):
    topic: str


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "engine": "yfinance Live Market + Local RAG",
        "policies_loaded": len(POLICY_CHUNKS),
        "author": "Ajit babu kakumanu"
    }


@app.get("/api/ai/trending-market")
def get_trending_market():
    now = time.time()
    if TRENDING_CACHE["data"] and (now - TRENDING_CACHE["timestamp"] < CACHE_TTL_SECONDS):
        return TRENDING_CACHE["data"]

    watched = [
        ("GC=F", "Gold", "$"),
        ("INR=X", "USD/INR", "₹"),
        ("BTC-USD", "Bitcoin", "$"),
        ("NVDA", "NVIDIA AI", "$"),
        ("SAP", "SAP SE", "$"),
    ]

    items = []
    for sym, label, prefix in watched:
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if not hist.empty and len(hist) >= 2:
                curr = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                pct = ((curr - prev) / prev) * 100
                sign = "+" if pct >= 0 else ""
                items.append({
                    "name": label,
                    "price": f"{prefix}{curr:,.2f}",
                    "trend": f"{sign}{pct:.2f}%"
                })
        except Exception:
            continue

    if not items:
        items = [{"name": "Market Feed", "price": "Connecting...", "trend": "Retry"}]

    result = {"updatedAt": time.strftime("%H:%M:%S"), "items": items}
    TRENDING_CACHE["timestamp"] = now
    TRENDING_CACHE["data"] = result
    return result


@app.post("/api/ai/market-intel")
def get_market_intel(payload: MarketQuery):
    sym, label = resolve_symbol(payload.topic)
    try:
        hist = yf.Ticker(sym).history(period="1mo")
        if hist.empty or len(hist) < 2:
            return {
                "topic": payload.topic,
                "analysis": f"No live market data found for '{payload.topic}'. Try: gold, silver, bitcoin, usd, crude oil, nvidia, aws, sap, microsoft, google, tcs."
            }

        recent_7 = hist.tail(7)
        closes = [float(x) for x in recent_7["Close"].tolist()]
        present = closes[-1]
        week_start = closes[0]
        week_avg = sum(closes) / len(closes)
        week_high = max(closes)
        week_low = min(closes)
        week_change_pct = ((present - week_start) / week_start) * 100

        # Simple momentum-based 7-day projection
        daily_slope = (present - week_start) / max(len(closes) - 1, 1)
        projected_7d = max(present + (daily_slope * 5), 0.01)
        trend_label = "Bullish (Upward)" if week_change_pct > 0.5 else ("Bearish (Downward)" if week_change_pct < -0.5 else "Sideways / Stable")

        prefix = "₹" if sym in ["INR=X", "TCS.NS", "INFY.NS"] else "$"
        insight = (
            "Prices are trending up — consider locking in vendor contracts or hedges early."
            if week_change_pct > 0.5 else
            "Prices are softening — good window for spot procurement or renegotiation."
            if week_change_pct < -0.5 else
            "Market is stable — standard procurement schedule is optimal."
        )

        analysis = (
            f"LIVE MARKET INTELLIGENCE: {label} ({sym})\n\n"
            f"1. PRESENT RATE (LIVE):\n"
            f"   • Current Price: {prefix}{present:,.2f}\n\n"
            f"2. PAST 1-WEEK TREND & AVERAGE:\n"
            f"   • 7-Day Average: {prefix}{week_avg:,.2f}\n"
            f"   • 7-Day Range: {prefix}{week_low:,.2f} (Low) — {prefix}{week_high:,.2f} (High)\n"
            f"   • 7-Day Change: {'+' if week_change_pct >= 0 else ''}{week_change_pct:.2f}% ({trend_label})\n\n"
            f"3. SHORT-TERM PREDICTION (7-DAY MOMENTUM MODEL):\n"
            f"   • Projected Target: ~{prefix}{projected_7d:,.2f}\n"
            f"   • Outlook: {trend_label} momentum based on recent 7-session trajectory.\n\n"
            f"4. PROCUREMENT INSIGHT:\n"
            f"   • {insight}"
        )
        return {"topic": payload.topic, "analysis": analysis}
    except Exception as e:
        return {"topic": payload.topic, "analysis": f"Error fetching live data for {sym}: {str(e)}"}


@app.post("/api/ai/ask-policy")
def ask_policy(payload: PolicyQuery):
    q = payload.question.lower().strip()
    orders = payload.orders or []
    vendors = payload.vendors or []

    # 1. Live Database Intent: Newest Order
    if any(k in q for k in ["new order", "newest", "latest", "recent"]):
        if not orders:
            return {"question": payload.question, "answer": "No purchase orders found in the database.", "sources": []}
        latest = sorted(orders, key=lambda x: x.get("createdAt") or x.get("poNumber", ""), reverse=True)[0]
        return {
            "question": payload.question,
            "answer": (
                f"Newest Purchase Order (Live SAP DB):\n"
                f"• PO Number: {latest.get('poNumber')}\n"
                f"• Title: {latest.get('title')} ({latest.get('department')})\n"
                f"• Amount: ${float(latest.get('amount', 0)):,.2f} {latest.get('currency_code', 'USD')}\n"
                f"• Status: {latest.get('status')} | AI Compliance: {latest.get('aiComplianceCheck', 'NotChecked')}"
            ),
            "sources": ["Live SAP CAP Database"]
        }

    # 2. Live Database Intent: Flagged / Risk / Pending Orders
    if any(k in q for k in ["flagged", "risk", "violation", "pending", "review"]):
        flagged = [
            o for o in orders
            if o.get("aiComplianceCheck") in ["Flagged", "NeedsReview"] or o.get("status") in ["Pending", "NeedsReview"]
        ]
        if not flagged:
            return {"question": payload.question, "answer": "No flagged or pending orders right now.", "sources": ["Live SAP CAP Database"]}
        lines = [
            f"• {o.get('poNumber')} — {o.get('title')} (${float(o.get('amount', 0)):,.2f}) | Status: {o.get('status')} | AI: {o.get('aiComplianceCheck')}"
            for o in flagged
        ]
        return {
            "question": payload.question,
            "answer": f"Orders Requiring Attention ({len(flagged)} found):\n" + "\n".join(lines),
            "sources": ["Live SAP CAP Database"]
        }

    # 3. Live Database Intent: Total Spend / Budget
    if any(k in q for k in ["total", "spend", "budget", "summary", "how many"]):
        total_spend = sum(float(o.get("amount", 0)) for o in orders)
        approved_spend = sum(float(o.get("amount", 0)) for o in orders if o.get("status") == "Approved")
        return {
            "question": payload.question,
            "answer": (
                f"Live Procurement Summary:\n"
                f"• Total Purchase Orders: {len(orders)}\n"
                f"• Total Requested Spend: ${total_spend:,.2f} USD\n"
                f"• Approved Spend: ${approved_spend:,.2f} USD\n"
                f"• Active Vendors: {len(vendors)}"
            ),
            "sources": ["Live SAP CAP Database"]
        }

    # 4. Fallback: Policy RAG
    matches = retrieve_policies(payload.question, top_k=2)
    if matches:
        return {"question": payload.question, "answer": matches[0]["policy"], "sources": matches}

    return {
        "question": payload.question,
        "answer": "No matching policy found. Try asking about 'newest order', 'flagged orders', 'total budget', or 'approval rule above $10,000'.",
        "sources": []
    }


@app.post("/api/ai/check-compliance")
def check_compliance(po: PurchaseOrderRequest):
    query_text = f"{po.title} {po.description} {po.department} {po.vendorName} amount {po.amount}"
    matched_policies = retrieve_policies(query_text, top_k=2)

    flags = []
    if not po.vendorApproved:
        flags.append("VIOLATION (POLICY-01): Vendor is NOT approved.")
    if po.vendorRating < 3.0:
        flags.append(f"HIGH RISK (POLICY-04): Vendor rating ({po.vendorRating}) is below minimum 3.0 threshold.")
    if po.amount > 10000:
        flags.append(f"APPROVAL REQUIRED (POLICY-02/03): Order amount (${po.amount:,.2f}) exceeds $10,000 — VP Finance sign-off required.")
    elif po.amount >= 5000:
        flags.append(f"APPROVAL REQUIRED (POLICY-02): Order amount (${po.amount:,.2f}) requires Senior Director approval.")

    if not po.vendorApproved or po.vendorRating < 3.0:
        status = "Flagged"
        recommendation = "Reject or hold for Compliance Officer review."
    elif po.amount >= 5000:
        status = "NeedsReview"
        recommendation = "Route to Senior Director / VP Finance for sign-off."
    else:
        status = "Compliant"
        recommendation = "Eligible for fast-track manager approval."

    return {
        "poNumber": po.poNumber,
        "aiComplianceCheck": status,
        "recommendation": recommendation,
        "flags": flags if flags else ["All automated policy checks passed."],
        "retrievedPolicies": matched_policies
    }