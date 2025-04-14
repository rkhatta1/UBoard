#!/bin/bash

# Function for colorful output
print_color() {
    case $1 in
        "green") echo -e "\e[32m$2\e[0m" ;;
        "red") echo -e "\e[31m$2\e[0m" ;;
        "yellow") echo -e "\e[33m$2\e[0m" ;;
        "blue") echo -e "\e[34m$2\e[0m" ;;
    esac
}

# Check if running as root and refuse
if [ "$(id -u)" -eq 0 ]; then
    print_color "red" "This script should not be run as root or with sudo."
    print_color "yellow" "It will use sudo only when necessary for installing dependencies."
    exit 1
fi

print_color "blue" "===== Linux Clipboard Manager Installation ====="
print_color "blue" "This script will install the clipboard manager and its dependencies."

# Install dependencies
print_color "yellow" "Installing required dependencies..."
sudo apt-get update
sudo apt-get install -y python3 python3-gi python3-pynput gir1.2-gtk-3.0 xdotool python3-cairo python3-pyperclip

# Create user bin directory if it doesn't exist
if [ ! -d "$HOME/bin" ]; then
    print_color "yellow" "Creating ~/bin directory..."
    mkdir -p "$HOME/bin"
fi

# Add ~/bin to PATH if not already there
if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
    print_color "yellow" "Adding ~/bin to your PATH in .bashrc..."
    echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.bashrc"
    print_color "green" "Added ~/bin to PATH. Changes will take effect after restarting your terminal."
fi

# Copy the script to ~/bin
print_color "yellow" "Copying clipboard manager to ~/bin..."
cp clipboard.py "$HOME/bin/"
chmod +x "$HOME/bin/clipboard.py"
print_color "green" "Clipboard manager installed to ~/bin/"

# Ask about adding to startup
read -p "Do you want to add the clipboard manager to startup applications? (y/n): " add_startup

if [[ $add_startup =~ ^[Yy]$ ]]; then
    # Create autostart directory if it doesn't exist
    mkdir -p "$HOME/.config/autostart"
    
    # Create desktop file for autostart
    cat > "$HOME/.config/autostart/u-board.desktop" << EOF
[Desktop Entry]
Type=Application
Name=Clipboard Manager
Comment=Linux Clipboard History Manager
Exec=$HOME/bin/clipboard.py
Icon=gtk-paste
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF
    
    print_color "green" "Added clipboard manager to startup applications."
    print_color "green" "It will start automatically when you log in."
else
    print_color "yellow" "Clipboard manager not added to startup."
    print_color "yellow" "You can start it manually by running 'clipboard' in a terminal."
fi

print_color "green" "Installation complete! Please restart your system to ensure maximum compatibility :D"
print_color "blue" "Usage:"
print_color "blue" "- Press Alt+V to show/hide the clipboard history"
print_color "blue" "- Click on an item to paste it"
print_color "blue" "- Close the window to hide it (it will continue running in the background)"