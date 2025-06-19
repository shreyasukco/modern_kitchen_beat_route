import streamlit as st
import pandas as pd
import traceback
from auth import AuthenticationManager  # Fixed import
from data_loader import DataLoader  # Fixed import
from route_optimizer import RouteOptimizer  # Fixed import
from map_generator import MapGenerator  # Fixed import
from ui_components import UIComponents  # Fixed import
from admin import AdminPanel  # Fixed import
from streamlit_folium import st_folium

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
        
        if st.query_params.get('logout'):
            st.session_state.authenticated = False
            st.session_state.user_role = None
            st.session_state.user_name = None
            st.rerun()

        ui_components.create_main_header()

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

        with col1:
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
                
        if not df_display.empty and selected_beat != "All Beats":
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
                        
                        st.info(f"**Total Route Distance:** {total_distance:.2f} km")
                        
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
                
    except Exception as e:
        st.error(f"Unexpected application error: {e}")
        st.error(traceback.format_exc())

if __name__ == "__main__":
    main()