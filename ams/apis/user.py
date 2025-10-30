import frappe
import json
import requests
from ams.utils import createAPIErrorLog


@frappe.whitelist()
def createUser():
    try:
        data = json.loads(frappe.request.data)
        if frappe.db.exists('User', {'email': data.get('email')}):
            return "User already exists"
        else:
            user = frappe.new_doc('User')
            if data.get('first_name'):
                user.first_name = data.get('first_name')
            if data.get('last_name'):
                user.last_name = data.get('last_name')
            if data.get('email'):
                user.email = data.get('email')
            if data.get('gender'):
                user.gender = data.get('gender')
            if data.get('phone'):
                user.phone = data.get('phone')
            if data.get('birth_date'):
                user.birth_date = data.get('birth_date')
            if data.get('location'):
                user.location = data.get('location')
            user.username = frappe.scrub(data.get('first_name'))
            # strip space and @
            user.username = user.username.strip(" @")
            if user.username_exists():
                user.username = user.suggest_username()
            user.send_welcome_email = 1
            user.append('roles', {
                'role': 'Sales User'
            })
            user.save(ignore_permissions=True)
            frappe.db.commit()
            return "User-created successfully"
    except Exception:
        createAPIErrorLog(frappe.get_traceback())


@frappe.whitelist()
def updateUser():
    try:
        data = json.loads(frappe.request.data)
        if not frappe.db.exists("User", {"email": data.get("email")}):
            createUser()
        else:
            user_doc = frappe.get_doc("User", {"email": data.get("email")})

            if user_doc.first_name != data.get("first_name"):
                user_doc.first_name = data.get("first_name")

            if user_doc.last_name != data.get("last_name"):
                user_doc.last_name = data.get("last_name")

            if user_doc.gender != data.get("gender"):
                user_doc.gender = data.get("gender")

            if user_doc.phone != data.get("phone"):
                user_doc.phone = data.get("phone")

            if str(user_doc.birth_date) != str(data.get("birth_date")):
                user_doc.birth_date = data.get("birth_date")

            if user_doc.location != data.get("location"):
                user_doc.location = data.get("location")

            user_doc.save(ignore_permissions=True)
            frappe.db.commit()
            return "User data Updated !"
    except Exception:
        createAPIErrorLog(frappe.get_traceback())


@frappe.whitelist()
def disableUser():
    try:
        if frappe.request.data:
            data = json.loads(frappe.request.data)
            if data.get("email"):
                email = data.get("email")
                if not frappe.db.exists("User", {"email": email}):
                    return email+" User Does not Exist"
                else:
                    user_data = frappe.get_doc("User", email)
                    if user_data.enabled != 1:
                        return email + " User is Already Disabled"
                    else:
                        user_data.enabled = 0
                        user_data.save(ignore_permissions=True)
                        frappe.db.commit()
                        return email + " User Disabled Successfully"
    except Exception:
        createAPIErrorLog(frappe.get_traceback())