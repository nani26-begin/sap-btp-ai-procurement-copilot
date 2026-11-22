import cds from '@sap/cds';

export default cds.service.impl(async function () {
    const { PurchaseOrders, ApprovalLogs } = this.entities;

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
});