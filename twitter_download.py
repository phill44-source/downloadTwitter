import os, sys
import re
import tweepy
import wget
import pandas as pd
import numpy as np

from config import *
# API's setup
def twitter_setup():
    CONSUMER_KEY    = CREDENTIALS['CONSUMER_KEY']
    CONSUMER_SECRET = CREDENTIALS['CONSUMER_SECRET']

    ACCESS_TOKEN  = CREDENTIALS['ACCESS_TOKEN']
    ACCESS_SECRET = CREDENTIALS['ACCESS_SECRET']

    # Authentication and access using keys
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)

    # Return API with authentication
    api = tweepy.API(auth)
    print("twitter_setup started")
    return api

def fetch_friends():
    api = twitter_setup()
    friends = []
    for foll_user in FOLLOWER_USER:
        for user in tweepy.Cursor(api.get_friends, screen_name=foll_user).items():
            friends.append(user.screen_name)
    return friends        

def get_all_tweets(screen_name, count, extend):
    '''
    Get all (maximum of 3240) tweets from an user
    '''
    #Twitter only allows access to a users most recent 3240 tweets with this method
    api = twitter_setup()

    #initialize a list to hold all the tweepy Tweets
    alltweets = []

    #make initial request for most recent tweets (200 is the maximum allowed count)
    new_tweets = api.user_timeline(screen_name = screen_name, count=count,
                                    tweet_mode='extended', include_rts=False, exclude_replies=True)
    #save most recent tweets
    alltweets.extend(new_tweets)
    print("alltweets.extended")
    #save the id of the oldest tweet less one
    oldest = alltweets[-1].id - 1
    if extend==True:
        #keep grabbing tweets until there are no tweets left to grab
        while len(new_tweets) > 0:
            print("getting tweets before %s" % (oldest))
            
            #all subsiquent requests use the max_id param to prevent duplicates
            new_tweets = api.user_timeline(screen_name = screen_name,count=count,
                                            tweet_mode='extended', include_rts=False,
                                            exclude_replies=True, max_id=oldest)
            
            #save most recent tweets
            alltweets.extend(new_tweets)

            #update the id of the oldest tweet minus one
            oldest = alltweets[-1].id - 1

            print(f"...{len(alltweets)} /3240 of {screen_name}'s tweets fetched so far")

    else:
        print(f"...{len(alltweets)} /3240 of {screen_name}'s tweets fetched!")

    return alltweets

def get_media(tweets, type):
    '''
    Get all urls of user's photos/videos
    '''
    
    photos = set()
    videos = set()
    for status in tweets:
        # check if tweet as extended entitites (with media files)
        if hasattr(status, 'extended_entities'):
            media = status.extended_entities.get('media', [])
            for i in range(len(media)):
                # check if the media is photo, get photo url
                if media[i]['type'] == 'photo':
                    photos.add(media[i]['media_url'])
                # if media file is video, get .mp4 url
                elif media[i]['type'] == 'video':
                    # get the link with the highest bitrate (highest quality)
                    bitrates=[]
                    variants = media[i]['video_info'].get('variants', [])
                    for var in variants:
                        if var['content_type'] == 'video/mp4':
                            bitrates.append(var['bitrate'])
                    # use url[:-6] to remove tag in file extension
                    videos.add(variants[np.argmax(bitrates)]['url'][:-6])
        else:
            continue

    if type == 'photo':
        return photos
    elif type == 'video':
        return videos

def create_folder(output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

def download_images(photo_urls, output_folder):
    create_folder(output_folder)

    for url in photo_urls:
        # Only download if picture hasn't been in the folder yet
        file_name = os.path.split(url)[1]
        if not os.path.exists(os.path.join(output_folder, file_name)):
            wget.download(url, out = output_folder+'/'+file_name)

def download_videos(username, video_urls, output_folder, download=False):
    if download == False:
        data = pd.DataFrame(data = [url for url in video_urls], columns=['Video Links'])
        # write to csv file
        data.to_csv(username+'_video_urls.csv', index=False)
        print("Writing complete!")
    else:
        create_folder(output_folder)
        for url in video_urls:
            # Only download if video hasn't been in the folder yet
            file_name = os.path.split(url)[1]
            if not os.path.exists(os.path.join(output_folder, file_name)):
                wget.download(url, out = output_folder+'/'+file_name)
        print("Video download complete!")

def main():
    url_type = FILE_TYPE
    friends_in_users = fetch_friends()
    for UsEr in USERS:
        friends_in_users.append(UsEr)

    for name in friends_in_users:
        outdir = name+'_download'
        print("Fetching tweets for user %s......." % name)

        print()
        # set extend to False if you don't want to fetch tweets continuously
        tweets = get_all_tweets(name, N_TWEETS, extend=EXTEND_STATE)

        urls = get_media(tweets, type=url_type)
            
            
            
        if url_type == 'photo':
            download_images(urls, outdir)
            print("Photo download complete!")
        elif url_type == 'video':
            download_videos(name, urls, outdir, download=VIDEO_DL)

if __name__=='__main__':
    main()

