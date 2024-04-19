import streamlit as st
import json
import pandas as pd
from mwclient import Site
import json 
import os
import numpy as np 
from scipy.ndimage import gaussian_filter
import matplotlib.pyplot as plt 
from matplotlib import cm 
from PIL import Image
import time

################# FUNCTIONS #####################################################################################

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

            for column_index,value in enumerate(row):

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

    return most_blue_pick_champions, position_b1_pick.reset_index(drop = False), position_r3_pick.reset_index(drop = False), position_r5_pick.reset_index(drop = False), matrix_counts_blue, matrix_counts_red, matrix_percentages_blue.round(1), matrix_percentages_red.round(1)

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

def get_df_event(list_game_timeline_geng_compet):

    # condition :  game['frames'][i]['events'][j]['type'] == 'CHAMPION_KILL'
    # position : game['frames'][i]['events'][j]['position']['x'] & game['frames'][i]['events'][j]['position']['y']
    # killer : game['frames'][i]['events'][j]['killerId'] /// list participants ids assists : game['frames'][i]['events'][j]['assistingParticipantIds'] 
    # deaths : game['frames'][i]['events'][j]['victimId']
    # timestamp : game['frames'][i]['events'][j]['timestamp']


    list_dict_events = []

    for game in list_game_timeline_geng_compet:
     
        for i in range(len(game['frames'])):

            for j in range(len(game['frames'][i]['events'])):
                dict_events = {}
                if game['frames'][i]['events'][j]['type'] == 'CHAMPION_KILL':
                    
                    dict_events['game_id'] = str(game['gameId'])
                    dict_events['event_type'] = game['frames'][i]['events'][j]['type']
                    dict_events['killer'] = game['frames'][i]['events'][j]['killerId']
                    dict_events['deaths'] = game['frames'][i]['events'][j]['victimId']
                    try:
                        dict_events['assists'] = game['frames'][i]['events'][j]['assistingParticipantIds']
                    except KeyError:
                        dict_events['assists'] = None
                    dict_events['x'] = game['frames'][i]['events'][j]['position']['x']
                    dict_events['y'] = game['frames'][i]['events'][j]['position']['y']
                    dict_events['timestamp'] = game['frames'][i]['events'][j]['timestamp'] / 60000
                    list_dict_events.append(dict_events)     

    return pd.DataFrame(list_dict_events)

def map_id_to_names(df_event,df_players_stats):

    grouped = df_players_stats.groupby('GameId')

    # Initialize an empty dictionary to store results
    game_players_dict = {}

    # Iterate over each group
    for game_id, group_df in grouped:
        # Extracting the first unique values of "Player" for each group
        unique_players = group_df['Player'].drop_duplicates().tolist()
        # Storing the result in the dictionary
        game_players_dict[game_id.split("_")[1]] = unique_players


    df_events['killer'] = df_events['killer'].astype(object)
    df_events['deaths'] = df_events['deaths'].astype(object)

    for index, row in df_events.iterrows():
        # Get the gameId for the current row
        game_id = row['game_id']
        
        killer_id = row['killer']-1
        killer_index = int(killer_id) if killer_id is not None else None  # Convert to int if not None
  
        if killer_index is not None and killer_index < len(game_players_dict.get(game_id, [])):
            df_events.at[index, 'killer'] = game_players_dict[game_id][killer_index]
        
        # Replace 'deaths' ID with player name
        deaths_id = row['deaths']-1
        deaths_index = int(deaths_id) if deaths_id is not None else None  # Convert to int if not None
        if deaths_index is not None and deaths_index < len(game_players_dict.get(game_id, [])):
            df_events.at[index, 'deaths'] = game_players_dict[game_id][deaths_index]
            
        # Replace 'assists' IDs with player names
        assists_ids  = row['assists']
        try: 
            assists_names = [game_players_dict[game_id][int(player_id)-1] for player_id in assists_ids if int(player_id) < len(game_players_dict.get(game_id, []))]
        except:
            assists_names = None
    
        df_events.at[index, 'assists'] = assists_names


    return df_events

def get_games_player_stats(list_game_end_geng_compet, list_players):
    # Initialize empty lists to store data
    game_id = []
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

            #if player in list_players:
            game_id.append(game['platformId'] +"_"+str(game['gameId']))
            players.append(player)
            champions.append(player_data['championName'] if player_data['championName'] != 'FiddleSticks' else 'Fiddlesticks')
            kills.append(player_data['kills'])
            assists.append(player_data['assists'])
            deaths.append(player_data['deaths'])
            kdas.append(player_data['challenges']['kda'])
            try:
                kill_participations.append(player_data['challenges']['killParticipation'])
            except KeyError:
                kill_participations.append(0)
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
        'GameId' : game_id,
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

