#!/usr/bin/python3
"""podfox - podcatcher for the terminal


Usage:
    podfox.py import <feed-url> [<shortname>] [-c=<path>]
    podfox.py update [<shortname>] [-c=<path>]
    podfox.py feeds [-c=<path>]
    podfox.py episodes <shortname> [-c=<path>]
    podfox.py download [<shortname> --how-many=<n>] [-c=<path>]
    podfox.py rename <shortname> <newname> [-c=<path>]
    podfox.py prune [<shortname> --maxage-days=<n>] [-c=<path>]

Options:
    -c --config=<path>    Specify an alternate config file [default: ~/.podfox.json]
    -h --help     Show this help
"""
# (C) 2015 Bastian Reitemeier
# mail(at)brtmr.de

from colorama import Fore, Back, Style
from docopt import docopt
from os.path import expanduser
from sys import exit
import colorama
import datetime
import feedparser
import json
import os
import os.path
import requests
import sys
import re

# RSS datetimes follow RFC 2822, same as email headers.
# this is the chain of stackoverflow posts that led me to believe this is true.
# http://stackoverflow.com/questions/11993258/
# what-is-the-correct-format-for-rss-feed-pubdate
# http://stackoverflow.com/questions/885015/
# how-to-parse-a-rfc-2822-date-time-into-a-python-datetime

from email.utils import parsedate
from time import mktime

CONFIGURATION_DEFAULTS = {
    "podcast-directory": "~/Podcasts",
    "maxnum": 5000,
    "mimetypes": [ "audio/aac",
                   "audio/ogg",
                   "audio/mpeg",
                   "audio/x-mpeg",
                   "audio/mp3",
                   "audio/mp4",
                   "video/mp4" ]
}
CONFIGURATION = {}

mimetypes = [
    'audio/ogg',
    'audio/mpeg',
    'audio/x-mpeg',
    'video/mp4',
    'audio/x-m4a'
]

def print_err(err):
    print(Fore.RED + Style.BRIGHT + err +
          Fore.RESET + Back.RESET + Style.RESET_ALL, file=sys.stderr)


def print_green(s):
    print(Fore.GREEN + s + Fore.RESET)


def get_folder(shortname):
    base = CONFIGURATION['podcast-directory']
    return os.path.join(base, shortname)


def get_feed_file(shortname):
    return os.path.join(get_folder(shortname), 'feed.json')


def get_filename_from_url(url):
    return url.split('/')[-1].split('?')[0]


def episode_too_old(episode, maxage):
    now = datetime.datetime.utcnow()
    dt_published = datetime.datetime.fromtimestamp(episode["published"])
    return maxage and (now - dt_published > datetime.timedelta(days=maxage))


def sort_feed(feed):
    feed['episodes'] = sorted(feed['episodes'], key=lambda k: k['published'],
                              reverse=True)
    return feed


def import_feed(url, shortname=''):
    '''
    creates a folder for the new feed, and then inserts a new feed.json
    that will contain all the necessary information about this feed, and
    all the episodes contained.
    '''
    # configuration for this feed, will be written to file.
    feed = {}
    #get the feed.
    d = feedparser.parse(url)

    if shortname:
        folder = get_folder(shortname)
        if os.path.exists(folder):
            print_err(
                '{} already exists'.format(folder))
            exit(-1)
        else:
            os.makedirs(folder)
    #if the user did not specify a folder name,
    #we have to create one from the title
    if not shortname:
        # the rss advertises a title, lets use that.
        if hasattr(d['feed'], 'title'):
            title = d['feed']['title']
        # still no succes, lets use the last part of the url
        else:
            title = url.rsplit('/', 1)[-1]
        # we wanna avoid any filename crazyness,
        # so foldernames will be restricted to lowercase ascii letters,
        # numbers, and dashes:
        title = ''.join(ch for ch in title
                if ch.isalnum() or ch == ' ')
        shortname = title.replace(' ', '-').lower()
        if not shortname:
            print_err('could not auto-deduce shortname.')
            print_err('please provide one explicitly.')
            exit(-1)
        folder = get_folder(shortname)
        if os.path.exists(folder):
            print_err(
                '{} already exists'.format(folder))
            exit(-1)
        else:
            os.makedirs(folder)
    #we have succesfully generated a folder that we can store the files
    #in
    #trawl all the entries, and find links to audio files.
    feed['episodes'] = episodes_from_feed(d)
    feed['shortname'] = shortname
    feed['title'] = d['feed']['title']
    feed['url'] = url
    # write the configuration to a feed.json within the folder
    feed_file = get_feed_file(shortname)
    feed = sort_feed(feed)
    with open(feed_file, 'x') as f:
        json.dump(feed, f, indent=4)
    print('imported ' +
          Fore.GREEN + feed['title'] + Fore.RESET + ' with shortname ' +
          Fore.BLUE + feed['shortname'] + Fore.RESET)


