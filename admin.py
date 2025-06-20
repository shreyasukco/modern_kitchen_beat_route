import streamlit as st
from auth import AuthenticationManager
from exceptions import AdminError
from constants import DATA_FILE

class AdminPanel:
    def __init__(self, df):
        self.df = df
        self.auth_manager = AuthenticationManager()
        self.reset_user_management_state()
        
        # Initialize session state keys for beat renaming
        if 'beat_renaming_selected_beat' not in st.session_state:
            st.session_state.beat_renaming_selected_beat = ''
        if 'beat_renaming_new_name' not in st.session_state:
            st.session_state.beat_renaming_new_name = ''

    def reset_user_management_state(self):
        """Reset user management form state after successful operations"""
        if 'user_management_state' not in st.session_state:
            st.session_state.user_management_state = {
                'new_mobile': '',
                'new_name': '',
                'new_role': 'user',
                'selected_user': None,
                'assigned_beats': []
            }

    def beat_renaming(self):
        # Define session state key for selected beat
        SELECTED_BEAT_KEY = "beat_renaming_selected_beat"
        
        with st.expander("✏️ Rename Beat", expanded=False):
            all_beats = sorted(self.df["full_beat"].unique()) if "full_beat" in self.df.columns else []
            
            if not all_beats:
                st.info("No beats available for renaming")
                if SELECTED_BEAT_KEY in st.session_state:
                    del st.session_state[SELECTED_BEAT_KEY]
                return
                
            # Initialize or reset selected beat
            if SELECTED_BEAT_KEY not in st.session_state or st.session_state[SELECTED_BEAT_KEY] not in all_beats:
                st.session_state[SELECTED_BEAT_KEY] = all_beats[0]
            
            # Create a form to avoid direct widget state modification
            with st.form("beat_rename_form"):
                beat_to_rename = st.selectbox(
                    "Select beat to rename",
                    options=all_beats,
                    index=all_beats.index(st.session_state[SELECTED_BEAT_KEY])
                )
                
                new_beat_name = st.text_input(
                    "New beat name",
                    placeholder="Enter new beat name"
                ).strip()
                
                submit_button = st.form_submit_button("🚀 Rename Beat")
            
            if submit_button:
                # Validation checks
                if not new_beat_name:
                    st.error("New beat name cannot be empty")
                elif beat_to_rename == new_beat_name:
                    st.error("New name must be different from current name")
                elif new_beat_name in all_beats:
                    st.error("A beat with this name already exists. Please choose a different name.")
                else:
                    try:
                        # Perform rename operation
                        self.df.loc[self.df['full_beat'] == beat_to_rename, 'full_beat'] = new_beat_name
                        self.df.to_csv(DATA_FILE, index=False)
                        st.cache_data.clear()
                        
                        # Show success message
                        st.success(f"Successfully renamed '{beat_to_rename}' to '{new_beat_name}'")
                        
                        # Update beat list
                        updated_beats = sorted(self.df["full_beat"].unique())
                        
                        # Reset selected beat to first in updated list
                        if updated_beats:
                            st.session_state[SELECTED_BEAT_KEY] = updated_beats[0]
                        else:
                            del st.session_state[SELECTED_BEAT_KEY]
                        
                        # Rerun to refresh state
                        st.rerun()
                    except Exception as e:
                        raise AdminError(f"Beat renaming failed: {e}")

    def user_management(self):
        with st.expander("👥 User Management", expanded=False):
            tab1, tab2 = st.tabs(["Create User", "Assign Beats"])
            
            with tab1:
                with st.form("create_user_form", clear_on_submit=True):
                    new_mobile = st.text_input(
                        "Mobile Number (10 digits)", 
                        max_chars=10,
                        value=st.session_state.user_management_state['new_mobile']
                    )
                    new_name = st.text_input(
                        "Full Name",
                        value=st.session_state.user_management_state['new_name']
                    )
                    new_role = st.selectbox(
                        "Role", 
                        ["admin", "user"],
                        index=0 if st.session_state.user_management_state['new_role'] == "admin" else 1
                    )
                    
                    if st.form_submit_button("➕ Create User"):
                        try:
                            authorized_users = self.auth_manager.load_authorized_users()
                            
                            if new_mobile in authorized_users:
                                st.error("User with this mobile number already exists")
                            elif len(new_mobile) != 10 or not new_mobile.isdigit():
                                st.error("Mobile number must be 10 digits")
                            elif not new_name.strip():
                                st.error("Name cannot be empty")
                            else:
                                authorized_users[new_mobile] = {
                                    "name": new_name,
                                    "role": new_role,
                                    "assigned_beats": []
                                }
                                if self.auth_manager.save_authorized_users(authorized_users):
                                    # Reset form state
                                    st.session_state.user_management_state.update({
                                        'new_mobile': '',
                                        'new_name': '',
                                        'new_role': 'user'
                                    })
                                    st.success(f"User {new_name} created successfully!")
                                    st.rerun()
                        except Exception as e:
                            raise AdminError(f"User creation failed: {e}")
            
            with tab2:
                try:
                    authorized_users = self.auth_manager.load_authorized_users()
                    user_options = [f"{num} - {info['name']} ({info['role']})" 
                                   for num, info in authorized_users.items() 
                                   if info["role"] == "user"]
                    
                    if not user_options:
                        st.info("No users available for assignment")
                        return
                    
                    # Get last selected user or first in list
                    default_idx = 0
                    if st.session_state.user_management_state['selected_user']:
                        try:
                            default_idx = user_options.index(st.session_state.user_management_state['selected_user'])
                        except:
                            pass
                    
                    selected_user = st.selectbox(
                        "Select User", 
                        user_options,
                        index=default_idx
                    )
                    
                    # Store current selection
                    st.session_state.user_management_state['selected_user'] = selected_user
                    user_mobile = selected_user.split(" - ")[0]
                    
                    all_beats = sorted(self.df["full_beat"].unique()) if "full_beat" in self.df.columns else []
                    
                    # Get current assignments and filter out non-existent beats
                    current_assigned = authorized_users[user_mobile]["assigned_beats"]
                    valid_assigned = [beat for beat in current_assigned if beat in all_beats]
                    
                    assigned_beats = st.multiselect(
                        "Assign Beats",
                        options=all_beats,
                        default=valid_assigned
                    )
                    
                    if st.button("💾 Save Assignments"):
                        authorized_users[user_mobile]["assigned_beats"] = assigned_beats
                        if self.auth_manager.save_authorized_users(authorized_users):
                            # Reset form state
                            st.session_state.user_management_state['assigned_beats'] = []
                            st.success("Beat assignments updated successfully!")
                            st.rerun()
                except Exception as e:
                    raise AdminError(f"Beat assignment failed: {e}")

    def render(self):
        with st.sidebar:
            st.markdown("### 🔐 Admin Panel")
            self.beat_renaming()
            self.user_management()