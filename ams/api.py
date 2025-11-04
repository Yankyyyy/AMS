import frappe
from frappe import _
from frappe.utils import cint, today, add_days, now, get_datetime
from frappe.exceptions import ValidationError
import json
import re

# ============== RESPONSE HELPERS ==============

def success_response(data=None, message="Success", status_code=200):
    """Standardized success response"""
    return {
        "success": True,
        "message": message,
        "data": data,
        "status": status_code
    }

def error_response(message="Error", error_code="UNKNOWN_ERROR", status_code=400):
    """Standardized error response"""
    frappe.log_error(title=error_code, message=message)
    return {
        "success": False,
        "message": message,
        "error_code": error_code,
        "status": status_code
    }

def paginate(items, page=1, page_size=20):
    """Helper to paginate results"""
    page = max(1, cint(page))
    page_size = min(cint(page_size), 100)  # Max 100 per page
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        "items": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": len(items)
    }

# ============== AUTH ENDPOINTS ==============

@frappe.whitelist(allow_guest=True)
def register_alumni(email, first_name, last_name, batch_year, phone=None, course=None):
    """Register new alumni"""
    try:
        # Validate email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return error_response("Invalid email format", "INVALID_EMAIL", 400)
        
        # Check if alumni exists
        if frappe.db.exists("Alumni", email):
            return error_response("Alumni already registered", "ALUMNI_EXISTS", 409)
        
        # Create alumni record
        alumni = frappe.get_doc({
            "doctype": "Alumni",
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "batch_year": cint(batch_year),
            "course": course,
            "status": "Active"
        })
        alumni.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return success_response(
            {"email": alumni.email, "name": alumni.name},
            "Alumni registered successfully. Check your email for verification.",
            201
        )
    except Exception as e:
        return error_response(str(e), "REGISTRATION_ERROR", 500)

@frappe.whitelist(allow_guest=True)
def login(email, password):
    """Authenticate user and return token"""
    try:
        # Note: This is a simplified example. Use Frappe's built-in auth in production
        user = frappe.db.get_value("User", email, ["name", "password"])
        if not user:
            return error_response("Invalid credentials", "AUTH_FAILED", 401)
        
        # Generate session token (Frappe handles this)
        from frappe.auth import LoginManager
        login_manager = LoginManager()
        login_manager.authenticate(email, password)
        
        alumni = frappe.db.get_value("Alumni", {"email": email}, "name")
        
        return success_response(
            {
                "token": frappe.session.sid,
                "email": email,
                "alumni_id": alumni
            },
            "Login successful"
        )
    except Exception as e:
        return error_response(str(e), "AUTH_ERROR", 401)

@frappe.whitelist()
def get_current_user():
    """Get current logged-in user's profile"""
    try:
        current_user = frappe.session.user
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, [
            "name", "first_name", "last_name", "email", "phone",
            "batch_year", "course", "job_title", "company", "bio",
            "profile_picture", "linkedin_url", "location", "status"
        ])
        
        if not alumni:
            return error_response("Alumni profile not found", "PROFILE_NOT_FOUND", 404)
        
        return success_response({
            "id": alumni[0],
            "first_name": alumni[1],
            "last_name": alumni[2],
            "email": alumni[3],
            "phone": alumni[4],
            "batch_year": alumni[5],
            "course": alumni[6],
            "job_title": alumni[7],
            "company": alumni[8],
            "bio": alumni[9],
            "profile_picture": alumni[10],
            "linkedin_url": alumni[11],
            "location": alumni[12],
            "status": alumni[13]
        })
    except Exception as e:
        return error_response(str(e), "USER_FETCH_ERROR", 500)

# ============== ALUMNI ENDPOINTS ==============

