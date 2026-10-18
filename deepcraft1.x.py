#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeekCraft 0.1  --  "Minecraft Infdev Edition"
=================================================
A single-file Minecraft Infdev style voxel sandbox written in pure Python on
top of pygame-ce.  Every asset (terrain, HUD, icon) is generated in memory,
so the program needs no external files whatsoever.

The game calls itself "DeepSeekCraft 0.1" everywhere: the window caption, the
title screen, the in-game HUD, the save file and the console banner.

Controls
--------
  Mouse ............ look around (click the title screen to capture the mouse)
  W A S D .......... walk              SHIFT ... sneak / descend while flying
  SPACE ............ jump              F ....... toggle flying
  CTRL ............. sprint
  Left mouse ....... break block       Right mouse ... place block
  Mouse wheel ...... cycle hotbar      1 .. 9 ... select hotbar slot
  T ................ freeze / unfreeze the day-night cycle
  [ / ] ............ decrease / increase render distance (manual)
  V ................ toggle automatic render distance (holds 60 FPS)
  F5 / F9 .......... save / load the world
  N ................ generate a new random world
  ESC .............. pause menu (Q quits)

Run with `-h` for the command line options.
"""

from __future__ import annotations

import base64
import json
import math
import os
import random
import sys
import time
import zlib

# ---------------------------------------------------------------------------
# Metadata / branding
# ---------------------------------------------------------------------------

GAME_NAME = "DeepSeekCraft"
GAME_VERSION = "0.1"
GAME_EDITION = "Minecraft Infdev Edition"
GAME_TITLE = f"{GAME_NAME} {GAME_VERSION}"
WINDOW_TITLE = f"{GAME_TITLE} - {GAME_EDITION}"
SAVE_FILE = f"deepseekcraft_{GAME_VERSION}_world.json"

try:
    import pygame
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "DeepSeekCraft 0.1 needs pygame-ce.\n"
        "Install it with:  python -m pip install pygame-ce\n"
    )
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# Configuration  (60 FPS target, speed 10)
# ---------------------------------------------------------------------------

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 640
TARGET_FPS = 60                 # locked 60 FPS target
FOV = 70.0
NEAR_PLANE = 0.05

WALK_SPEED = 10.0               # requested movement speed
SPRINT_MULT = 1.6
FLY_SPEED = 10.0 * 1.8
GRAVITY = 26.0
JUMP_SPEED = 8.6
REACH_DISTANCE = 5.5
EYE_HEIGHT = 1.62
PLAYER_HALF_WIDTH = 0.30
PLAYER_HEIGHT = 1.80
MOUSE_SENSITIVITY = 0.0024

CHUNK_X = 16
CHUNK_Z = 16
WORLD_HEIGHT = 64
SEA_LEVEL = 28
RENDER_DISTANCE = 3            # in chunks (adjustable in game with [ and ])
MIN_VIEW_DISTANCE = 2
MAX_VIEW_DISTANCE = 6
FOG_MARGIN = 8

DAY_LENGTH = 600.0             # seconds for a full day-night cycle
SKY_DAY = (118, 176, 235)
SKY_NIGHT = (12, 14, 32)
SUNSET = (232, 132, 90)

MAX_FACES = 26000              # hard safety cap per frame

SAVE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), SAVE_FILE
)

# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

AIR = 0
GRASS = 1
DIRT = 2
STONE = 3
COBBLE = 4
PLANK = 5
LOG = 6
LEAVES = 7
SAND = 8
WATER = 9
BEDROCK = 10
GLASS = 11
BRICK = 12
GRAVEL = 13
GOLD_ORE = 14
IRON_ORE = 15
COAL_ORE = 16
DIAMOND_ORE = 17
OBSIDIAN = 18
SNOW = 19
TNT = 20
GLOWSTONE = 21

# name, top colour, side colour, bottom colour, opaque, solid, liquid, alpha
BLOCK_INFO = {
    AIR:          ("Air",          None,               None,               None,               False, False, False, None),
    GRASS:        ("Grass Block",  (110, 175, 70),     (134, 110, 72),     (134, 110, 72),     True,  True,  False, None),
    DIRT:         ("Dirt",         (134, 110, 72),     (134, 110, 72),     (134, 110, 72),     True,  True,  False, None),
    STONE:        ("Stone",        (128, 128, 128),    (128, 128, 128),    (128, 128, 128),    True,  True,  False, None),
    COBBLE:       ("Cobblestone",  (112, 112, 112),    (112, 112, 112),    (112, 112, 112),    True,  True,  False, None),
    PLANK:        ("Oak Planks",   (166, 133, 82),     (166, 133, 82),     (166, 133, 82),     True,  True,  False, None),
    LOG:          ("Oak Log",      (156, 127, 78),     (104, 78, 46),      (156, 127, 78),     True,  True,  False, None),
    LEAVES:       ("Leaves",       (58, 120, 40),      (52, 108, 36),      (46, 98, 32),       True,  True,  False, None),
    SAND:         ("Sand",         (219, 208, 160),    (219, 208, 160),    (219, 208, 160),    True,  True,  False, None),
    WATER:        ("Water",        (54, 96, 200),      (44, 82, 186),      (36, 70, 170),      False, False, True,  150),
    BEDROCK:      ("Bedrock",      (58, 58, 62),       (58, 58, 62),       (58, 58, 62),       True,  True,  False, None),
    GLASS:        ("Glass",        (196, 224, 236),    (186, 214, 230),    (178, 206, 224),    False, True,  False, 90),
    BRICK:        ("Bricks",       (150, 72, 56),      (150, 72, 56),      (150, 72, 56),      True,  True,  False, None),
    GRAVEL:       ("Gravel",       (136, 126, 122),    (136, 126, 122),    (136, 126, 122),    True,  True,  False, None),
    GOLD_ORE:     ("Gold Ore",     (150, 134, 78),     (150, 134, 78),     (150, 134, 78),     True,  True,  False, None),
    IRON_ORE:     ("Iron Ore",     (152, 140, 128),    (152, 140, 128),    (152, 140, 128),    True,  True,  False, None),
    COAL_ORE:     ("Coal Ore",     (92, 92, 92),       (92, 92, 92),       (92, 92, 92),       True,  True,  False, None),
    DIAMOND_ORE:  ("Diamond Ore",  (108, 168, 172),    (108, 168, 172),    (108, 168, 172),    True,  True,  False, None),
    OBSIDIAN:     ("Obsidian",     (26, 18, 40),       (26, 18, 40),       (26, 18, 40),       True,  True,  False, None),
    SNOW:         ("Snow",         (242, 246, 250),    (238, 242, 248),    (232, 238, 244),    True,  True,  False, None),
    TNT:          ("TNT",          (200, 62, 58),      (200, 62, 58),      (176, 54, 50),      True,  True,  False, None),
    GLOWSTONE:    ("Glowstone",    (246, 220, 138),    (232, 200, 118),    (214, 182, 104),    True,  True,  False, None),
}

HOTBAR_BLOCKS = [GRASS, DIRT, STONE, COBBLE, PLANK, LOG, LEAVES, SAND, GLASS]

# Cube faces: direction neighbour, corner offsets (perimeter order), shade, colour slot
# colour slot: 0 = top, 1 = side, 2 = bottom
FACE_TABLE = (
    ((0, 1, 0),  ((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)), 1.00, 0),
    ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)), 0.46, 2),
    ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)), 0.72, 1),
    ((1, 0, 0),  ((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)), 0.72, 1),
    ((0, 0, -1), ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)), 0.86, 1),
    ((0, 0, 1),  ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)), 0.86, 1),
)

# Index of a relative cube-corner offset (-1..1 on each axis) into the
# per-frame camera-space offset table.
REL_INDEX = {}
for _dz in (-1, 0, 1):
    for _dy in (-1, 0, 1):
        for _dx in (-1, 0, 1):
            REL_INDEX[(_dx, _dy, _dz)] = (_dx + 1) + 3 * (_dy + 1) + 9 * (_dz + 1)
del _dz, _dy, _dx


def _shaded(rgb, shade):
    return (int(rgb[0] * shade), int(rgb[1] * shade), int(rgb[2] * shade))


# Pre-bake the shaded colour for every block/face combination.
# FACE_TABLE entry layout: (neighbour, corners, shade, colour_slot)
BLOCK_FACE_RGB = {}
for _bid, _info in BLOCK_INFO.items():
    if _info[1] is None:
        continue
    _slots = (_info[1], _info[2], _info[3])          # top, side, bottom
    BLOCK_FACE_RGB[_bid] = tuple(
        _shaded(_slots[_f[3]], _f[2]) for _f in FACE_TABLE
    )


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def clamp(value, low, high):
    return low if value < low else (high if value > high else value)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_rgb(a, b, t):
    return (int(lerp(a[0], b[0], t)),
            int(lerp(a[1], b[1], t)),
            int(lerp(a[2], b[2], t)))


def _hash_xy(x, y, seed):
    n = (x * 374761393 + y * 668265263 + seed * 1442695040888963407) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n ^= n >> 16
    return (n & 0xFFFFFFFF) / 4294967295.0


def _hash_xyz(x, y, z, seed):
    n = (x * 374761393 + y * 668265263 + z * 2147483647
         + seed * 1442695040888963407) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n ^= n >> 16
    return (n & 0xFFFFFFFF) / 4294967295.0


def value_noise2(x, z, seed):
    x0 = math.floor(x)
    z0 = math.floor(z)
    tx = x - x0
    tz = z - z0
    sx = tx * tx * (3.0 - 2.0 * tx)
    sz = tz * tz * (3.0 - 2.0 * tz)
    v00 = _hash_xy(x0, z0, seed)
    v10 = _hash_xy(x0 + 1, z0, seed)
    v01 = _hash_xy(x0, z0 + 1, seed)
    v11 = _hash_xy(x0 + 1, z0 + 1, seed)
    a = v00 + (v10 - v00) * sx
    b = v01 + (v11 - v01) * sx
    return a + (b - a) * sz


def fbm2(x, z, seed, octaves=4, lac=2.0, gain=0.5):
    total = 0.0
    amp = 1.0
    freq = 1.0
    norm = 0.0
    for i in range(octaves):
        total += amp * value_noise2(x * freq, z * freq, seed + i * 131)
        norm += amp
        amp *= gain
        freq *= lac
    return total / norm


def value_noise3(x, y, z, seed):
    x0 = math.floor(x)
    y0 = math.floor(y)
    z0 = math.floor(z)
    tx = x - x0
    ty = y - y0
    tz = z - z0
    sx = tx * tx * (3.0 - 2.0 * tx)
    sy = ty * ty * (3.0 - 2.0 * ty)
    sz = tz * tz * (3.0 - 2.0 * tz)
    c = _hash_xyz
    v000 = c(x0, y0, z0, seed)
    v100 = c(x0 + 1, y0, z0, seed)
    v010 = c(x0, y0 + 1, z0, seed)
    v110 = c(x0 + 1, y0 + 1, z0, seed)
    v001 = c(x0, y0, z0 + 1, seed)
    v101 = c(x0 + 1, y0, z0 + 1, seed)
    v011 = c(x0, y0 + 1, z0 + 1, seed)
    v111 = c(x0 + 1, y0 + 1, z0 + 1, seed)
    a = lerp(v000 + (v100 - v000) * sx, v010 + (v110 - v010) * sx, sy)
    b = lerp(v001 + (v101 - v001) * sx, v011 + (v111 - v011) * sx, sy)
    return lerp(a, b, sz)


# ---------------------------------------------------------------------------
# World
# ---------------------------------------------------------------------------

class Chunk:
    __slots__ = ("cx", "cz", "blocks", "mesh", "dirty")

    def __init__(self, cx, cz):
        self.cx = cx
        self.cz = cz
        self.blocks = bytearray(CHUNK_X * CHUNK_Z * WORLD_HEIGHT)
        self.mesh = None
        self.dirty = True

    def idx(self, x, y, z):
        return x + z * CHUNK_X + y * CHUNK_X * CHUNK_Z


class VoxelWorld:
    """An effectively infinite chunked voxel world."""

    def __init__(self, seed):
        self.seed = seed
        self.chunks = {}
        self.modified = set()

    # -- terrain ---------------------------------------------------------
    def height_at(self, wx, wz):
        base = fbm2(wx * 0.0100, wz * 0.0100, self.seed, 4)
        detail = fbm2(wx * 0.0520, wz * 0.0520, self.seed + 77, 2)
        h = SEA_LEVEL - 3 + (base ** 1.10) * 24.0 + (detail - 0.5) * 5.0
        return int(clamp(h, 3, WORLD_HEIGHT - 12))

    def generate_chunk(self, cx, cz):
        key = (cx, cz)
        if key in self.chunks:
            return self.chunks[key]
        chunk = Chunk(cx, cz)
        blocks = chunk.blocks
        idx = chunk.idx
        seed = self.seed
        bx = cx * CHUNK_X
        bz = cz * CHUNK_Z
        heights = [[0] * CHUNK_Z for _ in range(CHUNK_X)]

        for x in range(CHUNK_X):
            for z in range(CHUNK_Z):
                wx = bx + x
                wz = bz + z
                h = self.height_at(wx, wz)
                heights[x][z] = h
                beach = h <= SEA_LEVEL + 1
                for y in range(0, h + 1):
                    if y == 0:
                        b = BEDROCK
                    elif y > h - 4:
                        b = SAND if beach else (GRASS if y == h else DIRT)
                    else:
                        b = STONE
                        r = _hash_xyz(wx, y, wz, seed + 771)
                        if y < 16 and r > 0.9986:
                            b = DIAMOND_ORE
                        elif y < 30 and r > 0.9955:
                            b = GOLD_ORE
                        elif r > 0.9880:
                            b = IRON_ORE
                        elif r > 0.9720:
                            b = COAL_ORE
                        elif r < 0.0060:
                            b = GRAVEL
                    blocks[idx(x, y, z)] = b
                for y in range(h + 1, SEA_LEVEL + 1):
                    blocks[idx(x, y, z)] = WATER

        self._carve_caves(chunk, heights)
        self.chunks[key] = chunk
        self._plant_trees(chunk, heights)
        return chunk

    def _carve_caves(self, chunk, heights):
        blocks = chunk.blocks
        idx = chunk.idx
        seed = self.seed + 101
        bx = chunk.cx * CHUNK_X
        bz = chunk.cz * CHUNK_Z
        for x in range(0, CHUNK_X, 2):
            for z in range(0, CHUNK_Z, 2):
                h = heights[x][z]
                wx = bx + x
                wz = bz + z
                for y in range(2, h - 2, 2):
                    n = value_noise3(wx * 0.075, y * 0.11, wz * 0.075, seed)
                    if n > 0.655:
                        for dx in (0, 1):
                            for dy in (0, 1):
                                for dz in (0, 1):
                                    yy = y + dy
                                    if yy <= 1 or yy >= h:
                                        continue
                                    blocks[idx(x + dx, yy, z + dz)] = AIR

    def _plant_trees(self, chunk, heights):
        blocks = chunk.blocks
        idx = chunk.idx
        seed = self.seed + 4242
        bx = chunk.cx * CHUNK_X
        bz = chunk.cz * CHUNK_Z
        for x in range(2, CHUNK_X - 2):
            for z in range(2, CHUNK_Z - 2):
                h = heights[x][z]
                if h <= SEA_LEVEL + 1 or h + 7 >= WORLD_HEIGHT:
                    continue
                if blocks[idx(x, h, z)] != GRASS:
                    continue
                if _hash_xy(bx + x, bz + z, seed) < 0.9880:
                    continue
                trunk = 4 + int(_hash_xy(bx + x, bz + z, seed + 1) * 3)
                for ty in range(1, trunk + 1):
                    blocks[idx(x, h + ty, z)] = LOG
                top = h + trunk
                for lx in range(-2, 3):
                    for lz in range(-2, 3):
                        for ly in range(-1, 3):
                            if abs(lx) == 2 and abs(lz) == 2:
                                continue
                            if ly == -1 and (abs(lx) == 2 or abs(lz) == 2):
                                continue
                            px, pz, py = x + lx, z + lz, top + ly
                            if not (0 <= px < CHUNK_X and 0 <= pz < CHUNK_Z):
                                continue
                            if 0 <= py < WORLD_HEIGHT and blocks[idx(px, py, pz)] == AIR:
                                blocks[idx(px, py, pz)] = LEAVES

    # -- block access ----------------------------------------------------
    def get_block(self, wx, wy, wz):
        if wy < 0 or wy >= WORLD_HEIGHT:
            return AIR
        chunk = self.chunks.get((wx >> 4, wz >> 4))
        if chunk is None:
            return AIR
        return chunk.blocks[chunk.idx(wx & 15, wy, wz & 15)]

    def set_block(self, wx, wy, wz, block, record=True):
        if wy < 0 or wy >= WORLD_HEIGHT:
            return False
        cx, cz = wx >> 4, wz >> 4
        chunk = self.chunks.get((cx, cz))
        if chunk is None:
            return False
        lx, lz = wx & 15, wz & 15
        ci = chunk.idx(lx, wy, lz)
        if chunk.blocks[ci] == block:
            return False
        chunk.blocks[ci] = block
        chunk.dirty = True
        if record:
            self.modified.add((wx, wy, wz))
        # neighbours may need re-meshing across a chunk border
        if lx == 0:
            self._touch(cx - 1, cz)
        elif lx == CHUNK_X - 1:
            self._touch(cx + 1, cz)
        if lz == 0:
            self._touch(cx, cz - 1)
        elif lz == CHUNK_Z - 1:
            self._touch(cx, cz + 1)
        return True

    def _touch(self, cx, cz):
        c = self.chunks.get((cx, cz))
        if c is not None:
            c.dirty = True

    def is_solid(self, wx, wy, wz):
        b = self.get_block(wx, wy, wz)
        return BLOCK_INFO[b][5] if b else False

    # -- streaming -------------------------------------------------------
    def ensure_area(self, px, pz, radius, budget=2):
        ccx = int(math.floor(px)) >> 4
        ccz = int(math.floor(pz)) >> 4
        wanted = []
        for cx in range(ccx - radius, ccx + radius + 1):
            for cz in range(ccz - radius, ccz + radius + 1):
                if (cx, cz) in self.chunks:
                    continue
                d = (cx - ccx) ** 2 + (cz - ccz) ** 2
                wanted.append((d, cx, cz))
        if not wanted:
            return 0
        wanted.sort()
        made = 0
        for _d, cx, cz in wanted:
            if made >= budget:
                break
            self.generate_chunk(cx, cz)
            made += 1
        return made

    def chunks_near(self, px, pz, radius):
        ccx = int(math.floor(px)) >> 4
        ccz = int(math.floor(pz)) >> 4
        out = []
        for cx in range(ccx - radius, ccx + radius + 1):
            for cz in range(ccz - radius, ccz + radius + 1):
                chunk = self.chunks.get((cx, cz))
                if chunk is not None:
                    out.append(chunk)
        return out

    # -- save / load -----------------------------------------------------
    def to_json(self):
        data = {}
        for (cx, cz), chunk in self.chunks.items():
            raw = zlib.compress(bytes(chunk.blocks), 6)
            data[f"{cx},{cz}"] = base64.b64encode(raw).decode("ascii")
        return data

    def load_json(self, data):
        self.chunks.clear()
        self.modified.clear()
        for key, payload in data.items():
            cx, cz = (int(v) for v in key.split(","))
            chunk = Chunk(cx, cz)
            chunk.blocks[:] = zlib.decompress(base64.b64decode(payload))
            chunk.dirty = True
            self.chunks[(cx, cz)] = chunk


# ---------------------------------------------------------------------------
# Mesh building
# ---------------------------------------------------------------------------

def build_mesh(world, chunk):
    """Return (opaque_faces, transparent_faces) for a chunk.

    Each face is a flat tuple:
        (x0,y0,z0, x1,y1,z1, x2,y2,z2, x3,y3,z3, colour_int, cx, cy, cz)
    """
    opaque = [[], [], [], []]
    trans = [[], [], [], []]
    blocks = chunk.blocks
    idx = chunk.idx
    bx = chunk.cx * CHUNK_X
    bz = chunk.cz * CHUNK_Z
    get = world.get_block
    info = BLOCK_INFO
    face_rgb = BLOCK_FACE_RGB
    chunk_x = CHUNK_X
    chunk_z = CHUNK_Z

    for y in range(WORLD_HEIGHT):
        for z in range(chunk_z):
            for x in range(chunk_x):
                b = blocks[idx(x, y, z)]
                if b == AIR:
                    continue
                bopaque = info[b][4]
                # quick interior skip: if fully surrounded by opaque blocks
                if bopaque:
                    lx0 = x - 1
                    lx1 = x + 1
                    lz0 = z - 1
                    lz1 = z + 1
                    if 0 <= lx0 and lx1 < chunk_x and 0 <= lz0 and lz1 < chunk_z \
                            and 1 <= y < WORLD_HEIGHT - 1:
                        if (info[blocks[idx(lx0, y, z)]][4]
                                and info[blocks[idx(lx1, y, z)]][4]
                                and info[blocks[idx(x, y, lz0)]][4]
                                and info[blocks[idx(x, y, lz1)]][4]
                                and info[blocks[idx(x, y - 1, z)]][4]
                                and info[blocks[idx(x, y + 1, z)]][4]):
                            continue

                colors = face_rgb[b]
                alpha = info[b][7]
                target = (opaque if alpha is None else trans)[y >> 4]
                wx = bx + x
                wz = bz + z

                for fi, (dirv, corners, _shade, _slot) in enumerate(FACE_TABLE):
                    nx, ny, nz = dirv
                    cy = y + ny
                    if cy < 0 or cy >= WORLD_HEIGHT:
                        nb = AIR
                    else:
                        lxx = x + nx
                        lzz = z + nz
                        if 0 <= lxx < chunk_x and 0 <= lzz < chunk_z:
                            nb = blocks[idx(lxx, cy, lzz)]
                        else:
                            nb = get(wx + nx, cy, wz + nz)
                    if nb == b:
                        continue
                    if nb != AIR and info[nb][4]:
                        continue
                    c0 = corners[0]
                    cx0, cy0, cz0 = c0
                    c1 = corners[1]
                    c2 = corners[2]
                    c3 = corners[3]
                    mx = (cx0 + c1[0] + c2[0] + c3[0]) * 0.25 + wx
                    my = (cy0 + c1[1] + c2[1] + c3[1]) * 0.25 + y
                    mz = (cz0 + c1[2] + c2[2] + c3[2]) * 0.25 + wz
                    col = colors[fi]
                    packed = (col[0] << 16) | (col[1] << 8) | col[2]
                    target.append((
                        wx + cx0, y + cy0, wz + cz0,
                        13,
                        REL_INDEX[(c1[0] - cx0, c1[1] - cy0, c1[2] - cz0)],
                        REL_INDEX[(c2[0] - cx0, c2[1] - cy0, c2[2] - cz0)],
                        REL_INDEX[(c3[0] - cx0, c3[1] - cy0, c3[2] - cz0)],
                        packed, mx, my, mz,
                    ))

    chunk.mesh = (opaque, trans)
    chunk.dirty = False
    return chunk.mesh


# ---------------------------------------------------------------------------
# Player physics & ray casting
# ---------------------------------------------------------------------------

def _box_solid(world, x0, x1, y0, y1, z0, z1):
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                b = world.get_block(x, y, z)
                if b != AIR and BLOCK_INFO[b][5]:
                    return True
    return False


def move_body(world, pos, vel, dt, hw, height):
    """Move an AABB through the world, resolving collisions per axis."""
    on_ground = False

    # ---- X
    pos[0] += vel[0] * dt
    y0 = int(math.floor(pos[1] + 0.001))
    y1 = int(math.floor(pos[1] + height - 0.001))
    z0 = int(math.floor(pos[2] - hw))
    z1 = int(math.floor(pos[2] + hw))
    if vel[0] > 0:
        bx = int(math.floor(pos[0] + hw))
        if _box_solid(world, bx, bx, y0, y1, z0, z1):
            pos[0] = bx - hw - 0.001
            vel[0] = 0.0
    elif vel[0] < 0:
        bx = int(math.floor(pos[0] - hw))
        if _box_solid(world, bx, bx, y0, y1, z0, z1):
            pos[0] = bx + 1 + hw + 0.001
            vel[0] = 0.0

    # ---- Z
    pos[2] += vel[2] * dt
    x0 = int(math.floor(pos[0] - hw))
    x1 = int(math.floor(pos[0] + hw))
    y0 = int(math.floor(pos[1] + 0.001))
    y1 = int(math.floor(pos[1] + height - 0.001))
    if vel[2] > 0:
        bz = int(math.floor(pos[2] + hw))
        if _box_solid(world, x0, x1, y0, y1, bz, bz):
            pos[2] = bz - hw - 0.001
            vel[2] = 0.0
    elif vel[2] < 0:
        bz = int(math.floor(pos[2] - hw))
        if _box_solid(world, x0, x1, y0, y1, bz, bz):
            pos[2] = bz + 1 + hw + 0.001
            vel[2] = 0.0

    # ---- Y
    pos[1] += vel[1] * dt
    x0 = int(math.floor(pos[0] - hw))
    x1 = int(math.floor(pos[0] + hw))
    z0 = int(math.floor(pos[2] - hw))
    z1 = int(math.floor(pos[2] + hw))
    if vel[1] > 0:
        by = int(math.floor(pos[1] + height))
        if _box_solid(world, x0, x1, by, by, z0, z1):
            pos[1] = by - height - 0.001
            vel[1] = 0.0
    elif vel[1] < 0:
        by = int(math.floor(pos[1]))
        if _box_solid(world, x0, x1, by, by, z0, z1):
            pos[1] = by + 1 + 0.001
            vel[1] = 0.0
            on_ground = True

    return on_ground


def _aabb_visible(planes, x0, y0, z0, x1, y1, z1):
    """Conservative frustum-vs-AABB test using the positive-vertex trick."""
    for nx, ny, nz, o in planes:
        px = x1 if nx >= 0.0 else x0
        py = y1 if ny >= 0.0 else y0
        pz = z1 if nz >= 0.0 else z0
        if nx * px + ny * py + nz * pz - o < 0.0:
            return False
    return True


def raycast(world, origin, direction, max_dist):
    """Amanatides & Woo voxel traversal. Returns (bx,by,bz,nx,ny,nz) or None."""
    x, y, z = origin
    dx, dy, dz = direction
    bx, by, bz = int(math.floor(x)), int(math.floor(y)), int(math.floor(z))

    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1
    step_z = 1 if dz > 0 else -1

    inf = float("inf")
    t_max_x = ((bx + (1 if dx > 0 else 0)) - x) / dx if dx != 0 else inf
    t_max_y = ((by + (1 if dy > 0 else 0)) - y) / dy if dy != 0 else inf
    t_max_z = ((bz + (1 if dz > 0 else 0)) - z) / dz if dz != 0 else inf

    t_delta_x = abs(1.0 / dx) if dx != 0 else inf
    t_delta_y = abs(1.0 / dy) if dy != 0 else inf
    t_delta_z = abs(1.0 / dz) if dz != 0 else inf

    nx = ny = nz = 0
    t = 0.0
    while t <= max_dist:
        b = world.get_block(bx, by, bz)
        if b and BLOCK_INFO[b][6] is False and BLOCK_INFO[b][5]:
            return bx, by, bz, nx, ny, nz
        if t_max_x < t_max_y:
            if t_max_x < t_max_z:
                bx += step_x
                t = t_max_x
                t_max_x += t_delta_x
                nx, ny, nz = -step_x, 0, 0
            else:
                bz += step_z
                t = t_max_z
                t_max_z += t_delta_z
                nx, ny, nz = 0, 0, -step_z
        else:
            if t_max_y < t_max_z:
                by += step_y
                t = t_max_y
                t_max_y += t_delta_y
                nx, ny, nz = 0, -step_y, 0
            else:
                bz += step_z
                t = t_max_z
                t_max_z += t_delta_z
                nx, ny, nz = 0, 0, -step_z
    return None


# ---------------------------------------------------------------------------
# Mobs (simple pigs, Infdev style)
# ---------------------------------------------------------------------------

class Pig:
    __slots__ = ("pos", "vel", "yaw", "timer", "on_ground")

    def __init__(self, x, y, z):
        self.pos = [x, y, z]
        self.vel = [0.0, 0.0, 0.0]
        self.yaw = random.random() * math.tau
        self.timer = random.uniform(1.0, 3.0)
        self.on_ground = False

    def update(self, world, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.timer = random.uniform(1.5, 4.0)
            self.yaw = random.random() * math.tau
        speed = 1.4
        self.vel[0] = math.sin(self.yaw) * speed
        self.vel[2] = math.cos(self.yaw) * speed
        self.vel[1] -= GRAVITY * 0.55 * dt
        if self.vel[1] < -30.0:
            self.vel[1] = -30.0

        before = (self.pos[0], self.pos[2])
        self.on_ground = move_body(world, self.pos, self.vel, dt, 0.42, 0.9)
        moved = abs(self.pos[0] - before[0]) + abs(self.pos[2] - before[1])
        if moved < 0.002 and self.on_ground:
            self.yaw += math.pi * 0.75
            self.vel[1] = 6.0
        if self.pos[1] < -4:
            self.pos[1] = WORLD_HEIGHT + 2


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        self.reset_stats()

    def reset_stats(self):
        self.faces_drawn = 0
        self.chunks_drawn = 0

    def draw(self, world, cam_pos, yaw, pitch, render_distance, fog_colour):
        screen = self.screen
        width, height = screen.get_size()
        self.reset_stats()

        # camera basis
        sy, cy = math.sin(yaw), math.cos(yaw)
        sp, cp = math.sin(pitch), math.cos(pitch)
        fx, fy, fz = sy * cp, sp, -cy * cp
        rx, ry, rz = cy, 0.0, sy
        ux = -sy * sp
        uy = cp
        uz = cy * sp

        focal = (width * 0.5) / math.tan(math.radians(FOV) * 0.5)
        half_w = width * 0.5
        half_h = height * 0.5
        near = NEAR_PLANE
        cxw, cyw, czw = cam_pos

        far = render_distance * CHUNK_X
        max_d2 = far * far
        fog_start = max(4.0, far - FOG_MARGIN)
        fog_end = float(far)
        fog_span = max(0.001, fog_end - fog_start)
        fog_start_sq = fog_start * fog_start
        sky_r, sky_g, sky_b = fog_colour

        opaque_draw = []
        trans_draw = []
        opaque_append = opaque_draw.append
        drawn = 0
        chunks_drawn = 0

        # Full view frustum, used to cull whole 16x16x16 sections at once.
        tan_half_h = half_w / focal
        tan_half_v = half_h / focal
        near_o = cxw * fx + cyw * fy + czw * fz + near

        def _plane(nx, ny, nz):
            ln = math.sqrt(nx * nx + ny * ny + nz * nz)
            if ln < 1e-9:
                return (0.0, 0.0, 1.0, 0.0)
            nx /= ln
            ny /= ln
            nz /= ln
            return (nx, ny, nz, nx * cxw + ny * cyw + nz * czw)

        planes = (
            (fx, fy, fz, near_o),
            _plane(fx * tan_half_h + rx, fy * tan_half_h + ry, fz * tan_half_h + rz),
            _plane(fx * tan_half_h - rx, fy * tan_half_h - ry, fz * tan_half_h - rz),
            _plane(fx * tan_half_v - ux, fy * tan_half_v - uy, fz * tan_half_v - uz),
            _plane(fx * tan_half_v + ux, fy * tan_half_v + uy, fz * tan_half_v + uz),
        )
        visible = _aabb_visible

        # Camera-space offsets of the 27 relative cube corners. Every block
        # face is a unit quad, so the four corners are just origin + offset.
        rel = [None] * 27
        for _dz in (-1, 0, 1):
            for _dy in (-1, 0, 1):
                for _dx in (-1, 0, 1):
                    rel[(_dx + 1) + 3 * (_dy + 1) + 9 * (_dz + 1)] = (
                        _dx * rx + _dy * ry + _dz * rz,
                        _dx * ux + _dy * uy + _dz * uz,
                        _dx * fx + _dy * fy + _dz * fz,
                    )

        for chunk in world.chunks_near(cxw, czw, render_distance):
            mesh = chunk.mesh
            if mesh is None:
                continue
            # cheap chunk level cull against the view direction
            relx = chunk.cx * CHUNK_X + 8.0 - cxw
            rely = 30.0 - cyw
            relz = chunk.cz * CHUNK_Z + 8.0 - czw
            if relx * relx + rely * rely + relz * relz > max_d2:
                continue
            chunks_drawn += 1
            cbx = chunk.cx * CHUNK_X
            cbz = chunk.cz * CHUNK_Z

            op_faces = []
            for si in range(4):
                sect = mesh[0][si]
                if sect:
                    sy = si * 16
                    if visible(planes, cbx, sy, cbz, cbx + 16, sy + 16, cbz + 16):
                        op_faces.extend(sect)

            # ---- opaque faces: inlined hot path --------------------------
            for face in op_faces:
                mdx = face[8] - cxw
                mdy = face[9] - cyw
                mdz = face[10] - czw
                d2 = mdx * mdx + mdy * mdy + mdz * mdz
                if d2 > max_d2 or (mdx * fx + mdy * fy + mdz * fz) < -0.9:
                    continue

                a0 = face[0] - cxw
                a1 = face[1] - cyw
                a2 = face[2] - czw
                o0 = a0 * rx + a1 * ry + a2 * rz
                o1 = a0 * ux + a1 * uy + a2 * uz
                o2 = a0 * fx + a1 * fy + a2 * fz
                r = rel[face[3]]
                p0x = o0 + r[0]
                p0y = o1 + r[1]
                p0z = o2 + r[2]
                r = rel[face[4]]
                p1x = o0 + r[0]
                p1y = o1 + r[1]
                p1z = o2 + r[2]
                r = rel[face[5]]
                p2x = o0 + r[0]
                p2y = o1 + r[1]
                p2z = o2 + r[2]
                r = rel[face[6]]
                p3x = o0 + r[0]
                p3y = o1 + r[1]
                p3z = o2 + r[2]

                if p0z < near or p1z < near or p2z < near or p3z < near:
                    pts = self._project(face, cxw, cyw, czw, rel,
                                        rx, ry, rz, ux, uy, uz, fx, fy, fz,
                                        focal, half_w, half_h, near)
                    if pts is None:
                        continue
                else:
                    i0 = focal / p0z
                    sx0 = half_w + p0x * i0
                    sy0 = half_h - p0y * i0
                    i1 = focal / p1z
                    sx1 = half_w + p1x * i1
                    sy1 = half_h - p1y * i1
                    i2 = focal / p2z
                    sx2 = half_w + p2x * i2
                    sy2 = half_h - p2y * i2
                    i3 = focal / p3z
                    sx3 = half_w + p3x * i3
                    sy3 = half_h - p3y * i3
                    minx = sx0
                    maxx = sx0
                    if sx1 < minx:
                        minx = sx1
                    elif sx1 > maxx:
                        maxx = sx1
                    if sx2 < minx:
                        minx = sx2
                    elif sx2 > maxx:
                        maxx = sx2
                    if sx3 < minx:
                        minx = sx3
                    elif sx3 > maxx:
                        maxx = sx3
                    miny = sy0
                    maxy = sy0
                    if sy1 < miny:
                        miny = sy1
                    elif sy1 > maxy:
                        maxy = sy1
                    if sy2 < miny:
                        miny = sy2
                    elif sy2 > maxy:
                        maxy = sy2
                    if sy3 < miny:
                        miny = sy3
                    elif sy3 > maxy:
                        maxy = sy3
                    if maxx < 0 or minx > width or maxy < 0 or miny > height:
                        continue
                    if maxx - minx < 1.2 and maxy - miny < 1.2:
                        continue
                    pts = [(int(sx0), int(sy0)), (int(sx1), int(sy1)),
                           (int(sx2), int(sy2)), (int(sx3), int(sy3))]

                packed = face[7]
                r = (packed >> 16) & 255
                g = (packed >> 8) & 255
                b = packed & 255
                if d2 > fog_start_sq:
                    fog = (math.sqrt(d2) - fog_start) / fog_span
                    if fog > 1.0:
                        fog = 1.0
                    r = int(r + (sky_r - r) * fog)
                    g = int(g + (sky_g - g) * fog)
                    b = int(b + (sky_b - b) * fog)
                opaque_append((d2, pts, (r, g, b)))
                drawn += 1
                if drawn >= MAX_FACES:
                    break

            tr_faces = []
            for si in range(4):
                sect = mesh[1][si]
                if sect:
                    sy = si * 16
                    if visible(planes, cbx, sy, cbz, cbx + 16, sy + 16, cbz + 16):
                        tr_faces.extend(sect)
            if tr_faces:
                for face in tr_faces:
                    if self._emit(face, cxw, cyw, czw, rel,
                                  rx, ry, rz, ux, uy, uz, fx, fy, fz,
                                  focal, half_w, half_h, near,
                                  max_d2, fog_start, fog_span, sky_r, sky_g, sky_b,
                                  trans_draw):
                        drawn += 1
                        if drawn >= MAX_FACES:
                            break

            if drawn >= MAX_FACES:
                break

        self.faces_drawn = drawn
        self.chunks_drawn = chunks_drawn

        opaque_draw.sort(reverse=True)
        for _d, pts, colour in opaque_draw:
            pygame.draw.polygon(screen, colour, pts)

        if trans_draw:
            overlay = self.overlay
            overlay.fill((0, 0, 0, 0))
            trans_draw.sort(reverse=True)
            for _d, pts, colour in trans_draw:
                pygame.draw.polygon(overlay, colour, pts)
            screen.blit(overlay, (0, 0))

        return drawn

    def _emit(self, face, cxw, cyw, czw, rel,
              rx, ry, rz, ux, uy, uz, fx, fy, fz, focal,
              half_w, half_h, near, max_d2, fog_start, fog_span,
              sky_r, sky_g, sky_b, out):
        mdx = face[8] - cxw
        mdy = face[9] - cyw
        mdz = face[10] - czw
        d2 = mdx * mdx + mdy * mdy + mdz * mdz
        if d2 > max_d2:
            return False
        # reject faces that sit behind the camera plane (cheap, avoids projection)
        if mdx * fx + mdy * fy + mdz * fz < -0.9:
            return False

        pts = self._project(face, cxw, cyw, czw, rel,
                            rx, ry, rz, ux, uy, uz, fx, fy, fz,
                            focal, half_w, half_h, near)
        if pts is None:
            return False
        depth = math.sqrt(d2)
        fog = (depth - fog_start) / fog_span
        if fog < 0.0:
            fog = 0.0
        elif fog > 1.0:
            fog = 1.0
        packed = face[7]
        r = (packed >> 16) & 255
        g = (packed >> 8) & 255
        b = packed & 255
        if fog > 0.0:
            r = int(r + (sky_r - r) * fog)
            g = int(g + (sky_g - g) * fog)
            b = int(b + (sky_b - b) * fog)
        out.append((depth, pts, (r, g, b)))
        return True

    @staticmethod
    def _project(face, cxw, cyw, czw, rel,
                 rx, ry, rz, ux, uy, uz, fx, fy, fz,
                 focal, half_w, half_h, near):
        a0 = face[0] - cxw
        a1 = face[1] - cyw
        a2 = face[2] - czw
        o0 = a0 * rx + a1 * ry + a2 * rz
        o1 = a0 * ux + a1 * uy + a2 * uz
        o2 = a0 * fx + a1 * fy + a2 * fz
        poly = []
        zmin = 1e9
        zmax = -1e9
        for k in (face[3], face[4], face[5], face[6]):
            r = rel[k]
            px = o0 + r[0]
            py = o1 + r[1]
            pz = o2 + r[2]
            poly.append((px, py, pz))
            if pz < zmin:
                zmin = pz
            if pz > zmax:
                zmax = pz

        if zmax < near:
            return None

        if zmin < near:
            clipped = []
            n = len(poly)
            for j in range(n):
                cur = poly[j]
                nxt = poly[(j + 1) % n]
                cur_in = cur[2] >= near
                nxt_in = nxt[2] >= near
                if cur_in:
                    clipped.append(cur)
                if cur_in != nxt_in:
                    t = (near - cur[2]) / (nxt[2] - cur[2])
                    clipped.append((cur[0] + (nxt[0] - cur[0]) * t,
                                    cur[1] + (nxt[1] - cur[1]) * t,
                                    near))
            if len(clipped) < 3:
                return None
            poly = clipped

        pts = []
        min_x = 1e9
        max_x = -1e9
        min_y = 1e9
        max_y = -1e9
        for px, py, pz in poly:
            inv = focal / pz
            sx = half_w + px * inv
            sy = half_h - py * inv
            if sx < min_x:
                min_x = sx
            if sx > max_x:
                max_x = sx
            if sy < min_y:
                min_y = sy
            if sy > max_y:
                max_y = sy
            pts.append((int(sx), int(sy)))
        if max_x < 0 or min_x > half_w * 2 or max_y < 0 or min_y > half_h * 2:
            return None
        # drop sub-pixel faces (invisible, pure draw-call overhead)
        if max_x - min_x < 1.2 and max_y - min_y < 1.2:
            return None
        return pts


# ---------------------------------------------------------------------------
# Sky / time of day
# ---------------------------------------------------------------------------

def sky_palette(t):
    """t in [0,1): 0 = midnight, 0.25 = dawn, 0.5 = noon, 0.75 = dusk."""
    daylight = 0.5 - 0.5 * math.cos(math.tau * t)
    colour = lerp_rgb(SKY_NIGHT, SKY_DAY, daylight)
    # warm tint around dawn and dusk
    twilight = 1.0 - abs(daylight - 0.5) * 2.0
    if twilight > 0.0:
        colour = lerp_rgb(colour, SUNSET, twilight * 0.45)
    return colour, daylight


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------

def draw_crosshair(screen):
    w, h = screen.get_size()
    cx, cy = w // 2, h // 2
    col = (255, 255, 255)
    pygame.draw.line(screen, (0, 0, 0), (cx - 9, cy), (cx + 9, cy), 3)
    pygame.draw.line(screen, (0, 0, 0), (cx, cy - 9), (cx, cy + 9), 3)
    pygame.draw.line(screen, col, (cx - 8, cy), (cx + 8, cy), 1)
    pygame.draw.line(screen, col, (cx, cy - 8), (cx, cy + 8), 1)


def draw_hotbar(screen, font, selected, hotbar):
    w, h = screen.get_size()
    slot = 52
    gap = 4
    count = len(hotbar)
    total = count * slot + (count - 1) * gap
    x0 = (w - total) // 2
    y0 = h - slot - 16
    for i, block in enumerate(hotbar):
        sx = x0 + i * (slot + gap)
        rect = pygame.Rect(sx, y0, slot, slot)
        pygame.draw.rect(screen, (36, 36, 40), rect)
        info = BLOCK_INFO[block]
        swatch = info[2] or (120, 120, 120)
        inner = rect.inflate(-10, -10)
        pygame.draw.rect(screen, swatch, inner)
        pygame.draw.rect(screen, (18, 18, 22), rect, 2)
        if i == selected:
            pygame.draw.rect(screen, (255, 255, 255), rect, 3)
        key = font.render(str(i + 1), True, (220, 220, 220))
        screen.blit(key, (sx + 4, y0 + 2))
    name = BLOCK_INFO[hotbar[selected]][0]
    label = font.render(name, True, (255, 255, 255))
    screen.blit(label, (w // 2 - label.get_width() // 2, y0 - 22))


def draw_hud(screen, big_font, font, small, player, stats):
    w, h = screen.get_size()
    # persistent branding
    title = big_font.render(GAME_TITLE, True, (255, 255, 255))
    shadow = big_font.render(GAME_TITLE, True, (0, 0, 0))
    screen.blit(shadow, (16 + 2, 12 + 2))
    screen.blit(title, (16, 12))
    tag = small.render(GAME_EDITION, True, (230, 230, 230))
    screen.blit(tag, (18, 12 + title.get_height()))

    px, py, pz = player.pos
    lines = [
        f"X {px:8.2f}  Y {py:8.2f}  Z {pz:8.2f}",
        f"FPS {stats['fps']:.0f}   faces {stats['faces']}   chunks {stats['chunks']}",
        f"view {stats['render_distance']}   fly {'on' if stats['flying'] else 'off'}   time {stats['clock']}",
        f"seed {stats['seed']}",
    ]
    for i, text in enumerate(lines):
        surf = font.render(text, True, (255, 255, 255))
        bg = font.render(text, True, (0, 0, 0))
        screen.blit(bg, (16 + 1, 60 + i * 20 + 1))
        screen.blit(surf, (16, 60 + i * 20))

    # health bar
    hearts = int(round(player.health / 2.0))
    for i in range(10):
        hx = 16 + i * 18
        hy = h - 34
        colour = (210, 40, 40) if i < hearts else (60, 60, 60)
        pygame.draw.rect(screen, colour, (hx, hy, 14, 14))
        pygame.draw.rect(screen, (20, 20, 20), (hx, hy, 14, 14), 2)


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

class Player:
    def __init__(self, x, y, z):
        self.pos = [x, y, z]
        self.vel = [0.0, 0.0, 0.0]
        self.yaw = 0.0
        self.pitch = 0.0
        self.on_ground = False
        self.flying = False
        self.health = 20.0

    def respawn(self):
        self.pos = [0.5, WORLD_HEIGHT + 6.0, 0.5]
        self.vel = [0.0, 0.0, 0.0]
        self.health = 20.0


# ---------------------------------------------------------------------------
# The game
# ---------------------------------------------------------------------------

class DeepSeekCraft:
    def __init__(self, seed=None):
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_icon(make_icon())
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 20)
        self.small = pygame.font.Font(None, 17)
        self.big = pygame.font.Font(None, 34)
        self.huge = pygame.font.Font(None, 78)

        self.seed = seed if seed is not None else random.randint(1, 2 ** 31 - 1)
        print(f"{GAME_TITLE} - {GAME_EDITION}  (seed {self.seed}, {TARGET_FPS} FPS)")
        self.world = VoxelWorld(self.seed)
        self.renderer = Renderer(self.screen)
        self.player = Player(0.5, WORLD_HEIGHT + 4.0, 0.5)
        self.pigs = []
        self.hotbar = list(HOTBAR_BLOCKS)
        self.selected = 0
        self.render_distance = RENDER_DISTANCE
        self.auto_view = True
        self.view_work = 0.0
        self.view_frames = 0
        self.view_headroom = 0
        self.view_cooldown = 0
        self.time_of_day = 0.30
        self.time_frozen = False
        self.paused = True
        self.running = True
        self.show_menu = True
        self.last_save_msg = ""
        self.last_save_t = 0.0

        self._preload()

    # -- world bootstrap -------------------------------------------------
    def _preload(self):
        total = 0
        radius = max(3, self.render_distance)
        span = (radius * 2 + 1) ** 2
        step = 0
        for cx in range(-radius, radius + 1):
            for cz in range(-radius, radius + 1):
                self.world.generate_chunk(cx, cz)
                step += 1
                if step % 4 == 0:
                    self._loading_frame(step / span)
        self.world.generate_chunk(0, 0)
        total = step
        # drop the player onto the surface
        h = self.world.height_at(0, 0)
        self.player.pos = [0.5, max(h + 2, SEA_LEVEL + 3), 0.5]
        self._spawn_pigs(12)

    def _loading_frame(self, progress):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit(0)
        self.screen.fill((10, 12, 20))
        t = self.huge.render(GAME_TITLE, True, (245, 245, 255))
        self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 150))
        e = self.big.render(GAME_EDITION, True, (170, 190, 220))
        self.screen.blit(e, (SCREEN_WIDTH // 2 - e.get_width() // 2, 150 + t.get_height()))
        bar = pygame.Rect(SCREEN_WIDTH // 2 - 200, 380, 400, 18)
        pygame.draw.rect(self.screen, (40, 44, 56), bar)
        pygame.draw.rect(self.screen, (90, 170, 250),
                         pygame.Rect(bar.x, bar.y, int(bar.width * clamp(progress, 0, 1)), bar.height))
        pygame.draw.rect(self.screen, (150, 160, 180), bar, 2)
        cap = self.font.render("Generating world...", True, (200, 210, 230))
        self.screen.blit(cap, (SCREEN_WIDTH // 2 - cap.get_width() // 2, 406))
        pygame.display.flip()

    def _spawn_pigs(self, count):
        self.pigs = []
        for _ in range(count):
            cx = self.player.pos[0] + random.uniform(-14, 14)
            cz = self.player.pos[2] + random.uniform(-14, 14)
            h = self.world.height_at(int(cx), int(cz))
            self.pigs.append(Pig(cx, h + 1.2, cz))

    # -- world management ------------------------------------------------
    def new_world(self, seed=None):
        self.seed = seed if seed is not None else random.randint(1, 2 ** 31 - 1)
        self.world = VoxelWorld(self.seed)
        self.player.respawn()
        self.time_of_day = 0.30
        self._preload()

    def save(self):
        payload = {
            "game": GAME_TITLE,
            "edition": GAME_EDITION,
            "seed": self.seed,
            "time_of_day": self.time_of_day,
            "player": {
                "pos": self.player.pos,
                "yaw": self.player.yaw,
                "pitch": self.player.pitch,
                "health": self.player.health,
            },
            "chunks": self.world.to_json(),
        }
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
            self._notify(f"Saved {len(payload['chunks'])} chunks -> {SAVE_FILE}")
        except OSError as exc:
            self._notify(f"Save failed: {exc}")

    def load(self):
        if not os.path.exists(SAVE_PATH):
            self._notify("No save file found")
            return
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, ValueError) as exc:
            self._notify(f"Load failed: {exc}")
            return
        self.seed = payload.get("seed", self.seed)
        self.world = VoxelWorld(self.seed)
        self.world.load_json(payload.get("chunks", {}))
        pdata = payload.get("player", {})
        self.player.pos = list(pdata.get("pos", self.player.pos))
        self.player.yaw = pdata.get("yaw", 0.0)
        self.player.pitch = pdata.get("pitch", 0.0)
        self.player.health = pdata.get("health", 20.0)
        self.player.vel = [0.0, 0.0, 0.0]
        self.time_of_day = payload.get("time_of_day", 0.30)
        self._spawn_pigs(12)
        self._notify(f"Loaded {GAME_TITLE} world (seed {self.seed})")

    def _notify(self, text):
        print(f"[{GAME_TITLE}] {text}")
        self.last_save_msg = text
        self.last_save_t = time.time()

    # -- interaction -----------------------------------------------------
    def target_block(self):
        p = self.player.pos
        eye = (p[0], p[1] + EYE_HEIGHT, p[2])
        sy, cy = math.sin(self.player.yaw), math.cos(self.player.yaw)
        sp, cp = math.sin(self.player.pitch), math.cos(self.player.pitch)
        direction = (sy * cp, sp, -cy * cp)
        return raycast(self.world, eye, direction, REACH_DISTANCE)

    def break_block(self):
        hit = self.target_block()
        if hit is None:
            return
        bx, by, bz, _nx, _ny, _nz = hit
        if by <= 0:
            self._notify("Bedrock cannot be broken")
            return
        self.world.set_block(bx, by, bz, AIR)

    def place_block(self):
        hit = self.target_block()
        if hit is None:
            return
        bx, by, bz, nx, ny, nz = hit
        tx, ty, tz = bx + nx, by + ny, bz + nz
        block = self.hotbar[self.selected]
        if not (0 <= ty < WORLD_HEIGHT):
            return
        existing = self.world.get_block(tx, ty, tz)
        if existing not in (AIR, WATER):
            return
        # do not place a block inside the player
        p = self.player.pos
        if (p[0] - PLAYER_HALF_WIDTH < tx + 1 and p[0] + PLAYER_HALF_WIDTH > tx
                and p[1] < ty + 1 and p[1] + PLAYER_HEIGHT > ty
                and p[2] - PLAYER_HALF_WIDTH < tz + 1 and p[2] + PLAYER_HALF_WIDTH > tz):
            return
        self.world.set_block(tx, ty, tz, block)

    # -- update ----------------------------------------------------------
    def update(self, dt):
        player = self.player
        keys = pygame.key.get_pressed()

        sy, cy = math.sin(player.yaw), math.cos(player.yaw)
        fx, fz = sy, -cy
        rx, rz = cy, sy

        mx = 0.0
        mz = 0.0
        if keys[pygame.K_w]:
            mx += fx
            mz += fz
        if keys[pygame.K_s]:
            mx -= fx
            mz -= fz
        if keys[pygame.K_d]:
            mx += rx
            mz += rz
        if keys[pygame.K_a]:
            mx -= rx
            mz -= rz
        length = math.hypot(mx, mz)
        if length > 0.0:
            mx /= length
            mz /= length

        sprint = keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]
        speed = WALK_SPEED * (SPRINT_MULT if sprint else 1.0)

        if player.flying:
            vy = 0.0
            if keys[pygame.K_SPACE]:
                vy += FLY_SPEED
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                vy -= FLY_SPEED
            player.vel = [mx * FLY_SPEED, vy, mz * FLY_SPEED]
            move_body(self.world, player.pos, player.vel, dt,
                      PLAYER_HALF_WIDTH, PLAYER_HEIGHT)
        else:
            player.vel[0] = mx * speed
            player.vel[2] = mz * speed
            player.vel[1] -= GRAVITY * dt
            if player.vel[1] < -60.0:
                player.vel[1] = -60.0
            if keys[pygame.K_SPACE] and player.on_ground:
                player.vel[1] = JUMP_SPEED
            player.on_ground = move_body(self.world, player.pos, player.vel, dt,
                                         PLAYER_HALF_WIDTH, PLAYER_HEIGHT)

        if player.pos[1] < -20:
            player.respawn()

        if not self.time_frozen:
            self.time_of_day = (self.time_of_day + dt / DAY_LENGTH) % 1.0

        for pig in self.pigs:
            pig.update(self.world, dt)

    # -- render ----------------------------------------------------------
    def render(self, fps):
        sky, daylight = sky_palette(self.time_of_day)
        self.screen.fill(sky)
        self._draw_sun(daylight)
        faces = self.renderer.draw(
            self.world, self.player.pos, self.player.yaw, self.player.pitch,
            self.render_distance, sky,
        )
        self._draw_pigs()
        draw_crosshair(self.screen)
        clock_hours = int(self.time_of_day * 24)
        clock = f"{clock_hours:02d}:{int((self.time_of_day * 24 % 1) * 60):02d}"
        stats = {
            "fps": fps,
            "faces": faces,
            "chunks": self.renderer.chunks_drawn,
            "render_distance": f"{self.render_distance}{' (auto)' if self.auto_view else ''}",
            "flying": self.player.flying,
            "clock": clock,
            "seed": self.seed,
        }
        draw_hud(self.screen, self.big, self.small, self.small, self.player, stats)
        draw_hotbar(self.screen, self.small, self.selected, self.hotbar)
        if self.last_save_msg and time.time() - self.last_save_t < 4.0:
            msg = self.font.render(self.last_save_msg, True, (255, 255, 200))
            self.screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, 44))
        if self.show_menu:
            self._draw_menu()

    def _draw_sun(self, daylight):
        # project a far away sun/moon along the sky arc
        angle = (self.time_of_day - 0.25) * math.tau
        sx = SCREEN_WIDTH * 0.5 + math.cos(angle) * SCREEN_WIDTH * 0.42
        sy = SCREEN_HEIGHT * 0.42 - math.sin(angle) * SCREEN_HEIGHT * 0.55
        if sy > SCREEN_HEIGHT * 0.75:
            return
        is_sun = 0.25 < self.time_of_day < 0.75
        colour = (255, 240, 200) if is_sun else (225, 228, 245)
        radius = 30 if is_sun else 22
        pygame.draw.circle(self.screen, colour, (int(sx), int(sy)), radius)
        glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 240, 200, 60), (radius * 2, radius * 2), radius * 2)
        self.screen.blit(glow, (int(sx) - radius * 2, int(sy) - radius * 2))

    def _draw_pigs(self):
        # simple billboarded boxes: project the pig centre and scale by distance
        w, h = self.screen.get_size()
        focal = (w * 0.5) / math.tan(math.radians(FOV) * 0.5)
        p = self.player.pos
        sy, cy = math.sin(self.player.yaw), math.cos(self.player.yaw)
        sp, cp = math.sin(self.player.pitch), math.cos(self.player.pitch)
        fx, fy, fz = sy * cp, sp, -cy * cp
        rx, ry, rz = cy, 0.0, sy
        ux, uy, uz = -sy * sp, cp, cy * sp
        far = self.render_distance * CHUNK_X
        for pig in self.pigs:
            ax = pig.pos[0] - p[0]
            ay = pig.pos[1] + 0.5 - (p[1] + EYE_HEIGHT)
            az = pig.pos[2] - p[2]
            pz = ax * fx + ay * fy + az * fz
            if pz < 0.4 or pz > far:
                continue
            px = ax * rx + ay * ry + az * rz
            py = ax * ux + ay * uy + az * uz
            inv = focal / pz
            sx = w * 0.5 + px * inv
            syc = h * 0.5 - py * inv
            size = max(3.0, inv * 0.95)
            rect = pygame.Rect(0, 0, int(size), int(size * 0.8))
            rect.center = (int(sx), int(syc))
            pygame.draw.rect(self.screen, (232, 170, 170), rect)
            head = pygame.Rect(0, 0, int(size * 0.5), int(size * 0.45))
            head.center = (int(sx), int(syc - size * 0.45))
            pygame.draw.rect(self.screen, (245, 190, 190), head)
            pygame.draw.rect(self.screen, (120, 70, 70), rect, 1)

    def _draw_menu(self):
        w, h = self.screen.get_size()
        veil = pygame.Surface((w, h), pygame.SRCALPHA)
        veil.fill((6, 10, 22, 170))
        self.screen.blit(veil, (0, 0))

        title = self.huge.render(GAME_TITLE, True, (245, 248, 255))
        self.screen.blit(title, (w // 2 - title.get_width() // 2, 90))
        edition = self.big.render(GAME_EDITION, True, (150, 200, 255))
        self.screen.blit(edition, (w // 2 - edition.get_width() // 2,
                                   90 + title.get_height()))

        lines = [
            "W A S D  walk      SPACE jump      SHIFT sneak",
            "CTRL sprint        F toggle fly    Mouse look",
            "LMB break          RMB place       1-9 / wheel hotbar",
            "T freeze time      [ ] view dist    V auto view",
            "F5 save  F9 load   N new world      ESC pause  Q quit",
        ]
        if self.paused:
            lines.insert(0, "Click or press ENTER to play")
        for i, text in enumerate(lines):
            surf = self.small.render(text, True, (225, 230, 240))
            self.screen.blit(surf, (w // 2 - surf.get_width() // 2, 300 + i * 24))

    # -- events ----------------------------------------------------------
    def _capture_mouse(self, capture):
        self.show_menu = not capture
        self.paused = not capture
        try:
            pygame.event.set_grab(capture)
        except pygame.error:
            pass
        pygame.mouse.set_visible(not capture)
        if capture:
            pygame.mouse.get_rel()
            pygame.event.set_grab(True)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._on_key(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.paused:
                    self._capture_mouse(True)
                elif event.button == 1:
                    self.break_block()
                elif event.button == 3:
                    self.place_block()
                elif event.button == 4:
                    self.selected = (self.selected - 1) % len(self.hotbar)
                elif event.button == 5:
                    self.selected = (self.selected + 1) % len(self.hotbar)
            elif event.type == pygame.MOUSEMOTION and not self.paused:
                dx, dy = event.rel
                self.player.yaw += dx * MOUSE_SENSITIVITY
                self.player.pitch -= dy * MOUSE_SENSITIVITY
                lim = math.radians(89.0)
                self.player.pitch = clamp(self.player.pitch, -lim, lim)

    def _on_key(self, event):
        key = event.key
        if key == pygame.K_ESCAPE:
            if self.paused:
                self._capture_mouse(True)
            else:
                self._capture_mouse(False)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.paused:
                self._capture_mouse(True)
        elif self.paused:
            if key == pygame.K_q:
                self.running = False
            return
        elif key == pygame.K_f:
            self.player.flying = not self.player.flying
            self.player.vel[1] = 0.0
        elif key == pygame.K_t:
            self.time_frozen = not self.time_frozen
            self._notify("Time " + ("frozen" if self.time_frozen else "running"))
        elif key == pygame.K_n:
            self.new_world()
            self._notify("New world generated")
        elif key == pygame.K_F5:
            self.save()
        elif key == pygame.K_F9:
            self.load()
        elif key == pygame.K_LEFTBRACKET:
            self.render_distance = max(MIN_VIEW_DISTANCE, self.render_distance - 1)
            self.auto_view = False
        elif key == pygame.K_RIGHTBRACKET:
            self.render_distance = min(MAX_VIEW_DISTANCE, self.render_distance + 1)
            self.auto_view = False
        elif key == pygame.K_v:
            self.auto_view = not self.auto_view
            self._notify("Auto view " + ("on" if self.auto_view else "off"))
        elif pygame.K_1 <= key <= pygame.K_9:
            slot = key - pygame.K_1
            if slot < len(self.hotbar):
                self.selected = slot

    # -- main loop -------------------------------------------------------
    def run(self):
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        while self.running:
            dt = self.clock.tick(TARGET_FPS) / 1000.0
            if dt > 0.05:
                dt = 0.05
            self.handle_events()
            if not self.running:
                break
            t0 = time.perf_counter()
            if not self.paused:
                self.world.ensure_area(self.player.pos[0], self.player.pos[2],
                                       self.render_distance, budget=2)
                self.update(dt)
            self._ensure_meshes()
            self.render(self.clock.get_fps())
            pygame.display.flip()
            # keep the frame budget so the loop can hold TARGET_FPS
            self.view_work += (time.perf_counter() - t0) * 1000.0
            self.view_frames += 1
            if self.view_frames >= 45:
                self._tune_view()
                self.view_work = 0.0
                self.view_frames = 0
        pygame.quit()

    def _tune_view(self):
        if not self.auto_view:
            return
        avg = self.view_work / max(1, self.view_frames)
        budget = 1000.0 / TARGET_FPS
        if self.view_cooldown > 0:
            self.view_cooldown -= 1
            self.view_headroom = 0
            return
        if avg > budget * 0.90:
            # frames are getting long: shorten the view to protect the FPS
            if self.render_distance > MIN_VIEW_DISTANCE:
                self.render_distance -= 1
                self.view_cooldown = 2
            self.view_headroom = 0
        elif avg < budget * 0.45:
            # plenty of spare time; grow the view only after it holds twice
            self.view_headroom += 1
            if self.view_headroom >= 2 and self.render_distance < MAX_VIEW_DISTANCE:
                self.render_distance += 1
                self.view_headroom = 0
                self.view_cooldown = 2
        else:
            self.view_headroom = 0

    def _ensure_meshes(self):
        budget = 3
        for chunk in self.world.chunks_near(self.player.pos[0], self.player.pos[2],
                                            self.render_distance):
            if chunk.mesh is None or chunk.dirty:
                build_mesh(self.world, chunk)
                budget -= 1
                if budget <= 0:
                    break


# ---------------------------------------------------------------------------
# Icon
# ---------------------------------------------------------------------------

def make_icon():
    size = 32
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((30, 34, 44))
    for y in range(size):
        for x in range(size):
            if (x // 8 + y // 8) % 2 == 0:
                surf.set_at((x, y), (52, 92, 190))
    pygame.draw.rect(surf, (110, 175, 70), (2, 2, size - 4, 10))
    pygame.draw.rect(surf, (134, 110, 72), (2, 10, size - 4, size - 12))
    return surf


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def print_help():
    print(f"""{GAME_TITLE} - {GAME_EDITION}

