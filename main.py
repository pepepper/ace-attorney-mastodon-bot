#! /usr/bin/python
import random
import threading
import queue
import os
import time
import re
import json
from mastodon import Mastodon, CallbackStreamListener, MastodonAPIError, MastodonRatelimitError
import sys
sys.path.insert(0, './ace-attorney-reddit-bot')
import anim
from collections import Counter
from datetime import datetime
from comment_list_brige import Comment
from xml.sax.saxutils import unescape

mention_queue = queue.Queue()


def init_twitter_api():
    global api
    if (os.path.isfile('clientcred.secret') == False):
        Mastodon.create_app(
            'ace-attorney',
            api_base_url=keys['domain'],
            to_file='clientcred.secret'
        )
    if (os.path.isfile('usercred.secret') == False):
        m = Mastodon(
            client_id='clientcred.secret',
            api_base_url=keys['domain']
        )
        m.log_in(
            keys['mail'],
            keys['password'],
            to_file='usercred.secret'
        )

    api = Mastodon(
        access_token='usercred.secret',
        api_base_url=keys['domain']
    )


def sanitize_tweet(tweet):
    tweet['content'] = re.sub(r'(https)\S*', '(link)', tweet.content)
    tweet['content'] = re.sub(r'<[^>]*?>', '', tweet.content)
    tweet['content'] = re.sub(r'^(@\S+ )+', '', tweet.content)
    tweet['content'] = unescape(tweet.content, {"&quot;": '"', "&apos;": "'"})


def on_notification(notification):
    global mention_queue
    if notification['type'] == 'mention':
        status = api.status(notification['status'])
        if 'render' in status.content:
            mention_queue.put(status)


def check_mentions():
    global mention_queue
    api.stream_user(CallbackStreamListener(notification_handler=on_notification), run_async=True, timeout=300,
                    reconnect_async=True, reconnect_async_wait_sec=5)


def process_tweets():
    global mention_queue
    global lastTime
    while True:
        try:
            tweet = mention_queue.get()
            thread = []
            users_to_names = {}  # This will serve to link @display_names with usernames
            counter = Counter()
            current_tweet = tweet
            songs = ['PWR', 'JFA', 'TAT', 'rnd']

            if 'music=' in tweet.content:
                music_tweet = tweet.content.split('music=', 1)[1][:3]
            else:
                music_tweet = 'PWR'

            if music_tweet == 'rnd':
                music_tweet = random.choices(songs, [1, 1, 1, 0], k=1)[0]

            if music_tweet not in songs:  # If the music is written badly in the mention tweet, the bot will remind how to write it properly
                try:
                    api.status_post('@' + tweet.account.username +
                                    ' The music argument format is incorrect. The posibilities are: \nPWR: Phoenix Wright Ace Attorney \nJFA: Justice for All \nTAT: Trials and Tribulations \nrnd: Random', in_reply_to_id=tweet)
                except Exception as musicerror:
                    print(musicerror)
            else:
                while (current_tweet is not None) and current_tweet.in_reply_to_id:
                    try:
                        context_data = api.status_context(current_tweet.id)
                        current_tweet = api.status(
                            context_data['ancestors'][len(context_data['ancestors'])-1])
                        sanitize_tweet(current_tweet)
                        users_to_names[current_tweet.account.username] = current_tweet.account.display_name
                        counter.update({current_tweet.account.username: 1})
                        thread.insert(0, Comment(current_tweet))
                    except MastodonAPIError as e:
                        try:
                            api.status_post(
                                '@' + tweet.account.username + ' I\'m sorry. I wasn\'t able to retrieve the full thread. Deleted tweets or private accounts may exist', in_reply_to_id=tweet)
                        except Exception as second_error:
                            print('Exception:'+second_error)
                        current_tweet = None
                if (len(users_to_names) >= 2):
                    most_common = [users_to_names[t[0]]
                                   for t in counter.most_common()]
                    characters = anim.get_characters(most_common)
                    output_filename = str(tweet.id) + '.mp4'
                    anim.comments_to_scene(
                        thread, characters, name_music=music_tweet, output_filename=output_filename)
                    # Give some time to the other thread
                    time.sleep(1)
                    try:
                        uploaded_media = api.media_post(
                            output_filename, mime_type='video/mp4')
                        api.status_post('@' + tweet.account.username + ' ',
                                        in_reply_to_id=tweet, media_ids=[uploaded_media])
                    except MastodonRatelimitError as e:
                        print("I'm Rated-limited :(")
                        mention_queue.put(tweet)
                    except MastodonAPIError as e:
                        try:
                            print(e)
                        except Exception as parsexc:
                            print('Exception:'+parsexc)
                        try:
                            api.status_post(
                                '@' + tweet.account.username + ' ' + str(e), in_reply_to_id=tweet)
                        except Exception as second_error:
                            print('Exception:'+second_error)
                        print(e)
                    os.remove(output_filename)
                else:
                    try:
                        api.status_post(
                            '@' + tweet.account.username + " There should be at least two people in the conversation", in_reply_to_id=tweet)
                    except Exception as e:
                        print('Exception:'+e)
            time.sleep(1)
        except Exception as e:
            print(e)

# Main


# Load keys
with open('keys.json', 'r') as keyfile:
    keys = json.load(keyfile)

# Init
init_twitter_api()
check_mentions()
consumer = threading.Thread(target=process_tweets)
consumer.start()