def create_heatmap(position_x,position_y,output:str="output",map_file:str="Image/map.png",debug:bool=False):
    #Valeurs correspondantes au dimension de la map
    x_min = -120 
    x_max = 14870
    y_min = -120
    y_max = 14980

    
    #Nombre de colone pour les histogrames
    bins=1000 #normalement il est optimisé mais sinon il faut le toucher
    #Variable d'ecart type
    sigma=12
    #Variable de localisation de la heatmap
    location_heatmap = 'Image/heatmap.png'

    if debug:
        print(f"[+] Init HeatMap creation with the param :\nx_min:{x_min} | x_max:{x_max}\ny_min:{y_min} | y_max:{y_max}\nsigma:{sigma} | bins:{bins}\nlocation_heatmap:{location_heatmap} | map_file:{map_file}")

    if debug:
        print(f"[+] End attribution variable position\nposition_x:{position_x}\nposition_y:{position_y}")
        print("[+] Caculate the heatmap filter")

    #Calcul de la carte de chaleurs
    heatmap, xedges, yedges = np.histogram2d(position_x, position_y, bins=bins, range=[[x_min,x_max],[y_min,y_max]])
    heatmap = gaussian_filter(heatmap, sigma=sigma)
    
    if debug:
        print("[+] HeatMap Caculated")

    #Création de l'image de la heatmap sans modification
    if debug:
        print("[+] Heatmap filter image creation")
    img = heatmap.T

    fig, ax1 = plt.subplots()
    ax1.imshow(img, extent=[x_min,x_max,y_min,y_max], origin='lower', cmap=cm.jet,alpha=0.8) # ne pas changer

    plt.axis('off')
    
    plt.savefig(location_heatmap, bbox_inches='tight', pad_inches=0,dpi=1000)

    if debug:
        print(f"[+] Image saved at : {location_heatmap}")
    
    #Petit moment pour que le fichier du filtre gaussien soit bien crée
    time.sleep(1)

    #Supprésion du fond
    if debug:
        print(f'[+] Background Suppression')
    
    #Ouverture du filtre gaussien enregistré plus tot
    im = Image.open(location_heatmap)
    
    if debug:
        print('[+] Conversion to RGBA')
    #Convertissement de l'image en tableau contentant le code RGB de l'image
    im = im.convert('RGBA')

    data = np.array(im)
    
    if debug:
        print("[+] Loop delete blue")
    # Boucle pour enlever les nuances de bleu
    for i in range (150,230):
        rgb = data[:,:,:3]
        color = [51, 51, i]
        white = [255,255,255,255]
        mask = np.all(rgb == color, axis = -1)
        # On change les pixels correspondants en blanc
        data[mask] = white
    
    if debug:
        print("[+] Loop end\n[+] New Image Creation")

    #Création de la nouvelle image
    img = Image.fromarray(data)
    datas = img.getdata()
    newData = []
    for item in datas:
        if item[0] == 255 and item[1] == 255 and item[2] == 255:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    img.putdata(newData)
    if debug:
        print('[+] Creation finished')
        img.save("Image/heatmap_transparent.png", "PNG")
        print('[+] Saving the heatmap with transparent background')

    #Ouverture de l'image de fond
    if debug:
        print('[+] Oppening the background map')    
    base_image = Image.open(map_file)
    #Récupération des dimmensions de l'image
    width, height = base_image.size

    # Attribution de l'image de mask
    mask_image = img
    # Resize the mask image to 512x512
    mask_image = mask_image.resize((width, height))

    # Ajout de l'image du mask au dessus de l'image de la map
    base_image.paste(mask_image, (0,0), mask = mask_image)
    if debug:
        print("[+] Saving the output file")
    if debug == False:
        os.remove("heatmap.png")
    base_image.save(str(output)+'.png')    

def path_to_image_html(path): #crédit mascode 
    '''
     This function essentially convert the image url to 
     '<img src="'+ path + '"/>' format. And one can put any
     formatting adjustments to control the height, aspect ratio, size etc.
     within as in the below example. 
    '''

    return '<img src="'+ path + '" style="max-height:50px;"/>'


##################  DATA IMPORTS ####################################################################

with open("list_game_end_geng_compet.json",'r') as file:
    list_game_end_geng_compet = json.load(file)
with open("list_game_timeline_geng_compet.json",'r') as file:
    list_game_timeline_geng_compet = json.load(file)

df_events = pd.read_csv('df_event_v0_not_all_data.csv')

