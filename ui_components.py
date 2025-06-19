import streamlit as st

class UIComponents:
    @staticmethod
    def apply_custom_styles():
        st.markdown("""
        <style>
        #MainMenu, footer, header {visibility: hidden;}
        .header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px;
            background: linear-gradient(135deg, #003d8f, #0066cc);
            border-radius: 10px;
            color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .beat-header {
            background: linear-gradient(135deg, #003d8f, #0066cc);
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .info-card {
            border: 1px solid #dee2e6;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            background: #ffffff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .user-info {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(0, 61, 143, 0.9);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 14px;
            z-index: 1000;
        }
        .logout-btn {
            color: white !important;
            text-decoration: underline !important;
            margin-left: 10px;
            cursor: pointer;
        }
        .admin-form {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #dee2e6;
        }
        .admin-section {
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }
        .admin-section h3 {
            color: #003d8f;
            border-bottom: 2px solid #003d8f;
            padding-bottom: 10px;
        }
        </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def outlet_info_card(row):
        try:
            with st.expander(f"🔹 {row['sequence']}. {row['outlet_name']}", expanded=False):
                st.markdown("#### Google Maps Link")
                st.markdown(f"""
                <div style="margin-bottom:20px;">
                    <a href="{row['gmaps_link']}" target="_blank" style="text-decoration:none;">
                        <button style="background:#198754; color:white; border:none; border-radius:4px; padding:8px 16px; cursor:pointer; width:100%;">
                            🗺️ Open in Google Maps
                        </button>
                    </a>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown("###### Outlet Information")
                    st.markdown(f"**Outlet Name**  \n{row['outlet_name']}")
                    st.markdown(f"**Outlet Type**  \n{row['type_name']}")
                    st.markdown(f"**Beat**  \n{row['full_beat']}")
                    st.markdown(f"**Owner Name**  \n{row['owner_name']}")
                    st.markdown(f"**Owner NO**  \n{row['contact_no']}")
                
                with col2:
                    st.markdown("###### Location Information")
                    st.markdown(f"**District**  \n{row['district']}")
                    st.markdown(f"**Taluka**  \n{row['taluka']}")
                    st.markdown(f"**PIN Code**  \n{row['pin_code']}")
                    st.markdown(f"**street_address**  \n{row['street_address']}")
                    st.markdown(f"**landmark**  \n{row['landmark']}")
        except Exception as e:
            st.error(f"Error creating outlet card: {e}")

    @staticmethod
    def create_main_header():
        st.markdown("""
        <div class="header-container">
            <h1>📍 MODERN-KITCHEN: Outlet Beat Mapping</h1>
        </div>
        """, unsafe_allow_html=True)