def update_feed(feed):
    '''
    download the current feed, and insert previously unknown
    episodes into our local config.
    '''
    d = feedparser.parse(feed['url'])
    #only append new episodes!
    for episode in episodes_from_feed(d):
        found = False
        for old_episode in feed['episodes']:
            if episode['published'] == old_episode['published'] \
                    and episode['title'] == old_episode['title']:
                found = True
        if not found:
            feed['episodes'].append(episode)
            print('new episode.')
    feed = sort_feed(feed)
    overwrite_config(feed)


def overwrite_config(feed):
    '''
    after updating the feed, or downloading new items,
    we want to update our local config to reflect that fact.
    '''
    filename = get_feed_file(feed['shortname'])
    with open(filename, 'w') as f:
        json.dump(feed, f, indent=4)


def episodes_from_feed(d):
    mimetypes = CONFIGURATION['mimetypes']

    episodes = []
    for entry in d.entries:
        # convert publishing time to unix time, so that we can sort
        # this should be unix time, barring any timezone shenanigans
        try:
            date = mktime(parsedate(entry.published))
        except TypeError:
            continue
        if hasattr(entry, 'links'):
            for link in entry.links:
                if not hasattr(link, 'type'):
                    continue
                if hasattr(link, 'type') and (link.type in mimetypes):
                    if hasattr(entry, 'title'):
                        episode_title = entry.title
                    else:
                        episode_title = link.href
                    episodes.append({
                        'title':      episode_title,
                        'url':        link.href,
                        'downloaded': False,
                        'listened':   False,
                        'published':  date
                        })
    return episodes


def download_multiple(feed, maxnum):
    for episode in feed['episodes']:
        if maxnum == 0:
            break
        if not episode['downloaded'] and not episode_too_old(episode, CONFIGURATION['maxage-days']):
            episode['filename'] = download_single(feed['shortname'], episode['url'])
            episode['downloaded'] = True
            maxnum -= 1
    overwrite_config(feed)

def download_single(folder, url):
    print(url)
    base = CONFIGURATION['podcast-directory']
    r = requests.get(url.strip(), stream=True)
    try:
        filename = re.findall('filename="([^"]+)', r.headers['content-disposition'])[0]
    except:
        filename = get_filename_from_url(url)
    print_green("{:s} downloading".format(filename))
    with open(os.path.join(base, folder, filename), 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024**2):
            f.write(chunk)
    print("done.")

    return filename

def available_feeds():
    '''
    podfox will save each feed to its own folder. Each folder should
    contain a json configuration file describing which elements
    have been downloaded already, and how many will be kept.
    '''
    base = CONFIGURATION['podcast-directory']
    paths = [p for p in os.listdir(base)
             if os.path.isdir(get_folder(p))
             and os.path.isfile(get_feed_file(p))]
    #for every folder, check wether a configuration file exists.
    results = []
    for shortname in paths:
        with open(get_feed_file(shortname), 'r') as f:
            feed = json.load(f)
            results.append(feed)
    return sorted(results, key=lambda k: k['title'])


def find_feed(shortname):
    '''
    all feeds are identified by their shortname, which is also the name of
    the folder they will be stored in.
    this function will find the correct folder, and parse the json file
    within that folder to generate the feed data
    '''
    feeds = available_feeds()
    for feed in feeds:
        if feed['shortname'] == shortname:
            return feed
    return None

def rename(shortname, newname):
    folder = get_folder(shortname)
    new_folder = get_folder(newname)
    if not os.path.isdir(folder):
        print_err('folder {0} not found'.format(folder))
        exit(-1)
    os.rename(folder, new_folder)
    feed = find_feed(shortname)
    feed['shortname'] = newname
    overwrite_config(feed)

