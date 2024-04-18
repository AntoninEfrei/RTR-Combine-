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
    most_blue_pick_champions = df_blue['champion'].value_counts() # ??????????
    position_b1_pick = df_blue[df_blue['pickOrder'] == 1]['champion'].value_counts()
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

    return most_blue_pick_champions, position_b1_pick, position_r3_pick, position_r5_pick, matrix_counts_blue, matrix_counts_red, matrix_percentages_blue, matrix_percentages_red

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

def get_games_player_stats(list_game_end_geng_compet, list_players):
    # Initialize empty lists to store data
    players = []
    champions = []
    kills = []
    assists = []
    deaths = []
    kdas = []
    kill_participations = []
    damage_per_minutes = []
    gold_per_minutes = []
    team_damage_percentages = []
    plates_takens = []
    plates_losts = []
    enemy_jgl_camp_killeds = []
    vision_score_per_minutes = []
    pink_ward_time_coverage_in_ennemy_or_rivers = []
    control_wards_boughts = []
    wards_placeds = []
    wards_killeds = []
    csm = []
    wins = []
    # Loop through each game in the list
    for game in list_game_end_geng_compet:
        for index in range(10):  # Assuming there are always 10 participants in a game
            player_data = game['participants'][index]
            player = player_data['riotIdGameName']

            if player in list_players:
                players.append(player)
                champions.append(player_data['championName'])
                kills.append(player_data['kills'])
                assists.append(player_data['assists'])
                deaths.append(player_data['deaths'])
                kdas.append(player_data['challenges']['kda'])
                kill_participations.append(player_data['challenges']['killParticipation'])
                damage_per_minutes.append(player_data['challenges']['damagePerMinute'])
                gold_per_minutes.append(player_data['challenges']['goldPerMinute'])
                team_damage_percentages.append(player_data['challenges']['teamDamagePercentage'])
                plates_takens.append(player_data['challenges']['turretPlatesTaken'])
                plates_losts.append(player_data['challenges']['turretTakedowns'])
                enemy_jgl_camp_killeds.append(player_data['challenges']['enemyJungleMonsterKills'])
                vision_score_per_minutes.append(player_data['challenges']['visionScorePerMinute'])
                try : 
                    pink_ward_time_coverage_in_ennemy_or_rivers.append(player_data['challenges']['controlWardTimeCoverageInRiverOrEnemyHalf'])
                except KeyError:
                    pink_ward_time_coverage_in_ennemy_or_rivers.append(0)
                control_wards_boughts.append(player_data['visionWardsBoughtInGame'])
                wards_placeds.append(player_data['wardsPlaced'])
                wards_killeds.append(player_data['wardsKilled'])
                csm.append((player_data['totalMinionsKilled']+player_data['totalAllyJungleMinionsKilled']+player_data['totalEnemyJungleMinionsKilled'])/(game['gameDuration']/60))
                wins.append(player_data['win'])

    # Create a DataFrame
    df = pd.DataFrame({
        'Player': players,
        'Champion': champions,
        'KDA': kdas,
        'Kills': kills,
        'Deaths': deaths,
        'Assists' : assists,
        'Kill Participation': kill_participations,
        'Damage Per Minute': damage_per_minutes,
        'Gold Per Minute': gold_per_minutes,
        'Team Damage Percentage': team_damage_percentages,
        'Plates Taken': plates_takens,
        'Plates Lost': plates_losts,
        'Enemy Jungle Camp Killed': enemy_jgl_camp_killeds,
        'Vision Score Per Minute': vision_score_per_minutes,
        'Pink Ward Time Coverage': pink_ward_time_coverage_in_ennemy_or_rivers,
        'Control Wards Bought': control_wards_boughts,
        'Wards Placed': wards_placeds,
        'Wards Killed': wards_killeds,
        'Cs/min':csm,
        'Win': wins
    })

    return df

def player_champion_stats(df):
    # Grouping data by champion
    champion_group = df.groupby('Champion')

    # Calculating statistics
    champion_stats_df = pd.DataFrame()
    champion_stats_df['Games'] = champion_group['Player'].count()
    champion_stats_df['KDA'] = champion_group['KDA'].mean()
    champion_stats_df['KP'] = champion_group['Kill Participation'].mean()*100
    champion_stats_df['DmgShare'] = champion_group['Team Damage Percentage'].mean()*100
    champion_stats_df['Gold/min'] = champion_group['Gold Per Minute'].mean()
    champion_stats_df['Dmg/min'] = champion_group['Damage Per Minute'].mean()
    champion_stats_df['Cs/min'] = champion_group['Cs/min'].mean()


    gold_damage_ratios = []
    for champion, group in champion_group:
        gold_damage_ratio = (group['Damage Per Minute'] / group['Gold Per Minute']).mean()
        gold_damage_ratios.append(gold_damage_ratio)

    champion_stats_df['G/D ratio'] = gold_damage_ratios

    champion_stats_df['W/R'] = champion_group['Win'].mean()*100
    return champion_stats_df.sort_values(by='Games', ascending= False).round(1)

