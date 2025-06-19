import pandas as pd
import streamlit as st
from exceptions import DataError  # Fixed import
from constants import DATA_FILE

class DataLoader:
    @st.cache_data
    def load_data(_self):
        try:
            dff = pd.read_csv(DATA_FILE)
            
            for col in dff.select_dtypes(include='object').columns:
                dff[col] = dff[col].astype(str).fillna("").replace("nan", "")
            
            dff["lat"] = pd.to_numeric(dff["lat"], errors="coerce")
            dff["longi"] = pd.to_numeric(dff["longi"], errors="coerce")
            
            dff = dff.dropna(subset=["lat", "longi"])
            dff = dff[(dff['lat'] != 0) | (dff['longi'] != 0)]
            
            dff["outlet_id"] = dff["outlet_name"] + "_" + dff["lat"].astype(str) + "_" + dff["longi"].astype(str)
            
            return dff
        except Exception as e:
            raise DataError(f"Data loading error: {e}")