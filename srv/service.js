import cds from '@sap/cds';

const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://127.0.0.1:8000';

export default cds.service.impl(async function () {
    const { PurchaseOrders, Vendors, ApprovalLogs } = this.entities;

    // Auto-generate PO Number and default status before creating a PO
    this.before('CREATE', PurchaseOrders, async (req) => {
        if (!req.data.poNumber) {
            const randomNum = Math.floor(10000 + Math.random() * 90000);
            req.data.poNumber = `PO-2026-${randomNum}`;
        }
        if (!req.data.status) {
            req.data.status = 'Pending';
        }
    });

    // Custom Action: Approve Order
    this.on('approveOrder', PurchaseOrders, async (req) => {
        const { ID } = req.params[0];
        const { comments } = req.data;

        await UPDATE(PurchaseOrders).set({ status: 'Approved' }).where({ ID });

        await INSERT.into(ApprovalLogs).entries({
            purchaseOrder_ID: ID,
            action: 'Approved',
            actor: req.user?.id || 'Manager_Demo',
            comments: comments || 'Approved via Procurement Copilot'
        });

        return SELECT.one.from(PurchaseOrders).where({ ID });
    });

    // Custom Action: Reject Order
    this.on('rejectOrder', PurchaseOrders, async (req) => {
        const { ID } = req.params[0];
        const { comments } = req.data;

        await UPDATE(PurchaseOrders).set({ status: 'Rejected' }).where({ ID });

        await INSERT.into(ApprovalLogs).entries({
            purchaseOrder_ID: ID,
            action: 'Rejected',
            actor: req.user?.id || 'Manager_Demo',
            comments: comments || 'Rejected via Procurement Copilot'
        });

        return SELECT.one.from(PurchaseOrders).where({ ID });
    });

    // AI Action: Run RAG Policy Compliance Check via Python FastAPI
    this.on('runAIComplianceCheck', PurchaseOrders, async (req) => {
        const { ID } = req.params[0];
        const po = await SELECT.one.from(PurchaseOrders).where({ ID });
        if (!po) return req.error(404, `PurchaseOrder ${ID} not found`);

        const vendor = po.vendor_ID
            ? await SELECT.one.from(Vendors).where({ ID: po.vendor_ID })
            : null;

        const response = await fetch(`${AI_SERVICE_URL}/api/ai/check-compliance`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                poNumber: po.poNumber,
                title: po.title,
                description: po.description || '',
                department: po.department || 'General',
                amount: Number(po.amount),
                vendorName: vendor?.name || 'Unknown',
                vendorApproved: vendor?.isApproved ?? false,
                vendorRating: Number(vendor?.rating || 0)
            })
        });

        if (!response.ok) {
            return req.error(502, 'AI Policy Service is unavailable. Ensure FastAPI is running on port 8000.');
        }

        const aiResult = await response.json();
        const notes = `${aiResult.recommendation} | Flags: ${aiResult.flags.join(' ; ')}`;

        await UPDATE(PurchaseOrders)
            .set({
                aiComplianceCheck: aiResult.aiComplianceCheck,
                aiPolicyNotes: notes.slice(0, 1000)
            })
            .where({ ID });

        return SELECT.one.from(PurchaseOrders).where({ ID });
    });

    // AI Action: Hybrid Live-DB + Policy Copilot
    this.on('askPolicyCopilot', async (req) => {
        const { question } = req.data;
        const orders = await SELECT.from(PurchaseOrders);
        const vendors = await SELECT.from(Vendors);

        const response = await fetch(`${AI_SERVICE_URL}/api/ai/ask-policy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, orders, vendors })
        });

        if (!response.ok) {
            return req.error(502, 'AI Policy Service is unavailable.');
        }

        const data = await response.json();
        return data.answer;
    });

    // Real-Time Trending Market Feed (via Gemini + Google Search)
    this.on('getTrendingMarket', async (req) => {
        const response = await fetch(`${AI_SERVICE_URL}/api/ai/trending-market`);
        if (!response.ok) return req.error(502, 'AI Market Service unavailable.');
        const data = await response.json();
        return JSON.stringify(data);
    });

    // Live Market & Tech Intelligence (Present + 1-Week Avg + Prediction)
    this.on('getMarketIntel', async (req) => {
        const { topic } = req.data;
        const response = await fetch(`${AI_SERVICE_URL}/api/ai/market-intel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic })
        });
        if (!response.ok) return req.error(502, 'AI Market Service unavailable.');
        const data = await response.json();
        return data.analysis;
    });
});