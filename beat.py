import streamlit as st
import pandas as pd
import traceback
from streamlit_folium import st_folium
from auth import AuthenticationManager
from data_loader import DataLoader
from route_optimizer import RouteOptimizer
from map_generator import MapGenerator
from ui_components import UIComponents
from admin import AdminPanel
import time

auth_manager = AuthenticationManager()
data_loader = DataLoader()
route_optimizer = RouteOptimizer()
map_generator = MapGenerator()
ui_components = UIComponents()

st.set_page_config(
    page_title="MODERN-KITCHEN BEAT MAP",
    layout="wide",
    initial_sidebar_state="collapsed"
)

ui_components.apply_custom_styles()

def main():
    try:
        user_role = auth_manager.authenticate_user()
        is_admin = user_role == "admin"
        user_name = st.session_state.user_name

        ui_components.create_main_header()

        # Custom green-styled welcome message (shown only once per session)
        if "welcome_shown" not in st.session_state:
            welcome_placeholder = st.empty()
            welcome_placeholder.markdown(
                f"""
                <div style='
                    padding: 1rem;
                    background-color: #eafaf1;
                    border-left: 5px solid #2ecc71;
                    border-radius: 5px;
                    color: #2c662d;
                    font-weight: 500;
                '>
                    👋 Welcome, <strong>{user_name}</strong>! You're logged in as 
                    <strong>{'Administrator' if is_admin else 'Field User'}</strong>.
                </div>
                """,
                unsafe_allow_html=True
            )
            time.sleep(1)  # Show the message for 2 seconds
            welcome_placeholder.empty()
            st.session_state.welcome_shown = True

        # Persistent info message for non-admins
        if not is_admin:
            st.info("Select your beat from the dropdown to view your outlet visit plan")

        try:
            with st.spinner("Loading outlet data..."):
                df = data_loader.load_data()
        except Exception as e:
            st.error(f"Data loading error: {e}")
            return

        if df.empty:
            st.warning("No outlet data loaded. Please check your data source.")
            return

        if is_admin:
            try:
                admin_panel = AdminPanel(df)
                admin_panel.render()
            except Exception as e:
                st.error(f"Admin panel error: {e}")

        st.markdown("##### Filter Options")
        col1, col2 = st.columns([3, 1])


        if is_admin:
            all_beats = sorted(df["full_beat"].unique()) if "full_beat" in df.columns else []
        else:
            all_beats = st.session_state.assigned_beats

        options_list = ["All Beats"] + all_beats if all_beats else ["All Beats"]

        selected_beat = st.selectbox(
            "Select a beat to view details",
            options=options_list,
            index=0
        )

        if selected_beat == "All Beats" and all_beats:
            df_display = df[df["full_beat"].isin(all_beats)] if not is_admin else df
        elif selected_beat != "All Beats":
            df_display = df[df["full_beat"] == selected_beat]
        else:
            df_display = pd.DataFrame()

        # Show map only for admins
        if is_admin:
            st.markdown("### 🗺️ Outlet Locations by Beat")
            try:
                with st.spinner("Generating map visualization..."):
                    fig = map_generator.create_plotly_map(df_display, marker_size=9)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("No valid location data to display.")
            except Exception as e:
                st.error(f"Map generation error: {e}")
                
        # ADMIN VIEW: Full route optimization features
        if is_admin and not df_display.empty and selected_beat != "All Beats":
            st.markdown("### 🚗 Route Optimization")
            beat_df = df_display.copy()
            coords = beat_df[["lat", "longi"]].values
            
            if len(coords) > 0:
                try:
                    with st.spinner(f"Optimizing route for {selected_beat}..."):
                        route_order = route_optimizer.optimize_single_beat(coords)
                        sorted_df = beat_df.iloc[route_order].copy()
                        sorted_df.reset_index(drop=True, inplace=True)
                        sorted_df["sequence"] = sorted_df.index + 1
                        sorted_df["gmaps_link"] = "https://www.google.com/maps/search/?api=1&query=" + \
                                                sorted_df["lat"].astype(str) + "," + \
                                                sorted_df["longi"].astype(str)
                        
                        total_distance = route_optimizer.calculate_route_distance(sorted_df)
                        sorted_df["total_distance"] = total_distance
                        
                        st.markdown(f"<div class='beat-header'><h3>Beat Details: {selected_beat}</h3></div>", unsafe_allow_html=True)
                        
                        st.markdown("### 💾 Download Beat Details")
                        try:
                            download_df = sorted_df.copy()
                            if "geometry" in download_df.columns:
                                download_df = download_df.drop(columns=["geometry"])
                            
                            csv = download_df.to_csv(index=False).encode('utf-8')
                            
                            st.download_button(
                                label="Download optimized beat details as CSV",
                                data=csv,
                                file_name=f"{selected_beat}_optimized_route.csv",
                                mime="text/csv"
                            )
                        except Exception as e:
                            st.error(f"CSV export error: {e}")
                        
                        st.info(f"**Total Minimum Route Distance:** {total_distance:.2f} km")
                        
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.markdown("#### Outlet Details")
                            for i, row in sorted_df.iterrows():
                                ui_components.outlet_info_card(row)
                        
                        with col2:
                            st.markdown("#### 📍 Optimized Route Map")
                            try:
                                folium_map = map_generator.create_folium_map(sorted_df)
                                st_folium(folium_map, width=600, height=500, returned_objects=[])
                            except Exception as e:
                                st.error(f"Route map error: {e}")
                except Exception as e:
                    st.error(f"Route optimization error: {e}")            
            else:
                st.warning(f"No outlets found for beat: {selected_beat}")
                
        # USER VIEW: Optimized outlet list with same style as admin
        elif not is_admin and not df_display.empty and selected_beat != "All Beats":
            st.markdown(f"<div class='beat-header'><h3>Beat: {selected_beat}</h3></div>", unsafe_allow_html=True)
            
            beat_df = df_display.copy()
            coords = beat_df[["lat", "longi"]].values
            
            if len(coords) > 0:
                try:
                    with st.spinner(f"Optimizing visit order for {selected_beat}..."):
                        route_order = route_optimizer.optimize_single_beat(coords)
                        sorted_df = beat_df.iloc[route_order].copy()
                        sorted_df.reset_index(drop=True, inplace=True)
                        sorted_df["sequence"] = sorted_df.index + 1
                        sorted_df["gmaps_link"] = "https://www.google.com/maps/search/?api=1&query=" + \
                                                sorted_df["lat"].astype(str) + "," + \
                                                sorted_df["longi"].astype(str)
                        
                        total_distance = route_optimizer.calculate_route_distance(sorted_df)
                        
                        st.info(f"**Total Minimum Route Distance:** {total_distance:.2f} km")
                        st.info(f"**Number of Outlets:** {len(sorted_df)}")
                        
                        # Show optimized sequence in the same style as admin
                        st.markdown("#### Outlet Visit Plan")
                        for i, row in sorted_df.iterrows():
                            ui_components.outlet_info_card(row)
                        
                        # Download button for user
                        st.markdown("### 💾 Download Visit Plan")
                        try:
                            download_df = sorted_df.copy()
                            if "geometry" in download_df.columns:
                                download_df = download_df.drop(columns=["geometry"])
                            
                            # Keep only essential columns for users
                            user_columns = [
                                "sequence", "outlet_name", "type_name", "owner_name", 
                                "contact_no", "street_address", "landmark", "gmaps_link"
                            ]
                            download_df = download_df[user_columns]
                            
                            csv = download_df.to_csv(index=False).encode('utf-8')
                            
                            st.download_button(
                                label="Download visit plan as CSV",
                                data=csv,
                                file_name=f"{selected_beat}_visit_plan.csv",
                                mime="text/csv"
                            )
                        except Exception as e:
                            st.error(f"Error creating download file: {e}")
                except Exception as e:
                    st.error(f"Error optimizing visit order: {e}")            
            else:
                st.warning(f"No outlets found for beat: {selected_beat}")
        # elif not is_admin:
        #     st.info("👆 Select a beat to view your outlet visit plan")
                
    except Exception as e:
        st.error(f"Unexpected application error: {e}")
        st.error(traceback.format_exc())

if __name__ == "__main__":
    main()