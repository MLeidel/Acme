#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
# Safe environment flags to prevent GTK driver crashes
os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
os.environ["WEBKIT_DISABLE_DMABUF_RENDERER"] = "1"
# # Disable JSC JIT compiler (prevents WebAssembly segfaults on heavy crypto sites)
os.environ["JSC_useJIT"] = "false"  # leaving off for now
# os.environ["WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS"] = "1"

import sys
import faulthandler
from pathlib import Path
import shutil
import gi
import sqlite3
from urllib.parse import urlparse
import warnings
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message="WebKit2.NavigationPolicyDecision.get_request is deprecated"
)  # in on_decide_policy for add blocking


# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

gi.require_version('Gdk', '3.0')
gi.require_version("Gtk", "3.0")        # GUI toolkit
gi.require_version("WebKit2", "4.1")    # Web content engine
from gi.repository import Gtk, WebKit2 as wk, Gdk, Pango, Gio, GLib  # WebKitGTK version: 2.52.3

# for neo.dat and wingeo
glink = ""
gwidth = 0
gheight = 0
gx = 0
gy = 0
homepage = ""
searchen = ""
histlimit = ""
gotab = ""
deffont = ""
defsize = 0
monfont = ""
monsize = 0
bkmpath = ""
alt1 = ""
alt2 = ""
alt3 =  ""
alt4 =  ""

blocker_on = 1  # mode switch for Ad blocker start ON
blockcount = 0  # for addblocking

