#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango

import pyperclip
import threading
import time
from collections import deque
from pynput import keyboard
from pynput.keyboard import Key, KeyCode, Controller as KeyboardController
# import os # No longer needed as script_name print is removed

# --- Configuration ---
HISTORY_SIZE = 25
HOTKEY_COMBINATION = {Key.alt_l, KeyCode.from_char('v')}

# --- Global State ---
clipboard_history = deque(maxlen=HISTORY_SIZE)
last_added_text = None # Track what we last *added* to history
clipboard_window = None # Holds the single, persistent window instance
window_created = False # Flag to know if window exists
monitoring_active = True # To prevent self-pasting feedback loop
keyboard_controller = KeyboardController()
# script_name = os.path.basename(__file__) # Removed
gtk_clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD) # Use GTK clipboard for signals
current_keys = set() # Moved global definition here for clarity

# --- Clipboard Monitoring (Event-Driven) ---
def on_clipboard_owner_change(clipboard, event):
    """Callback when clipboard owner changes."""
    clipboard.request_text(on_clipboard_text_received, None)

def on_clipboard_text_received(clipboard, text, user_data):
    """Process text received from clipboard."""
    GLib.idle_add(process_new_clipboard_text, text)
    return False

def process_new_clipboard_text(text):
    """Adds new, valid text to history deque."""
    global last_added_text, monitoring_active

    if not monitoring_active:
        return False

    if text and isinstance(text, str) and len(text.strip()) > 0:
        if text != last_added_text:
            # print(f"Adding to history: {text[:30]}...") # Removed debug print
            if text in clipboard_history:
                temp_list = list(clipboard_history)
                temp_list.remove(text)
                clipboard_history.clear()
                clipboard_history.extendleft(reversed(temp_list))

            clipboard_history.appendleft(text)
            last_added_text = text

            if clipboard_window and clipboard_window.is_visible():
                 update_listbox_content()

    return False # Tell GLib.idle_add not to repeat

# --- GUI Window ---
def create_clipboard_window():
    """Creates the persistent clipboard window (but doesn't show it)."""
    global clipboard_window, window_created

    if window_created:
        return

    # print("Creating persistent clipboard window...") # Removed debug print
    window = Gtk.Window(title="Clipboard History")
    window.set_position(Gtk.WindowPosition.CENTER)
    window.set_default_size(400, 500)
    window.set_keep_above(True)
    window.set_type_hint(Gdk.WindowTypeHint.DIALOG)

    window.connect("delete-event", on_window_hide_request)
    window.connect("key-press-event", on_key_press_hide)
    window.connect("destroy", on_window_destroyed_cleanup)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    window.add(vbox)

    listbox = Gtk.ListBox()
    listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    listbox.connect("row-activated", on_item_activated)
    window.listbox = listbox # Store reference

    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled_window.add(listbox)
    vbox.pack_start(scrolled_window, True, True, 0)

    clear_button = Gtk.Button(label="Clear History")
    clear_button.connect("clicked", on_clear_clicked)
    vbox.pack_start(clear_button, False, False, 0)

    clipboard_window = window
    window_created = True

def update_listbox_content():
    """Refreshes the items shown in the ListBox."""
    if not clipboard_window or not hasattr(clipboard_window, 'listbox'):
        return

    listbox = clipboard_window.listbox
    for child in listbox.get_children():
        child.destroy()

    if not clipboard_history:
        label = Gtk.Label(label="Clipboard history is empty.")
        listbox.add(label)
    else:
        for item_text in clipboard_history:
            label = Gtk.Label()
            label.set_text(item_text)
            label.set_halign(Gtk.Align.START)
            label.set_line_wrap(True)
            label.set_max_width_chars(60)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_margin_top(3)
            label.set_margin_bottom(3)
            label.set_margin_start(5)
            label.set_margin_end(5)
            row = Gtk.ListBoxRow()
            row.add(label)
            row.set_tooltip_text(item_text)
            row.clipboard_text = item_text
            listbox.add(row)

    listbox.show_all()


