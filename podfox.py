#!/usr/bin/python3
"""podfox - podcatcher for the terminal


Usage:
    podfox.py import <feed-url> [<shortname>] [-c=<path>]
    podfox.py update [<shortname>] [-c=<path>]
    podfox.py feeds [-c=<path>]
    podfox.py episodes <shortname> [-c=<path>]
    podfox.py download [<shortname> --how-many=<n>] [-c=<path>]
    podfox.py rename <shortname> <newname> [-c=<path>]

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
from threading import Thread, active_count
import colorama
import feedparser
import json
import os
import os.path
import pycurl
import sys

# RSS datetimes follow RFC 2822, same as email headers.
# this is the chain of stackoverflow posts that led me to believe this is true.
# http://stackoverflow.com/questions/11993258/
# what-is-the-correct-format-for-rss-feed-pubdate
# http://stackoverflow.com/questions/885015/
# how-to-parse-a-rfc-2822-date-time-into-a-python-datetime

from email.utils import parsedate
from time import mktime

CONFIGURATION = {}

mimetypes = [
    'audio/ogg',
    'audio/mpeg',
    'video/mp4'
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
    feed['episodes'] = sorted(feed['episodes'], key=lambda k: k['published'],
                              reverse=True)
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
    episodes = []
    for entry in d.entries:
        # convert publishing time to unix time, so that we can sort
        # this should be unix time, barring any timezone shenanigans
        date = mktime(parsedate(entry.published))
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
    if "maxthreads" in CONFIGURATION.keys():
        maxthreads = CONFIGURATION['maxthreads']
    else:
        maxthreads = maxnum

    for episode in feed['episodes']:
        if maxnum == 0:
            break
        if not episode['downloaded']:
        #TODO: multithreading
            downloadthread = download_thread(feed['shortname'], episode['url'])
            downloadthread.start()
            #download_single(feed['shortname'], episode['url'])
            episode['downloaded'] = True
            maxnum -= 1

        while active_count() > maxthreads:
            try:
                downloadthread.join(60)
            except RuntimeError:
                pass

    overwrite_config(feed)


class download_thread(Thread):
    def __init__(self, folder, url):
        Thread.__init__(self)

        self.folder = folder
        self.url = url
        self.daemon = True

    def run(self):
        download_single(self.folder, self.url)

def download_single(folder, url):
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
    print("{:s} done.".format(filename))


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

def pretty_print_feeds(feeds):
    format_str = Fore.GREEN + '{0:40.40}  |'
    format_str += Fore.BLUE + '  {1:40}' + Fore.RESET + Back.RESET
    print(format_str.format('title', 'shortname'))
    print('='*64)
    for feed in feeds:
        print(format_str.format(feed['title'], feed['shortname']))


def pretty_print_episodes(feed):
    format_str = Fore.GREEN + '{0:40}  |'
    format_str += Fore.BLUE + '  {1:20}' + Fore.RESET + Back.RESET
    for e in feed['episodes']:
        status = 'Downloaded' if e['downloaded'] else 'Not Downloaded'
        print(format_str.format(e['title'][:40], status))


if __name__ == '__main__':
    colorama.init()
    arguments = docopt(__doc__, version='p0d 0.01')
    # before we do anything with the commands,
    # find the configuration file
    configfile = expanduser(arguments["--config"])

    with open(configfile) as conf_file:
        try:
            CONFIGURATION = json.load(conf_file)
        except ValueError:
            print("invalid json in configuration file.")
            exit(-1)
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
