# podfox - podcatching for the unix terminal.

a program for catching/ managing/ moving/ listening to podcasts for the linux terminal. 
Work in Progress and unfinished. Use at your own risk.

```
Usage:
    podfox.py import <feed-url> [--shortname=<shortname>]
    podfox.py update [--shortname=<shortname>]
    podfox.py feeds
    podfox.py episodes <shortname>
    podfox.py download <shortname> [--how-many=<n>]
    podfox.py sync-to <folder> [--delete --how-many=<n> <feeds>]
Options:
    -h --help     Show this help
    -v --verbose  Show more output
```

To use, put a file named `.podfox.json` in your home directory, this will be your main configuration file.
Here is mine: 
```
{
    "podcast-directory" : "/home/basti/podcasts",
    "player"            : "vlc",
    "maxnum"            : 5
}
```
Make sure that your podcast-directory exists.
