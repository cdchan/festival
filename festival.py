# Festival

import math
import StringIO
import time
import urllib
import urllib2

from lxml import etree
from operator import itemgetter

# Retrieve festival's lineup, need eventid
def festival(eventid=3182649):
    # Sasquatch event id: 3182649
    url = 'http://ws.audioscrobbler.com/2.0/?method=event.getinfo&event=' + eventid + '&api_key=b25b959554ed76058ac220b7b2e0a026'
    
    response = urllib2.urlopen(url).read()
    
    tree = etree.parse(StringIO.StringIO(response))
    
    artists = []
    # Extract artists from XML
    for t in tree.xpath('//artist'):
        artists.append(t.text)
    
    # Check if artist is cached, if not, download XML
    for a in artists:
        check(a)
        
    return artists

# Download an artist's similar artists
def download(artist):
    artist = artist.replace(' ', '+')  # URLs have '+' instead of spaces in artist name
    
    # URL for similar artists XML
    url = u'http://ws.audioscrobbler.com/2.0/?method=artist.getsimilar&artist=' + artist + '&api_key=b25b959554ed76058ac220b7b2e0a026'
    
    url = url.encode('utf8')  # Need to encode URL in UTF8 as per last.fm
    
    urllib.urlretrieve(url, 'cache/' + artist + '_similar.xml')  # caches XML
    
    print 'Downloading ' + artist
    
    # Wait 5 seconds between downloads
    for i in range(5):
        time.sleep(1.0)
        print '.'

# Check if an artist's similar artists XML has been cached or not
def check(artist):
    artist = artist.replace(' ', '+')  # URLs have '+' instead of spaces in artist name
    type = 'similar'
    
    try:
        file = open('cache/' + artist + '_' + type + '.xml')
    except IOError:
        download(artist)
    else:
        file.close()

# Download a last.fm profile's top artists
# Option argument for chart period
def profile(username, period='overall'):
    url = 'http://ws.audioscrobbler.com/2.0/?method=user.gettopartists&user=' + username + '&period=' + period + '&limit=300&api_key=b25b959554ed76058ac220b7b2e0a026'
    
    response = urllib2.urlopen(url).read()
    
    tree = etree.parse(StringIO.StringIO(response))
    
    my_artists = []
    
    # Artist element has name and total playcount tags
    for t in tree.xpath('//artist'):
        my_artist = {}
        my_artist['name'] = t.xpath('name')[0].text
        my_artist['plays'] = int(t.xpath('playcount')[0].text)
        
        my_artists.append(my_artist)
    
    return my_artists

#####

# Create custom playlist for a given lineup and profile
def create_playlist(lineup, my_artists):
    scores = []
    
    # For every artist in the lineup, check if any of their similar artists match the artists in the given profile
    # If there is a match, use the matching percentage and playcount to add to the score
    for artist in lineup:
        # print artist
        file_artist = artist.replace(' ', '+')  # URLs have '+' instead of spaces in artist name
        
        # Load the artist's similar artist XML
        file = open('cache/' + file_artist + "_" + 'similar' + '.xml')
        tree = etree.parse(StringIO.StringIO(file.read()))
        file.close()
        
        # Give the artist a match number for themselves
        # The max_match number controls how similar artists must be have substantial influence
        max_match = 2.5
        self_match = max_match - 0.01
        
        # Extract all similar artists and their match percentage
        similar_artists = [{'name': artist, 'match': self_match}]
        for t in tree.xpath('//artist'):
            similar_artist = {}
            similar_artist['name'] = t.xpath('name')[0].text
            similar_artist['match'] = float(t.xpath('match')[0].text)
            
            similar_artists.append(similar_artist)
        
        # Loop through all artists in the profile
        # If a similar artist exists in the profile, record the match number
        # Currently this uses an exponential distance metric to force give more weight to bands that are very similar to bands in the profile
        # This prevents the problem of a band not being very much like any other bands, but sitting between them all and being given lots of weight for being slightly similar to many bands
        # Should vectorize this
        weights = []
        for ma in my_artists:
            try:
                i = [a['name'] for a in similar_artists].index(ma['name'])
            except ValueError:
                weights.append(0)
            else:
                w = [a['match'] for a in similar_artists][i]
                # Match number is subject to the exponential distance metric
                weights.append(math.exp(-1 * (max_match - w)))
        
        # Total score calculated by multiplying weight by playcount
        scores.append(sum([a * b for (a, b) in zip(weights, [a['plays'] for a in my_artists])]))
    
    # Associate scores with lineup artists
    playlist = zip(lineup, scores)
    
    # Sort by score and return
    playlist = sorted(playlist, key=lambda playlist: playlist[1], reverse=True)
    
    return playlist