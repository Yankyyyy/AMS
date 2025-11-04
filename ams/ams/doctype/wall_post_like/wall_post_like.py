# Copyright (c) 2025, Yanky and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now

class WallPostLike(Document):
    def before_insert(self):
        """Set liked_on timestamp and enforce uniqueness"""
        self.liked_on = now()
        
        # Check if already liked
        existing = frappe.db.get_value(
            "Wall Post Like",
            {"post": self.post, "alumni": self.alumni}
        )
        if existing:
            frappe.throw(frappe._("You have already liked this post"))
    
    def on_trash(self):
        """Update wall post likes count when like is deleted"""
        post = frappe.get_doc("Wall Post", self.post)
        post.likes_count = max(0, (post.likes_count or 1) - 1)
        post.save()