import spotipy
import spotipy.util as util
import random
import yaml
import pandas as pd
from toolz import dicttoolz


class PlaylistMaker:
    def __init__(self):
        with open('credentials.yaml') as f:
            credentials = yaml.load(f)
        self.username = credentials['spotify_username']
        self.client_id = credentials['spotify_client_id']
        self.client_secret = credentials['spotify_client_secret']
        self.scope = 'user-library-modify'
        self.REDIRECT_URI = 'http://localhost:8888/callback'
        self.token = util.prompt_for_user_token(self.username,
                                                self.scope,
                                                self.client_id,
                                                self.client_secret,
                                                self.REDIRECT_URI)
        if self.token:
            # Initialize Spotify object
            self.spotify = spotipy.Spotify(auth=self.token)
        else:
            print("Can't get token for", self.username)

    def create_playlist(self, name):
        """Creates playlist with the name given as the argument."""
        if self.find_playlist(name) is None:
            self.spotify.user_playlist_create(self.username, name, public=False)

    def get_artist_names_from(self, txt):
        """Gets track names from txt file"""
        artist_names = []
        with open(txt, 'r') as f:
            for entry in f.readlines():
                entry = entry.strip()
                artist_names.append(entry)
        return artist_names

    def artist_name_from_id(self, id):
        result = self.spotify.artists([id])
        return result['artists'][0]['name']

    def expand_dicts_in_list(self, l_of_d, dict_to_add):
        out = []
        for d in l_of_d:
            c = d.copy()
            c.update(dict_to_add)
            out.append(c)
        return out

    def artist_extractor(self, o):
        return {'Artist Name': o['name'],
                'Artist ID': o['id'],
                'Artist Popularity': o['popularity'],
                'Artist Followers': o['followers']['total'],
                'Artist Genres': o['genres'],
                'Artist Image': o['images'][0]['url']}

    def track_extractor(self, o):
        return {'Track Name': o['name'],
                'Track ID': o['id'],
                'Track Popularity': o['popularity']}

    def track_extractor_plus(self, o):
        return {'Artist': o['artists'][0]['name'],
                'Track Name': o['name'],
                'Track ID': o['id'],
                'Track Popularity': o['popularity']}

    def audio_feature_extractor(self, o):
        return {'Energy': o['energy'],
                'Liveness': o['liveness'],
                'Speechiness': o['speechiness'],
                'Acousticness': o['acousticness'],
                'Instrumentalness': o['instrumentalness'],
                'Time Signature': o['time_signature'],
                'Danceability': o['danceability'],
                'Key': o['key'],
                'Major/Minor': o['mode'],
                'Duration': float(o['duration_ms']) / (1000 * 60),
                'Loudness': o['loudness'],
                'Valence': o['valence']}

    def track_from_pl_extractor(self, o):
        return {'Track Name': o['name'],
                'Track ID': o['id'],
                'Artist': o['artists']['name']}

    def track_details(self, track_id):
        urn = f"spotify:track:{track_id}"
        track_json = self.spotify.track(urn)
        track_details = self.track_extractor_plus(track_json)
        return track_details#pd.DataFrame(track_details)

    def audio_features(self, track_list, chunk_size=50):
        """

        Notes:
        acousticness - 0 to 1, 1.0 represents high confidence the track is acoustic.
        danceability - how suitable a track is for dancing based on a combination of musical elements including tempo,
                        rhythm stability, beat strength, and overall regularity.
                        A value of 0.0 is least danceable and 1.0 is most danceable.
        energy - measure from 0.0 to 1.0 and represents a perceptual measure of intensity and activity.
                Typically, energetic tracks feel fast, loud, and noisy. For example, death metal has high energy,
                while a Bach prelude scores low on the scale. Perceptual features contributing to this attribute include
                dynamic range, perceived loudness, timbre, onset rate, and general entropy.

        instrumentalness - Predicts whether a track contains no vocals.
                            "Ooh" and "aah" sounds are treated as instrumental in this context.
                            Rap or spoken word tracks are clearly "vocal".
                            The closer the instrumentalness value is to 1.0, the greater likelihood the track contains
                            no vocal content. Values above 0.5 are intended to represent instrumental tracks, but
                            confidence is higher as the value approaches 1.0.
        key	 - The key the track is in. Integers map to pitches using standard Pitch Class notation.
                E.g. 0 = C, 1 = C#/Db, 2 = D, and so on.
        liveness - Detects the presence of an audience in the recording. Higher liveness values represent an increased
                    probability that the track was performed live. A value above 0.8 provides strong likelihood that the
                    track is live.
        loudness - The overall loudness of a track in decibels (dB). Loudness values are averaged across the entire track
                    and are useful for comparing relative loudness of tracks. Loudness is the quality of a sound that
                    is the primary psychological correlate of physical strength (amplitude). Values typical range
                    between -60 and 0 db.
        mode - Mode indicates the modality (major or minor) of a track, the type of scale from which its melodic content
                is derived. Major is represented by 1 and minor is 0.
        speechiness	- detects the presence of spoken words in a track. The more exclusively speech-like the recording
                        (e.g. talk show, audio book, poetry), the closer to 1.0 the attribute value. Values above 0.66
                        describe tracks that are probably made entirely of spoken words. Values between 0.33 and 0.66
                        describe tracks that may contain both music and speech, either in sections or layered, including
                        such cases as rap music. Values below 0.33 most likely represent music and other non-speech-like
                        tracks.
        tempo - the overall estimated tempo of a track in beats per minute (BPM). In musical terminology, tempo
                is the speed or pace of a given piece and derives directly from the average beat duration.
        time_signature	- An estimated overall time signature of a track. The time signature (meter) is a notational
                            convention to specify how many beats are in each bar (or measure).
        valence - a measure from 0.0 to 1.0 describing the musical positiveness conveyed by a track.
                    Tracks with high valence sound more positive (e.g. happy, cheerful, euphoric), while tracks with low
                    valence sound more negative (e.g. sad, depressed, angry).

        :param track_list: dataframe of tracks
        :param chunk_size: number of tracks to add per request (max=100)
        :return:
        """
        chunk_size = min(chunk_size, 100)
        chunks = [track_list[x:x + chunk_size] for x in range(0, len(track_list), chunk_size)]
        features = []
        for chunk in chunks:
            result = self.spotify.audio_features(list(chunk['Track ID']))
            result = [self.audio_feature_extractor(r) for r in result]
            features += result
        return pd.DataFrame(features)

    def artist_details(self, artist_list):
        """Gets artist IDs from a list of entries (tracks or artist). Returns list."""
        if isinstance(artist_list, str):
            artist_list = [artist_list]
        assert isinstance(artist_list, list)
        artist_ids = []
        for artist in artist_list:
            result = self.spotify.search(artist, type='artist', limit=1)
            if result['artists']['items']:
                artist_ids.append(self.artist_extractor(result['artists']['items'][0]))
            else:
                print(f'{artist} is not a valid artist')
        artist_df = pd.DataFrame(artist_ids)
        return artist_df

    def find_related_artists(self, artist_list, num_artists=1, shuffle_artists=True):
        """For each artist in list, finds random related artist ids (num_artists). Returns list."""
        related_artist_ids = []
        for artist_id in artist_list['Artist ID']:
            related = self.spotify.artist_related_artists(artist_id)#['Artist ID'])
            random_related_artists = [self.artist_extractor(r) for r in related['artists']]
            if shuffle_artists:
                random.shuffle(random_related_artists)
            random_related_artists = random_related_artists[:min(len(random_related_artists), num_artists)]
            related_artist_ids += random_related_artists
        related_artist_ids_df = pd.DataFrame(related_artist_ids)
        #related_artist_ids_df = related_artist_ids_df.set_index('Artist Name', drop=True)
        return related_artist_ids_df

    def find_top_tracks(self, artist_list, num_tracks=5):
        """Find top n tracks of the artists in the argument"""
        track_ids = []
        for row, artist in artist_list.iterrows():
            track_list = self.spotify.artist_top_tracks(artist['Artist ID'])
            track_list = [self.track_extractor(t) for t in track_list['tracks']]
            track_list = self.expand_dicts_in_list(track_list, artist)
            top_n = track_list[:min(len(track_list), num_tracks)]
            track_ids += top_n
        return track_ids

    def find_playlist(self, playlist_name):
        """
        Given the name of a playlist, return the playlist's ID. If playlist name appears more than once, the fist
        occurrence is returned.
        :param playlist_name: string
        :return: playlist_id
        """

        users_playlists = self.spotify.user_playlists(self.username)
        playlist_id = None
        for playlist in users_playlists['items']:
            if playlist['name'] == playlist_name:
                playlist_id = playlist['id']
                break
        return playlist_id

    def user_playlist_add_tracks(self, playlist, track_list, chunk_size=50):
        """
        :param playlist: Playlist ID
        :param track_list: list of Track IDs
        :param chunk_size: number of tracks to add per request (max=100)
        :return: None
        """
        chunk_size = min(chunk_size, 100)
        chunks = [track_list[x:x + chunk_size] for x in range(0, len(track_list), chunk_size)]
        for chunk in chunks:
            self.spotify.user_playlist_add_tracks(self.username, playlist, chunk)

    def add_audio_features(self, track_list):
        """
        :param track_list: dataframe of tracks
        :return: dataframe with features added
        """
        tracks_with_features = self.audio_features(track_list)
        return pd.concat([pd.DataFrame(track_list),
                          pd.DataFrame(tracks_with_features)],
                         axis=1)

    def create_track_list_of_related_artists(self, artists_,
                                             include_seed_artists=True,
                                             num_top_tracks_per_artist=5,
                                             num_related_artists=8):
        """
        Given a list of artists, return a list of top tracks for related artists (and optionally the original artists)

        :param artists_: list of artists or text file of artists
        :type artist_file: list or string
        :param include_seed_artists: whether output should include seed artists (default=True)
        :type include_seed_artists: bool
        :param num_top_tracks_per_artist: Number of tracks per artist (default=5)
        :type num_top_tracks_per_artist: int
        :param num_related_artists: Number of related artists per seed artist (default=8)
        :type num_related_artists: int
        :return: dataframe of tracks
        """
        if isinstance(artists_, str):
            artists_ = self.get_artist_names_from(artists_)
        artists = self.artist_details(artists_)
        related_artists = self.find_related_artists(artists, num_related_artists)
        if include_seed_artists:
            related_artists.append(artists)
        track_list = self.find_top_tracks(related_artists, num_top_tracks_per_artist)
        track_df = pd.DataFrame(track_list)
        track_df.drop_duplicates(subset='Track ID', inplace=True)
        return track_df

    def create_playlist_of_tracks(self, track_iterable, playlist_name):
        """
        Create playlist given a DataFrame of tracks.

        :param track_df: tracks for playlist
        :type track_df: pd.DataFrame
        :param playlist_name: Name of playlist
        :type playlist_name: str
        :return: None
        """
        if isinstance(track_iterable, pd.DataFrame):
            track_ids = list(track_iterable['Track ID'])
        elif isinstance(track_iterable, list):
            track_ids = track_iterable
        # TODO: add handling for other cases. also, fix comment
        self.create_playlist(playlist_name)
        self.user_playlist_add_tracks(self.find_playlist(playlist_name), track_ids)

    def track_details_from_playlist(self, playlist_name):
        pid = self.find_playlist(playlist_name)
        tracks_json = self.spotify.user_playlist_tracks(self.username,
                                                      playlist_id=pid)
        track_list = [self.track_extractor_plus(t['track']) for t in tracks_json['items']]
        track_df = pd.DataFrame(track_list)
        return track_df

    def get_artist_tracks(self, artist_name):
        result = self.spotify.search(artist_name, limit=1, type='artist')
        artist_id = result['artists']['items'][0]['id']
        result = self.spotify.artist_albums(artist_id, album_type='album')
        artist_albums = []
        for items in result['items']:
            artist_albums.append({'Album Name': items['name'],
                                 'Album ID': items['id'],
                                 'Release Date': items['release_date']})
        track_list = []
        for album in artist_albums:
            result = self.spotify.album_tracks(album['Album ID'])
            track_ids = [t['id'] for t in result['items']]

            album_tracks = [self.track_details(id_) for id_ in track_ids]
            album_tracks = [dicttoolz.merge((album, trk)) for trk in album_tracks]

            track_list += album_tracks

        track_df = pd.DataFrame(track_list)
        return track_df

    def playlist_from_file_of_tracks(self, input_file, playlist_name):
        with open(input_file) as f:
            ids = []
            for id_ in f:
                # id_ = id_.encode("utf-8")
                id_ = id_.replace('\n', '')
                ids.append(id_)
        self.create_playlist_of_tracks(ids, playlist_name)

    def get_recommendations(self, artists_list):
        pass
        #https://developer.spotify.com/documentation/web-api/reference/browse/get-recommendations/
        # self.artist_details(artists_list)