@frappe.whitelist()
def get_alumni_profile(alumni_id):
    """Get detailed alumni profile by ID or email"""
    try:
        alumni = frappe.get_doc("Alumni", alumni_id)
        
        # Get posts count
        posts_count = frappe.db.count("Wall Post", {"alumni": alumni.name, "status": "Published"})
        
        # Get membership status
        membership = frappe.db.get_value("Membership", {"alumni": alumni.name}, 
                                        ["membership_type", "status", "expiry_date"])
        
        return success_response({
            "id": alumni.name,
            "first_name": alumni.first_name,
            "last_name": alumni.last_name,
            "email": alumni.email,
            "phone": alumni.phone,
            "batch_year": alumni.batch_year,
            "course": alumni.course,
            "job_title": alumni.job_title,
            "company": alumni.company,
            "bio": alumni.bio,
            "profile_picture": alumni.profile_picture,
            "linkedin_url": alumni.linkedin_url,
            "location": alumni.location,
            "status": alumni.status,
            "joined_on": alumni.joined_on,
            "posts_count": posts_count,
            "membership": {
                "type": membership[0] if membership else None,
                "status": membership[1] if membership else None,
                "expiry_date": membership[2] if membership else None
            } if membership else None
        })
    except frappe.DoesNotExistError:
        return error_response("Alumni not found", "ALUMNI_NOT_FOUND", 404)
    except Exception as e:
        return error_response(str(e), "PROFILE_FETCH_ERROR", 500)

@frappe.whitelist()
def search_alumni(query="", batch_year=None, course=None, company=None, page=1, page_size=20):
    """Advanced alumni search with filters"""
    try:
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
        if course:
            filters.append(["Alumni", "course", "=", course])
        if company:
            filters.append(["Alumni", "company", "like", f"%{company}%"])
        
        filters.append(["Alumni", "status", "=", "Active"])
        
        results = frappe.db.get_list(
            "Alumni",
            filters=filters,
            fields=["name", "first_name", "last_name", "batch_year", "job_title", 
                   "company", "profile_picture", "location"],
            order_by="modified desc"
        )
        
        paginated = paginate(results, page, page_size)
        return success_response(paginated)
    except Exception as e:
        return error_response(str(e), "SEARCH_ERROR", 500)

@frappe.whitelist()
def get_alumni_by_batch(batch_year, page=1, page_size=20):
    """Get all alumni from a specific batch"""
    try:
        results = frappe.db.get_list(
            "Alumni",
            filters={"batch_year": cint(batch_year), "status": "Active"},
            fields=["name", "first_name", "last_name", "job_title", "company", 
                   "profile_picture", "location"],
            order_by="first_name asc"
        )
        
        paginated = paginate(results, page, page_size)
        return success_response(paginated)
    except Exception as e:
        return error_response(str(e), "BATCH_FETCH_ERROR", 500)

@frappe.whitelist()
def get_alumni_by_course(course, page=1, page_size=20):
    """Get all alumni from a specific course"""
    try:
        results = frappe.db.get_list(
            "Alumni",
            filters={"course": course, "status": "Active"},
            fields=["name", "first_name", "last_name", "batch_year", "job_title", 
                   "company", "profile_picture"],
            order_by="batch_year desc, first_name asc"
        )
        
        paginated = paginate(results, page, page_size)
        return success_response(paginated)
    except Exception as e:
        return error_response(str(e), "COURSE_FETCH_ERROR", 500)

@frappe.whitelist()
def update_alumni_profile(first_name=None, last_name=None, phone=None, bio=None, 
                         job_title=None, company=None, linkedin_url=None, location=None):
    """Update current user's alumni profile"""
    try:
        current_user = frappe.session.user
        alumni = frappe.get_doc("Alumni", {"email": current_user})
        
        if first_name:
            alumni.first_name = first_name
        if last_name:
            alumni.last_name = last_name
        if phone:
            alumni.phone = phone
        if bio:
            alumni.bio = bio
        if job_title:
            alumni.job_title = job_title
        if company:
            alumni.company = company
        if linkedin_url:
            alumni.linkedin_url = linkedin_url
        if location:
            alumni.location = location
        
        alumni.save()
        frappe.db.commit()
        
        return success_response({"name": alumni.name}, "Profile updated successfully")
    except Exception as e:
        return error_response(str(e), "UPDATE_ERROR", 500)

# ============== WALL POST ENDPOINTS ==============