# class #
class BrowserTab(Gtk.VBox):
    ''' Re-sequenced Init 082226 '''

    def __init__(self, browser, *args, **kwargs):
        super(BrowserTab, self).__init__(*args, **kwargs)

        self.browser = browser

        # # # # injecting css
        self.user_content = wk.UserContentManager()
        css = '''
        ::selection {
            background-color: #ff007f; /* Custom background color for selections */
            color: #ffffff;            /* Text color */
        }
        '''
        stylesheet = wk.UserStyleSheet.new(
            css,
            wk.UserContentInjectedFrames.ALL_FRAMES,
            wk.UserStyleLevel.USER,
            None,   # whitelist
            None    # blacklist
        )

        self.user_content.add_style_sheet(stylesheet)

        self.web_view = wk.WebView.new_with_user_content_manager(self.user_content)  ## CREATE web_view!

        context = wk.WebContext.get_default()

        settings = self.web_view.get_settings()  # now the settings

        settings.set_user_agent(
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
        )

        settings.set_hardware_acceleration_policy(
            wk.HardwareAccelerationPolicy.NEVER
        )
        settings.set_enable_javascript(True)
        settings.set_enable_html5_local_storage(True)
        settings.set_enable_developer_extras(True)
        settings.set_javascript_can_open_windows_automatically(True)

        settings.set_property("default-font-family", current_settings["deffont"])
        settings.set_property("default-font-size", int(current_settings["defsize"]))
        settings.set_property("monospace-font-family", current_settings["monfont"])
        settings.set_property("default-monospace-font-size", int(current_settings["monsize"]))

        settings.set_allow_universal_access_from_file_urls(True)
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_enable_write_console_messages_to_stdout(False)

        # # # # #

        self.web_view.connect("decide-policy", self.on_decide_policy)
        self.web_view.connect("mouse-target-changed", self.displayuri)
        self.web_view.connect("button-press-event", self.on_button_press)
        self.web_view.connect("load-changed", self.on_load_changed)
        self.web_view.connect("create", self.on_create)

        # needed for printing from context menu
        self.print_action = Gio.SimpleAction.new("print-page", None)
        self.print_action.connect("activate", self.on_print_page)
        self.web_view.connect("context-menu", self.on_context_menu)

        # Inspector setup
        inspector = self.web_view.get_inspector()

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
        self.button_bookmarx.set_icon_name("bookmark-new-symbolic")    # BOOKMARKS
        self.button_bookmarx.set_tooltip_text("Bookmarks")            # BOOKMARKS
        self.button_bookmarx.connect("clicked", self.browser.save_active_tab_info)    # BOOKMARKS

        self.button_find = Gtk.ToolButton(stock_id=Gtk.STOCK_FIND)   # FIND BUTTON
        self.button_find.set_tooltip_text("Find Ctrl+F")            # FIND BUTTON
        self.button_find.connect("clicked", self.browser.raise_find_dialog)      # FIND BUTTON

        self.button_printer = Gtk.ToolButton(stock_id=Gtk.STOCK_PRINT)
        self.button_printer.set_tooltip_text("Print")
        self.button_printer.connect("clicked", self.browser.on_print_clicked)

        self.button_back.connect("clicked", lambda x: self.web_view.go_back())
        self.button_close_tab.connect("clicked", browser.close_current_tab)
        self.button_forward.connect("clicked", lambda x: self.web_view.go_forward())
        self.button_refresh.connect("clicked", lambda x: self.web_view.reload())
        self.button_home.connect("clicked", lambda x: self.web_view.load_uri(current_settings['homepage']))
        self.button_new_tab.connect("clicked", browser.open_new_tab)

        url_box = Gtk.HBox()
        url_box.pack_start(self.button_back, False, False, 0)
        url_box.pack_start(self.button_close_tab, False, False, 0)
        url_box.pack_start(self.button_forward, False, False, 0)
        url_box.pack_start(self.button_refresh, False, False, 0)
        url_box.pack_start(self.button_home, False, False, 0)
        url_box.pack_start(self.button_new_tab, False, False, 0)
        url_box.pack_start(self.address_bar, True, True, 0)

        url_box.pack_start(self.button_bookmarx, False, False, 0)    # BOOKMARKS
        url_box.pack_start(self.button_find, False, False, 0)  # FIND BUTTON
        url_box.pack_start(self.button_printer, False, False, 0)

        self.pack_start(url_box, False, False, 0)   # move here

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(self.web_view)

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

        # self.pack_start(url_box, False, False, 0)
        self.pack_start(find_box, False, False, 0)
        self.pack_start(scrolled_window, True, True, 0)


        self.show_all()
        # breakpoint()
        if start_url is not None:
            self.web_view.load_uri(start_url)
        else:
            self.web_view.load_uri(current_settings["homepage"])

        self.find_box.set_visible(False)
        GLib.idle_add(self.web_view.grab_focus)


    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


    def open_devtools(self):
        ''' Shift-Ctrl-I opens Developer Tools
        see open_devtools_for_current_tab in Browser Class '''
        try:
            inspector = self.web_view.get_inspector()
            inspector.show()
        except:
            print("error")


    def on_create(self, webview, navigation_action):
        '''
        Make JS window.open() work.

        We return a WebKit "window" (a related WebView) so the page gets a valid
        window object. We also decide whether to open it in a new GTK tab.
        '''
        req = None
        uri = None

        # Common case: window.open("https://...") gives us a NEW_WINDOW_ACTION
        # and navigation_action contains the request.
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
        return

        # # Create a related popup view that shares the same session/context
        # popup_webview = wk.WebView.new_with_related_view(webview)

        # # Ensure popup can also open further windows if needed
        # # (optional but helps some sites)
        # popup_settings = popup_webview.get_settings()
        # popup_settings.set_enable_javascript(True)
        # popup_settings.set_javascript_can_open_windows_automatically(True)

        # # Put the popup WebView into a new tab (instead of a separate Gtk.Window)
        # # IMPORTANT: we must integrate the popup_webview into your existing Notebook UI.
        # self.browser.open_popup_as_tab(popup_webview, uri)

        # # Return the view so JS receives a valid window object
        # return popup_webview


    def sync_address_bar(self):
        ''' sync the address bar with URL '''
        uri = self.web_view.get_uri()
        if uri:
            self.address_bar.set_text(uri)
            # self.address_bar.select_region(0, -1)  # highlight text

    def on_load_changed(self, web_view, load_event):
        ''' sync the address bar with URL for load_changed event '''
        if load_event == wk.LoadEvent.FINISHED:
            uri = web_view.get_uri()
            if uri:
                self.address_bar.set_text(uri)
                with open(os.path.expanduser("browser_history.txt"), "a", encoding="utf-8") as f:
                    f.write(uri + "\n")


    def is_url(self, text):
        ''' determines if a string in the address bar is a URL '''
        if " " in text:
            return False
        if "." not in text:
            return False
        if text.startswith(("http://", "https://")):
            return True
        parts = text.split(".")
        return len(parts) >= 2 and len(parts[-1]) >= 2


    def load_page(self, widget, url=None):
        ''' loads the file or URL from the address bar
            or executes a search with text from the address bar '''
        if url:
            text = url
        else:
            text = self.address_bar.get_text().strip()

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
        ''' User hit Enter in the address bar with Ctrl key pressed  '''
        if event.keyval == Gdk.KEY_Return or event.keyval == Gdk.KEY_KP_Enter:
            if event.state & Gdk.ModifierType.CONTROL_MASK:
                self.load_page_in_new_tab()
                return True
        return False


    def load_page_in_new_tab(self):
        ''' User used Ctrl click to open link in a new tab '''
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
        ''' User clicked find button or clicked Ctrl-f '''
        search_text = self.find_entry.get_text()
        if search_text:
            self.find_controller.count_matches(search_text, wk.FindOptions.CASE_INSENSITIVE, 1000)
            self.find_controller.search(search_text, wk.FindOptions.CASE_INSENSITIVE, 1000)

    def find_text_next(self, widget):
        ''' helper '''
        self.find_controller.search_next()

    def find_text_prev(self, widget):
        ''' helper '''
        self.find_controller.search_previous()

    def displayuri(self, d, hittestresult, u):
        if self.browser:
            if hittestresult.context_is_link():
                link = hittestresult.get_link_uri()
                self.browser.set_status(link)
            else:
                self.browser.set_status("")

    def on_button_press(self, widget, event):
        if event.button == 2:
            hit = self.web_view.get_hit_test_result(event)
            if hit and hit.context_is_link():
                uri = hit.get_link_uri()
                if self.browser:
                    self.browser.open_new_tab(None, uri)
                return True
        return False

    def on_decide_policy(self, webview, decision, decision_type):
        global blockcount
        if decision_type in (wk.PolicyDecisionType.NAVIGATION_ACTION,
                             wk.PolicyDecisionType.NEW_WINDOW_ACTION):

            nav = decision.get_navigation_action()
            request = nav.get_request()
            uri = request.get_uri()

            ctrl_pressed = False
            try:
                ctrl_pressed = bool(nav.get_modifiers() & Gdk.ModifierType.CONTROL_MASK)
            except Exception:
                pass

            if ctrl_pressed or (decision_type == wk.PolicyDecisionType.NEW_WINDOW_ACTION):  # changed 7/22/26
                if self.browser:
                    self.browser.open_new_tab(None, uri)
                decision.ignore()
            else:
                decision.use()

        # add blocking
        if blocker_on:
            req = decision.get_request()
            uri = req.get_uri() or ""

            parsed = urlparse(uri)
            host = parsed.hostname or ""   # <-- equivalent to “host”, derived from URI

            haystack = (host + " " + uri).lower()
            for kw in BLOCK_SUBSTRINGS:
                if kw in haystack:
                    decision.ignore()  # cancel the request
                    blockcount += 1
                    self.browser.set_status(str(blockcount) + " ads blocked")
                    return

            decision.use()  # allow it


    # printing stuff - to handle button and context menu

    def on_print_clicked(self):
        print_op = wk.PrintOperation.new(self.web_view)
        print_op.connect('finished', lambda op: print("Print finished"))
        result = print_op.run_dialog()
        if result:
            print("Print error occurred")
        else:
            print("Print applied")

    def on_print_page(self, action, parameter):
        self.do_print()

    def do_print(self):
        print("Printing...")
        self.on_print_clicked()

    def on_context_menu(self, web_view, context_menu, hit_test_result, event):
        item = wk.ContextMenuItem.new_from_gaction(
            self.print_action,
            "Print Page",
            None
        )
        context_menu.append(item)
        return False


