#!/usr/bin/python3
"""podfox - podcatcher for the terminal


Usage:
    podfox.py import <feed-url> [--shortname=<shortname>]
    podfox.py update [--shortname=<shortname>]
    podfox.py feeds
    podfox.py episodes <shortname>
    podfox.py download <shortname> [--how-many=<n>]

Options:
    -h --help     Show this help
    -v --verbose  Show more output
"""
# (C) 2015 Bastian Reitemeier
# mail(at)brtmr.de

from colorama import Fore, Back, Style
from docopt import docopt
from os.path import expanduser
from sys import exit
import colorama
import feedparser
import json
import os
import os.path
import pycurl
import sys

# RSS datetimes follow RFC 2822, same as email headers.
# this is the chain of stackoverflow posts that led me to believe this is true.
# http://stackoverflow.com/questions/11993258/what-is-the-correct-format-for-rss-feed-pubdate
# http://stackoverflow.com/questions/885015/how-to-parse-a-rfc-2822-date-time-into-a-python-datetime
from email.utils import parsedate
from time import mktime


PODCAST_DIRECTORY = ''
CONFIGURATION = {}
DEFAULT_LIMIT = 5


def print_err(err):
    print(Fore.RED + Style.BRIGHT + err + \
            Fore.RESET + Back.RESET + Style.RESET_ALL \
            , file=sys.stderr)

def print_green(s):
    print(Fore.GREEN + Style.BRIGHT + s + Fore.RESET + Style.RESET_ALL)


def import_feed(url, shortname=''):
    '''
    creates a folder for the new feed, and then inserts a new feed.json
    that will contain all the necessary information about this feed, and
    all the episodes contained.
    '''
    global CONFIGURATION
    # configuration for this feed, will be written to file.
    feed_conf = {}
    # check if the folder exists.
    folder_created = False
    if shortname:
        folder = os.path.join(CONFIGURATION['podcast-directory'],shortname)
        if os.path.exists(folder):
            print_err(
                    '{} already exists'.format(folder))
            exit(-1)
        else:
            os.makedirs(folder)
            folder_created = True
    #get the feed.
    d = feedparser.parse(url)
    #if the user did not specify a folder name,
    #we have to create one from the title
    if not folder_created:
        # the rss advertises a title, lets use that.
        if hasattr(d['feed'], 'title'):
            title = d['feed']['title']
        # still no succes, lets use the last part of the url
        else:
             title = url.rsplit('/',1)[-1]
        # we wanna avoid any filename crazyness,
        # so foldernames will be restricted to lowercase ascii letters,
        # numbers, and dashes:
        title = ''.join(ch for ch in title \
                if ch.isalnum() or ch==' ')
        shortname=title.replace(' ','-').lower()
        folder = os.path.join(CONFIGURATION['podcast-directory'],shortname)
        if os.path.exists(folder):
            print_err(
                    '{} already exists'.format(folder))
            exit(-1)
        else:
            os.makedirs(folder)
            folder_created = True
    #we have succesfully generated a folder that we can store the files
    #in
    feed_conf['episodes'] = []
    #trawl all the entries, and find links to audio files.
    feed_conf['episodes'] = episodes_from_feed(d)
    feed_conf['shortname'] = shortname
    feed_conf['title'] = d['feed']['title']
    feed_conf['url'] = url
    # write the configuration to a feed.json within the folder
    feed_conf_file = os.path.join(folder,'feed.json')
    with open(feed_conf_file,'x') as f:
        json.dump(feed_conf,f)

def update_feed(feed):
    '''
    download the current feed, and insert previously unknown
    episodes into our local config.
    '''
    d = feedparser.parse(feed['url'])
    #only append new episodes!
    for episode in episodes_from_feed(d):
        if episode in feed['episodes']:
            continue
        else: feed['episodes'].append(episode)
    overwrite_config(feed)


def overwrite_config(feed):
    '''
    after updating the feed, or downloading new items,
    we want to update our local config to reflect that fact.
    '''
    base = CONFIGURATION['podcast-directory']
    filename = os.path.join(base,feed['shortname'],'feed.json')
    with open(filename,'w') as f:
        json.dump(feed,f)

