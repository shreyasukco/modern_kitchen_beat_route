import streamlit as st
import pandas as pd
import time
import plotly.express as px
import numpy as np
import folium
from geopy.distance import geodesic
from streamlit_folium import st_folium
from scipy.spatial import distance_matrix
import json
import traceback
import os
import random  # Essential for genetic algorithm operations

# ------------------- Authentication -------------------
def load_authorized_users():
    """Load authorized users from JSON file"""
    try:
        if not os.path.exists("authorized_users.json"):
            # Create default admin if file doesn't exist
            default_users = {
                "9483933659": {"name": "Admin User", "role": "admin"},
                "6362253376": {"name": "Sales Rep", "role": "user"}
            }
            with open("authorized_users.json", "w") as f:
                json.dump(default_users, f)
            return default_users
        
        with open("authorized_users.json", "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading user data: {e}")
        return {}

def authenticate_user():
    """Authenticate user based on mobile number"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_role = None
        st.session_state.user_name = None
    
    if not st.session_state.authenticated:
        # st.title("🔐 Modern-Kitchen Authentication")
        
        with st.form("auth_form"):
            mobile_number = st.text_input("Enter your 10-digit mobile number", 
                                         placeholder="9876543210",
                                         max_chars=10)
            
            if st.form_submit_button("Authenticate"):
                authorized_users = load_authorized_users()
                if mobile_number in authorized_users:
                    st.session_state.authenticated = True
                    st.session_state.user_role = authorized_users[mobile_number]["role"]
                    st.session_state.user_name = authorized_users[mobile_number]["name"]
                    st.success(f"Welcome, {st.session_state.user_name}!")
                    st.rerun()
                else:
                    st.error("You are not authorized to access this system. Please contact your administrator.")
        st.stop()
    
    return st.session_state.user_role

# ------------------- Page Config -------------------
st.set_page_config(
    page_title="MODERN-KITCHEN BEAT MAP",
    layout="wide",
    initial_sidebar_state="expanded"
)

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ------------------- Load Data -------------------
@st.cache_data
def load_data():
    try:
        dff = pd.read_csv("2025-06-16T12-18_export.csv")

        for col in dff.select_dtypes(include='object').columns:
            dff[col] = dff[col].astype(str).fillna("").replace("nan", "")

        dff["lat"] = pd.to_numeric(dff["lat"], errors="coerce")
        dff["longi"] = pd.to_numeric(dff["longi"], errors="coerce")

        dff = dff.dropna(subset=["lat", "longi"])
        dff = dff[(dff['lat'] != 0) | (dff['longi'] != 0)]
        
        # Add unique ID for outlets
        dff["outlet_id"] = dff["outlet_name"] + "_" + dff["lat"].astype(str) + "_" + dff["longi"].astype(str)
        
        return dff
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.error(traceback.format_exc())
        return pd.DataFrame()

# ------------------- Map Function -------------------
def create_map(df, marker_size=8):
    try:
        if df.empty:
            return None

        center_lat = df["lat"].mean()
        center_lon = df["longi"].mean()

        if "full_beat" in df.columns:
            df["full_beat"] = df["full_beat"].astype(str)

        fig = px.scatter_mapbox(
            df,
            lat="lat",
            lon="longi",
            color="full_beat",
            hover_name="full_beat" if "full_beat" in df.columns else None,
            hover_data=["outlet_name","type_name", "pin_code", "district", "taluka","beat_number"],
            zoom=10,
            center={"lat": center_lat, "lon": center_lon},
            height=600,
            opacity=0.7
        )

        fig.update_layout(
            mapbox_style="carto-positron",
            margin=dict(r=0, t=0, l=0, b=0),
            hovermode="closest",
            showlegend=True
        )

        fig.update_traces(marker=dict(size=marker_size), selector=dict(mode="markers"))

        return fig
        
    except Exception as e:
        st.error(f"Error creating map: {e}")
        st.error(traceback.format_exc())
        return None

# ------------------- Route Optimization Functions -------------------
def two_opt_improved(route, dist_matrix):
    """Improved 2-opt algorithm with limited search window"""
    best = route.copy()
    improved = True
    while improved:
        improved = False
        for i in range(1, len(route) - 2):
            for j in range(i + 2, min(len(route), i + 15)):
                a, b, c, d = best[i - 1], best[i], best[j - 1], best[j % len(best)]
                current = dist_matrix[a, b] + dist_matrix[c, d]
                potential = dist_matrix[a, c] + dist_matrix[b, d]
                if potential < current:
                    best[i:j] = best[i:j][::-1]
                    improved = True
    return best

def route_distance_numba(route, dist_matrix):
    """Calculate total distance of a route"""
    total = 0.0
    for i in range(len(route) - 1):
        total += dist_matrix[route[i], route[i+1]]
    return total

@st.cache_data(show_spinner=True, max_entries=20)
def optimize_single_beat(coords):
    try:
        n = len(coords)
        if n < 2:
            return list(range(n))

        dist_matrix = distance_matrix(coords, coords)
        
        population_size = min(200, max(50, n * 2))
        generations = min(1000, max(100, n * 5))
        mutation_rate = max(0.01, min(0.1, 0.5 / n))

        def create_individual():
            individual = np.random.permutation(n)
            return two_opt_improved(individual, dist_matrix)

        population = [create_individual() for _ in range(population_size)]
        progress_bar = st.progress(0)

        for gen in range(generations):
            population = sorted(population, key=lambda x: route_distance_numba(x, dist_matrix))
            next_gen = population[:10]
            
            while len(next_gen) < population_size:
                p1, p2 = random.choices(population[:50], k=2)
                a, b = sorted(random.sample(range(n), 2))
                child = np.concatenate([
                    p2[~np.isin(p2, p1[a:b])],
                    p1[a:b]
                ])
                
                if random.random() < mutation_rate:
                    i, j = random.sample(range(n), 2)
                    child[i], child[j] = child[j], child[i]
                
                child = two_opt_improved(child, dist_matrix)
                next_gen.append(child)
            
            population = next_gen
            progress_bar.progress((gen + 1) / generations)

        progress_bar.empty()
        return min(population, key=lambda x: route_distance_numba(x, dist_matrix))
        
    except Exception as e:
        st.error(f"Error in route optimization: {e}")
        st.error(traceback.format_exc())
        return list(range(len(coords)))

# ------------------- UI Components -------------------
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

# ------------------- Main App -------------------
def main():
    try:
        # Authenticate user
        user_role = authenticate_user()
        is_admin = user_role == "admin"
        
        # Custom CSS
        st.markdown("""
        <style>
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
        </style>
        """, unsafe_allow_html=True)

        # User info badge
        st.markdown(f"""
        <div class="user-info">
            👤 {st.session_state.user_name} | {user_role.capitalize()}
            <span class="logout-btn" onclick="window.location.href='?logout=true'">🔒 Logout</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Handle logout using modern st.query_params
        if st.query_params.get('logout'):
            st.session_state.authenticated = False
            st.session_state.user_role = None
            st.session_state.user_name = None
            st.rerun()

        # Main header
        st.markdown("""
        <div class="header-container">
            <h1>📍 MODERN-KITCHEN: Outlet Beat Mapping</h1>
        </div>
        """, unsafe_allow_html=True)

        # Load data
        with st.spinner("Loading outlet data..."):
            df = load_data()

        if df.empty:
            st.warning("No outlet data loaded. Please check your data source.")
            return

        # Filter container
        st.markdown("### 🔍 Filter Options")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            all_beats = sorted(df["full_beat"].unique()) if "full_beat" in df.columns else []
            selected_beat = st.selectbox(
                "Select a beat to view details",
                options=["All Beats"] + all_beats,
                index=0
            )
            
        with col2:
            if is_admin:
                st.markdown("### ⚙️ Map Settings")
                marker_size = st.slider(
                    "Marker size",
                    min_value=3,
                    max_value=20,
                    value=8,
                    label_visibility="collapsed"
                )
            else:
                marker_size = 8  # Default size for non-admins

        # Apply beat filter
        if selected_beat == "All Beats":
            df_display = df
        else:
            df_display = df[df["full_beat"] == selected_beat]

        # ADMIN FEATURES
        if is_admin:
            # Show map
            st.markdown("### 🗺️ Outlet Locations by Beat")
            with st.spinner("Generating map visualization..."):
                fig = create_map(df_display, marker_size=marker_size)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No valid location data to display.")
                    
            # Show table of outlet count per beat
            st.markdown("### 📊 Outlet Count per Beat")
            if "full_beat" in df_display.columns:
                beat_counts = (
                    df_display.groupby("full_beat")
                    .size()
                    .reset_index(name="Number of Outlets")
                    .sort_values("Number of Outlets", ascending=False)
                )
                st.dataframe(beat_counts, use_container_width=True)
            else:
                st.info("No beat information available in the dataset.")
                
            # Route Optimization (Admin only)
            st.markdown("### 🚗 Route Optimization")
            if selected_beat != "All Beats":
                beat_df = df_display.copy()
                coords = beat_df[["lat", "longi"]].values
                
                if len(coords) > 0:
                    with st.spinner(f"Optimizing route for {selected_beat}..."):
                        try:
                            route_order = optimize_single_beat(coords)
                            sorted_df = beat_df.iloc[route_order].copy()
                            sorted_df.reset_index(drop=True, inplace=True)
                            sorted_df["sequence"] = sorted_df.index + 1
                            sorted_df["gmaps_link"] = "https://www.google.com/maps/search/?api=1&query=" + \
                                                    sorted_df["lat"].astype(str) + "," + \
                                                    sorted_df["longi"].astype(str)
                            
                            # Calculate total distance
                            total_distance = 0
                            for i in range(1, len(sorted_df)):
                                point1 = (sorted_df.iloc[i-1]["lat"], sorted_df.iloc[i-1]["longi"])
                                point2 = (sorted_df.iloc[i]["lat"], sorted_df.iloc[i]["longi"])
                                total_distance += geodesic(point1, point2).km
                            
                            sorted_df["total_distance"] = total_distance
                            
                            st.markdown(f"<div class='beat-header'><h3>Beat Details: {selected_beat}</h3></div>", unsafe_allow_html=True)
                            
                            # Download button
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
                                st.error(f"Error creating download file: {e}")
                            
                            # Show optimized sequence
                            if "total_distance" in sorted_df.columns:
                                total_distance = sorted_df["total_distance"].iloc[0]
                                st.info(f"**Total Route Distance:** {total_distance:.2f} km")
                            
                            # Create two columns
                            col1, col2 = st.columns([1, 1])
                            
                            with col1:
                                st.markdown("#### Outlet Details")
                                for i, row in sorted_df.iterrows():
                                    outlet_info_card(row)
                            
                            with col2:
                                st.markdown("#### 📍 Optimized Route Map")
                                try:
                                    if len(sorted_df) == 1:
                                        center = [sorted_df["lat"].iloc[0], sorted_df["longi"].iloc[0]]
                                        m = folium.Map(location=center, zoom_start=14, tiles="OpenStreetMap")
                                        folium.Marker(
                                            location=[sorted_df["lat"].iloc[0], sorted_df["longi"].iloc[0]],
                                            popup=f"<b>1. {sorted_df['outlet_name'].iloc[0]}</b><br>Total Outlets: 1",
                                            tooltip=sorted_df["outlet_name"].iloc[0],
                                            icon=folium.Icon(color="green", icon="store", prefix="fa")
                                        ).add_to(m)
                                        st_folium(m, width=600, height=500, returned_objects=[])
                                    else:
                                        center = [sorted_df["lat"].mean(), sorted_df["longi"].mean()]
                                        m = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap")

                                        # Add route path
                                        route_points = sorted_df[["lat", "longi"]].values.tolist()
                                        folium.plugins.AntPath(
                                            locations=route_points,
                                            color="#0066cc",
                                            weight=6,
                                            dash_array=[10, 20],
                                            delay=1000,
                                            pulse_gap=500
                                        ).add_to(m)

                                        # Add markers
                                        for i, row in sorted_df.iterrows():
                                            icon_color = "green" if i == 0 else "red" if i == len(sorted_df)-1 else "blue"
                                            folium.Marker(
                                                location=[row["lat"], row["longi"]],
                                                popup=f"""
                                                    <b>{row['sequence']}. {row['outlet_name']}</b><br>
                                                    Type: {row['type_name']}<br>
                                                    Total Outlets: {len(sorted_df)}
                                                """,
                                                tooltip=f"{row['sequence']}. {row['outlet_name']}",
                                                icon=folium.Icon(color=icon_color, icon="store", prefix="fa")
                                            ).add_to(m)

                                        st_folium(m, width=600, height=500, returned_objects=[])
                                except Exception as e:
                                    st.error(f"Error creating map: {e}")
                        except Exception as e:
                            st.error(f"Error optimizing route: {e}")            
                else:
                    st.warning(f"No outlets found for beat: {selected_beat}")
            else:
                st.info("Select a specific beat to view route optimization details.")
                
        # NON-ADMIN VIEW
        else:
            st.info(f"👤 Welcome {st.session_state.user_name}. You have access to outlet details but not mapping features.")
            
            if selected_beat != "All Beats":
                beat_df = df[df["full_beat"] == selected_beat].copy()
                
                if not beat_df.empty:
                    st.markdown(f"### 📋 Outlets in Beat: {selected_beat}")
                    st.markdown(f"**Total Outlets:** {len(beat_df)}")
                    
                    # Add sequence number and Google Maps link
                    beat_df["sequence"] = range(1, len(beat_df) + 1)
                    beat_df["gmaps_link"] = "https://www.google.com/maps/search/?api=1&query=" + \
                                          beat_df["lat"].astype(str) + "," + \
                                          beat_df["longi"].astype(str)
                    
                    # Show outlet cards
                    for i, row in beat_df.iterrows():
                        outlet_info_card(row)
                else:
                    st.warning(f"No outlets found in beat: {selected_beat}")
            else:
                st.info("Select a specific beat to view outlet details")
            
    except Exception as e:
        st.error(f"Unexpected application error: {e}")
        st.error(traceback.format_exc())

if __name__ == "__main__":
    main()