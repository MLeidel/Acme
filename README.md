# Internet Browser

Acme is an Internet browser developed in Python. The engin is WebKitGtk.

WebKitGtk is still working out bugs - this implementation may crash on certain sites.
For instance, it won't pass the "Cloudflare" screening you find on many sites.

Is it secure?
    It is as secure as the sites you direct it too. There are no hidden adgendas built into the browser.

My first Internet home was called "Roadrunner". With that in mind, I named this browser "Acme" :)

## Features

### Implements:

        developer tools
        persistent history
        bookmarking
        cookie management
        cache management
        user settings
        window geometry
        agressive ad blocking
        
### Does not implement:

        extentions
        password manager or form data

## files

cookies.sqlite

        database of active cookies

neo.dat

        config data for user settings
            homepage, search engine, defaults font info, and Alt key snippets

acme.py

        source code for Acme browser

goodcookie.txt

        contains list of cookie host names that you mantain.
        These cookies will NOT be removed from the cookies database
        whey you click "reset cookies". Cookies can also be deleted
        from the "cookie manager" button.

listcook.py

        prints out a list of unique active cookie host names  
        to help you manage the goodcookie.txt file

clear_cache.py

        REMOVE ALL persistent cache data for acme.py, acme.pyc  
        usually found in user's .cache directory
        
browser_history.txt

        persistent history limited to N recent URLs

## Installation

```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo libgirepository1.0-dev gir1.2-gtk-3.0 gir1.2-webkit2-4.1
sudo apt install gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad 
sudo apt install gstreamer1.0-plugins-ugly gstreamer1.0-libav
```

## A note about settings

Acme has only 12 settings you can change:
    
1. Your homepage URL (you have to pick one, the browser doesn't have one)
2. The search engine with query string of your choice
3. numeric - Limit of persistent history items to allow
4. yes/no - Jump to new tabs when opened
5. Default browser font family name
6. Default browser font size
7. Default browser monospace font family name
8. Default browser monospace font size
9. Book marks path
10. Alt-1
11. Alt-2
12. Alt-3
13. Alt-4
    
Alt-1 through 4 can be any kind of text you with to insert into an HTML input text field.  

## Running on Windows WSL

Running on Windows WSL can be tricky, but this is what worked well for me.

1. Make sure WSL is activated and you can get to the Linux shell (any distro is fine)
2. In the root of your user directory create a bash file with this:
    
        #!/usr/bin/bash
        
        cd /mnt/c/Acme
        export GTK_THEME=Adwaita:dark
        export GTK_APPLICATION_PREFER_DARK_THEME=1
        ./amce.py
              
3. In your Windows user directory create this command file:
        
        wsl.exe --cd ~ -- bash -l -c "./bashfilefrom#2.sh"
        
4. Then create a shorcut on your desktop that will execute the cmd file in 3
    which will run the a bash file you created in 2 which will run acme.py.

---