def episodes_from_feed(d):
    episodes=[]
    for entry in d.entries:
        # convert publishing time to unix time, so that we can sort
        # this should be unix time, barring any timezone shenanigans
        date = mktime(parsedate(entry.published))
        if hasattr(entry, 'links'):
            for link in entry.links:
                if not hasattr(link,'type'):
                    continue
                if hasattr(link,'type') and link.type == 'audio/mpeg' or link.type == 'audio/ogg':
                    if hasattr(entry, 'title'):
                        episode_title = entry.title
                    else:
                        episode_title = link.href
                    episodes.append({
                        'title'      : episode_title,
                        'url'        : link.href,
                        'downloaded' : False,
                        'listened'   : False,
                        'published'  : date
                        })
    return episodes


def download_single_podcast(folder,url):
    base = CONFIGURATION['podcast-directory']
    filename = url.split('/')[-1]
    filename = filename.split('?')[0]
    print_green("{:s} downloading".format(filename))
    with open(os.path.join(base, folder, filename), 'wb') as f:
        c = pycurl.Curl()
        c.setopt(c.URL, url)
        c.setopt(c.WRITEDATA, f)
        # Follow redirect. Podcast cdns love redirecting you around.
        c.setopt(c.FOLLOWLOCATION, True)
        c.perform()
        c.close()
    print_green("{:s} downloaded".format(filename))


def available_feeds():
    base = CONFIGURATION['podcast-directory']
    '''
    p0d will save each feed to its own folder. Each folder should
    contain a json configuration file describing which elements
    have been downloaded already, and how many will be kept.
    '''
    paths = [p for p in os.listdir(base) \
             if  os.path.isdir(os.path.join(base,p)) \
             and os.path.isfile(os.path.join(base,p,'feed.json'))]
    #for every folder, check wether a configuration file exists.
    results = []
    for path in paths:
        with open(os.path.join(base,path,'feed.json'),'r') as f:
            feed = json.load(f)
            results.append(feed)
    return results

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

def pretty_print_feeds(feeds):
    format_str = Fore.GREEN + '{0:40}  |' + \
        Fore.BLUE  + '  {1:20}' + Fore.RESET + Back.RESET
    print(format_str.format('title', 'shortname'))
    print('='*64)
    for feed in feeds:
        print(format_str.format(feed['title'], feed['shortname']))


def pretty_print_episodes(feed):
    format_str = Fore.GREEN + '{0:40}  |' + \
        Fore.BLUE  + '  {1:20}' + Fore.RESET + Back.RESET
    for e in feed['episodes']:
        print(format_str.format(e['title'][:40], 'Downloaded' if e['downloaded']
            else 'Not Downloaded'))


if __name__=='__main__':
    colorama.init()
    arguments = docopt(__doc__, version='p0d 0.01')
    # before we do anything with the commands,
    # find the configuration file
    home_directory = expanduser("~")
    with open(home_directory + '/.podfox.json') as conf_file:
        try:
            CONFIGURATION = json.load(conf_file)
        except ValueError:
            print("invalid json in configuration file.")
            exit(-1)
    #handle the commands
    if arguments['import']:
        if arguments['--shortname'] is None:
            import_feed(arguments['<feed-url>'])
        else:
            import_feed(arguments['<feed-url>'], shortname=arguments['--shortname'])
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
        maxnum = int(arguments['--how-many']) if arguments['--how-many'] else CONFIGURATION['maxnum']
        feed = find_feed(arguments['<shortname>'])
        if feed:
            for episode in feed['episodes']:
                if maxnum == 0:
                    break
                if not episode['downloaded']:
                #TODO: multithreading
                    download_single_podcast(feed['shortname'], episode['url'])
                    episode['downloaded'] = True
                    maxnum -= 1
            overwrite_config(feed)
            exit(0)
        else:
            print_err("feed {} not found".format(arguments['<shortname>']))
            exit(-1)
