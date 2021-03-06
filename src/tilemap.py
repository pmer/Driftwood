###################################
## Driftwood 2D Game Dev. Suite  ##
## map.py                        ##
## Copyright 2014 PariahSoft LLC ##
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

import layer
import tileset


class Tilemap:
    """This class reads the Tiled map file for the currently focused area, and presents an abstraction.

    Attributes:
        area: Parent AreaManager instance.

        width: Width of the map in tiles.
        height: Height of the map in tiles.
        tilewidth: Width of tiles in the map.
        tileheight: Height of tiles in the map.
        properties: A dictionary containing map properties.

        layers: The list of Layer class instances for each layer.
        tilesets: The list of Tileset class instances for each tileset.
    """

    def __init__(self, area):
        """Tilemap class initializer.

        Args:
            area: Link back to the parent AreaManager instance.
        """
        self.area = area

        # Attributes which will be updated with information about the map.
        self.width = 0
        self.height = 0
        self.tilewidth = 0
        self.tileheight = 0
        self.properties = {}

        self.layers = []
        self.tilesets = []

        # This contains the JSON of the Tiled map.
        self.__tilemap = {}

    def _read(self, data):
        """Read and abstract a Tiled map.

        Reads the JSON Tiled map and processes its information into useful abstractions. This method is marked private
        even though it's called from AreaManager, because it must only be called once per area focus.

        Args:
            data: JSON contents of the Tiled map.
        """
        # Reset variables left over from the last map.
        if self.layers:
            self.layers = []
        if self.tilesets:
            self.tilesets = []

        # Load the JSON data.
        self.__tilemap = data

        # Set class attributes representing information about the map.
        self.width = self.__tilemap["width"]
        self.height = self.__tilemap["height"]
        self.tilewidth = self.__tilemap["tilewidth"]
        self.tileheight = self.__tilemap["tileheight"]
        if "properties" in self.__tilemap:
            self.properties = self.__tilemap["properties"]

        # Call the on_enter event if set.
        if "on_enter" in self.properties:
            self.area.driftwood.script.call(*self.properties["on_enter"].split(':'))

        # Set the window title.
        if "title" in self.properties:
            self.area.driftwood.window.title(self.properties["title"])

        # Build the tileset abstractions.
        for ts in self.__tilemap["tilesets"]:
            self.tilesets.append(tileset.Tileset(self, ts))

        # Global object layer.
        gobjlayer = {}

        # Build the tile and layer abstractions.
        for zpos, l in enumerate(self.__tilemap["layers"]):
            # This layer is marked invisible, skip it.
            if not l["visible"]:
                continue

            # This is a tile layer.
            if l["type"] == "tilelayer":
                self.layers.append(layer.Layer(self, l, zpos))

            # This is an object layer.
            elif l["type"] == "objectgroup":
                # If this is the very first layer, it's the global object layer.
                if not self.layers:
                    gobjlayer = l

                else:
                    self.layers[-1]._process_objects(l)

        # Merge the global object layer into all tile layers.
        if gobjlayer:
            for l in self.layers:
                l._process_objects(gobjlayer)