usage: deepcraft1.x.py [options]

  --seed N        use a specific world seed
  --version       print the version banner and exit
  --selftest [N]  run N frames headless then exit (default 90)
  -h, --help      show this help
""")


def main(argv):
    seed = None
    selftest = 0
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help"):
            print_help()
            return 0
        if arg == "--version":
            print(f"{GAME_TITLE} - {GAME_EDITION}")
            return 0
        if arg == "--seed" and i + 1 < len(argv):
            try:
                seed = int(argv[i + 1])
            except ValueError:
                print("Invalid seed", file=sys.stderr)
                return 2
            i += 2
            continue
        if arg == "--selftest":
            selftest = 90
            if i + 1 < len(argv):
                try:
                    selftest = int(argv[i + 1])
                    i += 1
                except ValueError:
                    pass
            i += 1
            continue
        print(f"Unknown option: {arg}", file=sys.stderr)
        print_help()
        return 2

    if selftest:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    game = DeepSeekCraft(seed)
    if selftest:
        game.paused = False
        game.show_menu = False
        # warm up: stream the whole view in and build every mesh first
        for _ in range(400):
            if game.world.ensure_area(game.player.pos[0], game.player.pos[2],
                                      game.render_distance + 1, budget=16) == 0:
                break
        for chunk in list(game.world.chunks.values()):
            if chunk.mesh is None:
                build_mesh(game.world, chunk)
        for _ in range(20):
            game.update(1.0 / TARGET_FPS)
            game.render(TARGET_FPS)
        start = time.time()
        frames = 0
        while frames < selftest:
            dt = 1.0 / TARGET_FPS
            game.update(dt)
            game.world.ensure_area(game.player.pos[0], game.player.pos[2],
                                   game.render_distance, budget=4)
            game._ensure_meshes()
            game.render(TARGET_FPS)
            frames += 1
        elapsed = time.time() - start
        print(f"selftest ok: {frames} frames in {elapsed:.2f}s "
              f"({frames / max(elapsed, 1e-6):.1f} fps equivalent), "
              f"faces/frame ~{game.renderer.faces_drawn}, "
              f"chunks {len(game.world.chunks)}")
        pygame.quit()
        return 0

    game.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
