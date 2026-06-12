# revnet-verify

This is a script and support library intended to help verify the correctness of the Revolutionary Networks dataset. It
is not intended for public use.

## How to run the script

You can either run the script with an installed Python interpreter or build a standalone executable directory with
PyInstaller. The script provides ample help functionality on its own which you can access by passing the `-h` flag.

### Run using your Python interpreter

1. Install all the dependencies in `requirements.txt` with
    ```shell
    pip install -r requirements.txt
    ```
2. Run the script with
   ```shell
   revnet-verify [arguments]
   ```
   or
   ```shell
   python3 revnet-verify.py [arguments]
   ```

### Build an executable with PyInstaller
1. Install all the dependencies in `requirements.txt` with
    ```shell
    pip install -r requirements.txt
    ```
2. Install PyInstaller with
    ```shell
    pip install pyinstaller
    ```
3. Run the PyInstaller program on `revnet_verify.py`:
    ```shell
    pyinstaller revnet-verify.py
    ```
   This will create the executable in the `dist/revnet-verify` directory. You should not remove the script from this
   directory since it relies on the `_internal` sibling directory to execute. If you want to install this somewhere on
   your machine, move the entire directory and add a symbolic link to the executable in the appropriate `bin` directory.