def player_champion_vision_stats(df):
    # Grouping data by champion
    champion_group = df.groupby('Champion')

    # Calculating vision statistics
    vision_stats_df = pd.DataFrame()
    vision_stats_df['Games'] = champion_group['Player'].count()
    vision_stats_df['Wards Placed'] = champion_group['Wards Placed'].mean()
    vision_stats_df['Wards Killed'] = champion_group['Wards Killed'].mean()
    vision_stats_df['WardsLifetime'] = champion_group['Pink Ward Time Coverage'].mean()
    vision_stats_df['ControlWards Bought'] = champion_group['Control Wards Bought'].mean()
    vision_stats_df['VisionScore/Minute'] = champion_group['Vision Score Per Minute'].mean()

    return vision_stats_df.sort_values(by='Games', ascending= False).round(1)

def player_stats(df):

    # Player stats
    player_stats_dict = {
        'Average KDA': [df['KDA'].mean()],
        'Average Kill Participation': [df['Kill Participation'].mean() * 100],
        'Average Team Damage Share': [df['Team Damage Percentage'].mean() * 100],
        'Average Gold/Minute': [df['Gold Per Minute'].mean()],
        'Average Damage/Minute': [df['Damage Per Minute'].mean()],
        'Average Cs/Minute': [df['Cs/min'].mean()]

    }

    # Calculate gold/damage ratio for all games
    if not df.empty:
        valid_rows = df[(df['Gold Per Minute'] != 0) & (df['Damage Per Minute'] != 0)]
        if not valid_rows.empty:
            gold_damage_ratio = (valid_rows['Damage Per Minute'] / valid_rows['Gold Per Minute']).mean()
            player_stats_dict['Average Gold/Damage Ratio'] = [gold_damage_ratio]

    player_stats_df = pd.DataFrame(player_stats_dict)
    player_stats_df = player_stats_df.set_index('Average KDA')

    # Vision stats
    vision_stats_dict = {
        'Avg Wards Placed': [df['Wards Placed'].mean()],
        'Avg Wards Killed': [df['Wards Killed'].mean()],
        'Avg Control Ward Lifetime %': [df['Pink Ward Time Coverage'].mean()*100],
        'Avg Control Wards Bought': [df['Control Wards Bought'].mean()],
        'Avg Vision Score/min': [df['Vision Score Per Minute'].mean()]
    }
    
    vision_stats_df = pd.DataFrame(vision_stats_dict)
    vision_stats_df = vision_stats_df.set_index('Avg Wards Placed')
    return player_stats_df.round(1), vision_stats_df.round(1)

    

# DATA IMPORTS

with open("list_game_end_geng_compet.json",'r') as file:
    list_game_end_geng_compet = json.load(file)
with open("list_game_timeline_geng_compet.json",'r') as file:
    list_game_timeline_geng_compet = json.load(file)

list_players = ['GENKiin','GENCanyon','GENChovy','GENPeyz','GENLehends']

Kiin_puuid = "Vpq3Y6Nns_bME-adpgmXfI89CIH3k0MCfDbrWZN2ASTuE8FlBit7rwbz3kzy_t4T8kgpGAo51asizA"
Canyon_puuid = "C7SQvoTcKkF1B2dZxm9Oo5yiRFtp7M5t0QNur_5jiPm1EymkWiVlTQAISnUeqmvqOQcm1QvKjTIYkg"
Chovy_puuid = "0ZeAFCtsYyae-HzXEvKujLs8XQUG-1fUjJiybfBAW1cPHR9ZPMU0hiQlafxPcyNDYkiYW4J-pBkMHQ"
Peyz_puuid  = "KSM9lFqeaD6TAzg5c2hkxxbMhJ01-6d_w6dNNiCaY-vsPRcjRbgXjq1EjhiaPpvW4Da07vFeduKkRQ"
Lehends_puuid = "sbe811AZXiBHw3UDQFn8TMHINYaKCNrMJQM0xUb-K7wBgHVvZ2p0EXVAOtWE-agBX3CNxyMwtjwuwA"

