# Copyright (c) 2025, Yanky and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now

class WallPost(Document):
    def before_save(self):
        """Auto-set published_on when status changes to Published"""
        if self.status == "Published" and not self.published_on:
            self.published_on = now()
    
    def on_trash(self):
        """Clean up associated likes"""
        frappe.db.delete("Wall Post Like", {"wall_post": self.name})