Kiin_puuid = "Vpq3Y6Nns_bME-adpgmXfI89CIH3k0MCfDbrWZN2ASTuE8FlBit7rwbz3kzy_t4T8kgpGAo51asizA"
Canyon_puuid = "C7SQvoTcKkF1B2dZxm9Oo5yiRFtp7M5t0QNur_5jiPm1EymkWiVlTQAISnUeqmvqOQcm1QvKjTIYkg"
Chovy_puuid = "0ZeAFCtsYyae-HzXEvKujLs8XQUG-1fUjJiybfBAW1cPHR9ZPMU0hiQlafxPcyNDYkiYW4J-pBkMHQ"
Peyz_puuid  = "KSM9lFqeaD6TAzg5c2hkxxbMhJ01-6d_w6dNNiCaY-vsPRcjRbgXjq1EjhiaPpvW4Da07vFeduKkRQ"
Lehends_puuid = "sbe811AZXiBHw3UDQFn8TMHINYaKCNrMJQM0xUb-K7wBgHVvZ2p0EXVAOtWE-agBX3CNxyMwtjwuwA"

list_puuid = [Kiin_puuid,Canyon_puuid,Chovy_puuid,Peyz_puuid,Lehends_puuid]
list_players = ['GENKiin','GENCanyon','GENChovy','GENPeyz','GENLehends']

# Stylish header
st.set_page_config(layout="wide")


with st.sidebar.expander("Navigation"):
    # Display checkboxes for options within the expander

    page = st.radio('Choose a page',["Home Page","Draft Stats","Player Focus","Reporting In Game","SoloQ Overview"])

################# PAGES ##################################################################################### 

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

    
    
    st.markdown('')
    st.markdown('')
    st.markdown('')
    st.markdown('')
    st.markdown('')
    st.write('Shoutout to RTR Combine project that offers us opportunities to work and showcase it. It has been a pleasure to work in this case study.')
    st.write('Any feedbacks or recommendations is warmly welcome - do not hesitate on discord (Gulldiz) or elsewhere')
    st.markdown('Competitive Data (Drafts) from [Leaguepedia API](https://lol.fandom.com/wiki/Category:Developer_Documentation)  & In game data from [Riot APi](https://developer.riotgames.com/) nothing reported by hand.')

