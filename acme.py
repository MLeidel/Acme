#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
#   Safe environment flags to prevent GTK driver crashes
#   Were conflicting with certain settings causing video to not work
# os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
# os.environ["WEBKIT_DISABLE_DMABUF_RENDERER"] = "1"

#   Disable JSC JIT compiler (prevents WebAssembly segfaults on heavy crypto sites)
os.environ["JSC_useJIT"] = "False"  # left off for now

import sys
import shutil
import faulthandler
from pathlib import Path
import sqlite3
from urllib.parse import urlparse
from pathlib import PurePosixPath
import warnings

import gi

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message="WebKit2.NavigationPolicyDecision.get_request is deprecated"
)

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

gi.require_version('Gdk', '3.0')
gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2 as wk, Gdk, Pango, Gio, GLib
# Debian test environment
# webkit2gtk-driver/stable-security 2.52.6-1~deb13u1 all
# webkitgtk-webdriver/stable-security 2.52.6-1~deb13u1 amd64

# ------------------------------ Configuration ------------------------------
# Default settings in case config files are missing or incomplete
DEFAULT_HOMEPAGE = "https://duckduckgo.com"
DEFAULT_SEARCH = "https://duckduckgo.com/?q="
DEFAULT_HISTLIMIT = 100
DEFAULT_GOTAB = "yes"
DEFAULT_FONT = "Sans"
DEFAULT_FONT_SIZE = 14
DEFAULT_MONO_FONT = "Monospace"
DEFAULT_MONO_SIZE = 14
DEFAULT_BKMARK_PATH = "bkmarks.txt"
DEFAULT_ALT1 = ""
DEFAULT_ALT2 = ""
DEFAULT_ALT3 = ""
DEFAULT_ALT4 = ""

def load_config():
    """Load settings from neo.dat and window geometry from wingeo."""
    settings = {
        "homepage": DEFAULT_HOMEPAGE,
        "searchen": DEFAULT_SEARCH,
        "histlimit": DEFAULT_HISTLIMIT,
        "gotab": DEFAULT_GOTAB,
        "deffont": DEFAULT_FONT,
        "defsize": DEFAULT_FONT_SIZE,
        "monfont": DEFAULT_MONO_FONT,
        "monsize": DEFAULT_MONO_SIZE,
        "bkmpath": DEFAULT_BKMARK_PATH,
        "1": DEFAULT_ALT1,
        "2": DEFAULT_ALT2,
        "3": DEFAULT_ALT3,
        "4": DEFAULT_ALT4,
    }
    geometry = {"width": 0, "height": 0, "x": 0, "y": 0}

    # Load neo.dat (settings)
    neo_path = os.path.join(script_dir, "neo.dat")
    try:
        with open(neo_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]
        if len(lines) >= 13:
            settings = {
                "homepage": lines[0],
                "searchen": lines[1],
                "histlimit": lines[2],
                "gotab": lines[3],
                "deffont": lines[4],
                "defsize": lines[5],
                "monfont": lines[6],
                "monsize": lines[7],
                "bkmpath": lines[8],
                "1": lines[9],
                "2": lines[10],
                "3": lines[11],
                "4": lines[12],
            }
    except Exception as e:
        print(f"Warning: Could not load {neo_path}: {e}")

    # Load wingeo (window geometry)
    wingeo_path = os.path.join(script_dir, "wingeo")
    try:
        with open(wingeo_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]
        if len(lines) >= 4:
            geometry = {
                "width": int(lines[0]),
                "height": int(lines[1]),
                "x": int(lines[2]),
                "y": int(lines[3]),
            }
    except Exception as e:
        print(f"Warning: Could not load {wingeo_path}: {e}")

    # Convert numeric strings to ints
    for key in ("histlimit", "defsize", "monsize"):
        try:
            settings[key] = int(settings[key])
        except (ValueError, TypeError):
            settings[key] = {
                "histlimit": DEFAULT_HISTLIMIT,
                "defsize": DEFAULT_FONT_SIZE,
                "monsize": DEFAULT_MONO_SIZE
            }[key]
    return settings, geometry

# Load initial settings and geometry
current_settings, initial_geometry = load_config()

blocker_on = 1
blockcount = 0

BLOCK_SUBSTRINGS = [
    # Major ad/analytics/tracker networks
    "doubleclick.net",
    "adservice.google.",
    "googlesyndication.com",
    "googletagmanager.com",
    "gtag/js",
    "google-analytics.com",
    "googleadservices.com",
    "pagead/",
    "adnxs.com",
    "adsystem",
    "adsafeprotected.com",
    "criteo.com",
    "taboola.com",
    "revcontent.com",
    "outbrain.com",
    "zemanta.com",
    "scorecardresearch.com",
    "quantserve.com",
    "tapad.",
    "rubiconproject.com",
    "xandr.com",
    "appnexus.com",
    "adsrvr.org",
    "facebook.net",
    "twitter.com/i/ads",
    "t.co/ads",
    "segment.io",
    "segments/",
    "mixpanel.com",
    "cdn.mxpnl.com",
    "hotjar.com",
    "hj.",
    "recaptcha",
    "matomo.",
    "piwik.",
    "sentry.io",
    "loggly.com",
    # Common tracking/ads URL patterns
    "/ads",
    "/advert",
    "/adserver",
    "/adserver/",
    "/ads?",
    "/ad?",
    "/track?",
    "/tracking",
    "/click?",
    "/click",
    "/impression",
    "/imps",
    "/collect?",
    "/pixel?",
    "/event?",
    "/events?",
    "/beacon",
    "/beacon?",
    "/batch?",
    "/log?",
    "/logs?",
    "/stats",
    "/stat/",
    "/analytics",
    "/analytics?",
    "/gtm.js",
    "/gtag/",
    "/amplitude.js",
    "amplitude.com",
    "/w/analytics",
    "adsbygoogle",
    "googletagservices",
    "googletagservices.com",
    "gpt.js",
    "doubleclick",
]