@frappe.whitelist()
def get_feed(page=1, page_size=20, sort_by="latest"):
    """Get alumni feed (posts)"""
    try:
        order_by = "published_on desc" if sort_by == "latest" else "likes_count desc"
        
        posts = frappe.db.get_list(
            "Wall Post",
            filters={"status": "Published"},
            fields=["name", "title", "content", "alumni", "featured_image", 
                   "likes_count", "published_on"],
            order_by=order_by
        )
        
        # Enrich with alumni info
        enriched_posts = []
        for post in posts:
            alumni = frappe.db.get_value("Alumni", post.alumni, 
                                        ["first_name", "last_name", "profile_picture"])
            post["author"] = {
                "id": post.alumni,
                "name": f"{alumni[0]} {alumni[1]}",
                "profile_picture": alumni[2]
            }
            enriched_posts.append(post)
        
        paginated = paginate(enriched_posts, page, page_size)
        return success_response(paginated)
    except Exception as e:
        return error_response(str(e), "FEED_FETCH_ERROR", 500)

@frappe.whitelist()
def create_wall_post(title, content, featured_image=None):
    """Create a new wall post"""
    try:
        current_user = frappe.session.user
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, "name")
        
        if not alumni:
            return error_response("Alumni profile not found", "PROFILE_NOT_FOUND", 404)
        
        post = frappe.get_doc({
            "doctype": "Wall Post",
            "title": title,
            "content": content,
            "alumni": alumni,
            "featured_image": featured_image,
            "status": "Draft"
        })
        post.insert()
        frappe.db.commit()
        
        return success_response(
            {"id": post.name, "status": "draft"},
            "Post created successfully. Pending admin approval.",
            201
        )
    except Exception as e:
        return error_response(str(e), "POST_CREATE_ERROR", 500)

@frappe.whitelist()
def update_wall_post(post_id, title=None, content=None, featured_image=None):
    """Update a wall post (draft only)"""
    try:
        current_user = frappe.session.user
        post = frappe.get_doc("Wall Post", post_id)
        
        # Check permissions
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, "name")
        if post.alumni != alumni:
            return error_response("Unauthorized", "PERMISSION_DENIED", 403)
        
        if post.status != "Draft":
            return error_response("Cannot edit published posts", "POST_LOCKED", 400)
        
        if title:
            post.title = title
        if content:
            post.content = content
        if featured_image:
            post.featured_image = featured_image
        
        post.save()
        frappe.db.commit()
        
        return success_response({"id": post.name}, "Post updated successfully")
    except frappe.DoesNotExistError:
        return error_response("Post not found", "POST_NOT_FOUND", 404)
    except Exception as e:
        return error_response(str(e), "POST_UPDATE_ERROR", 500)

@frappe.whitelist()
def like_wall_post(post_id):
    """Like a wall post"""
    try:
        current_user = frappe.session.user
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, "name")
        
        if not alumni:
            return error_response("Alumni profile not found", "PROFILE_NOT_FOUND", 404)
        
        # Check if already liked
        existing_like = frappe.db.get_value(
            "Wall Post Like",
            {"post": post_id, "alumni": alumni}
        )
        
        if existing_like:
            return error_response("Already liked", "ALREADY_LIKED", 400)
        
        # Create like
        frappe.get_doc({
            "doctype": "Wall Post Like",
            "post": post_id,
            "alumni": alumni
        }).insert()
        
        # Update likes count
        post = frappe.get_doc("Wall Post", post_id)
        post.likes_count = (post.likes_count or 0) + 1
        post.save()
        frappe.db.commit()
        
        return success_response({"likes_count": post.likes_count}, "Post liked!")
    except Exception as e:
        return error_response(str(e), "LIKE_ERROR", 500)

@frappe.whitelist()
def unlike_wall_post(post_id):
    """Unlike a wall post"""
    try:
        current_user = frappe.session.user
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, "name")
        
        like_doc = frappe.db.get_value(
            "Wall Post Like",
            {"post": post_id, "alumni": alumni},
            "name"
        )
        
        if not like_doc:
            return error_response("Not liked yet", "NOT_LIKED", 400)
        
        frappe.delete_doc("Wall Post Like", like_doc)
        
        # Update likes count
        post = frappe.get_doc("Wall Post", post_id)
        post.likes_count = max(0, (post.likes_count or 1) - 1)
        post.save()
        frappe.db.commit()
        
        return success_response({"likes_count": post.likes_count}, "Post unliked!")
    except Exception as e:
        return error_response(str(e), "UNLIKE_ERROR", 500)

