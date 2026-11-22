# SAP BTP AI Procurement & Policy Copilot

An enterprise-grade **AI-powered Procurement & Policy Compliance Copilot** built on **SAP Business Technology Platform (SAP BTP)**, combining **SAP CAP (Node.js)** for OData V4 transactional workflows with a **Python FastAPI + RAG (LangChain & FAISS)** microservice for automated policy verification.

---

## Architecture & Tech Stack

* **Backend & APIs:** SAP Cloud Application Programming Model (CAP), Node.js (ESM), OData V4
* **Database:** SAP CDS Schema (`Vendors`, `PurchaseOrders`, `ApprovalLogs`) with SQLite (local/dev) & SAP HANA Cloud (production-ready)
* **AI Microservice (In Progress):** Python, FastAPI, LangChain, FAISS Vector Store (RAG for procurement policy compliance)
* **Deployment & Tooling:** SAP Business Application Studio (BAS), SAP BTP Cloud Foundry

---

## Key Features

* **OData V4 Procurement API (`/api/procurement`):** Full CRUD operations for `Vendors`, `PurchaseOrders`, and `ApprovalLogs`.
* **Automated PO Workflows:** Auto-generates structured PO numbers (`PO-2026-XXXXX`) and initializes approval states on creation.
* **Custom Approval Actions:** Bound OData actions (`approveOrder`, `rejectOrder`) with automatic audit trail logging in `ApprovalLogs`.
* **AI Policy Compliance (Phase 3):** RAG-based copilot to validate purchase orders against company procurement policies and flag unapproved vendors or budget anomalies.

---

## Project Roadmap

- [x] **Phase 1:** SAP BTP Trial, Business Application Studio (BAS) Dev Space, & GitHub Setup
- [x] **Phase 2:** SAP CAP Backend, CDS Data Model, OData V4 APIs, Custom Actions, & Seed Data
- [ ] **Phase 3:** Python FastAPI + LangChain/FAISS RAG Microservice
- [ ] **Phase 4:** Frontend Integration & SAP BTP Cloud Foundry Deployment

---

## Run Locally

```bash
npm install
cds watch
```

Open `http://localhost:4004` to access the custom landing page and OData V4 endpoints.

---

**Created by Ajit babu kakumanu**
