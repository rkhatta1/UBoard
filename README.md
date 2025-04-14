# UBoard
A Windows-inspired clipboard manager for Ubuntu/Linux.

## Installation Steps
1. Clone the repository.
2. In the terminal:

    ```
    cd UBoard
    chmod +x install.sh
    ./install.sh
    ```

    OR

    ```
    cd UBoard
    bash install.sh
    ```
3. Restart the system for the permissions to be set correctly and to maximize compatibility.

## Configuring the Keyboard Shortcut
1. Open the file ```clipboard.py```
2. Edit the string on ```Line #113: "<alt>+v"``` to your desired shortcut combination. Refer to the [pynput documentation](https://pynput.readthedocs.io/en/latest/) for more information.