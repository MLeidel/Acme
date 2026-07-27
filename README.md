# Internet Browser

## Features

### Does not implement:

        extentions
        bookmarks
        seaving of passwords or form data
        (superficial?) enhancement settings

### Does implement:

        developer tools
        persistent history
        cookie management
        cache management
        user settings
        window geometry
        
## files

cookies.sqlite

        database of active cookies

neo.dat

        config data for user settings
            homepage, search engine, defaults font info, and Alt key snippets

neo.py

        source code for Neo browser

goodcookie.txt

        contains list of cookie host names not to delete
        from the cookies database

listcook.py

        prints out a list of unique active cookie host names  
        to help you manage the goodcookie.txt file

delcookies.py

        deletes all active cookies from cookies.sqlite that
        ARE NOT LISTED in goodcookie.txt

delcache.py

        REMOVE ALL persistent cache data for neo.py, neo.pyc
        
browser_history.txt

        persistent history limited to N recent URLs

## Installation

```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo libgirepository1.0-dev gir1.2-gtk-3.0 gir1.2-webkit2-4.1
sudo apt install gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad 
sudo apt install gstreamer1.0-plugins-ugly gstreamer1.0-libav
```
