import frappe
from frappe import _
from frappe.utils import cint, today
from frappe.exceptions import ValidationError
import json

# ============== ALUMNI ENDPOINTS ==============

@frappe.whitelist()
def get_alumni_feed(limit=20, offset=0):
    """Get paginated alumni feed (posts + events)"""
    limit = cint(limit)
    offset = cint(offset)
    
    posts = frappe.db.get_list(
        "Wall Post",
        filters={"status": "Published"},
        fields=["name", "title", "content", "alumni", "published_on", "likes_count"],
        order_by="published_on desc",
        limit_page_length=limit,
        offset=offset
    )
    
    return {
        "posts": posts,
        "count": len(posts)
    }

@frappe.whitelist()
def get_alumni_profile(alumni_email):
    """Get detailed alumni profile"""
    try:
        alumni = frappe.get_doc("Alumni", alumni_email)
        
        # Check if requester has permission
        if not frappe.has_permission(doctype="Alumni", doc=alumni.name):
            frappe.throw(_("Permission Denied"))
        
        return {
            "name": alumni.name,
            "first_name": alumni.first_name,
            "last_name": alumni.last_name,
            "email": alumni.email,
            "phone": alumni.phone,
            "batch_year": alumni.batch_year,
            "job_title": alumni.job_title,
            "company": alumni.company,
            "bio": alumni.bio,
            "profile_picture": alumni.profile_picture,
            "linkedin_url": alumni.linkedin_url,
            "location": alumni.location,
        }
    except Exception as e:
        frappe.throw(_(f"Alumni not found: {str(e)}"))

@frappe.whitelist()
def search_alumni(query, batch_year=None):
    """Search alumni by name, company, or job title"""
    filters = []
    
    if query:
        filters.append([
            ["Alumni", "first_name", "like", f"%{query}%"],
            "or",
            ["Alumni", "last_name", "like", f"%{query}%"],
            "or",
            ["Alumni", "company", "like", f"%{query}%"],
            "or",
            ["Alumni", "job_title", "like", f"%{query}%"]
        ])
    
    if batch_year:
        filters.append(["Alumni", "batch_year", "=", cint(batch_year)])
    
    results = frappe.db.get_list(
        "Alumni",
        filters=filters,
        fields=["name", "first_name", "last_name", "job_title", "company", "profile_picture"],
        limit_page_length=20
    )
    
    return {"results": results}

# ============== EVENT ENDPOINTS ==============

@frappe.whitelist()
def get_upcoming_events(limit=10):
    """Get upcoming events"""
    from frappe.utils import now
    
    events = frappe.db.get_list(
        "Event",
        filters=[
            ["Event", "status", "in", ["Upcoming", "Ongoing"]],
            ["Event", "event_date", ">=", now()]
        ],
        fields=["name", "event_name", "event_date", "venue", "event_image", "rsvp_count"],
        order_by="event_date asc",
        limit_page_length=limit
    )
    
    return {"events": events}

@frappe.whitelist()
def rsvp_to_event(event_name, response_status="Going", guests=0):
    """RSVP to an event"""
    current_user = frappe.session.user
    
    try:
        # Get alumni record for current user
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, "name")
        if not alumni:
            frappe.throw(_("Alumni profile not found. Please complete your profile first."))
        
        # Check if already RSVPed
        existing_rsvp = frappe.db.get_value(
            "Event RSVP",
            {"event": event_name, "alumni": alumni}
        )
        
        if existing_rsvp:
            # Update existing RSVP
            rsvp = frappe.get_doc("Event RSVP", existing_rsvp)
            rsvp.response_status = response_status
            rsvp.guests = cint(guests)
            rsvp.save()
        else:
            # Create new RSVP
            rsvp = frappe.get_doc({
                "doctype": "Event RSVP",
                "event": event_name,
                "alumni": alumni,
                "response_status": response_status,
                "guests": cint(guests)
            })
            rsvp.save()
        
        return {"status": "success", "message": "RSVP updated successfully"}
    except Exception as e:
        frappe.throw(_(f"Error processing RSVP: {str(e)}"))

# ============== DONATION ENDPOINTS ==============

@frappe.whitelist(allow_guest=True)
def create_donation(donor_name, donor_email, amount, purpose="General Fund", payment_method="Card"):
    """Create a donation record"""
    try:
        donation = frappe.get_doc({
            "doctype": "Donation",
            "donor_name": donor_name,
            "donor_email": donor_email,
            "amount": float(amount),
            "purpose": purpose,
            "payment_method": payment_method,
            "status": "Pending",
            "donation_date": today()
        })
        donation.insert(ignore_permissions=True)
        
        return {
            "status": "success",
            "donation_id": donation.name,
            "message": "Donation created. Awaiting payment confirmation."
        }
    except Exception as e:
        frappe.throw(_(f"Error creating donation: {str(e)}"))

@frappe.whitelist()
def get_donation_stats():
    """Get donation statistics"""
    total_donations = frappe.db.get_value(
        "Donation",
        filters={"status": "Completed"},
        fieldname="sum(amount)"
    ) or 0
    
    total_count = frappe.db.count("Donation", filters={"status": "Completed"})
    
    return {
        "total_amount": total_donations,
        "total_donors": total_count,
        "average_donation": total_donations / total_count if total_count > 0 else 0
    }

# ============== WALL POST ENDPOINTS ==============

@frappe.whitelist()
def create_wall_post(title, content, featured_image=None):
    """Create a wall post"""
    current_user = frappe.session.user
    
    try:
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, "name")
        if not alumni:
            frappe.throw(_("Alumni profile not found."))
        
        post = frappe.get_doc({
            "doctype": "Wall Post",
            "title": title,
            "content": content,
            "alumni": alumni,
            "featured_image": featured_image,
            "status": "Draft"
        })
        post.insert()
        
        return {
            "status": "success",
            "post_id": post.name,
            "message": "Post created as draft. Pending admin approval."
        }
    except Exception as e:
        frappe.throw(_(f"Error creating post: {str(e)}"))

@frappe.whitelist()
def like_wall_post(post_name):
    """Like a wall post"""
    current_user = frappe.session.user
    
    try:
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, "name")
        
        # Check if already liked
        existing_like = frappe.db.get_value(
            "Wall Post Like",
            {"post": post_name, "alumni": alumni}
        )
        
        if not existing_like:
            frappe.get_doc({
                "doctype": "Wall Post Like",
                "post": post_name,
                "alumni": alumni
            }).insert()
            
            # Increment likes count
            post = frappe.get_doc("Wall Post", post_name)
            post.likes_count = (post.likes_count or 0) + 1
            post.save()
        
        return {"status": "success", "message": "Post liked!"}
    except Exception as e:
        frappe.throw(_(f"Error liking post: {str(e)}"))

# ============== MEMBERSHIP ENDPOINTS ==============

@frappe.whitelist()
def check_membership_status():
    """Check current user's membership status"""
    current_user = frappe.session.user
    
    try:
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, "name")
        
        membership = frappe.db.get_value(
            "Membership",
            {"alumni": alumni},
            ["name", "membership_type", "status", "expiry_date"]
        )
        
        if membership:
            return {
                "has_membership": True,
                "type": membership[1],
                "status": membership[2],
                "expiry_date": membership[3]
            }
        else:
            return {"has_membership": False}
    except Exception as e:
        frappe.throw(_(f"Error checking membership: {str(e)}"))