def prune(feed, maxage=0):
    shortname = feed['shortname']
    episodes = feed['episodes']

    print(shortname)
    for i, episode in enumerate(episodes):
        if episode['downloaded'] and episode_too_old(episode, maxage):
            episode_path = os.path.join(
                get_folder(shortname),
                episode.get("filename", get_filename_from_url(episode['url']))
            )
            try:
                os.remove(episode_path)
            except OSError:
                print("Unable to remove file (%s) for episode: %s" % (episode_path, episode["title"],))
            else:
                episodes[i]["downloaded"] = False
    print("done.")

    overwrite_config(feed)

def pretty_print_feeds(feeds):
    format_str = Fore.GREEN + '{0:45.45} |'
    format_str += Fore.BLUE + '  {1:40}' + Fore.RESET + Back.RESET
    print(format_str.format('title', 'shortname'))
    print('='*80)
    for feed in feeds:
        format_str = Fore.GREEN + '{0:40.40} {1:3d}{2:1.1} |'
        format_str += Fore.BLUE + '  {3:40}' + Fore.RESET + Back.RESET
        feed = sort_feed(feed)
        amount = len([ep for ep in feed['episodes'] if ep['downloaded']])
        dl = '' if feed['episodes'][0]['downloaded'] else '*'
        print(format_str.format(feed['title'], amount, dl, feed['shortname']))


def pretty_print_episodes(feed):
    format_str = Fore.GREEN + '{0:40}  |'
    format_str += Fore.BLUE + '  {1:20}' + Fore.RESET + Back.RESET
    for e in feed['episodes'][:20]:
        status = 'Downloaded' if e['downloaded'] else 'Not Downloaded'
        print(format_str.format(e['title'][:40], status))


def main():
    global CONFIGURATION
    colorama.init()
    arguments = docopt(__doc__, version='p0d 0.01')
    # before we do anything with the commands,
    # find the configuration file

    configfile = expanduser(arguments["--config"])

    try:
        with open(configfile) as conf_file:
            try:
                userconf = json.load(conf_file)
            except ValueError:
                print("invalid json in configuration file.")
                exit(-1)
    except FileNotFoundError:
        userconf = {}

    CONFIGURATION = CONFIGURATION_DEFAULTS.copy()
    CONFIGURATION.update(userconf)
    CONFIGURATION['podcast-directory'] = os.path.expanduser(CONFIGURATION['podcast-directory'])

    #handle the commands
    if arguments['import']:
        if arguments['<shortname>'] is None:
            import_feed(arguments['<feed-url>'])
        else:
            import_feed(arguments['<feed-url>'],
                        shortname=arguments['<shortname>'])
        exit(0)
    if arguments['feeds']:
        pretty_print_feeds(available_feeds())
        exit(0)
    if arguments['episodes']:
        feed = find_feed(arguments['<shortname>'])
        if feed:
            pretty_print_episodes(feed)
            exit(0)
        else:
            print_err("feed {} not found".format(arguments['<shortname>']))
            exit(-1)
    if arguments['update']:
        if arguments['<shortname>']:
            feed = find_feed(arguments['<shortname>'])
            if feed:
                print_green('updating {}'.format(feed['title']))
                update_feed(feed)
                exit(0)
            else:
                print_err("feed {} not found".format(arguments['<shortname>']))
                exit(-1)
        else:
            for feed in available_feeds():
                print_green('updating {}'.format(feed['title']))
                update_feed(feed)
            exit(0)
    if arguments['download']:
        if arguments['--how-many']:
            maxnum = int(arguments['--how-many'])
        else:
            maxnum = CONFIGURATION['maxnum']
        #download episodes for a specific feed
        if arguments['<shortname>']:
            feed = find_feed(arguments['<shortname>'])
            if feed:
                download_multiple(feed, maxnum)
                exit(0)
            else:
                print_err("feed {} not found".format(arguments['<shortname>']))
                exit(-1)
        #download episodes for all feeds.
        else:
            for feed in available_feeds():
                download_multiple(feed,  maxnum)
            exit(0)
    if arguments['rename']:
        rename(arguments['<shortname>'], arguments['<newname>'])

    if arguments['prune']:
        if arguments['--maxage-days']:
            maxage = int(arguments['--maxage-days'])
        else:
            maxage = CONFIGURATION.get('maxage-days', 0)

        if arguments['<shortname>']:
            feed = find_feed(arguments['<shortname>'])
            if feed:
                print_green('pruning {}'.format(feed['title']))
                prune(feed, maxage)
                exit(0)
            else:
                print_err("feed {} not found".format(arguments['<shortname>']))
                exit(-1)
        else:
            for feed in available_feeds():
                print_green('pruning {}'.format(feed['title']))
                prune(feed, maxage)
