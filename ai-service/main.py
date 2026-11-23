from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os

app = FastAPI(
    title="SAP BTP AI Procurement & Policy Copilot",
    description="RAG-powered Policy Compliance Microservice — Created by Ajit babu kakumanu",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load and chunk procurement policies
POLICY_FILE = os.path.join(os.path.dirname(__file__), "policies.txt")
with open(POLICY_FILE, "r", encoding="utf-8") as f:
    POLICY_CHUNKS = [chunk.strip() for chunk in f.read().split("\n\n") if chunk.strip()]

vectorizer = TfidfVectorizer(stop_words="english")
POLICY_VECTORS = vectorizer.fit_transform(POLICY_CHUNKS)


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


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AI Procurement RAG Copilot",
        "policies_loaded": len(POLICY_CHUNKS),
        "author": "Ajit babu kakumanu"
    }


@app.post("/api/ai/ask-policy")
def ask_policy(payload: PolicyQuery):
    matches = retrieve_policies(payload.question, top_k=2)
    if not matches:
        return {
            "question": payload.question,
            "answer": "No matching procurement policy found. Please consult the Finance Compliance team.",
            "sources": []
        }
    return {
        "question": payload.question,
        "answer": matches[0]["policy"],
        "sources": matches
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