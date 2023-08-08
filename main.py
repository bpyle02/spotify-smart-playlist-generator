"""

This program was written by Brandon Pyle

"""

from dotenv import load_dotenv
import os
import base64
from requests import post, get
import json
from requests_oauthlib import OAuth2Session
from requests.auth import HTTPBasicAuth

load_dotenv()

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')

# Step 1: authenticate and get token

def get_token():
    auth_string = client_id + ':' + client_secret
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = str(base64.b64encode(auth_bytes), 'utf-8')

    url = 'https://accounts.spotify.com/api/token'
    headers = {
        'Authorization': 'Basic ' + auth_base64,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}
    result = post(url, headers=headers, data=data)
    
    json_result = json.loads(result.content)
    token = json_result['access_token']
    return token

def get_auth_header():
    return {'Authorization': 'Bearer ' + get_token()}

def authorize_user():
    token_url = 'https://accounts.spotify.com/api/token'
    authorization_base_url = 'https://accounts.spotify.com/authorize'
    scope = ['playlist-modify-public', 'playlist-modify-private']
    redirect_uri = 'https://brandonpyle.com'

    spotify = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)

    authorization_url, state = spotify.authorization_url(authorization_base_url)

    print(f'Please navigate to this url to authorize access to spotify: {authorization_url}')

    redirect_response = input('Paste the full redirect url here: ')

    auth = HTTPBasicAuth(client_id, client_secret)

    token = spotify.fetch_token(token_url, auth=auth, authorization_response=redirect_response)

    print(token)

    return token

# Step 2: search for playlists

def search_for_playlists(search_terms, num_playlists):
    data = []

    url = 'https://api.spotify.com/v1/search'
    headers = get_auth_header()
    
    query = f'?q={search_terms}&type=playlist&limit={num_playlists}'
    query_url = url + query

    result = get(query_url, headers=headers)
    json_result = json.loads(result.content)['playlists']['items']

    if len(json_result) == 0:
        print('No playlists with this name exists')
        return None
    
    if len(json_result) < int(num_playlists):
        print(f"Only {len(json_result)} playlists found. proceeding...")
        for i in range(len(json_result)):
            if json_result[i]['owner']['id'] != 'spotify':
                print(f"Indexing songs from the playlist '{json_result[i]['name']}'")
                data.append(json_result[i]['id'])
            else:
                print("Playlist by spotify...")
    else:
        for i in range(int(num_playlists)):
            if json_result[i]['owner']['id'] != 'spotify':
                print(f"Indexing songs from the playlist '{json_result[i]['name']}'")
                data.append(json_result[i]['id'])
            else:
                print("Playlist by spotify...")

    print(len(data))

    return data

def get_playlist_songs(playlist_ids, num_playlists, allowExplicit):
    playlists = []
    song_ids = {}
    song_ids_final = {}

    for i in range(len(playlist_ids)):
        url = f'https://api.spotify.com/v1/playlists/{playlist_ids[i]}'
        headers = get_auth_header()
        result = get(url, headers=headers)
        num_tracks = len(json.loads(result.content)['tracks']['items'])
        num_invalid_songs = 0
        #print(f'Number of tracks in playlist {playlist_ids[i]}: {num_tracks}')

        if allowExplicit:
            for j in range(len(playlist_ids)):
                try:
                    id = json.loads(result.content)['tracks']['items'][j]['track']['id']
                    popularity = json.loads(result.content)['tracks']['items'][j]['track']['popularity']
                    isExplicit = json.loads(result.content)['tracks']['items'][j]['track']['explicit']

                    rank = 0
                    num_occurrences = 1

                    song_ids.update({id:[popularity, num_occurrences, isExplicit, rank]})

                    if id not in song_ids_final.keys():
                        song_ids_final.update({id:[popularity, num_occurrences, isExplicit, rank]})
                    else:
                        song_ids_final[id][1] += 1
                except:
                    num_invalid_songs += 1
        else:
            for j in range(len(playlist_ids)):
                try:
                    id = json.loads(result.content)['tracks']['items'][j]['track']['id']
                    popularity = json.loads(result.content)['tracks']['items'][j]['track']['popularity']
                    isExplicit = json.loads(result.content)['tracks']['items'][j]['track']['explicit']

                    if isExplicit:
                        break

                    rank = 0
                    num_occurrences = 1

                    song_ids.update({id:[popularity, num_occurrences, isExplicit, rank]})

                    if id not in song_ids_final.keys():
                        song_ids_final.update({id:[popularity, num_occurrences, isExplicit, rank]})
                    else:
                        song_ids_final[id][1] += 1
                except:
                    num_invalid_songs += 1

        if num_invalid_songs > 0:
            print(f'{num_invalid_songs} invalid songs found...')

    return song_ids_final

# Step 3: rank songs and sort dictionary by rank

def rank_songs(songs):
    for id in songs:
        songs[id][3] = (songs[id][1] * 2) + (songs[id][0] / 10)
    
    songs_sorted = dict(sorted(songs.items(), key=lambda item: item[1][3], reverse=True))

    return songs_sorted

# Step 4: create the playlist

def create_playlist(auth, user_id, name, visibility):
    url = 'https://api.spotify.com/v1/users/{}/playlists'.format(user_id)

    playlist_info = json.dumps({
        'name': name,
        "description": "This playlist was automatically generated using a Python program I wrote",
        'public': visibility
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(auth['access_token'])
    }

    response = post(url, data=playlist_info, headers=headers)
    json_result = response.json()

    print(response)

    return json_result

# Step 5: Add ranked songs to the playlist

def add_songs_to_playlist(auth, id, songs):
    song_list = []
    total_songs = 100

    for song in songs.keys():
        if total_songs > 0 and song is not None:
            song_list.append("spotify:track:" + song)
            total_songs -= 1
        else:
            break  

    url = 'https://api.spotify.com/v1/playlists/{}/tracks'.format(id)

    data = json.dumps({
        'uris': song_list,
        'position': 0
    })

    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(auth['access_token'])
    }

    response = post(url, data=data, headers=headers)
    json_result = response.json()

    print(response)
    

user_id = '1xobld5add2v49tsg512lh220'

search_terms = list(map(str,input('Please enter the playlist search terms separated by spaces: ').split()))
search_str = ''
for search_term in search_terms:
    search_str += search_term + "+"
search_str = search_str[:-1]

num_playlists = input('Please enter the total number of playlists to search through (0-50): ')

name_list = list(map(str,input('Please enter the name of the playlist you would like to create: ').split()))
name_str = ''
for name in name_list:
    name_str += name + " "

visibility = input('Would you like this playlist to be public (y/n): ')
isVisible = True

if visibility.upper() == 'N':
    isVisible = False
elif visibility.upper() == 'Y':
    isVisible = True
else:
    print('Error. Playlist will be created as a public playlist')

explicit = input('Would you like to allow explicit songs in this playlist (y/n): ')
allowExplicit = True

if explicit.upper() == 'N':
    allowExplicit = False
elif explicit.upper() == 'Y':
    allowExplicit = True
else:
    print('Error. Playlist will be created as a public playlist')

auth = authorize_user()

print('Searching for playlists matching your conditions...')
playlist_ids = search_for_playlists(search_str, num_playlists)

print('Getting songs from discovered playlists...')
playlist_song_ids = get_playlist_songs(playlist_ids, num_playlists, allowExplicit)

print('Ranking songs...')
songs = rank_songs(playlist_song_ids)

print('Creating your playlist...')
playlist = create_playlist(auth, user_id, name_str, isVisible)
created_playlist_id = playlist['id']

add_songs_to_playlist(auth, created_playlist_id, songs)