elif page == "Draft Stats":

    
    df_spring24_geng_draft = get_spring24_geng_draft()
    df_players_stats = get_games_player_stats(list_game_end_geng_compet,list_players)

    list_matchId_playoffs = df_spring24_geng_draft[df_spring24_geng_draft['ShownName'] == 'Spring Playoffs 24']['RiotPlatformGameId'].unique().tolist()
    list_matchId_regular = df_spring24_geng_draft[df_spring24_geng_draft['ShownName'] == 'Spring Split 24']['RiotPlatformGameId'].unique().tolist()

    list_competitions = df_spring24_geng_draft['ShownName'].unique().tolist() 
    list_competitions.append('Spring + Playoffs 24')
    competition_choice = st.sidebar.selectbox('Choose Step',list_competitions)

    # scope player stats on choosen data
    if competition_choice == 'Spring Playoffs 24':
        df_players_stats_scope = df_players_stats[df_players_stats['GameId'].isin(list_matchId_playoffs)]
        df_spring24_geng_draft_scope = df_spring24_geng_draft[df_spring24_geng_draft['ShownName'].isin([competition_choice])]
    elif competition_choice == 'Spring Split 24':
        df_players_stats_scope = df_players_stats[df_players_stats['GameId'].isin(list_matchId_regular)]
        df_spring24_geng_draft_scope = df_spring24_geng_draft[df_spring24_geng_draft['ShownName'].isin([competition_choice])].reset_index(drop = True)
    elif competition_choice == 'Spring + Playoffs 24':
        df_players_stats_scope = df_players_stats
        df_spring24_geng_draft_scope = df_spring24_geng_draft


    st.markdown(f"<h2 style='text-align: center;'>Statistics about Gen.G Drafts</h2><hr style='margin-bottom: 20px;'>", unsafe_allow_html=True)

    col_tab1,col_tab2,col_tab3,col_tab4,col_tab5 = st.columns([3,3,3,3,3])
    columns = [col_tab1,col_tab2,col_tab3,col_tab4,col_tab5]

    for player,col in zip(list_players,columns):
        
        #get the winrate for each player according to his role 
        role_df = df_players_stats_scope[(df_players_stats_scope['Player'] == player)]
        win_rates = role_df.groupby('Champion')['Win'].agg(['mean', 'size'])  # Aggregate mean and count
        win_rates.columns = ['W/R', 'Games']
        win_rates['W/R'] = (win_rates['W/R'] * 100).round(1)
        win_rates = win_rates.sort_values(by='Games', ascending = False)
        
        # display images 
        win_rates = win_rates.reset_index(drop = False)
        win_rates['Champ'] = "https://ddragon.leagueoflegends.com/cdn/14.5.1/img/champion/" + win_rates['Champion'] + ".png"
        win_rates.drop(columns=['Champion'], inplace = True)
        columns = ['Champ'] + [col for col in win_rates.columns if col != 'Champ']
        win_rates = win_rates[columns]   
        win_rates = win_rates.style.format({"Champ":path_to_image_html, "W/R": lambda x: f"{x:.1f}"})
        win_rates = win_rates.hide(axis = "index")
        win_rates = win_rates.to_html(escape = False)
   
        win_rates_html = f'<div style="height: 500px; overflow: auto;">{win_rates}</div>'

        # Display the HTML content in a Streamlit column
        with col:
            st.write(f"### {player} ")
            st.markdown(win_rates_html, unsafe_allow_html=True)

    
    
    with col_tab1:
            # get the draft datas
        most_blue_pick_champions, position_b1_pick, position_r3_pick, position_r5_pick, matrix_counts_blue, matrix_counts_red, matrix_percentages_blue, matrix_percentages_red = get_prio_position_draft(df_spring24_geng_draft_scope,'Gen.G')
        # MOST PICKED ??? MOST B1 POSITON ?? 
    
        #display matrixes
        matrix_percentages_red = matrix_percentages_red.reset_index( drop = False)
        matrix_percentages_blue = matrix_percentages_blue.reset_index( drop = False)


        df1_first_five = position_b1_pick.head().add_prefix('B1_')
        df2_first_five = position_r3_pick.head().add_prefix('R3_')
        df3_first_five = position_r5_pick.head().add_prefix('R5_')

        # Concatenate the DataFrames horizontally
        prio_pick = pd.concat([df1_first_five, df2_first_five, df3_first_five], axis=1)
        st.markdown(f'<h5>TOP 5 PRIO PICKS Advised to choose Split + Playoffs for this table </h5>', unsafe_allow_html = True)
        st.write(prio_pick)

    with col_tab3:
        st.markdown(f'<h5>Matrix Blue</h5>', unsafe_allow_html = True)
        st.write(matrix_percentages_blue)
    with col_tab5:
        st.markdown(f'<h5>Matrix Red</h5>', unsafe_allow_html = True)
        st.write(matrix_percentages_red)

elif page == "Reporting In Game":
    
    st.title('Reporting In Game')
  
elif page == "SoloQ Overview":
   
    st.title('Reporting SoloQ')
    df_spring24_geng_draft = get_spring24_geng_draft()
    df_players_stats = get_games_player_stats(list_game_end_geng_compet,list_players)  #from list of dict to all GenG players stats only
    df_events = get_df_event(list_game_timeline_geng_compet)
    df_events = map_id_to_names(df_events,df_players_stats)

    st.write(df_events)


    create_heatmap(df_events['x'].tolist(),df_events['y'].tolist(), debug = True)
    st.write('Good')

elif page == "Player Focus":
 
    col_tab1,col_tab2 = st.columns([3,8])
   
    with col_tab1:

        with st.expander("Choose Player", expanded = False):
            # Display options within the expander
            player = st.radio("Players", list_players)



    df_players_stats = get_games_player_stats(list_game_end_geng_compet,list_players) #from list of dict to all GenG players stats only
    df_players_stats_scope = df_players_stats[df_players_stats['Player'] == player] #focus on choosen player
    
    with col_tab2:

        # PLAYER WISE STATS
        df_player, df_player_vision = player_stats(df_players_stats_scope)
        st.markdown(f"<h2 style='text-align: center;'>{player} Statistics</h2><hr style='margin-bottom: 20px;'>", unsafe_allow_html=True)
        st.write('Global Statistics')
        st.write(df_player)
        
        st.write('Vision Statistics')
        st.write(df_player_vision)


    # CHAMPIONS WISE STATS
    st.title('Champion Focus')
    st.write('Champion Statistics')
    df_player_champion_stats = player_champion_stats(df_players_stats_scope)
    st.write(df_player_champion_stats)
    if player in ['GENLehends','GENCanyon']:
        st.write('Vision Statistics')
        df_player_vision_stats = player_champion_vision_stats(df_players_stats_scope)
        st.write(df_player_vision_stats)

    # HEAT MAPS 
