import streamlit as st
import json
import pandas as pd
from mwclient import Site
import json 
import requests


# FUNCTIONS 
def get_red_blue_df(df,teamname):
    #function that from the df_lec and a teamname gets blue and red side data as follow : 'Championplayed, pickOrder, pickOrder_2 (B1/B2/B3...) Position in game'


    #Keeping only the data of the wanted Team and checking if both sides exists(here BDS)

    blue_none = False
    red_none = False
    #blue
    blue_df = df[df['Blue'] == teamname][['BluePicksByRoleOrder']]
    if blue_df.empty:
        print('No data for blue side')
        blue_none = True
        draft_blue = pd.DataFrame()
    #red  
    red_df = df[df['Red'] == teamname][['RedPicksByRoleOrder']]
    if red_df.empty: 
        print('No data for red side')
        red_none = True
        draft_red = pd.DataFrame()
    #both  
    if red_none and blue_none:
        print('No data for blue AND red side')
        return None,None
    
    #mapping for position and pickorder_2 column
    position_mapping = {1: 'TOP', 2: 'JGL', 3: 'MID', 4: 'ADC', 5: 'SUPP'}
    pickorder_blue_mapping = {1: 'B1', 2: 'B2/B3', 3: 'B2/B3', 4: 'B4/B5', 5: 'B4/B5'}
    pickorder_red_mapping = {1: 'R1/R2', 2: 'R1/R2', 3: 'R3', 4: 'R4', 5: 'R5'}
    
    #Creating Red df if exists :
    if not red_df.empty:
        new_data = []
        for index, row in red_df.iterrows():
            
            for champion, order in row['RedPicksByRoleOrder'].items():  # Iterate through each champion and its order in the draft
                
                index_of_key = list(row['RedPicksByRoleOrder'].keys()).index(champion) # Get the index of the key in the original dictionary
                new_data.append({'champion': champion, 'pickOrder': order, 'position': index_of_key +1 }) # Append the data to the list
        
        draft_red = pd.DataFrame(new_data) # Create a new DataFrame from the list of data
        draft_red['position'] = draft_red['position'].map(position_mapping)
        draft_red['Red Side Picks'] = draft_red['pickOrder'].map(pickorder_red_mapping)
    #----------------------------------
    
    #Creating Blue df if exists : 
    if not blue_df.empty:
        new_data = []
        for index, row in blue_df.iterrows():
            
            for champion, order in row['BluePicksByRoleOrder'].items():
                
                index_of_key = list(row['BluePicksByRoleOrder'].keys()).index(champion)
                new_data.append({'champion': champion, 'pickOrder': order, 'position': index_of_key +1 })
                
        draft_blue = pd.DataFrame(new_data)
        draft_blue['position'] = draft_blue['position'].map(position_mapping)
        draft_blue['Blue Side Picks'] = draft_blue['pickOrder'].map(pickorder_blue_mapping)


        
    
        
    return draft_red,draft_blue

def get_prio_position_draft(df_draft,team_name):
    
    #get the list as dict (pickbyroleorder)
    for index, row in df_draft.iterrows():
        blue_champions_dict = {}
        red_champions_dict = {}
 
        # Iterate over the champions in the "BluePicksByRoleOrder" column
        for champion in row['BluePicksByRoleOrder']:
    
            for column_index, value in enumerate(row):

                if champion == df_draft.iloc[index,column_index]:
                    
                    blue_champions_dict[champion] = column_index - 17
                
        for champion in row['RedPicksByRoleOrder']:

            for column_index, value in enumerate(row):
                        
                if champion == df_draft.iloc[index,column_index]:
                    red_champions_dict[champion] = column_index - 22
       
        df_draft.at[index, 'BluePicksByRoleOrder'] = blue_champions_dict
        df_draft.at[index, 'RedPicksByRoleOrder'] = red_champions_dict  

    df_red,df_blue = get_red_blue_df(df_draft,team_name)  

    
    desired_order = ['TOP', 'JGL', 'MID', 'ADC', 'SUPP']
    most_picked_champions = df_blue['champion'].value_counts()
    position_b1_pick = df_blue[df_blue['pickOrder'] == 1]['position'].value_counts()
    position_r3_pick = df_red[df_red['pickOrder'] == 3]['champion'].value_counts()
    position_r5_pick = df_red[df_red['pickOrder'] == 5]['champion'].value_counts()


    # Set the position column as categorical with the desired order
    df_red['position'] = pd.Categorical(df_red['position'], categories=desired_order, ordered=True)
    df_blue['position'] = pd.Categorical(df_blue['position'], categories=desired_order, ordered=True)

    # Pivot the DataFrame and calculate the percentage of occurrences for each combination
    matrix_counts_blue = df_blue.pivot_table(index='position', columns='Blue Side Picks', aggfunc='size', fill_value=0, observed = True)
    matrix_percentages_blue = (matrix_counts_blue.div(matrix_counts_blue.sum(axis=1), axis=0) * 100).round(1)

    matrix_counts_red = df_red.pivot_table(index='position', columns='Red Side Picks', aggfunc='size', fill_value=0, observed = True)
    matrix_percentages_red = (matrix_counts_red.div(matrix_counts_red.sum(axis=1), axis=0) * 100).round(2)

    return most_picked_champions, position_b1_pick, position_r3_pick, position_r5_pick, matrix_counts_blue, matrix_counts_red, matrix_percentages_blue, matrix_percentages_red

