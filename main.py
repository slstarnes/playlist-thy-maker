import spotipy
import spotipy.util as util
import random
import yaml
import pandas as pd
import sys

class PlaylistMaker:
    def __init__(self):
        reload(sys)
        sys.setdefaultencoding('utf-8')
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
            print("Can't get token for", pm.username)

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
                'Artist Followers': o['followers']['total']}

    def track_extractor(self, o):
        return {'Track Name': o['name'],
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

        :param track_list:
        :param chunk_size:
        :return:
        """
        chunk_size = min(chunk_size, 100)
        chunks = [track_list[x:x + chunk_size] for x in xrange(0, len(track_list), chunk_size)]
        features = []
        for chunk in chunks:
            result = self.spotify.audio_features(list(chunk['Track ID']))
            result = [self.audio_feature_extractor(r) for r in result]
            features += result
        return pd.DataFrame(features)

    def artist_details(self, artist_list):
        """Gets artist IDs from a list of entries (tracks or artist). Returns list."""
        artist_ids = []
        for artist in artist_list:
            result = self.spotify.search(artist, type='artist', limit=1)
            artist_ids.append(self.artist_extractor(result['artists']['items'][0]))
        return artist_ids

    def find_related_artists(self, artist_list, num_artists=1, shuffle_artists=True):
        """For each artist in list, finds random related artist ids (num_artists). Returns list."""
        related_artist_ids = []
        for artist_id in artist_list:
            related = self.spotify.artist_related_artists(artist_id['Artist ID'])
            random_related_artists = [self.artist_extractor(r) for r in related['artists']]
            if shuffle_artists:
                random.shuffle(random_related_artists)
            random_related_artists = random_related_artists[:min(len(random_related_artists), num_artists)]
            related_artist_ids += random_related_artists
        return related_artist_ids

    def find_top_tracks(self, artist_list, num_tracks=5):
        """Find top n tracks of the artists in the argument"""
        track_ids = []
        for artist in artist_list:
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
        chunks = [track_list[x:x + chunk_size] for x in xrange(0, len(track_list), chunk_size)]
        for chunk in chunks:
            self.spotify.user_playlist_add_tracks(self.username, playlist, chunk)

    def add_audio_features(self, track_list):
        """
        :param track_list: dataframe of tracks
        :return: dataframe with features added
        """
        tracks_with_features = pm.audio_features(track_list)
        return pd.concat([pd.DataFrame(track_list),
                          pd.DataFrame(tracks_with_features)],
                         axis=1)

    def create_track_list_of_related_artists(self, artist_file,
                                             include_seed_artists=True,
                                             num_top_tracks_per_artist=5,
                                             num_related_artists=8):
        """
        :param artist_file: text file of artists
        :param include_seed_artists : whether output should include seed artists (default=True)
        :param num_top_tracks_per_artist: Number of tracks per artist (default=5)
        :param num_related_artists: Number of related artists per seed artist (default=8)
        :return: dataframe of tracks
        """
        artists = pm.get_artist_names_from(artist_file)
        artists = pm.artist_details(artists)
        related_artists = pm.find_related_artists(artists, num_related_artists)
        if include_seed_artists:
            artists += related_artists
        track_list = pm.find_top_tracks(artists, num_top_tracks_per_artist)
        track_list = pd.DataFrame(track_list)
        track_list.drop_duplicates(subset='Track ID', inplace=True)
        return track_list

    def create_playlist_of_tracks(self, track_list, playlist_name):
        track_ids = list(track_list['Track ID'])
        self.create_playlist(playlist_name)
        self.user_playlist_add_tracks(self.find_playlist(playlist_name), track_ids)


if __name__ == "__main__":
    pm = PlaylistMaker()

    if True:
        tracks = pm.create_track_list_of_related_artists('artists.txt')
        pm.create_playlist_of_tracks(tracks, 'Rainy Sunday')
        tracks = pm.add_audio_features(tracks)
        tracks.to_csv('tracks.csv')

    if False:
        pid = pm.find_playlist('Special Earth Songs from Tennessee')
        print (pm.spotify.user_playlist_tracks(pm.username,playlist_id=pid,fields='items(track(name,id,artists(name)))'))
        ## Next: give me a playlist name and I give you back a dataframe with tracks with audio features

        ##idea
        # get all tracks by artist... get artist albums, get each albums tracks
        # filter down by some audio feature. thinking...tom waits and acoustic.

