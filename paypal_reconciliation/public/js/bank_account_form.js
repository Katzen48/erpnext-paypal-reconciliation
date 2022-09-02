frappe.ui.form.on('Bank Account', {
    refresh(frm) {
        if(frm.doc.is_paypal_account) {
            frm.add_custom_button(__('Sync with PayPal'), function() {
                frappe.call({
                    method: "paypal_reconciliation.paypal_reconciliation.doctype.paypal_reconciliation_settings.paypal_reconciliation_settings.sync_transactions",
                    args: {
                        bank_account: frm.doc.name
                    }
                })
            });
        }
    }
});