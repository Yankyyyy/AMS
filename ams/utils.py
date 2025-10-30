import frappe
from frappe.utils import today, add_days, getdate
from frappe import _

# ============== SCHEDULED TASKS ==============

def send_event_reminders():
    """Send event reminders 24 hours before event"""
    tomorrow = add_days(today(), 1)
    
    events = frappe.db.get_list(
        "Event",
        filters=[
            ["Event", "status", "=", "Upcoming"],
            ["Event", "event_date", ">=", tomorrow],
            ["Event", "event_date", "<=", add_days(tomorrow, 1)]
        ]
    )
    
    for event_name in events:
        event = frappe.get_doc("Event", event_name)
        
        # Get all RSVPs
        rsvps = frappe.db.get_list(
            "Event RSVP",
            filters={"event": event.name, "response_status": "Going"}
        )
        
        for rsvp_doc in rsvps:
            rsvp = frappe.get_doc("Event RSVP", rsvp_doc.name)
            alumni = frappe.get_doc("Alumni", rsvp.alumni)
            
            # Send email reminder
            frappe.sendmail(
                recipients=[alumni.email],
                subject=f"Reminder: {event.event_name} is tomorrow!",
                message=f"""
                <p>Hi {alumni.first_name},</p>
                <p>This is a reminder that <strong>{event.event_name}</strong> is happening tomorrow!</p>
                <p><strong>Date:</strong> {event.event_date}</p>
                <p><strong>Venue:</strong> {event.venue}</p>
                <p>See you there!</p>
                """
            )

def update_expired_memberships():
    """Update expired membership statuses"""
    expired_members = frappe.db.get_list(
        "Membership",
        filters=[
            ["Membership", "status", "=", "Active"],
            ["Membership", "expiry_date", "<", today()]
        ]
    )
    
    for member_name in expired_members:
        member = frappe.get_doc("Membership", member_name)
        member.status = "Expired"
        member.save()

def send_membership_expiry_notifications():
    """Notify members about upcoming expiry (7 days before)"""
    expiry_date = add_days(today(), 7)
    
    expiring_members = frappe.db.get_list(
        "Membership",
        filters=[
            ["Membership", "status", "=", "Active"],
            ["Membership", "expiry_date", "=", expiry_date]
        ]
    )
    
    for member_name in expiring_members:
        member = frappe.get_doc("Membership", member_name)
        alumni = frappe.get_doc("Alumni", member.alumni)
        
        frappe.sendmail(
            recipients=[alumni.email],
            subject="Your Alumni Membership Expires in 7 Days",
            message=f"""
            <p>Hi {alumni.first_name},</p>
            <p>Your {member.membership_type} membership expires on {member.expiry_date}.</p>
            <p>Renew now to continue enjoying exclusive alumni benefits!</p>
            """
        )

def generate_monthly_stats():
    """Generate monthly alumni engagement stats"""
    from frappe.utils import get_first_day, get_last_day
    
    first_day = get_first_day(today())
    last_day = get_last_day(today())
    
    # Count new registrations
    new_alumni = frappe.db.count(
        "Alumni",
        filters=[
            ["Alumni", "joined_on", ">=", first_day],
            ["Alumni", "joined_on", "<=", last_day]
        ]
    )
    
    # Count new posts
    new_posts = frappe.db.count(
        "Wall Post",
        filters=[
            ["Wall Post", "published_on", ">=", first_day],
            ["Wall Post", "published_on", "<=", last_day],
            ["Wall Post", "status", "=", "Published"]
        ]
    )
    
    # Count donations
    total_donations = frappe.db.get_value(
        "Donation",
        filters=[
            ["Donation", "donation_date", ">=", first_day],
            ["Donation", "donation_date", "<=", last_day],
            ["Donation", "status", "=", "Completed"]
        ],
        fieldname="sum(amount)"
    ) or 0
    
    # Store stats (optional: create a DocType for this)
    return {
        "new_alumni": new_alumni,
        "new_posts": new_posts,
        "total_donations": total_donations,
        "period": f"{first_day} to {last_day}"
    }

def cleanup_old_data():
    """Clean up archived/old data (retention policy)"""
    # Delete archived wall posts older than 1 year
    old_date = add_days(today(), -365)
    
    archived_posts = frappe.db.get_list(
        "Wall Post",
        filters=[
            ["Wall Post", "status", "=", "Archived"],
            ["Wall Post", "published_on", "<", old_date]
        ]
    )
    
    for post_name in archived_posts:
        frappe.delete_doc("Wall Post", post_name)

# ============== HELPER FUNCTIONS ==============

def notify_admin_of_pending_posts():
    """Notify admins about pending wall posts for moderation"""
    pending_posts = frappe.db.get_list(
        "Wall Post",
        filters={"status": "Draft"}
    )
    
    if pending_posts:
        admins = frappe.db.get_list(
            "User",
            filters={"role_profile_name": "Alumni Admin"}
        )
        
        for admin in admins:
            frappe.sendmail(
                recipients=[admin.email],
                subject=f"Pending Posts for Moderation ({len(pending_posts)} new)",
                message=f"""
                <p>You have {len(pending_posts)} wall posts pending moderation.</p>
                <p>Please review and publish approved posts.</p>
                """
            )

def send_monthly_digest():
    """Send monthly alumni network digest"""
    from frappe.utils import get_first_day
    
    first_day = get_first_day(add_days(today(), -30))
    
    # Get top posts (by likes)
    top_posts = frappe.db.get_list(
        "Wall Post",
        filters=[
            ["Wall Post", "published_on", ">=", first_day],
            ["Wall Post", "status", "=", "Published"]
        ],
        fields=["title", "alumni", "likes_count"],
        order_by="likes_count desc",
        limit_page_length=5
    )
    
    # Get upcoming events
    upcoming_events = frappe.db.get_list(
        "Event",
        filters=[
            ["Event", "event_date", ">=", today()],
            ["Event", "status", "!=", "Cancelled"]
        ],
        fields=["event_name", "event_date", "venue"],
        limit_page_length=3
    )
    
    # Get all active alumni
    active_alumni = frappe.db.get_list("Alumni", filters={"status": "Active"})
    
    for alumni_email in active_alumni:
        frappe.sendmail(
            recipients=[alumni_email],
            subject="Your Monthly Alumni Network Digest",
            message=f"""
            <p>Hi,</p>
            <p><strong>This Month's Highlights:</strong></p>
            <ul>
                <li>New Alumni Members: {frappe.db.count('Alumni', filters=[['Alumni', 'joined_on', '>=', first_day]])}</li>
                <li>New Posts: {len(top_posts)}</li>
                <li>Upcoming Events: {len(upcoming_events)}</li>
            </ul>
            <p>Keep engaging with your alumni network!</p>
            """
        )
        
        
import frappe
import inspect

def createAPIErrorLog(error):
    """Create error log according the method from where createAPIErrorLog been called"""
    error_log =  frappe.new_doc("Error Log")
    error_log.method = inspect.stack()[1][3] #called method name will be fetched
    error_log.error = error
    error_log.save(ignore_permissions=True)