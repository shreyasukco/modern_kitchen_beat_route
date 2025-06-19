import json
import os
import streamlit as st
from exceptions import AuthError  # Fixed import
from constants import AUTH_FILE

class AuthenticationManager:
    def load_authorized_users(self):
        try:
            if not os.path.exists(AUTH_FILE):
                default_users = {
                    "9483933659": {"name": "Admin User", "role": "admin", "assigned_beats": []},
                    "6362253376": {"name": "Sales Rep", "role": "user", "assigned_beats": []}
                }
                with open(AUTH_FILE, "w") as f:
                    json.dump(default_users, f)
                return default_users
            
            with open(AUTH_FILE, "r") as f:
                users = json.load(f)
                for user in users.values():
                    if "assigned_beats" not in user:
                        user["assigned_beats"] = []
                return users
        except Exception as e:
            raise AuthError(f"Error loading user data: {e}")

    def save_authorized_users(self, users):
        try:
            with open(AUTH_FILE, "w") as f:
                json.dump(users, f, indent=2)
            return True
        except Exception as e:
            raise AuthError(f"Error saving user data: {e}")

    def authenticate_user(self):
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
            st.session_state.user_role = None
            st.session_state.user_name = None
            st.session_state.assigned_beats = []
        
        if not st.session_state.authenticated:
            with st.form("auth_form"):
                mobile_number = st.text_input(
                    "Enter your 10-digit mobile number", 
                    placeholder="9876543210",
                    max_chars=10
                )
                
                if st.form_submit_button("Authenticate"):
                    try:
                        authorized_users = self.load_authorized_users()
                        if mobile_number in authorized_users:
                            user_data = authorized_users[mobile_number]
                            st.session_state.authenticated = True
                            st.session_state.user_role = user_data["role"]
                            st.session_state.user_name = user_data["name"]
                            st.session_state.assigned_beats = user_data.get("assigned_beats", [])
                            st.success(f"Welcome, {st.session_state.user_name}!")
                            st.rerun()
                        else:
                            st.error("You are not authorized to access this system.")
                    except AuthError as e:
                        st.error(str(e))
            st.stop()
        
        return st.session_state.user_role