# ------------------------------ BrowserTab ------------------------------
class BrowserTab(Gtk.VBox):
    '''Represents a single browser tab.'''

    def __init__(self, browser, *args, **kwargs):
        super(BrowserTab, self).__init__(*args, **kwargs)

        self.browser = browser

        # Inject custom CSS
        self.user_content = wk.UserContentManager()
        css = '''
        ::selection {
            background-color: #ff007f;
            color: #ffffff;
        }
        '''
        stylesheet = wk.UserStyleSheet.new(
            css,
            wk.UserContentInjectedFrames.ALL_FRAMES,
            wk.UserStyleLevel.USER,
            None,
            None
        )
        self.user_content.add_style_sheet(stylesheet)

        self.web_view = wk.WebView.new_with_user_content_manager(self.user_content)

        # REWROTE SETTINGS ON NOV 12 2026
        # for Video and Downloads

        settings = self.web_view.get_settings()

        settings.set_enable_javascript(True)
        settings.set_enable_html5_local_storage(True)
        settings.set_enable_developer_extras(True)
        settings.set_javascript_can_open_windows_automatically(True)


        # # Font settings (with error handling)
        try:
            settings.set_property("default-font-family", current_settings["deffont"])
        except Exception:
            settings.set_property("default-font-family", DEFAULT_FONT)
        try:
            settings.set_property("default-font-size", int(current_settings["defsize"]))
        except Exception:
            settings.set_property("default-font-size", DEFAULT_FONT_SIZE)
        try:
            settings.set_property("monospace-font-family", current_settings["monfont"])
        except Exception:
            settings.set_property("monospace-font-family", DEFAULT_MONO_FONT)
        try:
            settings.set_property("default-monospace-font-size", int(current_settings["monsize"]))
        except Exception:
            settings.set_property("default-monospace-font-size", DEFAULT_MONO_SIZE)

        settings.set_allow_universal_access_from_file_urls(True)
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_enable_write_console_messages_to_stdout(False)

        # New settings ON NOV 12 202

        # JavaScript and storage
        settings.set_enable_javascript(True)
        # settings.set_enable_html5_local_storage(True)
        settings.set_enable_developer_extras(True)
        settings.set_javascript_can_open_windows_automatically(True)

        try:
            settings.set_enable_encrypted_media(True)
        except Exception as e:
            print("EME setting unavailable:", e)

        try:
            settings.set_media_playback_requires_user_gesture(False)
        except Exception as e:
            print("Autoplay setting unavailable:", e)

        try:
            settings.set_media_playback_allows_inline(True)
        except Exception as e:
            print("Inline playback setting unavailable:", e)

        settings.set_user_agent(None)



        # Signal connections
        self.web_view.connect("decide-policy", self.on_decide_policy)
        self.web_view.connect("mouse-target-changed", self.displayuri)
        self.web_view.connect("button-press-event", self.on_button_press)
        self.web_view.connect("load-changed", self.on_load_changed)
        self.web_view.connect("create", self.on_create)

        # Printing action for context menu
        self.print_action = Gio.SimpleAction.new("print-page", None)
        self.print_action.connect("activate", self.on_print_page)
        self.web_view.connect("context-menu", self.on_context_menu)

        # Toolbar buttons
        self.button_back = Gtk.ToolButton(stock_id=Gtk.STOCK_GO_BACK)
        self.button_close_tab = Gtk.ToolButton(stock_id=Gtk.STOCK_CLOSE)
        self.button_close_tab.set_tooltip_text("Close Tab (Esc)")
        self.button_forward = Gtk.ToolButton(stock_id=Gtk.STOCK_GO_FORWARD)
        self.button_refresh = Gtk.ToolButton(stock_id=Gtk.STOCK_REFRESH)
        self.button_home = Gtk.ToolButton(stock_id=Gtk.STOCK_HOME)
        self.button_new_tab = Gtk.ToolButton(stock_id=Gtk.STOCK_ADD)
        self.button_new_tab.set_tooltip_text("New Tab (Homepage)")

        self.address_bar = Gtk.Entry()
        self.address_bar.connect("activate", self.load_page)
        self.address_bar.connect("key-press-event", self.on_address_key_press)

        self.button_bookmarx = Gtk.ToolButton()
        self.button_bookmarx.set_icon_name("bookmark-new-symbolic")
        self.button_bookmarx.set_tooltip_text("Bookmarks")
        self.button_bookmarx.connect("clicked", self.browser.save_active_tab_info)

        self.button_find = Gtk.ToolButton(stock_id=Gtk.STOCK_FIND)
        self.button_find.set_tooltip_text("Find Ctrl+F")
        self.button_find.connect("clicked", self.browser.raise_find_dialog)

        self.button_printer = Gtk.ToolButton(stock_id=Gtk.STOCK_PRINT)
        self.button_printer.set_tooltip_text("Print")
        self.button_printer.connect("clicked", self.browser.on_print_clicked)

        self.button_back.connect("clicked", lambda x: self.web_view.go_back())
        self.button_close_tab.connect("clicked", self.browser.close_current_tab)
        self.button_forward.connect("clicked", lambda x: self.web_view.go_forward())
        self.button_refresh.connect("clicked", lambda x: self.web_view.reload())
        self.button_home.connect("clicked", lambda x: self.web_view.load_uri(current_settings['homepage']))
        self.button_new_tab.connect("clicked", self.browser.open_new_tab)

        # URL bar layout
        url_box = Gtk.HBox()
        url_box.pack_start(self.button_back, False, False, 0)
        url_box.pack_start(self.button_close_tab, False, False, 0)
        url_box.pack_start(self.button_forward, False, False, 0)
        url_box.pack_start(self.button_refresh, False, False, 0)
        url_box.pack_start(self.button_home, False, False, 0)
        url_box.pack_start(self.button_new_tab, False, False, 0)
        url_box.pack_start(self.address_bar, True, True, 0)
        url_box.pack_start(self.button_bookmarx, False, False, 0)
        url_box.pack_start(self.button_find, False, False, 0)
        url_box.pack_start(self.button_printer, False, False, 0)
        self.pack_start(url_box, False, False, 0)

        # Scrolled window for web view
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.web_view)

        # Find bar
        find_box = Gtk.HBox()
        self.find_controller = self.web_view.get_find_controller()
        button_close = Gtk.ToolButton(stock_id=Gtk.STOCK_CLOSE)
        button_next = Gtk.ToolButton(stock_id=Gtk.STOCK_GO_DOWN)
        button_prev = Gtk.ToolButton(stock_id=Gtk.STOCK_GO_UP)
        self.find_entry = Gtk.Entry()
        button_close.connect("clicked", lambda x: find_box.hide())
        self.find_entry.connect("activate", self.find_text)
        button_next.connect("clicked", self.find_text_next)
        button_prev.connect("clicked", self.find_text_prev)
        find_box.pack_start(button_close, False, False, 0)
        find_box.pack_start(self.find_entry, False, False, 0)
        find_box.pack_start(button_prev, False, False, 0)
        find_box.pack_start(button_next, False, False, 0)
        self.find_box = find_box

        self.pack_start(find_box, False, False, 0)
        self.pack_start(scrolled_window, True, True, 0)

        self.show_all()
        self.find_box.hide()

        # Load initial URL (either start_url from command line or homepage)
        if start_url is not None:
            self.web_view.load_uri(start_url)
        else:
            self.web_view.load_uri(current_settings["homepage"])

        GLib.idle_add(self.web_view.grab_focus)

    # ------------------- Helper methods -------------------
    def open_devtools(self):
        '''Show developer tools for this tab.'''
        try:
            inspector = self.web_view.get_inspector()
            inspector.show()
        except Exception as e:
            print(f"Error opening devtools: {e}")

    def on_create(self, webview, navigation_action):
        '''
        Handle JavaScript window.open() and context menu "Open Link in New Window".
        We create a new tab with the target URI and return None to cancel the
        default popup creation, avoiding potential crashes in WebKitGTK.
        '''
        uri = None
        if navigation_action:
            try:
                nav = navigation_action
                req = nav.get_request()
                if req:
                    uri = req.get_uri()
            except Exception:
                uri = None

        if self.browser:
            self.browser.open_new_tab(None, uri)
        return None  # Important: return None, not the new WebView

    def sync_address_bar(self):
        '''Update address bar with current URI.'''
        uri = self.web_view.get_uri()
        if uri:
            self.address_bar.set_text(uri)

    def on_load_changed(self, web_view, load_event):
        '''Update address bar on load finish and record history.'''
        if load_event == wk.LoadEvent.FINISHED:
            uri = web_view.get_uri()
            if uri:
                self.address_bar.set_text(uri)
                history_path = os.path.join(script_dir, "browser_history.txt")
                with open(history_path, "a", encoding="utf-8") as f:
                    f.write(uri + "\n")

    def is_url(self, text):
        '''Check if a string looks like a URL.'''
        if " " in text:
            return False
        if text.startswith(("http://", "https://", "file://")):
            return True
        # Accept localhost and IP addresses
        if text.startswith("localhost") or text.split(":")[0].replace(".", "").isdigit():
            return True
        if "." not in text:
            return False
        parts = text.split(".")
        return len(parts) >= 2 and len(parts[-1]) >= 2

    def load_page(self, widget, url=None):
        '''Load URL from address bar, or search if not a URL.'''
        if url:
            text = url
        else:
            text = self.address_bar.get_text().strip()

        # Check for local file
        base_dir = Path(__file__).resolve().parent
        file_path = (base_dir / text).resolve()
        if file_path.exists() and file_path.is_file():
            file_uri = GLib.filename_to_uri(str(file_path), None)
            self.address_bar.set_text(file_uri)
            self.web_view.load_uri(file_uri)
            return

        if self.is_url(text):
            url = text
            if not url.startswith(("http://", "https://", "file://")):
                url = "https://" + url
                self.address_bar.set_text(url)
            self.web_view.load_uri(url)
            return

        search_url = current_settings['searchen'] + text.replace(" ", "+")
        self.address_bar.set_text(search_url)
        self.web_view.load_uri(search_url)

    def on_address_key_press(self, widget, event):
        '''Handle Ctrl+Enter in address bar to open in new tab.'''
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if event.state & Gdk.ModifierType.CONTROL_MASK:
                self.load_page_in_new_tab()
                return True
        return False

    def load_page_in_new_tab(self):
        '''Open the address bar content in a new tab.'''
        url = self.address_bar.get_text().strip()
        if self.is_url(url):
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            target_uri = url
        else:
            target_uri = current_settings['searchen'] + url.replace(" ", "+")

        if self.browser:
            self.browser.open_new_tab(None, target_uri)

    def find_text(self, widget):
        '''Search for text in page.'''
        search_text = self.find_entry.get_text()
        if search_text:
            self.find_controller.count_matches(search_text, wk.FindOptions.CASE_INSENSITIVE, 1000)
            self.find_controller.search(search_text, wk.FindOptions.CASE_INSENSITIVE, 1000)

    def find_text_next(self, widget):
        self.find_controller.search_next()

    def find_text_prev(self, widget):
        self.find_controller.search_previous()

    def displayuri(self, d, hittestresult, u):
        '''Update status bar with hovered link.'''
        if self.browser:
            if hittestresult.context_is_link():
                link = hittestresult.get_link_uri()
                self.browser.set_status(link)
            else:
                self.browser.set_status("")

    def on_button_press(self, widget, event):
        '''Middle click opens link in new tab.'''
        if event.button == 2:
            hit = self.web_view.get_hit_test_result(event)
            if hit and hit.context_is_link():
                uri = hit.get_link_uri()
                if self.browser:
                    self.browser.open_new_tab(None, uri)
                return True
        return False

    def on_decide_policy(self, webview, decision, decision_type):
        '''Handle navigation policy decisions: Ctrl+click, popups, and ad blocking.'''
        global blockcount

        # Only handle navigation decisions
        if decision_type not in (wk.PolicyDecisionType.NAVIGATION_ACTION,
                                 wk.PolicyDecisionType.NEW_WINDOW_ACTION):
            decision.use()
            return

        nav = decision.get_navigation_action()
        request = nav.get_request()
        uri = request.get_uri()

        # Ctrl+click or new window action: open in new tab and cancel original
        ctrl_pressed = False
        try:
            ctrl_pressed = bool(nav.get_modifiers() & Gdk.ModifierType.CONTROL_MASK)
        except Exception:
            pass
        if decision_type == wk.PolicyDecisionType.NEW_WINDOW_ACTION or ctrl_pressed:
            if self.browser:
                self.browser.open_new_tab(None, uri)
            decision.ignore()
            return

        # Ad blocking check
        if blocker_on:
            parsed = urlparse(uri)
            host = parsed.hostname or ""
            haystack = (host + " " + uri).lower()
            for kw in BLOCK_SUBSTRINGS:
                if kw in haystack:
                    decision.ignore()
                    blockcount += 1
                    self.browser.set_status(str(blockcount) + " ads blocked")
                    return

        # Allow the navigation
        decision.use()

    # ------------------- Printing -------------------
    def on_print_clicked(self):
        print_op = wk.PrintOperation.new(self.web_view)
        print_op.connect('finished', lambda op: print("Print finished"))
        result = print_op.run_dialog()
        if result == wk.PrintOperationResult.ERROR:
            print("Print error occurred")
        elif result == wk.PrintOperationResult.CANCELLED:
            print("Print cancelled")
        else:
            print("Print applied")

    def on_print_page(self, action, parameter):
        self.do_print()

    def do_print(self):
        print("Printing...")
        self.on_print_clicked()

    # def on_context_menu(self, web_view, context_menu, hit_test_result, event):
    #     '''Add a print item to the context menu.'''
    #     item = wk.ContextMenuItem.new_from_gaction(
    #         self.print_action,
    #         "Print Page",
    #         None
    #     )
    #     context_menu.append(item)
    #     return False

    def on_context_menu(self, web_view, context_menu, hit_test_result, event):
        # Replace "Open Link in New Window" with a custom action that opens in a new tab
        items = context_menu.get_items()
        for item in list(items):  # work on a copy
            if item.get_action() == wk.ContextMenuAction.OPEN_LINK_IN_NEW_WINDOW:
                context_menu.remove(item)
                if hit_test_result and hit_test_result.context_is_link():
                    link_uri = hit_test_result.get_link_uri()
                    action = Gio.SimpleAction.new("open-link-new-tab", None)
                    action.connect(
                        "activate",
                        lambda a, p, uri=link_uri: self.browser.open_new_tab(None, uri)
                    )
                    new_item = wk.ContextMenuItem.new_from_gaction(
                        action,
                        "Open Link in New Tab",
                        None
                    )
                    context_menu.append(new_item)
                # else: no link, so simply remove the item
        # Add print item as before
        item = wk.ContextMenuItem.new_from_gaction(
            self.print_action,
            "Print Page",
            None
        )
        context_menu.append(item)
        return False

