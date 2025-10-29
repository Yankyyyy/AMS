# Copyright (c) 2025, Yanky and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import throw, ValidationError, _

class EventRSVP(Document):
    def before_save(self):
        """Check event capacity"""
        event = frappe.get_doc("AMS Event", self.event)
        if event.max_capacity:
            existing_rsvps = frappe.db.count(
                "Event RSVP",
                filters={"event": self.event, "response_status": "Going"}
            )
            if existing_rsvps >= event.max_capacity:
                throw(ValidationError, _("Event is at full capacity"))
    
    def after_insert(self):
        """Trigger event update"""
        from frappe.utils import now
        self.db_set("rsvp_date", now())
        frappe.get_doc("AMS Event", self.event).save()