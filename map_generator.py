import plotly.express as px
import folium
from streamlit_folium import st_folium
from exceptions import MapError  # Fixed import

class MapGenerator:
    def create_plotly_map(self, df, marker_size=8):
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
            raise MapError(f"Plotly map creation failed: {e}")

    def create_folium_map(self, sorted_df):
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
                return m
            
            center = [sorted_df["lat"].mean(), sorted_df["longi"].mean()]
            m = folium.Map(location=center, zoom_start=12, tiles="OpenStreetMap")

            route_points = sorted_df[["lat", "longi"]].values.tolist()
            folium.plugins.AntPath(
                locations=route_points,
                color="#0066cc",
                weight=6,
                dash_array=[10, 20],
                delay=1000,
                pulse_gap=500
            ).add_to(m)

            for i, row in sorted_df.iterrows():
                icon_color = "green" if i == 0 else "red" if i == len(sorted_df)-1 else "blue"
                folium.Marker(
                    location=[row["lat"], row["longi"]],
                    popup=f"<b>{row['sequence']}. {row['outlet_name']}</b><br>Type: {row['type_name']}<br>Total Outlets: {len(sorted_df)}",
                    tooltip=f"{row['sequence']}. {row['outlet_name']}",
                    icon=folium.Icon(color=icon_color, icon="store", prefix="fa")
                ).add_to(m)
            
            return m
        except Exception as e:
            raise MapError(f"Folium map creation failed: {e}")