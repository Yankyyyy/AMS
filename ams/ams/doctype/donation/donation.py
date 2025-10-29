# Copyright (c) 2025, Yanky and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe import throw, ValidationError, _

class Donation(Document):
    def before_save(self):
        """Validate donation amount"""
        if self.amount <= 0:
            throw(ValidationError, _("Donation amount must be greater than 0"))
    
    def after_insert(self):
        """Send donation receipt"""
        self.send_receipt_email()
    
    def send_receipt_email(self):
        """Generate and send donation receipt"""
        from frappe.core.doctype.communication.email import make
        make(
            doctype=self.doctype,
            name=self.name,
            subject=f"Donation Receipt - ₹{self.amount}",
            content=f"Thank you for your donation of ₹{self.amount}. Receipt attached."
        )