def show_clipboard_window():
    """Shows the persistent clipboard window."""
    global clipboard_window
    if not window_created:
        create_clipboard_window()

    if clipboard_window:
        if clipboard_window.is_visible():
            # print("Window already visible, presenting.") # Removed debug print
            clipboard_window.present()
        else:
            # print("Showing clipboard window...") # Removed debug print
            update_listbox_content()
            clipboard_window.show_all()
            clipboard_window.present()
            # GLib.idle_add(clipboard_window.grab_focus) # Optional focus grab

def hide_clipboard_window():
    """Hides the persistent clipboard window."""
    if clipboard_window and clipboard_window.is_visible():
        # print("Hiding clipboard window.") # Removed debug print
        clipboard_window.hide()

# --- Event Handlers ---
def on_window_hide_request(widget, event):
    """Handles clicking the window's close button."""
    hide_clipboard_window()
    return True # Prevent default destroy action

def on_window_destroyed_cleanup(widget):
    """Cleanup if window is somehow destroyed externally."""
    global clipboard_window, window_created
    # print("Clipboard window was destroyed.") # Removed debug print
    clipboard_window = None
    window_created = False

def on_key_press_hide(widget, event):
    """Handles key presses on the clipboard window (e.g., Escape)."""
    if event.keyval == Gdk.KEY_Escape:
        # print("Escape key pressed, hiding window.") # Removed debug print
        hide_clipboard_window()
        return True
    return False

def on_item_activated(listbox, row):
    """Handles selecting an item from the list."""
    global monitoring_active, last_added_text
    selected_text = row.clipboard_text
    # print(f"Item selected: {selected_text[:30]}...") # Removed debug print

    monitoring_active = False # Prevent self-copy
    try:
        pyperclip.copy(selected_text)
        last_added_text = selected_text # Update immediately
    except Exception as e:
        print(f"Error setting clipboard: {e}") # Keep error print
        monitoring_active = True
        hide_clipboard_window()
        return

    hide_clipboard_window()

    GLib.timeout_add(100, paste_and_reenable_monitoring)

def on_clear_clicked(button):
    """Handles the clear history button."""
    global clipboard_history, last_added_text
    # print("Clearing clipboard history.") # Removed debug print
    clipboard_history.clear()
    last_added_text = None
    # print("History cleared.") # Removed debug print
    update_listbox_content()
    hide_clipboard_window()

def paste_and_reenable_monitoring():
    """Simulates paste and re-enables monitoring."""
    global monitoring_active
    # print("Simulating Ctrl+V...") # Removed debug print
    try:
        time.sleep(0.05) # Keep small delay
        keyboard_controller.press(Key.ctrl_l)
        keyboard_controller.press('v')
        keyboard_controller.release('v')
        keyboard_controller.release(Key.ctrl_l)
    except Exception as e:
        print(f"Error simulating paste: {e}") # Keep error print
    finally:
        # print("Re-enabling clipboard monitoring.") # Removed debug print
        monitoring_active = True
    return False # Stop GLib timer

# --- Hotkey Listener ---
def on_press(key):
    """Hotkey press handler."""
    global current_keys # Make sure using global
    if key in HOTKEY_COMBINATION:
        current_keys.add(key)
        if all(k in current_keys for k in HOTKEY_COMBINATION):
            # print("Hotkey detected!") # Removed debug print
            GLib.idle_add(show_clipboard_window)

def on_release(key):
    """Hotkey release handler."""
    global current_keys # Make sure using global
    try:
        current_keys.remove(key)
    except KeyError:
        pass

def listen_for_hotkey():
    """Starts the pynput hotkey listener."""
    global current_keys
    current_keys = set() # Reset keys on listener start
    # print(f"Hotkey listener started...") # Removed debug print
    try:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
    except Exception as e:
        # Keep crucial error message
        print(f"ERROR starting pynput listener: {e}")
        # Attempt to gracefully stop the GTK main loop if listener fails
        GLib.idle_add(Gtk.main_quit)


# --- Main Execution ---
if __name__ == "__main__":

    hotkey_thread = threading.Thread(target=listen_for_hotkey, daemon=True)
    hotkey_thread.start()

    gtk_clipboard.connect('owner-change', on_clipboard_owner_change)

    # Removed startup status prints

    try:
        Gtk.main()
    except KeyboardInterrupt:
        print("\nExiting gracefully.") # Keep exit message

    # print(f"{script_name} exited.") # Removed debug print