list_puuid = [Kiin_puuid,Canyon_puuid,Chovy_puuid,Peyz_puuid,Lehends_puuid]

# Stylish header
st.set_page_config(layout="wide")


with st.sidebar.expander("Navigation"):
    # Display checkboxes for options within the expander

    page = st.radio('Choose a page',["Home Page","Draft Stats","Player Focus","Reporting In Game","SoloQ Overview"])

#### PAGES ##### 

if page == 'Home Page':
    st.markdown(
    """
    <h1 style='text-align: center; color: #f63366;'>Gen.G Reporting</h1>
    <h4 style='text-align: center; color: #ffffff;'>LIGHT THEME RECOMMENDED</h4>
    <h3 style='text-align: center;'>Running the Rift project made By Gulldiz</h3>
    <hr style='margin-bottom: 20px;'>
    """,
    unsafe_allow_html=True
)
    st.markdown('')
    st.markdown('')
    st.write("French young analyst started 2 months ago discovering RIOT's data world. I'm named Antonin aka Gulldiz I am 23 yo currently at my last year of a Master's degree in DataScience in Paris. I am pleased to present you my work of the last 4 days. I started from the principle that I present my work to the coach of a NACL team that will play against Gen.G in a Fearless Final (Which i'm new to - fun mode tho). I've taken some decisions about what to show and what to not because the timeline is kinda short - but enough.")
    st.markdown('')
    st.markdown('')

    
    st.write('Shoutout to RTR Combine project that offers us opportunities to work and showcase it. It has been a pleasure to work in this case study.')
    st.write('Any feedbacks or recommendations is warmly welcome - do not hesitate on discord (Gulldiz) or elsewhere')

elif page == "Draft Stats":

    df_spring24_geng_draft = get_spring24_geng_draft()


    st.title('Reporting Gen.G Draft')
    col_tab1,col_tab2,col_tab3,col_tab4 = st.columns([3,3,3,5])

    #scope on the choosen data
    list_competitions = df_spring24_geng_draft['ShownName'].unique().tolist()
    competition_choice = st.sidebar.multiselect('Choose Step',list_competitions, default = list_competitions)
    df_spring24_geng_draft_scope = df_spring24_geng_draft[df_spring24_geng_draft['ShownName'].isin(competition_choice)]


    # get the draft datas
    most_blue_pick_champions, position_b1_pick, position_r3_pick, position_r5_pick, matrix_counts_blue, matrix_counts_red, matrix_percentages_blue, matrix_percentages_red = get_prio_position_draft(df_spring24_geng_draft_scope,'Gen.G')
    # MOST PICKED ??? MOST B1 POSITON ?? 
 
    #display matrixes
    st.write(matrix_percentages_blue)
    st.write(matrix_percentages_red)

    with col_tab1:
        st.write('Most pick B1')
        st.write(position_b1_pick)
    with col_tab2:
        st.write('Most pick R3')
        st.write(position_r3_pick)
    with col_tab3:
        st.write('Most pick R5')
        st.write(position_r5_pick)

elif page == "Reporting In Game":
    
    st.title('Reporting In Game')
  
elif page == "SoloQ Overview":
   
   st.title('Reporting SoloQ')

elif page == "Player Focus":


    

    col_tab1,col_tab2 = st.columns([3,8])


   
    with col_tab1:

        with st.expander("Choose Player", expanded = False):
            # Display options within the expander
            player = st.radio("Players", list_players)


    df_players_stats = get_games_player_stats(list_game_end_geng_compet,list_players) #from list of dict to all GenG players stats only
    df_players_stats_scope = df_players_stats[df_players_stats['Player'] == player] #focus on choosen player
    
    with col_tab2:
        # PLAYER WISE FOCUS
   
        df_player, df_player_vision = player_stats(df_players_stats_scope)
        st.write('Player stats')
        st.write(df_player)
        
        st.write('Vision stats')
        st.write(df_player_vision)


    # CHAMPIONS WISE FOCUS
    st.title('Champion Focus')
    st.write('Champion Stats')
    df_player_champion_stats = player_champion_stats(df_players_stats_scope)
    st.write(df_player_champion_stats)
    if player in ['GENLehends','GENCanyon']:
        st.write('Vision Stats')
        df_player_vision_stats = player_champion_vision_stats(df_players_stats_scope)
        st.write(df_player_vision_stats)

    # HEAT MAPS 