# Copyright (c) 2025, Yanky and contributors
# For license information, please see license.txt

from frappe import _, throw, ValidationError
from frappe.model.document import Document
import re

class Alumni(Document):
    def before_save(self):
        """Validate email and normalize data"""
        if not self.is_valid_email(self.email):
            throw(ValidationError, _("Invalid email address"))
        
        self.email = self.email.lower().strip()
        
    def before_insert(self):
        """Set joined_on timestamp"""
        from frappe.utils import now
        self.joined_on = now()
        
    def after_insert(self):
        """Send welcome email"""
        from frappe.core.doctype.communication.email import make
        make(
            doctype=self.doctype,
            name=self.name,
            subject="Welcome to Alumni Network!",
            content=f"Hi {self.first_name}, welcome aboard!"
        )
    
    @staticmethod
    def is_valid_email(email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None