@frappe.whitelist()
def get_wall_post(post_id):
    """Get a specific wall post"""
    try:
        post = frappe.get_doc("Wall Post", post_id)
        alumni = frappe.db.get_value("Alumni", post.alumni, 
                                    ["first_name", "last_name", "profile_picture"])
        
        return success_response({
            "id": post.name,
            "title": post.title,
            "content": post.content,
            "featured_image": post.featured_image,
            "likes_count": post.likes_count,
            "status": post.status,
            "published_on": post.published_on,
            "author": {
                "id": post.alumni,
                "name": f"{alumni[0]} {alumni[1]}",
                "profile_picture": alumni[2]
            }
        })
    except frappe.DoesNotExistError:
        return error_response("Post not found", "POST_NOT_FOUND", 404)
    except Exception as e:
        return error_response(str(e), "POST_FETCH_ERROR", 500)

# ============== EVENT ENDPOINTS ==============

@frappe.whitelist()
def get_upcoming_events(page=1, page_size=10):
    """Get upcoming events"""
    try:
        events = frappe.db.get_list(
            "AMS Event",
            filters=[
                ["AMS Event", "status", "in", ["Upcoming", "Ongoing"]],
                ["AMS Event", "event_date", ">=", now()]
            ],
            fields=["name", "event_name", "event_date", "venue", "event_image", 
                   "rsvp_count", "max_capacity", "description"],
            order_by="event_date asc"
        )
        
        paginated = paginate(events, page, page_size)
        return success_response(paginated)
    except Exception as e:
        return error_response(str(e), "EVENTS_FETCH_ERROR", 500)

@frappe.whitelist()
def get_event_details(event_id):
    """Get detailed event information"""
    try:
        event = frappe.get_doc("AMS Event", event_id)
        
        # Get RSVP details
        rsvps = frappe.db.get_list(
            "Event RSVP",
            filters={"event": event.name},
            fields=["alumni", "response_status", "guests"],
            group_by="response_status"
        )
        
        rsvp_stats = {
            "going": 0,
            "maybe": 0,
            "not_going": 0
        }
        for rsvp in rsvps:
            status_key = rsvp.response_status.lower().replace(" ", "_")
            rsvp_stats[status_key] = frappe.db.count("Event RSVP", 
                                                     {"event": event.name, 
                                                      "response_status": rsvp.response_status})
        
        return success_response({
            "id": event.name,
            "name": event.event_name,
            "description": event.description,
            "date": event.event_date,
            "venue": event.venue,
            "image": event.event_image,
            "status": event.status,
            "max_capacity": event.max_capacity,
            "rsvp_stats": rsvp_stats
        })
    except frappe.DoesNotExistError:
        return error_response("Event not found", "EVENT_NOT_FOUND", 404)
    except Exception as e:
        return error_response(str(e), "EVENT_FETCH_ERROR", 500)

@frappe.whitelist()
def rsvp_event(event_id, response_status="Going", guests=0):
    """RSVP to an event"""
    try:
        current_user = frappe.session.user
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, "name")
        
        if not alumni:
            return error_response("Alumni profile not found", "PROFILE_NOT_FOUND", 404)
        
        # Check if already RSVPed
        existing_rsvp = frappe.db.get_value(
            "Event RSVP",
            {"event": event_id, "alumni": alumni},
            "name"
        )
        
        if existing_rsvp:
            rsvp = frappe.get_doc("Event RSVP", existing_rsvp)
            rsvp.response_status = response_status
            rsvp.guests = cint(guests)
            rsvp.save()
        else:
            rsvp = frappe.get_doc({
                "doctype": "Event RSVP",
                "event": event_id,
                "alumni": alumni,
                "response_status": response_status,
                "guests": cint(guests)
            })
            rsvp.insert()
        
        frappe.db.commit()
        
        return success_response({"rsvp_id": rsvp.name}, "RSVP updated successfully")
    except Exception as e:
        return error_response(str(e), "RSVP_ERROR", 500)

