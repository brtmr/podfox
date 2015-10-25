# podfox - podcatching for the terminal.
![](https://raw.githubusercontent.com/brtmr/podfox/master/logo/logo.png)


A program for catching/ managing/ listening to podcasts for the terminal. 

Work in Progress and unfinished. Use at your own risk.

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

### Import 

To import a new feed use: 
`podfox.py import <feed-url> [--shortname=<shortname>]`
For example, to import the haskell cast feed:

`podfox import http://www.haskellcast.com/feed.xml`
To import the techsnap podcast, and to store the episodes to a specific folder, use 


`podfox import http://feeds.feedburner.com/techsnapmp3 --shortname=ts`


### Update
`podfox update` will update all feeds (This does not include downloading any new episodes)

`podfox update <shortname>` will only update the feed associated with the given `shortname`

### Feeds 

`podfox feeds` will give an overview over the imported pocasts, and their `shortname`s

