#!/usr/bin/env python3
from http import server
from plumbum import cli, local, FG, BG
import os
import sys

from management.utils import M

@M.command('ping')
def ping(txt):
    print(txt)

if __name__ == '__main__':
    app = M()
    app.run()
