# podfox - podcatching for the terminal.
![podfox logo](https://raw.githubusercontent.com/brtmr/podfox/62a0a3e745185deee2ee92e1250034d65d863c21/logo/logo.png)


A program for managing & catching podcasts from the terminal. 

Work in Progress and unfinished. Use at your own risk.
## Requirements
requires feedparser, requests and colorama

install automatically via pip:

```pip install podfox```

## Configuration

podfox main configuration file is called `.podfox.json` and should be located in your home directory.
Here is mine: 
```
{
    "podcast-directory" : "/home/basti/podcasts",
    "maxnum"            : 5
}
```
`podcast-directory` is your main directory to store podcast data. This directory should be empty before you
begin adding feeds.
`maxnum` describes the maximum number of episodes you want to download with a single `download`-command.

## Directory Structure

In podfox, every podcast is identified with its own `shortname`, which is restricted to lowercase-letters, numbers, and dashes. If the `shortname` is not specifically given during import, it will be derived from the title of the feed. The following shows a directory tree for such a setup, including two podcasts, each with its own feed.json file for bookkeeping.
 
```
+ podcast-directory
|              
+-----------+ python-for-rockstars
|           |
|           + feed.json
|           + episode1.ogg
|           + episode2.ogg
|
+-----------+ cobol-today
            |
            + feed.json
            + episode289.ogg
            + episode288.ogg
```
## Usage:
```
    podfox.py import <feed-url> [<shortname>]
    podfox.py update [<shortname>]
    podfox.py feeds
    podfox.py episodes <shortname>
    podfox.py download [<shortname> --how-many=<n>]
```
### Import 

To import a new feed use: 
`podfox.py import <feed-url> [<shortname>]`
For example, to import the haskell cast feed:

`podfox import http://www.haskellcast.com/feed.xml`
To import the techsnap podcast, and to store the episodes to a specific folder `ts`, use 


`podfox import http://feeds.feedburner.com/techsnapmp3 ts`


### Update
`podfox update` will update all feeds (This does not include downloading any new episodes)

`podfox update <shortname>` will only update the feed associated with the given `shortname`

### Feeds 

`podfox feeds` will give an overview over the imported pocasts, and their `shortname`s.
In the example: 
```
$ podfox feeds
title                                     |  shortname           
================================================================
TechSNAP MP3                              |  ts                  
The Haskell Cast                          |  the-haskell-cast    
```

### Episodes

`podfox episodes <shortname>` will produce a list of episodes available for this podcast, and wether they have been downloaded yet.

```
$ podfox episodes ts
A Rip in NTP | TechSNAP 237               |  Not Downloaded      
National Security Breaking Agency | Tech  |  Not Downloaded      
Catching the Angler | TechSNAP 235        |  Not Downloaded      
Key Flaw With GPL | TechSNAP 234          |  Not Downloaded      
Dukes of Cyber Hazard | TechSNAP 233      |  Not Downloaded      
Hardware Insecurity Module | TechSNAP 23  |  Not Downloaded      
Leaky RSA Keys | TechSNAP 231             |  Not Downloaded      
Trojan Family Ties | TechSNAP 230         |  Not Downloaded      
Extortion Startups | TechSNAP 229         |  Not Downloaded      
[...]
```

### Downloading

`podfox download` will download `maxnum` not yet downloaded episodes for every feed (if possible.)

`podfox download ts --how-many=3` will download the 3 newest techsnap podcasts that have not yet been downloaded. (Skipping newer, but already downloaded ones). If the `--how-many` parameter is omitted, the `maxnum` parameter from the configuration file is used instead.