if __name__ == "__main__":
    pm = PlaylistMaker()
    assert isinstance(pm.get_artist_names_from('artists.txt'), list)
    assert pm.artist_name_from_id('43O3c6wewpzPKwVaGEEtBM') == 'My Morning Jacket'
    l = [{'rex':'p','ew':'mnk','cfr':'wsf'},
         {'rex':'p2','ew':'mnk2','cfr':'wsf2'}]
    d = {'stp':'added'}
    l_d = [{'rex':'p','ew':'mnk','cfr':'wsf', 'stp':'added'},
         {'rex':'p2','ew':'mnk2','cfr':'wsf2', 'stp':'added'}]
    assert pm.expand_dicts_in_list(l, d) == l_d
    related = pm.spotify.artist_related_artists('43O3c6wewpzPKwVaGEEtBM')
    assert isinstance(related['artists'], list)
    assert isinstance(related['artists'][0], dict)
    assert isinstance(pm.artist_extractor(related['artists'][0]), dict)
    track_list = pm.spotify.artist_top_tracks('43O3c6wewpzPKwVaGEEtBM')
    assert isinstance(pm.track_extractor(track_list['tracks'][0]), dict)
    assert isinstance(pm.track_extractor_plus(track_list['tracks'][0]), dict)
    assert isinstance(pm.track_details('7hxZF4jETnE5Q75rKQnMjE'), dict)


    if False:
        tracks = pm.create_track_list_of_related_artists('artists.txt')
        pm.create_playlist_of_tracks(tracks, 'Rainy Sunday')
        tracks.to_csv('tracks.csv')

    if False:
        tracks = pm.track_details_from_playlist('Special Earth Songs from Tennessee')
        tracks = pm.add_audio_features(tracks)
        tracks.to_csv('Special Earth Songs from Tennessee.csv')

    if False:
        tracks = pm.get_artist_tracks('Tom Waits')
        tracks = pm.add_audio_features(tracks)
        tracks.to_csv('Tom Waits.csv')

    if False:
        pm.playlist_from_file_of_tracks('tracks.txt', 'chill n waits')


# TODO -- add clustering to find how songs cluster -- http://scikit-learn.org/stable/modules/clustering.html
