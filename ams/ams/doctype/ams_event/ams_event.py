# Copyright (c) 2025, Yanky and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe import throw, ValidationError, _
from frappe.utils import get_datetime

class AMSEvent(Document):
    def before_save(self):
        """Validate event date is in future"""
        from frappe.utils import now
        if self.event_date <= now():
            throw(ValidationError, _("Event date must be in the future"))
    
    def on_update(self):
        """Update RSVP count"""
        from frappe.client import get_list
        rsvp_count = len(get_list("Event RSVP", filters={"event": self.name}))
        self.db_set("rsvp_count", rsvp_count)