###################################
## Project Driftwood             ##
## config.py                     ##
## Copyright 2013 PariahSoft LLC ##
###################################

## **********
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to
## deal in the Software without restriction, including without limitation the
## rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
## sell copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in
## all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
## FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
## IN THE SOFTWARE.
## **********

import argparse
import json
import sys


VERSION = "Project Driftwood PreAlpha-dev0"


class ConfigManager:
    """
    Configuration management class. This class handles command line imput and a configuration file and presents the
    resulting configuration for easy access. This class' state is not modified after initialization.

    Command line options always supercede their configuration file equivalents.
    """

    def __init__(self, baseclass):
        """
        ConfigManager class initializer.

        @type  baseclass: object
        @param baseclass: The base class instance.
        """
        self.baseclass = baseclass  # A link back to the top-level base class.
        self.__config_file = ""
        self.__config = {}
        self.__cmdline_args = self.__read_cmdline()
        self.__prepare_config()
        print("Project Driftwood\nStarting up...")

    def __contains__(self, item):
        if item in self.__config:
            return True
        return False

    def __getitem__(self, item):
        if self.__contains__(item):
            return self.__config[item]

    def __iter__(self):
        return self.__config.items()

    def __read_cmdline(self):
        """
        Read in command line options using ArgumentParser.

        @rtype:  object
        @return: result of parser.parse_args().
        """
        parser = argparse.ArgumentParser(description=VERSION,
                                         formatter_class=lambda prog: argparse.HelpFormatter(prog,
                                                                                             max_help_position=40))
        parser.add_argument("config", nargs='?', default="./config.json", help="config file to use")
        parser.add_argument("--path", nargs=1, dest="path", metavar="<name,...>", help="set path")
        parser.add_argument("--root", nargs=1, dest="root", metavar="<root>", help="set path root")
        parser.add_argument("--size", nargs=1, dest="size", metavar="<WxH>", help="set window dimensions")
        parser.add_argument("--cache-size", nargs=1, dest="cachesize", metavar="<megabytes>", help="set max cache size")
        parser.add_argument("--cache-ttl", nargs=1, dest="cachettl", metavar="<seconds>", help="set cache time-to-live")
        parser.add_argument("--cache-cycle", nargs=1, dest="cachecycle", metavar="<seconds>",
                            help="set cache clean cycle delay")
        parser.add_argument("--tps", nargs=1, dest="tps", metavar="<hertz>", help="set ticks-per-second")

        group1 = parser.add_mutually_exclusive_group()
        group1.add_argument("--window", default=None, action="store_false", dest="fullscreen",
                            help="run in windowed mode")
        group1.add_argument("--fullscreen", default=None, action="store_true", dest="fullscreen",
                            help="run in fullscreen mode")

        group2 = parser.add_mutually_exclusive_group()
        group2.add_argument("--quiet", default=None, action="store_false", dest="verbose",
                            help="run in quiet logging mode")
        group2.add_argument("--verbose", default=None, action="store_true", dest="verbose",
                            help="run in verbose logging mode")

        parser.add_argument("--version", action="store_true", dest="version", help="print the version string")

        return parser.parse_args()

    def __prepare_config(self):
        """
        Combine the command line arguments and the configuration file into the internal __config dictionary, favoring
        command line arguments.
        """
        self.__config = json.load(open(self.__cmdline_args.config, 'r'))

        if self.__cmdline_args.version:  # Print the version string and exit.
            print(VERSION)
            print("Copyright 2014 PariahSoft LLC")
            sys.exit(0)

        if self.__cmdline_args.path:
            self.__config["path"]["path"] = self.__cmdline_args.path[0].split(',')

        if self.__cmdline_args.root:
            self.__config["path"]["root"] = self.__cmdline_args.root

        if self.__cmdline_args.size:
            w, h = self.__cmdline_args.size[0].split('x')
            self.__config["window"]["width"], self.__config["window"]["height"] = int(w), int(h)

        if self.__cmdline_args.cachesize:
            self.__config["cache"]["size"] = int(self.__cmdline_args.cachesize)

        if self.__cmdline_args.cachettl:
            self.__config["cache"]["ttl"] = int(self.__cmdline_args.cachettl)

        if self.__cmdline_args.cachecycle:
            self.__config["cache"]["cycle"] = int(self.__cmdline_args.cachecycle)

        if self.__cmdline_args.tps:
            self.__config["tick"]["tps"] = int(self.__cmdline_args.tps)

        if self.__cmdline_args.fullscreen != None:
            if self.__cmdline_args.fullscreen:
                self.__config["window"]["fullscreen"] = True
            else:
                self.__config["window"]["fullscreen"] = False

        if self.__cmdline_args.verbose != None:
            if self.__cmdline_args.verbose:
                self.__config["log"]["verbose"] = True
            else:
                self.__config["log"]["verbose"] = False
