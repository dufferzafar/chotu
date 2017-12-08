from datetime import datetime as dt

from PyQt5 import QtCore as QtC

import lib_hotstrings as lhs
Xctx = lhs.get_Xctx()


# Keys are replaced with values as you type them
hotstrings = {
    # Personal Information
    "/name": "Shadab Zafar",

    "/dz": "dufferzafar",
    "/blog": "http://dufferzafar.github.io/",
    "/git": "http://github.com/dufferzafar/",

    # Misc
    "/hah": "hahahahahaha",
    "/lmgtfy": "http://lmgtfy.com/?q=",

    # ASCII Emoji
    "/shrug": "¯\_(ツ)_/¯",
    "/smile": "ಠ‿ಠ",

    # Functions
    "/date": dt.now().strftime("%d/%m/%Y"),
    "/time": dt.now().strftime("%I:%M %p"),
}


class Hotstrings(QtC.QThread):

    def run(self):
        lhs.watch(hotstrings, *Xctx)

    @classmethod
    def cleanup(cls):
        lhs.cleanup(*Xctx)