def get_spring24_geng_draft():
    site = Site('lol.fandom.com', path="/")
    tournament = "LCK/2024 Season/Spring Season"
    team = 'Gen.G'
    fields = [
        "PAB.Team1PicksByRoleOrder",
        "PAB.Team2PicksByRoleOrder",
        "MS.ShownName",
        "MSG.Blue",
        "MSG.Red",
        "MSG.Winner",
        "MSG.N_GameInMatch",
        "MS.BestOf",
        "PAB.Team1Ban1",
        *["PAB.Team{}Ban{}".format(i,j) for i in range(1,3) for j in range(1,6)],
        *["PAB.Team{}Pick{}".format(i,j) for i in range(1,3) for j in range(1,6)],
        "MS.DateTime_UTC",
        "MSG.RiotPlatformGameId",
    
    ]

    cargo_query = site.api(
        "cargoquery",
        limit = "max",
        tables = "MatchSchedule = MS,MatchScheduleGame = MSG, PicksAndBansS7 = PAB",
        fields = ",".join(fields),
        where = 'MS.OverviewPage="{}"'.format(tournament) + 'OR MSG.Blue ="{}"'.format(team) +'OR MSG.Red ="{}"'.format(team),
        order_by = "MS.DateTime_UTC DESC",
        join_on = "MS.MatchId = MSG.MatchId, MSG.GameId = PAB.GameId"
    )

    df = pd.DataFrame([d['title'] for d in cargo_query['cargoquery']])
    df_spring24 = df[df['ShownName'].isin(['LCK 2024 Spring','LCK 2024 Spring Playoffs'])]
    df_spring24 = df_spring24[(df_spring24['Blue'] == 'Gen.G') | (df_spring24['Red'] == 'Gen.G')]
    df_spring24 = df_spring24.rename(columns=lambda x: x.replace('Team1', 'Blue') if 'Team1' in x else x)
    df_spring24 = df_spring24.rename(columns=lambda x: x.replace('Team2', 'Red') if 'Team2' in x else x)
    df_spring24['RedPicksByRoleOrder'] = df_spring24['RedPicksByRoleOrder'].apply(lambda x: x.split(','))
    df_spring24['BluePicksByRoleOrder'] = df_spring24['BluePicksByRoleOrder'].apply(lambda x: x.split(','))
    df_spring24['ShownName'] = df_spring24['ShownName'].replace({'LCK 2024 Spring Playoffs': 'Spring Playoffs 24', 'LCK 2024 Spring': 'Spring Split 24'})

    df_spring24.reset_index(drop = True , inplace = True)
    return df_spring24

 ### DATA IMPORTS

# DATA IMPORTS

with open("list_game_end_geng_compet.json",'r') as file:
    list_game_end_geng_compet = json.load(file)
with open("list_game_timeline_geng_compet.json",'r') as file:
    list_game_timeline_geng_compet = json.load(file)

df_spring24_geng_draft = get_spring24_geng_draft()


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
    
    #scope on the choosen data
    list_competitions = df_spring24_geng_draft['ShownName'].unique().tolist()
    competition_choice = st.sidebar.multiselect('Choose Step',list_competitions, default = list_competitions)
    df_spring24_geng_draft_scope = df_spring24_geng_draft[df_spring24_geng_draft['ShownName'].isin(competition_choice)]

    # get the draft datas
    most_picked_champions, position_b1_pick, position_r3_pick, position_r5_pick, matrix_counts_blue, matrix_counts_red, matrix_percentages_blue, matrix_percentages_red = get_prio_position_draft(df_spring24_geng_draft,'Gen.G')
    
    st.write(most_picked_champions)
    #display matrixes
    st.write(matrix_percentages_blue)
    st.write(matrix_percentages_red)


elif page == "Reporting In Game":
    
    st.title('Reporting In Game')
  
    
    
elif page == "SoloQ Overview":
   
   st.title('Reporting SoloQ')