# ------------------------------ Browser ------------------------------
class Browser(Gtk.Window):

    def __init__(self, *args, **kwargs):
        super(Browser, self).__init__(*args, **kwargs)

        self.set_title("Acme Browser")
        icon_path = os.path.join(script_dir, "images/acme.png")
        if os.path.exists(icon_path):
            self.set_icon_from_file(icon_path)
        self.set_default_size(600, 600)
        self.connect("destroy", Gtk.main_quit)
        self.connect("delete-event", self.on_delete_event)
        self.connect("realize", lambda w: self.on_startup())

        # Download setup
        self.download_dir = Path.home() / "Downloads"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        # 1. Initialize your WebView / components if needed, or get default context
        self.web_context = wk.WebContext.get_default()
        # 2. Connect the signal successfully
        self.web_context.connect("download-started", self.on_download_started)

        # Set up cookie manager
        self.cookie_manager = self.web_context.get_cookie_manager()
        self.cookie_manager.set_persistent_storage(
            os.path.join(script_dir, "cookies.sqlite"),
            wk.CookiePersistentStorage.SQLITE
        )
        self.cookie_table = None  # will be detected later

        # Toolbar buttons
        self.tool_bar = Gtk.HBox()
        self.button_settings = Gtk.ToolButton()
        self.button_settings.set_icon_name("emblem-system")
        self.button_settings.set_tooltip_text("User Settings")
        self.button_reset_cookies = Gtk.ToolButton()
        self.button_reset_cookies.set_icon_name("emblem-synchronizing-symbolic")
        self.button_reset_cookies.set_tooltip_text("Reset to Good Cookies")
        self.button_history_all = Gtk.ToolButton()
        self.button_history_all.set_icon_name("edit-clear-symbolic")
        self.button_history_all.set_tooltip_text("Clear all history")
        self.button_history = Gtk.ToolButton()
        self.button_history.set_icon_name("document-open-recent-symbolic")
        self.button_history.set_tooltip_text("View History (Ctrl+H)")
        self.button_cookies = Gtk.ToolButton()
        self.button_cookies.set_icon_name("emblem-system-symbolic")
        self.button_cookies.set_tooltip_text("Cookie Manager")
        self.button_devtools = Gtk.ToolButton()
        self.button_devtools.set_icon_name("applications-utilities-symbolic")
        self.button_devtools.set_tooltip_text("Developer Tools")
        self.button_blocker = Gtk.ToolButton()
        self.button_blocker.set_icon_name("security-high-symbolic")
        self.button_blocker.set_tooltip_text("Toggle Pop-up Ad Blocking")
        self.button_bookmarks = Gtk.ToolButton()
        self.button_bookmarks.set_icon_name("user-bookmarks")
        self.button_bookmarks.set_tooltip_text("Open Bookmarks")
        self.button_clear_cache = Gtk.ToolButton()
        self.button_clear_cache.set_icon_name("edit-delete")
        self.button_clear_cache.set_tooltip_text("Clear All Cache")


        # Connect signals
        self.button_reset_cookies.connect("clicked", self.on_reset_cookies)
        self.button_history_all.connect("clicked", self.on_history_all)
        self.button_settings.connect("clicked", self.open_settings_dialog)
        self.button_cookies.connect("clicked", self.get_all_cookies)
        self.button_devtools.connect("clicked", self.on_devtools_clicked)
        self.button_history.connect("clicked", self.open_persist_history_dialog)
        self.button_blocker.connect("clicked", self.toggle_blocker)
        self.button_bookmarks.connect("clicked", self.open_persist_bookmarks_dialog)
        self.button_clear_cache.connect("clicked", self.clear_cache)

        # Pack toolbar
        self.tool_bar.pack_start(self.button_settings, False, False, 0)
        self.tool_bar.pack_start(self.button_devtools, False, False, 0)
        self.tool_bar.pack_start(self.button_blocker, False, False, 0)
        self.tool_bar.pack_start(self.button_clear_cache, False, False, 0)
        self.tool_bar.pack_start(self.button_reset_cookies, False, False, 0)
        self.tool_bar.pack_start(self.button_history_all, False, False, 0)
        self.tool_bar.pack_start(self.button_cookies, False, False, 0)
        self.tool_bar.pack_start(self.button_history, False, False, 0)
        self.tool_bar.pack_start(self.button_bookmarks, False, False, 0)

        # Status label
        self.status_label = Gtk.Label(label="")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_hexpand(True)
        self.status_label.set_ellipsize(Pango.EllipsizeMode.END)

        # Notebook for tabs
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        # self.notebook.set_tab_reorderable(True)

        self.tabs = []  # list of (BrowserTab, Gtk.Label)
        initial_tab = self.create_tab()
        label = Gtk.Label(label="New Tab")
        self.tabs.append((initial_tab, label))
        self.notebook.insert_page(initial_tab, label, 0)

        self.notebook.connect("switch-page", self.tab_changed)

        # Layout
        self.vbox_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.hbox_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.hbox_top.pack_start(self.tool_bar, True, True, 0)
        self.hbox_top.pack_end(self.status_label, False, False, 4)

        self.vbox_container.pack_start(self.notebook, True, True, 0)
        self.vbox_container.pack_end(self.hbox_top, False, False, 0)
        self.add(self.vbox_container)

        self.connect("key-press-event", self.on_key_press)

        self.show_all()
        self.set_can_focus(True)
        self.grab_focus()

        GLib.idle_add(self.show_startup_message)

    ### trigger the cursor carrot
    def show_startup_message(self):
        ''' Sole purpose is to trigger the cursor carrat '''
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            text="Welcome to \"Acme\" Browser\n\nRight-Click for Downloads"
        )
        dialog.set_modal(False)
        dialog.show_all()

        def close_dialog():
            if dialog.get_visible():
                dialog.destroy()
            return False  # stop the timeout

        GLib.timeout_add_seconds(2, close_dialog)
        return False  # stop the idle callback from repeating
    ###

    def on_startup(self):
        '''Run after window is realized.'''
        current_page = self.notebook.get_current_page()
        if 0 <= current_page < len(self.tabs):
            self.tabs[current_page][0].find_box.hide()
        print("WebKit:", wk.get_major_version(), wk.get_minor_version(), wk.get_micro_version())


    # Download stuff

    def on_download_started(self, context, download):
        print("Download started")

        download.connect("decide-destination", self.on_download_decide_destination)
        download.connect("created-destination", self.on_download_created_destination)
        download.connect("finished", self.on_download_finished)
        download.connect("failed", self.on_download_failed)
        download.connect("notify::status", self.on_download_status_changed)
        download.connect("notify::estimated-progress",
                         self.on_download_progress)

        self.set_status("Download started")

    def on_download_decide_destination(self, download, suggested_filename):
        """
        Choose the destination before the download begins.
        Return True to allow the download.
        """
        filename = suggested_filename or "download"

        # Prevent path traversal and accidental directory names
        filename = os.path.basename(filename)

        destination = self.download_dir / filename

        # Avoid overwriting an existing file
        stem = destination.stem
        suffix = destination.suffix
        counter = 1

        while destination.exists():
            destination = self.download_dir / f"{stem} ({counter}){suffix}"
            counter += 1

        uri = GLib.filename_to_uri(str(destination), None)
        download.set_destination(uri)

        print("Download destination:", destination)
        self.set_status(f"Downloading {destination.name}")

        return True


    def on_download_created_destination(self, download, destination):
        print("Created download destination:", destination)


    def on_download_progress(self, download, param=None):
        progress = download.get_estimated_progress()
        percent = int(progress * 100)

        self.set_status(f"Downloading... {percent}%")
        # print(f"Download progress: {percent}%")


    def on_download_status_changed(self, download, param=None):
        status = download.get_status()
        print("Download status:", status)


    def on_download_finished(self, download):
        """
        This means WebKit completed the download.
        Verify the file on disk as an additional check.
        """
        destination_uri = download.get_destination()
        path = None

        if destination_uri:
            path = GLib.filename_from_uri(destination_uri)[0]

        if path and os.path.isfile(path):
            size = os.path.getsize(path)

            if size > 0:
                print(f"Download successful: {path} ({size} bytes)")
                self.set_status(f"Download complete: {os.path.basename(path)}")
            else:
                print("Download finished, but the file is empty:", path)
                self.set_status("Download completed but the file is empty")
        else:
            print("Download reported finished, but the file was not found")
            self.set_status("Download failed: output file not found")


    def on_download_failed(self, download, error):
        print("Download failed:", error.message)
        print("Error domain:", error.domain)
        print("Error code:", error.code)

        destination_uri = download.get_destination()
        if destination_uri:
            try:
                path = GLib.filename_from_uri(destination_uri)[0]
                print("Failed destination:", path)
            except Exception:
                pass

        self.set_status(f"Download failed: {error.message}")

    # End Download stuff



    def clear_cache(self, e=None):
        ''' Clear Cache Button removed browser cache directories '''
        r = self.show_yesno_dialog("Confirm", "Clear ALL cache?")
        if r is False:
            return

        cache_root = Path.home() / ".cache" / "acme.pyc"
        if cache_root.exists():
            shutil.rmtree(cache_root)
        else:
            print(cache_root)
            return

        cache_root = Path.home() / ".cache" / "acme.py"
        if cache_root.exists():
            shutil.rmtree(cache_root)
        else:
            print(cache_root)
            return

        self.show_ok_dialog("Confirmed", "Cache was removed.")



    def toggle_blocker(self, e=None):
        global blocker_on
        if blocker_on == 1:
            blocker_on = 0
            self.set_status("Ad Blocker turned OFF")
            self.show_ok_dialog("Confirmed", "Ad Blocker turned Off")
        else:
            blocker_on = 1
            self.set_status("Ad Blocker turned ON")
            self.show_ok_dialog("Confirmed", "Ad Blocker turned ON")

    def show_yesno_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=title,
        )
        dialog.format_secondary_text(message)
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES

    def _get_cookie_table(self):
        '''Determine which table holds cookies in the SQLite database.'''
        cookie_db = os.path.join(script_dir, "cookies.sqlite")
        candidate_tables = ["cookies", "soup_cookies", "webkit_cookies", "moz_cookies"]
        try:
            if not os.path.exists(cookie_db):
                return "cookies"  # default guess
            conn = sqlite3.connect(cookie_db)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            for table in candidate_tables:
                if table in tables:
                    self.cookie_table = table
                    conn.close()
                    return table
            conn.close()
        except Exception as e:
            print(f"Error detecting cookie table: {e}")
        return "cookies"  # fallback

    def on_reset_cookies(self, e=None):
        '''Remove all but good cookies.'''
        if not self.show_yesno_dialog("Confirm", "Remove all but good cookies now?"):
            return

        goodcookie_path = os.path.join(script_dir, "goodcookie.txt")
        domains = set()
        if os.path.exists(goodcookie_path):
            with open(goodcookie_path, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    domains.add(s)

        if not domains:
            self.show_ok_dialog("Warning", "No good cookie domains found. Operation cancelled.")
            return

        table = self._get_cookie_table()
        placeholders = ",".join(["?"] * len(domains))
        sql = f"DELETE FROM {table} WHERE host NOT IN ({placeholders})"

        cookie_db = os.path.join(script_dir, "cookies.sqlite")
        try:
            conn = sqlite3.connect(cookie_db)
            cur = conn.cursor()
            cur.execute(sql, tuple(domains))
            conn.commit()
            print(f"Deleted {cur.rowcount} rows from {table}.")
            conn.close()
            self.set_status("* cookies reset to only goodcookies *")
            self.show_ok_dialog("Confirmed", "Cookies have been reset.")
        except Exception as e:
            print(f"Error resetting cookies: {e}")
            self.show_ok_dialog("Error", f"Could not reset cookies: {e}")

    def on_history_all(self, e=None):
        '''Clear all browsing history.'''
        if not self.show_yesno_dialog("Confirm", "Are you sure you want to clear history?"):
            return
        history_path = os.path.join(script_dir, "browser_history.txt")
        with open(history_path, "w", encoding="utf-8") as f:
            f.write("history\n")
        self.set_status("* History Cleared *")
        self.show_ok_dialog("Confirmed", "History Cleared")

    def set_status(self, text):
        self.status_label.set_text(text or "")

    def get_current_tab(self):
        page_num = self.notebook.get_current_page()
        if page_num < 0:
            return None
        return self.notebook.get_nth_page(page_num)

    def open_devtools_for_current_tab(self):
        tab = self.get_current_tab()
        if tab:
            tab.open_devtools()

    def on_devtools_clicked(self, widget):
        self.open_devtools_for_current_tab()

    def open_in_browser(self, url):
        self.open_new_tab(None, url)

    def open_persist_history_dialog(self, e=None):
        history_path = os.path.join(script_dir, "browser_history.txt")
        win = DialogWindow(history_path, "History", on_select_url=self.open_in_browser)
        win.set_keep_above(True)
        win.show_all()

    def open_persist_bookmarks_dialog(self, e=None):
        bookmarks_path = os.path.join(script_dir, current_settings['bkmpath'])
        win = DialogWindow(bookmarks_path, "Bookmarks", on_select_url=self.open_in_browser)
        win.set_keep_above(True)
        win.show_all()

    def on_key_press(self, widget, event):
        '''Keyboard shortcuts.'''
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        shift = event.state & Gdk.ModifierType.SHIFT_MASK

        if ctrl and shift and event.keyval == Gdk.KEY_I:
            self.open_devtools_for_current_tab()
            return True

        if event.keyval == Gdk.KEY_Escape:
            # If find bar is open, close it first
            current_page = self.notebook.get_current_page()
            if 0 <= current_page < len(self.tabs):
                if self.tabs[current_page][0].find_box.get_visible():
                    self.tabs[current_page][0].find_box.hide()
                    return True
            self.close_current_tab(None)
            return True

        if ctrl and event.keyval == Gdk.KEY_q:
            self.adjust_history_file()
            Gtk.main_quit()
            return True

        if ctrl and event.keyval == Gdk.KEY_f:
            self.raise_find_dialog(None)
            return True

        if ctrl and shift and event.keyval == Gdk.KEY_H:
            self.open_persist_history_dialog()
            return True

        if event.state & Gdk.ModifierType.MOD1_MASK:  # Alt-1,2,3,4
            keyname = Gdk.keyval_name(event.keyval)
            if keyname in current_settings:
                self.insert_text(current_settings[keyname])
                return True

        return False

    def tab_changed(self, notebook, current_page, index):
        if index < 0 or index >= len(self.tabs):
            return
        tab = self.tabs[index][0]
        title = tab.web_view.get_title()
        if title:
            self.set_title("Acme Browser - " + title)
        else:
            self.set_title("Acme Browser")
        tab.sync_address_bar()

    def title_changed(self, web_view, param):
        '''Update tab label when page title changes.'''
        current_page = self.notebook.get_current_page()
        for i, (tab, label) in enumerate(self.tabs):
            if tab.web_view is web_view:
                title = tab.web_view.get_title() or "New Tab"
                label.set_text(title[:27] + "..." if len(title) > 30 else title)
                if i == current_page:
                    self.tab_changed(None, None, i)
                break

    def create_tab(self):
        tab = BrowserTab(browser=self)
        tab.web_view.connect("notify::title", self.title_changed)
        return tab

    def close_current_tab(self, widget):
        if self.notebook.get_n_pages() <= 1:
            return
        page = self.notebook.get_current_page()
        if page < 0:
            return
        current_tab = self.tabs.pop(page)
        self.notebook.remove(current_tab[0])

    def open_new_tab(self, widget, uri=None):
        current_page = self.notebook.get_current_page()
        page_tuple = (self.create_tab(), Gtk.Label(label="New Tab"))
        self.tabs.insert(current_page + 1, page_tuple)
        self.notebook.insert_page(page_tuple[0], page_tuple[1], current_page + 1)
        if current_settings['gotab'].lower() == "yes":
            self.notebook.set_current_page(current_page + 1)
        self.notebook.set_tab_reorderable(page_tuple[0], True)
        if uri:
            page_tuple[0].web_view.load_uri(uri)

        return page_tuple[0]

    def save_active_tab_info(self, e=None):
        '''Append current page as a bookmark.'''
        tab = self.get_current_tab()
        if not tab:
            return
        bk_path = os.path.join(script_dir, current_settings['bkmpath'])
        with open(bk_path, "a", encoding="utf-8") as fout:
            fout.write(tab.web_view.get_title() + " <=> " + tab.web_view.get_uri() + "\n")
        self.show_ok_dialog("Confirm", f"Bookmark appended to {current_settings['bkmpath']}")

    def raise_find_dialog(self, widget):
        current_page = self.notebook.get_current_page()
        if 0 <= current_page < len(self.tabs):
            self.tabs[current_page][0].find_box.show_all()
            self.tabs[current_page][0].find_entry.grab_focus()

    def goto_home(self, widget):
        current_page = self.notebook.get_current_page()
        if 0 <= current_page < len(self.tabs):
            self.tabs[current_page][0].web_view.load_uri(current_settings['homepage'])

    def on_print_clicked(self, button):
        current_page = self.notebook.get_current_page()
        if 0 <= current_page < len(self.tabs):
            self.tabs[current_page][0].on_print_clicked()

    def get_all_cookies(self, widget):
        '''Read cookies from the SQLite database and display them.'''
        cookie_db = os.path.join(script_dir, "cookies.sqlite")
        cookies_data = []
        table_used = None

        try:
            if os.path.exists(cookie_db):
                conn = sqlite3.connect(cookie_db)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [t[0] for t in cursor.fetchall()]
                print(f"Tables in database: {tables}")

                table_configs = [
                    ("cookies", "name, value, domain, path"),
                    ("soup_cookies", "name, value, domain, path"),
                    ("webkit_cookies", "name, value, domain, path"),
                    ("moz_cookies", "name, value, host, path")
                ]

                for table_name, columns in table_configs:
                    if table_name in tables:
                        try:
                            cursor.execute(f"SELECT {columns} FROM {table_name}")
                            cookies_data = cursor.fetchall()
                            if cookies_data:
                                print(f"Found {len(cookies_data)} cookies in table '{table_name}'")
                                table_used = table_name
                                self.cookie_table = table_name
                                break
                        except sqlite3.OperationalError:
                            continue
                conn.close()
            else:
                print(f"Cookie database not found at {cookie_db}")
        except Exception as e:
            print(f"Error reading cookie database: {e}")

        cookies_list = []
        for row in cookies_data:
            if len(row) >= 4:
                domain = row[2] if row[2] else row[0]
                cookies_list.append((domain, row[0], row[3], row[1]))

        self.display_cookies(cookies_list)

    def display_cookies(self, cookies):
        dialog = Gtk.Dialog(title="Cookies", parent=self)
        dialog.set_default_size(600, 400)

        scrolled = Gtk.ScrolledWindow()
        liststore = Gtk.ListStore(str, str, str, str)
        treeview = Gtk.TreeView(model=liststore)

        selection = treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)

        for i, title in enumerate(["Domain", "Name", "Path", "Value"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            treeview.append_column(column)

        for cookie in cookies:
            liststore.append(cookie)

        scrolled.add(treeview)
        dialog.get_content_area().pack_start(scrolled, True, True, 0)

        dialog.add_button("Delete Selected", Gtk.ResponseType.REJECT)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.REJECT:
            self.delete_selected_cookies(selection, liststore)
            dialog.destroy()
            self.get_all_cookies(None)  # refresh the dialog
        else:
            dialog.destroy()

    def delete_selected_cookies(self, selection, liststore):
        '''Delete cookies selected in the cookie manager.'''
        cookie_db = os.path.join(script_dir, "cookies.sqlite")
        model, selected_rows = selection.get_selected_rows()
        if not selected_rows:
            return

        table = self._get_cookie_table()
        try:
            conn = sqlite3.connect(cookie_db)
            cursor = conn.cursor()
            for row_path in selected_rows:
                row_iter = liststore.get_iter(row_path)
                domain, name, path, value = liststore.get(row_iter, 0, 1, 2, 3)
                cursor.execute(
                    f"DELETE FROM {table} WHERE host=? AND name=? AND value=? AND path=?",
                    (domain, name, value, path)
                )
            conn.commit()
            conn.close()
            print(f"Deleted {len(selected_rows)} cookies")
        except Exception as e:
            print(f"Error deleting cookies: {e}")

    def add_cookie(self, domain, name, value, path="/"):
        '''Programmatically add a cookie (not used by UI).'''
        cookie = wk.Cookie.new(domain, name, value)
        cookie.set_path(path)
        self.cookie_manager.set_cookie(cookie, None, None, lambda *args: None)
        print(domain)

    def save_geometry(self):
        '''Save window size and position to wingeo file.'''
        width, height = self.get_size()
        x, y = self.get_position()
        wingeo_path = os.path.join(script_dir, "wingeo")
        with open(wingeo_path, "w") as fout:
            fout.write(str(width) + "\n")
            fout.write(str(height) + "\n")
            fout.write(str(x) + "\n")
            fout.write(str(y) + "\n")

    def adjust_history_file(self):
        '''Trim browser history to the set limit, removing duplicates.'''
        N = int(current_settings['histlimit'])
        history_path = os.path.join(script_dir, "browser_history.txt")
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            return

        # Deduplicate while preserving order, keeping the last occurrence of each line
        unique_lines = list(dict.fromkeys(reversed(lines)))
        unique_lines.reverse()

        if len(unique_lines) > N:
            # Keep only the last N lines
            unique_lines = unique_lines[-N:]
            with open(history_path, "w", encoding="utf-8") as fout:
                fout.writelines(unique_lines)
            print(f"Trimmed history to {N} entries")

    def on_delete_event(self, widget, event):
        '''Called when user closes window. Returns False to allow close.'''
        self.save_geometry()
        print(f"blocked {blockcount} ads...")
        self.adjust_history_file()
        return False

    def on_destroy(self, event):
        print("EOJ")
        return False

    def on_configure(self, widget, event):
        # Optional: handle window configure (not used)
        pass

    def open_settings_dialog(self, e=None):
        '''Open settings dialog and apply changes.'''
        global current_settings
        dialog = SettingsDialog(self, current_settings)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            new_settings = dialog.get_settings()

            # Convert numeric fields
            for key in ("histlimit", "defsize", "monsize"):
                try:
                    new_settings[key] = int(new_settings[key])
                except (ValueError, TypeError):
                    new_settings[key] = {
                        "histlimit": DEFAULT_HISTLIMIT,
                        "defsize": DEFAULT_FONT_SIZE,
                        "monsize": DEFAULT_MONO_SIZE
                    }[key]

            # Normalize gotab
            new_settings["gotab"] = "yes" if new_settings["gotab"].lower() in ("yes", "true", "1", "on") else "no"

            save_settings_to_file(new_settings)
            current_settings = new_settings

        dialog.destroy()

    def insert_text(self, text):
        js = f'''
        (function(text) {{
            function setNativeValue(el, value) {{
                const proto = Object.getPrototypeOf(el);
                const valueSetter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
                if (valueSetter) {{
                    valueSetter.call(el, value);
                }} else {{
                    el.value = value;
                }}
            }}

            const el = document.activeElement;
            if (!el) return;

            const tag = el.tagName;
            if (tag !== "INPUT" && tag !== "TEXTAREA") return;

            const start = el.selectionStart;
            const end = el.selectionEnd;
            const current = el.value || "";

            if (start != null && end != null) {{
                const newValue = current.slice(0, start) + text + current.slice(end);
                setNativeValue(el, newValue);
                el.selectionStart = el.selectionEnd = start + text.length;
            }} else {{
                setNativeValue(el, current + text);
            }}

            el.dispatchEvent(new Event("input", {{ bubbles: true }}));
            el.dispatchEvent(new Event("change", {{ bubbles: true }}));
        }})({text!r});
        '''
        current_page = self.notebook.get_current_page()
        if 0 <= current_page < len(self.tabs):
            self.tabs[current_page][0].web_view.evaluate_javascript(js, -1, None, None, None, None, None)

    def show_ok_dialog(self, title, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

# ------------------------------ DialogWindow ------------------------------
class DialogWindow(Gtk.Window):
    def __init__(self, input_file, win_title, on_select_url=None):
        super().__init__(title=win_title)
        self.set_default_size(600, 500)

        self.input_file = input_file
        self.on_select_url = on_select_url

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        self.store = Gtk.ListStore(str)
        self.view = Gtk.TreeView(model=self.store)
        self.view.set_margin_bottom(12)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("URL", renderer, text=0)
        self.view.append_column(column)

        self.view.connect("row-activated", self.on_row_activated)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.add(self.view)
        vbox.pack_start(scrolled, True, True, 0)

        button_box = Gtk.Box(spacing=6)
        vbox.pack_start(button_box, False, False, 0)

        self.open_button = Gtk.Button(label="Open Selected")
        self.open_button.connect("clicked", self.on_open_clicked)
        button_box.pack_start(self.open_button, False, False, 0)

        self.close_button = Gtk.Button(label="Close")
        self.close_button.connect("clicked", lambda btn: self.destroy())
        button_box.pack_start(self.close_button, False, False, 0)

        self.load_input_file()

    def load_input_file(self):
        self.store.clear()
        if not os.path.exists(self.input_file):
            return

        seen = set()
        with open(self.input_file, "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if not url:
                    continue
                if url in seen:
                    continue
                seen.add(url)
                self.store.append([url])

        model = self.view.get_model()
        if model and len(model) > 0:
            last_index = len(model) - 1
            path = Gtk.TreePath.new_from_string(str(last_index))
            self.view.scroll_to_cell(path, None, True, 1.0, 0.0)

    def get_selected_url(self):
        selection = self.view.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            return model[treeiter][0]
        return None

    def _extract_url(self, line):
        '''Extract actual URL from a bookmark line "title <=> url".'''
        if " <=> " in line:
            return line.split(" <=> ", 1)[1]
        return line

    def on_open_clicked(self, button):
        url = self.get_selected_url()
        if url and self.on_select_url:
            url = self._extract_url(url)
            self.on_select_url(url)

    def on_row_activated(self, treeview, path, column):
        url = self.get_selected_url()
        if url and self.on_select_url:
            url = self._extract_url(url)
            self.on_select_url(url)

    def on_reload_clicked(self, button):
        '''Not used.'''
        pass

# ------------------------------ SettingsDialog ------------------------------
class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent, current_settings):
        super().__init__(
            title="Browser Settings",
            transient_for=parent,
            modal=True
        )
        self.set_border_width(10)
        self.current_settings = current_settings
        self.entries = {}

        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)

        content_area = self.get_content_area()
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        content_area.add(scroll)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        scroll.add(grid)

        fields = [
            ("homepage", "Homepage"),
            ("searchen", "Search Engine"),
            ("histlimit", "History Limit"),
            ("gotab", "Open in New Tab"),
            ("deffont", "Default Font"),
            ("defsize", "Default Font Size"),
            ("monfont", "Monospace Font"),
            ("monsize", "Monospace Font Size"),
            ("bkmpath", "Bookmarks Path"),
            ("1", "Alt-1 Snippet"),
            ("2", "Alt-2 Snippet"),
            ("3", "Alt-3 Snippet"),
            ("4", "Alt-4 Snippet"),
        ]

        for row, (key, label_text) in enumerate(fields):
            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.START)
            label.set_size_request(160, -1)

            entry = Gtk.Entry()
            entry.set_text(str(current_settings.get(key, "")))
            entry.set_hexpand(True)

            grid.attach(label, 0, row, 1, 1)
            grid.attach(entry, 1, row, 1, 1)
            self.entries[key] = entry

        self.set_default_size(600, 300)
        self.show_all()

    def get_settings(self):
        settings = {}
        for key, entry in self.entries.items():
            settings[key] = entry.get_text().strip()
        return settings

# ------------------------------ Utility functions ------------------------------
def save_settings_to_file(settings, filename="neo.dat"):
    lines = [
        settings["homepage"],
        settings["searchen"],
        str(settings["histlimit"]),
        settings["gotab"],
        settings["deffont"],
        str(settings["defsize"]),
        settings["monfont"],
        str(settings["monsize"]),
        settings["bkmpath"],
        settings["1"],
        settings["2"],
        settings["3"],
        settings["4"],
    ]
    with open(os.path.join(script_dir, filename), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

# ------------------------------ Main entry ------------------------------
if __name__ == "__main__":
    # Initialize GTK (optional, Window creation will do it)
    # Gtk.init(sys.argv)

    # Handle command-line URL argument
    start_url = None
    if len(sys.argv) > 1:
        start_url = sys.argv[1]
        if not start_url.startswith(("http://", "https://", "file://")):
            start_url = "https://" + start_url

    browser = Browser()

    # Apply saved geometry if available
    if initial_geometry["width"] > 0 and initial_geometry["height"] > 0:
        browser.resize(initial_geometry["width"], initial_geometry["height"])
    if initial_geometry["x"] > 0 or initial_geometry["y"] > 0:
        browser.move(initial_geometry["x"], initial_geometry["y"])

    # Enable crash logging
    log_path = os.path.join(script_dir, "crash.log")
    log = open(log_path, "w")
    faulthandler.enable(file=log)

    Gtk.main()

