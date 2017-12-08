#!/usr/bin/env python

import qtapp
from hotstrings import Hotstrings


if __name__ == '__main__':

    # Start listening for hotstrings
    H = Hotstrings()
    H.start()

    # Run Qt Application
    # Currently, it only shows a SysTray icon
    qtapp.run()