@frappe.whitelist()
def get_my_rsvps():
    """Get current user's event RSVPs"""
    try:
        current_user = frappe.session.user
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, "name")
        
        if not alumni:
            return error_response("Alumni profile not found", "PROFILE_NOT_FOUND", 404)
        
        rsvps = frappe.db.get_list(
            "Event RSVP",
            filters={"alumni": alumni},
            fields=["name", "event", "response_status", "guests", "rsvp_date"]
        )
        
        # Enrich with event info
        enriched = []
        for rsvp in rsvps:
            event = frappe.db.get_value("AMS Event", rsvp.event, 
                                       ["event_name", "event_date", "venue"])
            rsvp["event_details"] = {
                "id": rsvp.event,
                "name": event[0],
                "date": event[1],
                "venue": event[2]
            }
            enriched.append(rsvp)
        
        return success_response({"rsvps": enriched})
    except Exception as e:
        return error_response(str(e), "MY_RSVPS_ERROR", 500)

# ============== DONATION ENDPOINTS ==============

@frappe.whitelist(allow_guest=True)
def create_donation(donor_name, donor_email, amount, purpose="General Fund", 
                   payment_method="Card", payment_reference=None):
    """Create a donation record"""
    try:
        if float(amount) <= 0:
            return error_response("Amount must be greater than 0", "INVALID_AMOUNT", 400)
        
        donation = frappe.get_doc({
            "doctype": "Donation",
            "donor_name": donor_name,
            "donor_email": donor_email,
            "amount": float(amount),
            "purpose": purpose,
            "payment_method": payment_method,
            "payment_reference": payment_reference,
            "status": "Pending",
            "donation_date": today()
        })
        donation.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return success_response(
            {"donation_id": donation.name},
            "Donation created successfully",
            201
        )
    except Exception as e:
        return error_response(str(e), "DONATION_ERROR", 500)

@frappe.whitelist()
def get_donation_stats():
    """Get donation statistics"""
    try:
        total = frappe.db.get_value(
            "Donation",
            filters={"status": "Completed"},
            fieldname="sum(amount)"
        ) or 0
        
        count = frappe.db.count("Donation", filters={"status": "Completed"})
        
        return success_response({
            "total_amount": total,
            "total_donors": count,
            "average_donation": total / count if count > 0 else 0
        })
    except Exception as e:
        return error_response(str(e), "STATS_ERROR", 500)

# ============== MEMBERSHIP ENDPOINTS ==============

@frappe.whitelist()
def check_membership_status():
    """Check current user's membership status"""
    try:
        current_user = frappe.session.user
        alumni = frappe.db.get_value("Alumni", {"email": current_user}, "name")
        
        if not alumni:
            return error_response("Alumni profile not found", "PROFILE_NOT_FOUND", 404)
        
        membership = frappe.db.get_value(
            "Membership",
            {"alumni": alumni},
            ["name", "membership_type", "status", "expiry_date", "start_date"]
        )
        
        if membership:
            return success_response({
                "id": membership[0],
                "type": membership[1],
                "status": membership[2],
                "expiry_date": membership[3],
                "start_date": membership[4]
            })
        else:
            return success_response(None, "No active membership")
    except Exception as e:
        return error_response(str(e), "MEMBERSHIP_ERROR", 500)

# ============== INSTITUTION ENDPOINTS ==============

@frappe.whitelist()
def get_institutions(page=1, page_size=50):
    """Get all institutions"""
    try:
        institutions = frappe.db.get_list(
            "Institution",
            filters={"status": "Active"},
            fields=["name", "institution_name", "institution_code", "institution_type", 
                   "city", "country", "contact_email", "website"],
            order_by="institution_name asc"
        )
        
        paginated = paginate(institutions, page, page_size)
        return success_response(paginated)
    except Exception as e:
        return error_response(str(e), "INSTITUTIONS_ERROR", 500)

# ============== STATISTICS & ANALYTICS ==============

@frappe.whitelist()
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        total_alumni = frappe.db.count("Alumni", {"status": "Active"})
        total_posts = frappe.db.count("Wall Post", {"status": "Published"})
        total_donations = frappe.db.get_value(
            "Donation",
            filters={"status": "Completed"},
            fieldname="sum(amount)"
        ) or 0
        upcoming_events = frappe.db.count(
            "AMS Event",
            filters=[["AMS Event", "event_date", ">=", now()]]
        )
        
        return success_response({
            "total_alumni": total_alumni,
            "total_posts": total_posts,
            "total_donations": total_donations,
            "upcoming_events": upcoming_events
        })
    except Exception as e:
        return error_response(str(e), "STATS_ERROR", 500)