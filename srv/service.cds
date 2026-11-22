using { sap.procurement.copilot as db } from '../db/schema';

service ProcurementService @(path: '/api/procurement') {
    entity Vendors as projection on db.Vendors;

    entity PurchaseOrders as projection on db.PurchaseOrders actions {
        action approveOrder(comments : String) returns PurchaseOrders;
        action rejectOrder(comments : String) returns PurchaseOrders;
    };

    entity ApprovalLogs as projection on db.ApprovalLogs;
}