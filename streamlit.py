import streamlit as st
import json

# DATA IMPORTS
with open("list_game_end_geng_compet.json",'r') as file:
    list_game_end_geng_compet = json.load('file')
with open("list_game_timeline_geng_compet.json",'r') as file:
    list_game_timeline_geng_compet = json.load('file')

# Stylish header
st.markdown(
    """
    <h2 style='text-align: center; color: #f63366;'>Gen.G Reporting made by Gulldiz</h2>
    <h4 style='text-align: center; color: #ffffff;'>LIGHT THEME RECOMMENDED</h4>
    <hr style='margin-bottom: 20px;'>
    """,
    unsafe_allow_html=True
)



page = st.sidebar.radio("Navigation", ("Home Page","Reporting Draft","Reporting In Game","SoloQ Overview"))


if page == 'Home Page':

    st.write("Homepage for Running the rift project made By Gulldiz"
)
elif page == "Reporting Draft":
    
    
    st.title('Reporting Gen.G Draft')
    
elif page == "Reporting In Game":
    
    st.title('Reporting Gen.G Draft')
  
    
    
elif page == "SoloQ Overview":
   
   st.title('Reporting SoloQ')
