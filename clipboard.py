#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import os
import json
from pynput import keyboard

class ClipboardManager:
    def __init__(self):
        # Create a Gtk application
        self.app = Gtk.Application(application_id="com.user.clipboardmanager")
        self.app.connect("activate", self.on_activate)
        
        # Initialize clipboard
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        
        # Set up clipboard owner-change signal for efficient monitoring
        # This is much more efficient than polling
        self.clipboard.connect('owner-change', self.on_clipboard_change)
        
        # Clipboard history (max 25 items)
        self.history = []
        self.max_items = 25
        
        # Load history from file if it exists
        self.history_file = os.path.expanduser("~/.clipboard_history.json")
        self.load_history()
        
        # Current clipboard content
        self.current_text = self.clipboard.wait_for_text()

    def load_history(self):
        """Load clipboard history from file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
                    # Keep only max_items
                    self.history = self.history[:self.max_items]
            except Exception as e:
                print(f"Error loading history: {e}")
                self.history = []

    def save_history(self):
        """Save clipboard history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f)
        except Exception as e:
            print(f"Error saving history: {e}")

    def on_clipboard_change(self, clipboard, event):
        """Handle clipboard content changes via signal"""
        # Use a small timeout to allow clipboard content to be fully available
        GLib.timeout_add(100, self.process_clipboard_change)
        
    def process_clipboard_change(self):
        """Process the changed clipboard content"""
        text = self.clipboard.wait_for_text()
        if text and text != self.current_text and text.strip():
            self.current_text = text
            
            # Remove this item if it already exists in history
            if text in self.history:
                self.history.remove(text)
                
            # Add new text to the beginning of history
            self.history.insert(0, text)
            
            # Trim history to max length
            if len(self.history) > self.max_items:
                self.history = self.history[:self.max_items]
                
            # Save history to file
            self.save_history()
            
            # Update listbox if window is open
            if hasattr(self, 'listbox') and self.window.is_visible():
                self.update_listbox()
        
        # Don't repeat this timeout
        return False

    def on_activate(self, app):
        """Set up the main application window"""
        # Create window
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_title("Clipboard History")
        self.window.set_default_size(400, 500)
        self.window.connect("delete-event", self.on_window_close)
        
        # Create a scrolled window
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        # Create listbox for clipboard items
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self.on_item_clicked)
        
        # Update listbox with current history
        self.update_listbox()
        
        # Add listbox to scrolled window
        scrolled_window.add(self.listbox)
        
        # Add scrolled window to main window
        self.window.add(scrolled_window)
        
        # Set up global hotkey using pynput
        self.listener = keyboard.GlobalHotKeys({
            '<alt>+v': self.toggle_visibility
        })
        self.listener.start()
        
        # Show all widgets then hide window
        self.window.show_all()
        self.window.hide()

    def update_listbox(self):
        """Update the listbox with current clipboard history"""
        # Remove all existing rows
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        
        # Add empty state message if no history
        if not self.history:
            label = Gtk.Label(label="No clipboard history yet")
            label.set_margin_top(20)
            label.set_margin_bottom(20)
            self.listbox.add(label)
            self.listbox.show_all()
            return
            
        # Add each history item
        for item in self.history:
            # Truncate long text for display
            display_text = item[:100] + "..." if len(item) > 100 else item
            display_text = display_text.replace("\n", " ")
            
            # Create a box for the item (better styling)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box.set_margin_start(10)
            box.set_margin_end(10)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            
            # Create a label with the text
            label = Gtk.Label(label=display_text)
            label.set_halign(Gtk.Align.START)
            label.set_line_wrap(True)
            label.set_max_width_chars(40)
            
            # Add label to box
            box.add(label)
            
            # Add a separator
            if item != self.history[-1]:  # Don't add separator after last item
                separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                separator.set_margin_top(8)
                box.add(separator)
            
            # Add box to listbox
            self.listbox.add(box)
        
        self.listbox.show_all()

    def on_item_clicked(self, listbox, row):
        """Handle click on a clipboard item"""
        index = row.get_index()
        
        # Empty state row
        if not self.history:
            self.window.hide()
            return
            
        if 0 <= index < len(self.history):
            # Get the text from history
            text = self.history[index]
            
            # Set clipboard text
            self.clipboard.set_text(text, -1)
            
            # Hide our window
            self.window.hide()
            
            # Sleep a bit and then paste
            GLib.timeout_add(300, self.perform_paste)
            
    def perform_paste(self):
        """Perform paste operation"""
        try:
            # Wait a bit for focus to return to previous window
            os.system("sleep 0.3")
            
            # Try pynput first as it seems more reliable
            from pynput.keyboard import Controller, Key
            keyboard = Controller()
            keyboard.press(Key.ctrl)
            keyboard.press('v')
            keyboard.release('v')
            keyboard.release(Key.ctrl)
            
            # Also try xdotool as a backup
            os.system("xdotool key --clearmodifiers ctrl+v")
        except Exception as e:
            print(f"Error pasting: {e}")
        
        return False

    def toggle_visibility(self):
        """Toggle the visibility of the window"""
        # Need to use GLib.idle_add to safely update UI from a different thread
        def toggle():
            if self.window.is_visible():
                self.window.hide()
            else:
                # Update listbox before showing
                self.update_listbox()
                self.window.present()
            return False
            
        GLib.idle_add(toggle)

    def on_window_close(self, window, event):
        """Handle window close event"""
        window.hide()
        return True  # Prevent window from closing

    def run(self):
        """Run the application"""
        self.app.run(None)


if __name__ == "__main__":
    # Run the clipboard manager
    manager = ClipboardManager()
    manager.run()
