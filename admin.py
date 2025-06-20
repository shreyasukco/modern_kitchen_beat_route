import streamlit as st
import time
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
            st.session_state.beat_renaming_selected_beat = None

    def reset_user_management_state(self):
        if 'user_management_state' not in st.session_state:
            st.session_state.user_management_state = {
                'new_mobile': '',
                'new_name': '',
                'new_role': '',
                'selected_user': None,
                'assigned_beats': []
            }

    def beat_renaming(self):
        SELECTED_BEAT_KEY = "beat_renaming_selected_beat"

        with st.expander("✏️ Rename Beat", expanded=False):
            all_beats = sorted(self.df["full_beat"].unique()) if "full_beat" in self.df.columns else []

            if not all_beats:
                st.info("No beats available for renaming")
                st.session_state[SELECTED_BEAT_KEY] = None
                return

            with st.form("beat_rename_form", clear_on_submit=True):
                beat_to_rename = st.selectbox(
                    "Select beat to rename",
                    options=all_beats,
                    index=None,
                    placeholder="Select a beat"
                )

                new_beat_name = st.text_input(
                    "New beat name",
                    placeholder="Enter new beat name"
                ).strip()

                submit_button = st.form_submit_button("🚀 Rename Beat")

            if submit_button:
                if not beat_to_rename:
                    st.error("Please select a beat to rename")
                elif not new_beat_name:
                    st.error("New beat name cannot be empty")
                elif beat_to_rename == new_beat_name:
                    st.error("New name must be different from current name")
                elif new_beat_name in all_beats:
                    st.error("A beat with this name already exists. Please choose a different name.")
                else:
                    try:
                        self.df.loc[self.df['full_beat'] == beat_to_rename, 'full_beat'] = new_beat_name
                        self.df.to_csv(DATA_FILE, index=False)
                        st.cache_data.clear()

                        st.toast(f"Successfully renamed '{beat_to_rename}' to '{new_beat_name}'", icon="✅")
                        time.sleep(2)
                        st.session_state[SELECTED_BEAT_KEY] = None
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
                        placeholder="Enter mobile number",
                        value=""
                    )
                    new_name = st.text_input(
                        "Full Name",
                        placeholder="Enter full name",
                        value=""
                    )
                    new_role = st.selectbox(
                        "Role",
                        ["admin", "user"],
                        index=None,
                        placeholder="Select role"
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
                            elif not new_role:
                                st.error("Please select a role")
                            else:
                                authorized_users[new_mobile] = {
                                    "name": new_name,
                                    "role": new_role,
                                    "assigned_beats": []
                                }
                                if self.auth_manager.save_authorized_users(authorized_users):
                                    st.toast(f"User {new_name} created successfully!", icon="✅")
                                    time.sleep(2)
                                    st.session_state.user_management_state.update({
                                        'new_mobile': '',
                                        'new_name': '',
                                        'new_role': '',
                                    })
                                    st.rerun()
                        except Exception as e:
                            raise AdminError(f"User creation failed: {e}")

            with tab2:
                try:
                    authorized_users = self.auth_manager.load_authorized_users()
                    user_options = [
                        f"{num} - {info['name']} ({info['role']})"
                        for num, info in authorized_users.items()
                        if info["role"] == "user"
                    ]

                    if not user_options:
                        st.info("No users available for assignment")
                        return

                    selected_user = st.selectbox(
                        "Select User",
                        user_options,
                        index=None,
                        placeholder="Select a user"
                    )

                    if selected_user:
                        user_mobile = selected_user.split(" - ")[0]
                        all_beats = sorted(self.df["full_beat"].unique()) if "full_beat" in self.df.columns else []

                        current_assigned = authorized_users[user_mobile]["assigned_beats"]
                        valid_assigned = [beat for beat in current_assigned if beat in all_beats]

                        assigned_beats = st.multiselect(
                            "Assign Beats",
                            options=all_beats,
                            default=valid_assigned,
                            placeholder="Select beats to assign"
                        )

                        if st.button("💾 Save Assignments"):
                            authorized_users[user_mobile]["assigned_beats"] = assigned_beats
                            if self.auth_manager.save_authorized_users(authorized_users):
                                st.toast("Beat assignments updated successfully!", icon="✅")
                                time.sleep(2)
                                st.session_state.user_management_state.update({
                                    'selected_user': None,
                                    'assigned_beats': []
                                })
                                st.rerun()
                except Exception as e:
                    raise AdminError(f"Beat assignment failed: {e}")

    def render(self):
        with st.sidebar:
            st.markdown("### 🔐 Admin Panel")
            self.beat_renaming()
            self.user_management()
