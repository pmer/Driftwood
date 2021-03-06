###################################
## Driftwood 2D Game Dev. Suite  ##
## entity.py                     ##
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

import spritesheet


class Entity:
    """This parent class represents an Entity. It is subclassed by either TileModeEntity or PixelModeEntity.

    Attributes:
        manager: Parent EntityManager instance.

        filename: Filename of the JSON entity descriptor.
        eid: The Entity ID number.
        mode: The movement mode of the entity.
        acceleration: Direction of next movement.
        velocity: Direction of current movement.
        collision: Whether collision should be checked for.
        spritesheet: Spritesheet instance of the spritesheet which owns this entity's graphic.
        layer: The layer of the entity.
        x: The x-coordinate of the entity.
        y: The y-coordinate of the entity.
        tile: Tile instance for the tile the entity is currently on.
        width: The width in pixels of the entity.
        height: The height in pixels of the entity.
        speed: The movement speed of the entity in pixels per second.
        members: A list of sequence positions of member graphics in the spritesheet.
        afps: Animation frames-per-second.
        gpos: A four-member list containing an x,y,w,h source rectangle for the entity's graphic.
        properties: Any custom properties of the entity.
    """

    def __init__(self, entitymanager):
        """Entity class initializer.

        Args:
            manager: Link back to the parent EntityManager instance.
        """
        self.manager = entitymanager

        self.filename = ""
        self.eid = 0

        if isinstance(self, TileModeEntity):
            self.mode = "tile"

        elif isinstance(self, PixelModeEntity):
            self.mode = "pixel"

        self.next_velocity = (0, 0)
        self.velocity = (0, 0)
        self.collision = None
        self.spritesheet = None
        self.layer = 0
        self.x = 0
        self.y = 0
        self.tile = None
        self.width = 0
        self.height = 0
        self.speed = 0
        self.members = []
        self.afps = 0
        self.properties = {}

        self.walking = None

        self.__cur_member = 0
        self._next_area = None

        self.__entity = {}

    def srcrect(self):
        """Return an (x, y, w, h) srcrect for the current graphic frame of the entity.
        """
        current_member = self.members[self.__cur_member]
        return (((current_member * self.width) % self.spritesheet.imagewidth),
                ((current_member * self.width) // self.spritesheet.imagewidth) * self.height,
                self.width, self.height)

    def _read(self, filename, eid):
        """Read the entity descriptor.
        """
        self.filename = filename
        self.eid = eid

        self.__entity = self.manager.driftwood.resource.request_json(filename)

        self.collision = self.__entity["collision"]
        self.width = self.__entity["width"]
        self.height = self.__entity["height"]
        self.speed = self.__entity["speed"]
        self.members = self.__entity["members"]
        self.afps = self.__entity["afps"]

        # Schedule animation.
        if self.afps:
            self.manager.driftwood.tick.register(self.__next_member, delay=(1000//self.afps))

        if "properties" in self.__entity:
            self.properties = self.__entity["properties"]

        ss = self.manager.spritesheet(self.__entity["image"])

        if ss:
            self.spritesheet = ss

        else:
            self.manager.spritesheets.append(spritesheet.Spritesheet(self.manager, self.__entity["image"]))
            self.spritesheet = self.manager.spritesheets[-1]

    def _collide(self, dsttile):
        """Report a collision.
        """
        if self.manager.collider:
            self.manager.collider(self, dsttile)

    def _tile_at(self, layer, x, y, px=0, py=0):
        """Retrieve a tile by layer and pixel coordinates.
        """
        return self.manager.driftwood.area.tilemap.layers[layer].tile(
            (x / self.manager.driftwood.area.tilemap.tilewidth) + px,
            (y / self.manager.driftwood.area.tilemap.tileheight) + py
        )

    def __next_member(self, millis):
        self.__cur_member = (self.__cur_member + 1) % len(self.members)
        self.manager.driftwood.area.changed = True


# TODO: When PixelModeEntity is done, move common logic into functions in the superclass.
class TileModeEntity(Entity):
    """This Entity subclass represents an Entity configured for movement in by-tile mode.
    """
    def teleport(self, layer, x, y):
        """Teleport the entity to a new tile position.

        This is also used to change layers.

        Args:
            layer: New layer, or None to skip.
            x: New x-coordinate, or None to skip.
            y: New y-coordinate, or None to skip.
        """
        tilemap = self.manager.driftwood.area.tilemap

        # Make sure this is a tile.
        if ((layer < 0 or len(tilemap.layers) <= layer) or
            (x is not None and x % tilemap.tilewidth != 0) or
            (y is not None and y % tilemap.tileheight != 0)
        ):
            self.manager.driftwood.log.msg("ERROR", "Entity", "attempted teleport to non-tile position")
            return

        if layer is not None:
            self.layer = layer

        if x is not None:
            self.x = x * tilemap.tilewidth

        if y is not None:
            self.y = y * tilemap.tileheight

        # Set the new tile.
        self.tile = self._tile_at(self.layer, self.x, self.y)

        # Call the on_tile event if set.
        self.__call_on_tile()

        # If we changed the layer, call the on_layer event if set.
        if layer is not None:
            self.__call_on_layer()

        self.manager.driftwood.area.changed = True

    def set_next_velocity(self, x, y):
        """Tell the entity that it wants to move in direction x, y.
        """
        if self.next_velocity == (0, 0):
            self.manager.driftwood.tick.register(self.__process_walk)
        self.next_velocity = (x, y)
        if self.velocity == (0, 0) and self.next_velocity == (0, 0):
            self.manager.driftwood.tick.unregister(self.__process_walk)

    def __process_walk(self, millis_past):
        """Move through tiles in a process that takes time.
        """
        # Accelerate
        if self.velocity == (0, 0):
            if self.next_velocity == (0, 0):
                self.manager.driftwood.log.info("DEBUG", "Entity", "__process_walk: velocity and next_velocity (0, 0)")
            x, y = self.next_velocity
            # Should we rate limit this?  We perform collisions every tick.
            if self.__can_walk(x, y):
                self.__change_velocity(*self.next_velocity)
            else:
                # The entity is trying to move in a direction but is being blocked.  We will keep trying to move each
                # frame until we get new orders.
                return

        # Inch along
        self.manager.driftwood.area.changed = True

        tilemap = self.manager.driftwood.area.tilemap
        tilewidth = tilemap.tilewidth
        tileheight = tilemap.tileheight

        x, y = self.velocity
        tile_pos = self.tile.pos

        self._partial_xy[0] += x * self.speed * millis_past / 1000
        self._partial_xy[1] += y * self.speed * millis_past / 1000
        self.x = int(tile_pos[0] * tilewidth + self._partial_xy[0])
        self.y = int(tile_pos[1] * tileheight + self._partial_xy[1])

        # Have we arrived at our next tile?
        while True:
            x, y = self.velocity
            if x == 0 and y == 0:
                break
            if ((x == -1 and tilewidth > -self._partial_xy[0])
                or (x ==  1 and tilewidth > self._partial_xy[0])
                or (y == -1 and tileheight > -self._partial_xy[1])
                or (y ==  1 and tileheight > self._partial_xy[1])):
                break

            # Set new tile
            self._partial_xy[0] -= x * tilewidth
            self._partial_xy[1] -= y * tileheight
            new_tile_x = tile_pos[0] * tilewidth + (tilewidth * x)
            new_tile_y = tile_pos[1] * tileheight + (tileheight * y)
            self.tile = self._tile_at(self.layer, new_tile_x, new_tile_y)

            # Arrive at the new tile
            if self.tile:
                self.__call_on_tile()
                self.__do_layermod()

            # If there is an exit, take it.
            # May be lazy exit, where we have no self.tile
            if self._next_area:

                # If we're the player, change the area.
                if self.manager.player.eid == self.eid:
                    self._do_exit()
                    self.__change_velocity(*self.next_velocity)

                # Exits destroy other entities.
                else:
                    self.manager.kill(self.eid)

            if self.velocity != self.next_velocity:
                if self.__can_walk(*self.next_velocity):
                    self.__change_velocity(*self.next_velocity)
                else:
                    self.__change_velocity(0, 0)
            elif not self.__can_walk(*self.velocity):
                self.__change_velocity(0, 0)

    def __can_walk(self, x, y):
        """Given the entity's current tile, can it move to tile in direction X, Y?
        """
        if x not in [-1, 0, 1]:
            self.manager.driftwood.log.info("DEBUG", "Entity", "__can_walk: x not in -1, 0, or 1")
            x = 0

        if y not in [-1, 0, 1]:
            self.manager.driftwood.log.info("DEBUG", "Entity", "__can_walk: y not in -1, 0, or 1")
            y = 0

        if not self.tile:
            self.manager.driftwood.log.info("DEBUG", "Entity", "__can_walk: no tile when called")
            return False # panic!

        # Perform collision detection.
        if self.collision:
            # Check if the destination tile is walkable.
            dsttile = self.manager.driftwood.area.tilemap.layers[self.layer].tile(self.tile.pos[0] + x,
                                                                                  self.tile.pos[1] + y)

            # Don't walk on nowalk tiles or off the edge of the map unless there's a lazy exit.
            if self.tile:
                if dsttile:
                    if dsttile.nowalk or dsttile.nowalk == "":
                        # Is the tile a player or npc specific nowalk?
                        if (dsttile.nowalk == "player" and self.manager.player.eid == self.eid
                                or dsttile.nowalk == "npc" and self.manager.player.eid != self.eid):
                            self._collide(dsttile)
                            return False

                        # Any other values are an unconditional nowalk.
                        elif not dsttile.nowalk in ["player", "npc"]:
                            self._collide(dsttile)
                            return False

                else:

                    # Are we allowed to walk off the edge of the area to follow a lazy exit?
                    if "exit:up" in self.tile.exits and y == -1:
                        self._next_area = self.tile.exits["exit:up"].split(',')

                    elif "exit:down" in self.tile.exits and y == 1:
                        self._next_area = self.tile.exits["exit:down"].split(',')

                    elif "exit:left" in self.tile.exits and x == -1:
                        self._next_area = self.tile.exits["exit:left"].split(',')

                    elif "exit:right" in self.tile.exits and x == 1:
                        self._next_area = self.tile.exits["exit:right"].split(',')

                    else:
                        self._collide(dsttile)
                        return False

            # Is there a regular exit on the destination tile?
            if dsttile and not self._next_area and "exit" in dsttile.exits:
                self._next_area = dsttile.exits["exit"].split(',')

            # Entity collision detection.
            for ent in self.manager.entities:
                # This is us.
                if ent.eid == self.eid:
                    continue

                # Collision detection.
                tilemap = self.manager.driftwood.area.tilemap
                tilewidth = tilemap.tilewidth
                tileheight = tilemap.tileheight
                if (
                    self.x + tilewidth < ent.x
                    or self.x > ent.x + tilewidth
                    or self.y + tileheight < ent.y
                    or self.y > ent.y + tileheight
                ):
                    self.manager.collision(self, ent)
                    return False

        return True

    def __change_velocity(self, x, y):
        """Reset walking if our X, Y velocities change."""
        self._partial_xy = [0, 0]
        self.velocity = (x, y)
        # TODO: Set up the walking animation.

        if self.velocity == (0, 0):
            tilemap = self.manager.driftwood.area.tilemap
            tilewidth = tilemap.tilewidth
            tileheight = tilemap.tileheight

            # Set the final position and cease walking.
            if self.tile:
                self.x = self.tile.pos[0] * tilewidth
                self.y = self.tile.pos[1] * tileheight

            self.manager.driftwood.tick.unregister(self.__process_walk)

    def _do_exit(self):
        """Perform an exit to another area.
        """
        # Call the on_exit event if set.
        if "on_exit" in self.manager.driftwood.area.tilemap.properties:
            self.manager.driftwood.script.call(*self.manager.driftwood.area.tilemap.properties["on_exit"].split(':'))

        # Enter the next area.
        if self.manager.driftwood.area.focus(self._next_area[0]):
            self.layer = int(self._next_area[1])
            self.x = int(self._next_area[2]) * self.manager.driftwood.area.tilemap.tilewidth
            self.y = int(self._next_area[3]) * self.manager.driftwood.area.tilemap.tileheight
            self.tile = self._tile_at(self.layer, self.x, self.y)

        self._next_area = None

        self.__call_on_tile()


    def __call_on_tile(self):
        # Call the on_tile event if set.
        if "on_tile" in self.tile.properties:
            args = self.tile.properties["on_tile"].split(':')
            self.manager.driftwood.script.call(*args)

    def __call_on_layer(self):
        if "on_layer" in self.manager.driftwood.area.tilemap.layers[self.layer].properties:
            args = self.manager.driftwood.area.tilemap.layers[self.layer].properties["on_layer"].split(':')
            self.manager.driftwood.script.call(*args)

    def __do_layermod(self):
        # Layermod macro, change the layer.
        if "layermod" in self.tile.properties:
            did_teleport = False
            xdiff, ydiff = 0, 0

            layermod = self.tile.properties["layermod"]
            # Go down so many layers.
            if layermod.startswith('-'):
                self.teleport(self.layer - int(layermod[1:]), None, None)
                did_teleport = True

            # Go up so many layers.
            elif layermod.startswith('+'):
                self.teleport(self.layer + int(layermod[1:]), None, None)
                did_teleport = True

            # Go to a specific layer.
            else:
                self.teleport(int(layermod), None, None)
                did_teleport = True

            self.__call_on_tile()

            return True

        return False


# TODO: Finish pixel mode.
class PixelModeEntity(Entity):
    """This Entity subclass represents an Entity configured for movement in by-pixel mode.
    """
    def teleport(self, layer, x, y):
        """Teleport the entity to a new pixel position.

        Args:
            layer: New layer, or None to skip.
            x: New x-coordinate, or None to skip.
            y: New y-coordinate, or None to skip.
        """
        if layer:
            self.layer = layer

        if x:
            self.x = x

        if y:
            self.y = y

        self.manager.driftwood.area.changed = True

    def walk(self, x, y):
        """Move the entity by one pixel to a new position relative to its current position.

        Args:
            x: -1 for left, 1 for right, 0 for no x movement.
            y: -1 for up, 1 for down, 0 for no y movement.

        Returns: True if succeeded, false if failed (due to collision).
        """
        if not x or not x in [-1, 0, 1]:
            x = 0

        if not y or not y in [-1, 0, 1]:
            y = 0

        # Perform collision detection.
        if self.collision:
            # TODO: Pixel mode tile collisions.

            # Entity collision detection.
            for ent in self.manager.entities:
                # This is us.
                if ent.eid == self.eid:
                    continue

                # Collision detection, proof by contradiction.
                if not (
                    self.x + x > ent.x + ent.width

                    and self.x + self.width + x < ent.x

                    and self.y + y > ent.y + ent.height

                    and self.y + self.height + y < ent.y
                ):
                    self.manager.collision(self, ent)
                    return False

        self.x += x
        self.y += y

        self.manager.driftwood.area.changed = True

        return True


# TODO: Implement turn mode.
class TurnModeEntity(Entity):
    """This Entity subclass represents an Entity configured for movement in turn-based mode.
    """
