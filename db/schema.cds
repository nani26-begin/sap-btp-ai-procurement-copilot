namespace sap.procurement.copilot;

using { cuid, managed, Currency } from '@sap/cds/common';

entity Vendors : cuid, managed {
    name          : String(100) not null;
    category      : String(50);
    rating        : Decimal(2,1);
    isApproved    : Boolean default true;
    contactEmail  : String(100);
}

entity PurchaseOrders : cuid, managed {
    poNumber          : String(20) not null;
    title             : String(120) not null;
    description       : String(500);
    vendor            : Association to Vendors;
    department        : String(50);
    amount            : Decimal(12,2) not null;
    currency          : Currency;
    status            : String(20) enum {
        Pending;
        Approved;
        Rejected;
        NeedsReview;
    } default 'Pending';
    aiComplianceCheck : String(20) default 'NotChecked';
    aiPolicyNotes     : String(1000);
    requestedBy       : String(100);
}

entity ApprovalLogs : cuid, managed {
    purchaseOrder : Association to PurchaseOrders;
    action        : String(20);
    actor         : String(100);
    comments      : String(500);
}