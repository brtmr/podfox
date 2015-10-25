"""p0d - podcatcher for the terminal


Usage:
    p0d.py import <feed-url> [--shortname=<shortname> --max-num=<n>]
    p0d.py findfeed <website-url>
    p0d.py get-updates <feedname>
    p0d.py show-updates <feedname>
    p0d.py download <feedname>
    p0d.py show-feeds
    p0d.py sync-to <folder> [--delete --max-num-<n> <feeds>]

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
import os.path
import sys
import os

PODCAST_DIRECTORY = ''
CONFIGURATION = {}

def print_err(err):
    print(Fore.RED + Style.BRIGHT + err + \
            Fore.RESET + Back.RESET + Style.RESET_ALL \
            , file=sys.stderr)

def import_feed(url, shortname=''):
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
        # we wanna avoid any filename crazyness,
        # so foldernames will be restricted to lowercase ascii letters,
        # numbers,
        # and dashes:
        title = d['feed']['title']
        title = ''.join(ch for ch in title \
                if ch.isalnum() or ch==' ')
        title=title.replace(' ','-').lower()
        folder = os.path.join(CONFIGURATION['podcast-directory'],title)
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
    for entry in d.entries:
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.type == 'audio/mpeg' or link.type == 'audio/ogg':
                    feed_conf['episodes'].append({
                        'title'      : entry.title,
                        'url'        : link.href,
                        'downloaded' : False,
                        'listened'   : False
                        })

    feed_conf['name'] = d['feed']['title']
    feed_conf['url'] = url
    # write the configuration to a feed.json within the folder
    feed_conf_file = os.path.join(folder,'feed.json')
    with open(feed_conf_file,'x') as f:
        json.dump(feed_conf,f)


def find_feed(url):
    pass

def available_feeds():
    '''
    p0d will save each feed to its own folder. Each folder should
    contain a json configuration file describing which elements
    have been downloaded already, and how many will be kept.
    '''
    pass

def show_updates():
    pass

if __name__=='__main__':
    colorama.init()
    arguments = docopt(__doc__, version='p0d 0.01')
    # before we do anything with the commands,
    # find the configuration file
    home_directory = expanduser("~")
    with open(home_directory + '/.p0d.json') as conf_file:
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
