from pygwalker.api.streamlit import StreamlitRenderer
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
 
st.set_page_config(
    page_title="Test",
    layout="wide"
)

conn = st.connection("gsheets", type=GSheetsConnection)

df = conn.read()

pyg_app = StreamlitRenderer(df)
 
pyg_app.explorer()