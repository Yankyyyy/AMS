# Copyright (c) 2025, Yanky and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import now, add_days
from frappe import _

class Membership(Document):
    def before_save(self):
        """Set expiry date based on membership type"""
        if self.membership_type == "Lifetime":
            self.expiry_date = None
        elif self.membership_type == "Premium":
            self.expiry_date = add_days(self.start_date, 365)
        elif self.membership_type == "Free":
            self.expiry_date = add_days(self.start_date, 30)
    
    def on_update(self):
        """Check and update expired memberships"""
        from frappe.utils import today
        if self.expiry_date and self.expiry_date < today() and self.status == "Active":
            self.db_set("status", "Expired")