# class #
class Browser(Gtk.Window):

    def __init__(self, *args, **kwargs):
        super(Browser, self).__init__(*args, **kwargs)

        self.connect("destroy", Gtk.main_quit)

        self.set_title("Acme Browser")
        self.set_icon_from_file(os.path.join(script_dir, "images/acme.png"))
        self.set_default_size(600, 600)
        self.connect("destroy", self.on_destroy)
        self.connect("delete-event", self.on_delete_event)
        self.connect("realize", lambda w: self.on_startup())
        self.web_context = wk.WebContext.get_default()
        self.cookie_manager = self.web_context.get_cookie_manager()
        self.cookie_manager.set_persistent_storage(
            os.path.join(script_dir, "cookies.sqlite"),
            wk.CookiePersistentStorage.SQLITE
        )

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

        self.button_reset_cookies.connect("clicked", self.on_reset_cookies)
        self.button_history_all.connect("clicked", self.on_history_all)

        self.button_settings.connect("clicked", self.open_settings_dialog)
        self.button_cookies.connect("clicked", self.get_all_cookies)
        self.button_devtools.connect("clicked", self.on_devtools_clicked)
        self.button_history.connect("clicked", self.open_persist_history_dialog)
        self.button_blocker.connect("clicked", self.toggle_blocker)

        self.tool_bar.pack_start(self.button_settings, False, False, 0)
        self.tool_bar.pack_start(self.button_devtools, False, False, 0)
        self.tool_bar.pack_start(self.button_blocker, False, False, 0)
        self.tool_bar.pack_start(self.button_cookies, False, False, 0)
        self.tool_bar.pack_start(self.button_reset_cookies, False, False, 0)
        self.tool_bar.pack_start(self.button_history, False, False, 0)
        self.tool_bar.pack_start(self.button_history_all, False, False, 0)


        self.status_label = Gtk.Label(label="")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_hexpand(True)
        self.status_label.set_ellipsize(Pango.EllipsizeMode.END)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)

        self.tabs = []

        self.tabs.append((self.create_tab(), Gtk.Label(label="New Tab")))
        self.notebook.insert_page(self.tabs[0][0], self.tabs[0][1], 0)

        self.connect("destroy", Gtk.main_quit)
        self.connect("configure-event", self.on_configure)
        self.connect("key-press-event", self.on_key_press)
        self.notebook.connect("switch-page", self.tab_changed)

        self.vbox_container = Gtk.VBox()

        self.vbox_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        self.hbox_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.hbox_top.pack_start(self.tool_bar, True, True, 0)
        self.hbox_top.pack_end(self.status_label, False, False, 4)

        self.vbox_container.pack_start(self.notebook, True, True, 0)
        self.vbox_container.pack_end(self.hbox_top, False, False, 0)

        self.add(self.vbox_container)

        self.tool_bar.show_all()
        self.status_label.show()
        self.notebook.show()
        self.vbox_container.show()
        self.show_all()
        self.set_can_focus(True)
        self.grab_focus()


    def on_startup(self):
        ''' some startup stuff '''
        current_page = self.notebook.get_current_page()
        self.tabs[current_page][0].find_box.hide()
        print("WebKit:", wk.get_major_version(),
              wk.get_minor_version(),
              wk.get_micro_version())


    def toggle_blocker(self, e=None):
        global blocker_on
        if blocker_on == 1:
            blocker_on = 0
            self.set_status("Ad Blocker turned OFF")
            self.show_ok_dialog("Confirmed", "Ad Blocker turned Off")

        else:
            blocker_on = 1
            self.show_ok_dialog("Confirmed", "Ad Blocker turned ON")
            self.set_status("Ad Blocker turned ON")


    def show_yesno_dialog(self, title, message):
        ''' use for confirmations '''
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


    def on_reset_cookies(self, e=None):
        ''' User clicked reset cookies '''
        if self.show_yesno_dialog("Confirm", "Remove all but good cookies now?"):
            # Cookies Reset
            domains = set()
            with open("goodcookie.txt", "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    domains.add(s)

            if not domains:
                print("No domains loaded. Refusing to delete all cookies.")
                sys.exit(1)

            placeholders = ",".join(["?"] * len(domains))

            # Delete cookies whose host is NOT in the allowed list.
            # Keep the exact string matches as provided in the file.
            sql = f"DELETE FROM moz_cookies WHERE host NOT IN ({placeholders})"

            conn = sqlite3.connect("cookies.sqlite")
            try:
                cur = conn.cursor()
                cur.execute(sql, tuple(domains))
                conn.commit()
                print(f"Deleted {cur.rowcount} rows from moz_cookies.")
            finally:
                conn.close()

            self.set_status("* cookies reset to only goodcookies *")
            self.show_ok_dialog("Confirmed", "Cookies have been reset.")



    def on_history_all(self, e=None):
        ''' Remove all history (browser_history.txt) '''
        if self.show_yesno_dialog("Confirm", "Are you sure you want to clear history?"):
            with open("browser_history.txt", "w", encoding="utf-8") as fout:
                fout.write("history\n")

            self.set_status("* History Cleared *")
            self.show_ok_dialog("Confirmed", "History Cleared")


    def set_status(self, text):
        ''' Status-Bar '''
        self.status_label.set_text(text or "")


    def get_current_tab(self):
        ''' returns the active web_view page handle '''
        page_num = self.notebook.get_current_page()
        if page_num < 0:
            return None
        return self.notebook.get_nth_page(page_num)


    def open_devtools_for_current_tab(self):
        ''' displays the Dev Tools window '''
        tab = self.get_current_tab()
        if tab:
            tab.open_devtools()


    def on_devtools_clicked(self, widget):
        self.open_devtools_for_current_tab()


    def open_in_browser(self, url):
        # This is where you connect to your browser app
        # opens in new tab
        # current_page = self.notebook.get_current_page()
        # self.tabs[current_page][0].web_view.load_uri(url)
        self.open_new_tab(None, url)


    def open_persist_history_dialog(self, e=None):
        # ("ctrl shift H")
        win = HistoryWindow("browser_history.txt", on_select_url=self.open_in_browser)
        win.connect("destroy", lambda w: None)
        win.set_keep_above(True)
        win.show_all()


    def on_key_press(self, widget, event):
        ''' Direct actions from keypress combinations '''
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        shift = event.state & Gdk.ModifierType.SHIFT_MASK

        if ctrl and shift and event.keyval == Gdk.KEY_I:
            self.open_devtools_for_current_tab()
            return True

        if event.keyval == Gdk.KEY_Escape:
            self.close_current_tab(None)
            return True

        if ctrl and event.keyval == Gdk.KEY_q:
            self.adjust_history_file() # always on EOF
            Gtk.main_quit()
            return True

        if ctrl and event.keyval == Gdk.KEY_f:
            self.raise_find_dialog(None)
            return True

        if ctrl and shift and event.keyval == Gdk.KEY_H:
            self. open_persist_history_dialog()
            return True

        if event.state & Gdk.ModifierType.MOD1_MASK:  # Alt-1,2,3,4
            keyname = Gdk.keyval_name(event.keyval)

            if keyname in current_settings:
                self.insert_text(current_settings[keyname])
                return True

        return False


    def tab_changed(self, notebook, current_page, index):
        if index is None:
            return
        tab = self.tabs[index][0]
        title = tab.web_view.get_title()
        if title:
            self.set_title("Acme Browser - " + title)
        else:
            self.set_title("Acme Browser")

        tab.sync_address_bar()


    def title_changed(self, web_view, frame):
        current_page = self.notebook.get_current_page()

        counter = 0
        for tab, label in self.tabs:
            if tab.web_view is web_view:
                title = tab.web_view.get_title() or "New Tab"
                label.set_text(title[:27] + "..." if len(title) > 30 else title)
                if counter == current_page:
                    self.tab_changed(None, None, counter)
                break
            counter += 1


    def create_tab(self):
        tab = BrowserTab(browser=self)
        tab.web_view.connect("notify::title", self.title_changed)
        return tab


    def close_current_tab(self, widget):
        if self.notebook.get_n_pages() == 1:
            return
        page = self.notebook.get_current_page()
        current_tab = self.tabs.pop(page)
        self.notebook.remove(current_tab[0])


    def open_new_tab(self, widget, uri=None):
        current_page = self.notebook.get_current_page()
        page_tuple = (self.create_tab(), Gtk.Label(label="New Tab"))
        self.tabs.insert(current_page + 1, page_tuple)
        self.notebook.insert_page(page_tuple[0], page_tuple[1], current_page + 1)
        if current_settings['gotab'].lower() == "yes":  # neo.dat
            self.notebook.set_current_page(current_page + 1)

        if uri:
            page_tuple[0].web_view.load_uri(uri)

        return page_tuple[0]


    def save_active_tab_info(self, e=None):
        ''' store user bookmark '''
        tab = self.get_current_tab()
        with open(current_settings['bkmpath'], "a", encoding="utf-8") as fout:
            fout.write(tab.web_view.get_title() + " <=> " + tab.web_view.get_uri() + "\n")
        self.show_ok_dialog("Confirm",f"Bookmark appended to {bkmpath}")


    def raise_find_dialog(self, widget):
        current_page = self.notebook.get_current_page()
        self.tabs[current_page][0].find_box.show_all()
        self.tabs[current_page][0].find_entry.grab_focus()


    def goto_home(self, widget):
        current_page = self.notebook.get_current_page()
        self.tabs[current_page][0].web_view.load_uri(current_settings['homepage'])
        # current_page = self.notebook.get_current_page()
        # self.tabs[current_page][0].find_box.hide()


    def on_print_clicked(self, button):
        ''' Printer was clicked in the status bar
            Runs this method located in the BrowserTab class '''
        current_page = self.notebook.get_current_page()
        self.tabs[current_page][0].on_print_clicked()


    def get_all_cookies(self, widget):
        cookie_db = os.path.join(script_dir, "cookies.sqlite")
        cookies_data = []

        try:
            if os.path.exists(cookie_db):
                conn = sqlite3.connect(cookie_db)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                print(f"Tables in database: {[t[0] for t in tables]}")

                table_configs = [
                    ("cookies", "name, value, domain, path"),
                    ("soup_cookies", "name, value, domain, path"),
                    ("webkit_cookies", "name, value, domain, path"),
                    ("moz_cookies", "name, value, host, path")
                ]

                for table_name, columns in table_configs:
                    try:
                        cursor.execute(f"SELECT {columns} FROM {table_name}")
                        cookies_data = cursor.fetchall()
                        print(f"Found {len(cookies_data)} cookies in table '{table_name}'")
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
            self.get_all_cookies(None)
        else:
            dialog.destroy()

    def delete_selected_cookies(self, selection, liststore):
        ''' User selected 1 or more cookies to delete '''
        cookie_db = os.path.join(script_dir, "cookies.sqlite")
        model, selected_rows = selection.get_selected_rows()

        if not selected_rows:
            return

        try:
            conn = sqlite3.connect(cookie_db)
            cursor = conn.cursor()

            for row_path in selected_rows:
                row_iter = liststore.get_iter(row_path)
                domain, name, path, value = liststore.get(row_iter, 0, 1, 2, 3)
                cursor.execute(
                    "DELETE FROM moz_cookies WHERE host=? AND name=? AND value=? AND path=?",
                    (domain, name, value, path)
                )

            conn.commit()
            conn.close()
            print(f"Deleted {len(selected_rows)} cookies")
        except Exception as e:
            print(f"Error deleting cookies: {e}")

    def add_cookie(self, domain, name, value, path="/"):
        ''' for cookie manager - not user '''
        cookie = wk.Cookie.new(domain, name, value)
        cookie.set_path(path)
        self.cookie_manager.set_cookie(cookie, None, None, lambda *args: None)
        print(domain)


    def save_geometry(self):
        ''' Rewrites the neo.dat "config" file '''
        width, height = self.get_size()
        x, y = self.get_position()
        with open(os.path.join(script_dir, "wingeo"), "w") as fout:
            fout.write(str(width) + "\n")
            fout.write(str(height) + "\n")
            fout.write(str(x) + "\n")
            fout.write(str(y) + "\n")


    def adjust_history_file(self):
        ''' trim browser_history to histlimit deduped '''
        N = int(current_settings['histlimit'])  # from neo.dat

        with open('browser_history.txt', 'r', encoding='utf-8') as f:
            unique_lines = list(dict.fromkeys(reversed(f.readlines())))
            unique_lines.reverse()  # dedupe last first

        ulines = len(unique_lines)
        count = 0
        if ulines > N:
            numdel = ulines - N
            with open("browser_history.txt", "w", encoding="utf-8") as fout:
                for line in unique_lines:
                    count += 1
                    if count >= numdel:
                        fout.write(line)
            print("removed ", numdel, "history")


    def on_delete_event(self, widget, event):
        ''' Called when user clicks 'X' or presses Alt+F4.
        Return TRUE to cancel close, FALSE to proceed. '''
        self.save_geometry() # just once at EOJ
        print(f"blocked {blockcount} adds...")
        self.adjust_history_file()
        return False

    def on_destroy(self, event):
        # Optional: explicit cleanup for WebKit if needed
        print ("EOJ")
        return False

    def on_configure(self, widget, event):
        # required?
        pass

    def open_settings_dialog(self, e=None):
        ''' Triggers the settings user dialog window '''
        global current_settings

        dialog = SettingsDialog(self, current_settings)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            new_settings = dialog.get_settings()

            # Convert numeric fields if needed
            try:
                new_settings["histlimit"] = int(new_settings["histlimit"])
            except ValueError:
                new_settings["histlimit"] = 25

            try:
                new_settings["defsize"] = int(new_settings["defsize"])
            except ValueError:
                new_settings["defsize"] = 14

            try:
                new_settings["monsize"] = int(new_settings["monsize"])
            except ValueError:
                new_settings["monsize"] = 14

            # gotab can be normalized to yes/no
            new_settings["gotab"] = "yes" if new_settings["gotab"].lower() in ("yes", "true", "1", "on") else "no"

            # Save back to file here
            save_settings_to_file(new_settings)
            # Save back to globals
            current_settings = new_settings

        dialog.destroy()

    def insert_text(self, text):
        '''
        1. Look at the focused field
        2. If it’s a text input or textarea:
           - insert the snippet at the cursor
           - preserve the rest of the text
           - keep the caret in the right place
           - trigger the right JavaScript events so the page reacts properly

        looks complicated because it’s trying to work across more websites.

        # simple version for basic pages:
            const el = document.activeElement;
            if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA")) {
                el.value += text;
            }  '''

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
        self.tabs[current_page][0].web_view.evaluate_javascript(js, -1, None, None, None, None, None, None)


    def show_ok_dialog(self, title, message):
        ''' simple dialog for confirmations '''
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

    # def open_popup_as_tab(self, popup_webview, uri=None):
    #     '''
    #     Insert an existing WebView (the WebKit popup view) into your notebook as a new tab.
    #     This keeps window.open() working because WebKit gets a valid related view.
    #     '''
    #     label = Gtk.Label(label="Popup")
    #     page_tuple = (BrowserTab(browser=self), label)

    #     # Replace the BrowserTab's web_view with the popup_webview we were given
    #     tab_widget = page_tuple[0]

    #     # Remove the old web_view from its scrolled window (if already packed).
    #     # Easiest: rebuild the tab container in place.
    #     # Since your BrowserTab constructor already builds UI, we’ll swap web_view safely:
    #     tab_widget.web_view = popup_webview

    #     # Replace the content inside the existing scrolled window:
    #     # BrowserTab created a scrolled_window with tab_widget.web_view inside.
    #     # We can just re-add popup_webview to the scrolled window by rebuilding layout.
    #     # Easiest reliable approach: create a lightweight container tab instead of swapping.
    #     #
    #     # So: we won't rely on the existing scrolled_window created in BrowserTab().__init__.
    #     # We'll rebuild the tab UI for this special case:

    #     # Destroy existing children and recreate minimal structure
    #     for child in list(tab_widget.get_children()):
    #         tab_widget.remove(child)

    #     tab_widget.web_view.connect("notify::title", self.title_changed)
    #     tab_widget.web_view.connect("load-changed", tab_widget.on_load_changed)

    #     scrolled_window = Gtk.ScrolledWindow()
    #     scrolled_window.add(tab_widget.web_view)

    #     tab_widget.pack_start(scrolled_window, True, True, 0)
    #     tab_widget.show_all()

    #     current_page = self.notebook.get_current_page()
    #     self.tabs.insert(current_page + 1, page_tuple)
    #     self.notebook.insert_page(tab_widget, label, current_page + 1)
    #     if current_settings['gotab'].lower() == "yes":
    #         self.notebook.set_current_page(current_page + 1)

    #     if uri:
    #         tab_widget.web_view.load_uri(uri)

    #     return tab_widget


# class #
class HistoryWindow(Gtk.Window):
    def __init__(self, history_file, on_select_url=None):
        super().__init__(title="Browser History")
        self.set_default_size(600, 400)

        self. history_file = history_file
        self.on_select_url = on_select_url

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        # List store: one column for the URL string
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

        self.load_history()

    def load_history(self):
        self.store.clear()

        if not os.path.exists(self.history_file):
            return

        seen = set()
        with open(self.history_file, "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if not url:
                    continue
                if url in seen:
                    continue
                seen.add(url)
                self.store.append([url])

        model = self.view.get_model()
        if not model or len(model) == 0:
            return
        # Get the path to the last row
        last_index = len(model) - 1
        path = Gtk.TreePath.new_from_string(str(last_index))
        # Parameters: (path, column, use_align, row_align, col_align)
        # row_align=1.0 aligns the bottom of the row to the bottom of the view
        self.view.scroll_to_cell(path, None, True, 1.0, 0.0)

    def get_selected_url(self):
        selection = self.view.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            return model[treeiter][0]
        return None

    def on_open_clicked(self, button):
        url = self.get_selected_url()
        if url and self.on_select_url:
            self.on_select_url(url)

    def on_row_activated(self, treeview, path, column):
        url = self.get_selected_url()
        if url and self.on_select_url:
            self.on_select_url(url)

    def on_reload_clicked(self, button):
        ''' not used '''
        self.load_history()

# class #
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

        # Dialog buttons
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)

        content_area = self.get_content_area()

        # Scrolled window
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        content_area.add(scroll)

        # Grid inside scrolled window
        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        scroll.add(grid)

        # Field definitions: key -> label
        fields = [
            ("homepage", "Homepage"),
            ("searchen", "Search Engine"),
            ("histlimit", "History Limit"),
            ("gotab", "Open in New Tab"),
            ("deffont", "Default Font"),
            ("defsize", "Default Font Size"),
            ("monfont", "Monospace Font"),
            ("monsize", "Monospace Font Size"),
            ("bkmpath", "bookmarks path"),
            # Add your Alt-snippet fields here:
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
        '''Return the values from the dialog fields.'''
        settings = {}
        for key, entry in self.entries.items():
            settings[key] = entry.get_text().strip()
        return settings

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


def save_settings_to_file(settings, filename="neo.dat"):
    ''' Save Settings back to file neo.dat '''
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

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

with open(os.path.join(script_dir, "wingeo")) as fin:
    dat = fin.readlines()
dat = [i.strip() for i in dat]
gwidth = int(dat[0])
gheight = int(dat[1])
gx = int(dat[2])
gy = int(dat[3])

# settings BOJ

with open(os.path.join(script_dir, "neo.dat")) as fin:
    dat = fin.readlines()
dat = [i.strip() for i in dat]
homepage = dat[0]
searchen = dat[1]
histlimit = dat[2]
gotab = dat[3]
deffont = dat[4]
defsize = dat[5]
monfont = dat[6]
monsize = dat[7]
bkmpath = dat[8]
alt1 = dat[9]
alt2 = dat[10]
alt3 = dat[11]
alt4 = dat[12]

current_settings = {
    "homepage": homepage,
    "searchen": searchen,
    "histlimit": histlimit,
    "gotab": gotab,
    "deffont": deffont,
    "defsize": defsize,
    "monfont": monfont,
    "monsize": monsize,
    "bkmpath": bkmpath,
    "1":alt1,
    "2":alt2,
    "3":alt3,
    "4":alt4,
}

##############

BLOCK_SUBSTRINGS = [
    # Major ad/analytics/tracker networks
    "doubleclick.net",
    "adservice.google.",        # google ad services
    "googlesyndication.com",
    "googletagmanager.com",
    "gtag/js",                  # common gtag path fragment
    "googletagmanager.com",
    "google-analytics.com",
    "googleadservices.com",
    "pagead/",

    "adnxs.com",
    "adsystem",                 # generic
    "adsafeprotected.com",
    "criteo.com",
    "taboola.com",
    "revcontent.com",
    "outbrain.com",
    "zemanta.com",
    "scorecardresearch.com",

    "scorecardresearch.com",
    "quantserve.com",
    "tapad.",

    "rubiconproject.com",
    "xandr.com",
    "appnexus.com",

    "34.231.",                  # (avoid if too broad; remove if it causes false positives)

    "adsrvr.org",
    "facebook.net",
    # "facebook.net/tr/",
    # "connect.facebook.net/",

    "twitter.com/i/ads",
    "t.co/ads",

    "segment.io",
    "segments/",

    "mixpanel.com",
    "cdn.mxpnl.com",

    "hotjar.com",
    "hj.",

    "outbrain.com",
    "recaptcha",              # sometimes not desired; comment out if needed

    "matomo.",                # analytics
    "piwik.",

    "sentry.io",              # might be desired; remove if you don’t want it
    "loggly.com",

    # Common tracking/ads URL patterns (heuristics)
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
    "/collect?",  # analytics pixel endpoints
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

    # Script containers sometimes used by ad tech
    "adsbygoogle",
    "googletagservices",
    "googletagservices.com",
    "gpt.js",                # google publisher tags
    "doubleclick",
]


if __name__ == "__main__":
    Gtk.init(sys.argv)
    global browser

    start_url = None
    if len(sys.argv) > 1:
        start_url = sys.argv[1]
        # Basic check to auto-prefix 'https://' if the user omitted it
        if not start_url.startswith(("http://", "https://", "file://")):
            start_url = "https://" + start_url

    browser = Browser()

    if gwidth > 0 and gheight > 0:
        browser.resize(gwidth, gheight)
    if gx > 0 or gy > 0:
        browser.move(gx, gy)

    # os.remove("crash.log")
    log = open("crash.log", "w")
    print(faulthandler.enable(file=log))

    Gtk.main()
