# -*- coding: utf-8 -*-
"""
双人大富翁 最终版 - Two-Player Monopoly Game (Final)
包含: 机遇卡/命运卡 + 背景音乐/音效 + 地产抵押系统
专门适配 Windows 3024×2056 高分辨率屏幕
窗口 2400×1600，UI 元素 2.5 倍缩放
"""

import ctypes

# ============ Windows High DPI Awareness ============
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import random
import math
import struct
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Callable
import sys
import subprocess
import os


# ========== Auto-install pygame ==========
def _ensure_pygame():
    try:
        import pygame
        return pygame
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame", "-q"])
        import pygame
        return pygame

pygame = _ensure_pygame()


# ==================== Constants ====================

WINDOW_WIDTH = 2400
WINDOW_HEIGHT = 1600

CELL_SIZE = 120
GRID_SIZE = 11
BOARD_SIZE = CELL_SIZE * GRID_SIZE  # 1320 px

BOARD_X = 220
BOARD_Y = 15
PANEL_X = 1580
PANEL_Y = 15
PANEL_WIDTH = 600
PANEL_HEIGHT = 1320

PLAYER1_COLOR = "#1E88E5"
PLAYER2_COLOR = "#E53935"
PLAYER1_LIGHT = "#BBDEFB"
PLAYER2_LIGHT = "#FFCDD2"

BOARD_BORDER = "#8B4513"
CELL_BG_DEFAULT = "#FFF8DC"
CELL_BG_START = "#A5D6A7"
CELL_BG_JAIL = "#FFCC80"
CELL_BG_PARKING = "#E0E0E0"
CELL_BG_BANKRUPTCY = "#EF9A9A"
CELL_BG_CHANCE = "#FFE0B2"
CELL_BG_COMMUNITY = "#BBDEFB"
CELL_BG_MORTGAGED = "#D7CCC8"  # Brownish-gray overlay for mortgaged cells
CENTER_BG = "#FFF9E6"

BTN_ROLL = "#FF9800"
BTN_BUY = "#4CAF50"
BTN_END = "#2196F3"
BTN_RESTART = "#9E9E9E"
BTN_RULES = "#795548"
BTN_MORTGAGE = "#FF7043"
BTN_MUTE_ON = "#607D8B"
BTN_MUTE_OFF = "#8BC34A"

CARD_BG_CHANCE = "#FFF3E0"
CARD_BORDER_CHANCE = "#E65100"
CARD_BG_COMMUNITY = "#E3F2FD"
CARD_BORDER_COMMUNITY = "#1565C0"

FONT_TITLE = ("Microsoft YaHei", 32, "bold")
FONT_SUBTITLE = ("Microsoft YaHei", 20, "bold")
FONT_PLAYER = ("Microsoft YaHei", 22, "bold")
FONT_PLAYER_INFO = ("Microsoft YaHei", 18)
FONT_PLAYER_SMALL = ("Microsoft YaHei", 16)
FONT_NORMAL = ("Microsoft YaHei", 18)
FONT_BUTTON = ("Microsoft YaHei", 16, "bold")
FONT_CELL_NAME = ("Microsoft YaHei", 13, "bold")
FONT_CELL_PRICE = ("Microsoft YaHei", 11)
FONT_STATUS = ("Microsoft YaHei", 20, "bold")
FONT_LOG = ("Consolas", 14)
FONT_RULES_TITLE = ("Microsoft YaHei", 22, "bold")
FONT_RULES_BODY = ("Microsoft YaHei", 16)
FONT_CENTER_TITLE = ("Microsoft YaHei", 42, "bold")
FONT_CENTER_SUB = ("Microsoft YaHei", 24, "italic")
FONT_DICE_NUM = ("Microsoft YaHei", 60, "bold")
FONT_CARD_TITLE = ("Microsoft YaHei", 20, "bold")
FONT_CARD_BODY = ("Microsoft YaHei", 16)
FONT_CARD_ICON = ("Microsoft YaHei", 28)
FONT_MORTGAGE_TITLE = ("Microsoft YaHei", 18, "bold")
FONT_MORTGAGE_ITEM = ("Microsoft YaHei", 14)

PIECE_SIZE = 40
PIECE_OFFSET = 18
INITIAL_CASH = 1500
CARD_DISPLAY_MS = 3500
CARD_FADE_STEPS = 6

# Audio
SAMPLE_RATE = 22050
BGM_VOLUME_DEFAULT = 0.3
SFX_VOLUME_DEFAULT = 0.5


# ==================== Audio System ====================

class AudioManager:
    """Manages all game audio using pygame synthesised sounds."""

    def __init__(self):
        try:
            pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
        except Exception:
            pass
        self.bgm_volume = BGM_VOLUME_DEFAULT
        self.sfx_volume = SFX_VOLUME_DEFAULT
        self.muted = False
        self._bgm_channel: Optional[pygame.mixer.Channel] = None
        self._sfx_channel: Optional[pygame.mixer.Channel] = None
        self._bgm_playing = False
        try:
            self._bgm_channel = pygame.mixer.Channel(0)
            self._sfx_channel = pygame.mixer.Channel(1)
        except Exception:
            pass

    # ── Sound generators ──

    def _gen_sound(self, freq: float, duration: float, wave: str = "sine",
                   decay: bool = True, volume: float = 1.0) -> pygame.mixer.Sound:
        """Generate a synthetic sound."""
        n_samples = int(SAMPLE_RATE * duration)
        buf = []
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            env = 1.0 - (i / n_samples) if decay else 1.0
            if wave == "sine":
                val = math.sin(2 * math.pi * freq * t)
            elif wave == "square":
                val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            elif wave == "triangle":
                phase = (freq * t) % 1.0
                val = 4.0 * abs(phase - 0.5) - 1.0
            elif wave == "noise":
                val = random.uniform(-1, 1)
            else:
                val = math.sin(2 * math.pi * freq * t)
            sample = int(val * env * volume * 16000)
            sample = max(-32767, min(32767, sample))
            buf.append(struct.pack('<h', sample))
        raw = b''.join(buf)
        try:
            return pygame.mixer.Sound(buffer=raw)
        except Exception:
            return None

    def _play_sfx(self, freq: float, duration: float, wave: str = "sine"):
        """Play a short sound effect."""
        if self.muted:
            return
        snd = self._gen_sound(freq, duration, wave, volume=self.sfx_volume)
        if snd and self._sfx_channel:
            snd.set_volume(self.sfx_volume)
            self._sfx_channel.play(snd)

    def _play_combo(self, notes: List[Tuple[float, float]], wave: str = "sine"):
        """Play a sequence of notes in quick succession."""
        if self.muted:
            return
        total = sum(d for _, d in notes)
        n_samples = int(SAMPLE_RATE * total)
        buf = []
        t_offset = 0
        for freq, duration in notes:
            n = int(SAMPLE_RATE * duration)
            for i in range(n):
                t = (t_offset + i) / SAMPLE_RATE
                env = max(0, 1.0 - (i / n))
                if wave == "sine":
                    val = math.sin(2 * math.pi * freq * t)
                elif wave == "square":
                    val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
                else:
                    val = math.sin(2 * math.pi * freq * t)
                sample = int(val * env * self.sfx_volume * 16000)
                sample = max(-32767, min(32767, sample))
                buf.append(struct.pack('<h', sample))
            t_offset += duration
        raw = b''.join(buf)
        try:
            snd = pygame.mixer.Sound(buffer=raw)
            snd.set_volume(self.sfx_volume)
            if self._sfx_channel:
                self._sfx_channel.play(snd)
        except Exception:
            pass

    # ── SFX methods ──

    def sfx_roll_dice(self):
        self._play_sfx(80, 0.15, "noise")
        self._play_combo([(300, 0.05), (400, 0.05), (500, 0.08)], "square")

    def sfx_move(self):
        self._play_sfx(200, 0.04, "square")

    def sfx_buy(self):
        self._play_combo([(523, 0.08), (659, 0.08), (784, 0.12)], "sine")

    def sfx_rent(self):
        self._play_combo([(400, 0.08), (300, 0.12)], "sine")

    def sfx_chance(self):
        self._play_combo([(440, 0.06), (554, 0.06), (659, 0.06), (880, 0.1)], "triangle")

    def sfx_community(self):
        self._play_combo([(330, 0.06), (440, 0.06), (523, 0.06), (659, 0.1)], "triangle")

    def sfx_jail(self):
        self._play_combo([(400, 0.1), (300, 0.1), (200, 0.15)], "square")

    def sfx_jail_free(self):
        self._play_combo([(523, 0.06), (659, 0.06), (784, 0.06), (1047, 0.12)], "sine")

    def sfx_bankrupt(self):
        self._play_combo([(600, 0.12), (400, 0.12), (200, 0.12), (100, 0.3)], "square")

    def sfx_win(self):
        self._play_combo([(523, 0.1), (659, 0.1), (784, 0.1), (1047, 0.1),
                          (784, 0.1), (1047, 0.2)], "sine")

    def sfx_click(self):
        self._play_sfx(800, 0.03, "sine")

    def sfx_card_draw(self):
        self._play_sfx(600, 0.08, "triangle")

    def sfx_game_start(self):
        self._play_combo([(392, 0.1), (523, 0.1), (659, 0.1), (784, 0.15)], "sine")

    # ── Background Music ──

    def _generate_bgm(self) -> Optional[pygame.mixer.Sound]:
        """Generate looping background music melody."""
        # Simple melody: C-D-E-F-G-A-B-C pattern
        melody = [
            (262, 0.3), (294, 0.3), (330, 0.3), (349, 0.3),
            (392, 0.3), (440, 0.3), (494, 0.3), (523, 0.3),
            (494, 0.3), (440, 0.3), (392, 0.3), (349, 0.3),
            (330, 0.3), (294, 0.3), (262, 0.3), (330, 0.3),
            (349, 0.3), (392, 0.3), (440, 0.3), (392, 0.3),
            (349, 0.3), (330, 0.3), (294, 0.3), (262, 0.4),
        ]
        total_dur = sum(d for _, d in melody) + 0.3
        n_samples = int(SAMPLE_RATE * total_dur)
        buf = []
        t_offset = 0
        for freq, duration in melody:
            n = int(SAMPLE_RATE * duration)
            for i in range(n):
                t = (t_offset + i) / SAMPLE_RATE
                env = 0.85
                # Soft attack/release
                attack = min(1.0, i / (SAMPLE_RATE * 0.02))
                release = max(0.0, 1.0 - max(0, i - n + SAMPLE_RATE * 0.03) / (SAMPLE_RATE * 0.03))
                env *= attack * release
                val = math.sin(2 * math.pi * freq * t) * 0.6
                val += math.sin(2 * math.pi * freq * 2 * t) * 0.2  # harmonic
                val += math.sin(2 * math.pi * freq * 3 * t) * 0.1
                sample = int(val * env * self.bgm_volume * 12000)
                sample = max(-32767, min(32767, sample))
                buf.append(struct.pack('<h', sample))
            t_offset += duration
        # Silence gap
        silent = int(SAMPLE_RATE * 0.3)
        for _ in range(silent):
            buf.append(struct.pack('<h', 0))
        raw = b''.join(buf)
        try:
            return pygame.mixer.Sound(buffer=raw)
        except Exception:
            return None

    def start_bgm(self):
        """Start looping background music."""
        if self.muted or self._bgm_playing:
            return
        try:
            snd = self._generate_bgm()
            if snd and self._bgm_channel:
                snd.set_volume(self.bgm_volume)
                self._bgm_channel.play(snd, loops=-1)
                self._bgm_playing = True
        except Exception:
            pass

    def stop_bgm(self):
        """Stop background music."""
        try:
            if self._bgm_channel:
                self._bgm_channel.stop()
            self._bgm_playing = False
        except Exception:
            pass

    def set_bgm_volume(self, vol: float):
        self.bgm_volume = vol
        if self._bgm_channel and self._bgm_playing:
            self._bgm_channel.set_volume(vol)

    def set_sfx_volume(self, vol: float):
        self.sfx_volume = vol

    def toggle_mute(self) -> bool:
        """Toggle mute. Returns new mute state."""
        self.muted = not self.muted
        if self.muted:
            self.stop_bgm()
        else:
            self.start_bgm()
        return self.muted


# ==================== Enums & Data Classes ====================

class CellType(Enum):
    START = "start"
    PROPERTY = "property"
    JAIL = "jail"
    FREE_PARKING = "free_parking"
    BANKRUPTCY = "bankruptcy"
    CHANCE = "chance"
    COMMUNITY_CHEST = "community"


class CardType(Enum):
    CHANCE = "chance"
    COMMUNITY_CHEST = "community"


@dataclass
class Card:
    card_type: CardType
    title: str
    description: str
    effect: Callable[['GameEngine', int], str]
    keepable: bool = False


@dataclass
class BoardCell:
    name: str
    price: int
    cell_type: CellType
    row: int
    col: int
    owner: Optional[int] = None
    mortgaged: bool = False   # 是否已抵押


@dataclass
class Player:
    name: str
    color: str
    light_color: str
    cash: int = INITIAL_CASH
    position: int = 0
    properties: List[int] = field(default_factory=list)
    skip_turn: bool = False
    jail_free_cards: int = 0


# ==================== Card Deck ====================

class CardDeck:
    def __init__(self, cards: List[Card]):
        self._all_cards = list(cards)
        self._draw_pile: List[Card] = []
        self._discard: List[Card] = []
        self.shuffle()

    def shuffle(self):
        combined = self._all_cards + self._discard
        self._draw_pile = list(combined)
        random.shuffle(self._draw_pile)
        self._discard = []

    def draw(self) -> Optional[Card]:
        if not self._draw_pile:
            self.shuffle()
        if self._draw_pile:
            card = self._draw_pile.pop(0)
            if not card.keepable:
                self._discard.append(card)
            return card
        return None

    def return_keepable(self, card: Card):
        self._discard.append(card)


# ==================== Card Effect Functions ====================

def _go_to_jail(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    player.position = 30
    player.skip_turn = True
    return "直接进监狱，不经过起点，暂停一回合！"


def _chance_go_to_start(engine, p): engine.players[p].position = 0; engine.players[p].cash += 200; return "前进到起点，获得 200 元！"

def _chance_go_to_pos25(engine, p):
    player = engine.players[p]; target = 25; old = player.position
    if target < old: player.cash += 200
    player.position = target; cell = engine.get_cell(target)
    if cell.owner is None: return f"前进到 {cell.name}(¥{cell.price})，可购买"
    elif cell.owner == p: return f"前进到 {cell.name}，这是你的地产"
    else:
        rent = max(1, int(cell.price * 0.1)) * 2; player.cash -= rent
        engine.players[cell.owner].cash += rent
        return f"前进到 {cell.name}，支付双倍过路费 ¥{rent}"

def _chance_go_to_pos35(engine, p):
    player = engine.players[p]; target = 35; old = player.position
    if target < old: player.cash += 200
    player.position = target; cell = engine.get_cell(target)
    if cell.owner is None: return f"前进到 {cell.name}(¥{cell.price})，可购买"
    elif cell.owner == p: return f"前进到 {cell.name}，这是你的地产"
    else:
        fee = (engine.dice1 + engine.dice2) * 10; player.cash -= fee
        engine.players[cell.owner].cash += fee
        return f"前进到 {cell.name}，支付 10倍骰子 ¥{fee}"

def _chance_dividend(engine, p): engine.players[p].cash += 50; return "银行支付股息 50 元！"
def _chance_jail_free(engine, p): engine.players[p].jail_free_cards += 1; return "获得「出狱免费卡」一张！"
def _chance_go_back_3(engine, p): engine.players[p].position = (engine.players[p].position - 3) % 40; return "后退 3 格"
def _chance_speed_fine(engine, p): engine.players[p].cash -= 15; return "超速罚款 15 元"
def _chance_pay_each(engine, p):
    engine.players[p].cash -= 50; engine.players[1-p].cash += 50
    return f"向 {engine.players[1-p].name} 支付 50 元"
def _chance_loan(engine, p): engine.players[p].cash += 150; return "建筑贷款到期，获得 150 元"
def _chance_crossword(engine, p): engine.players[p].cash += 100; return "赢得填字比赛，获得 100 元"
def _chance_go_to_pos26(engine, p):
    t=26; engine.players[p].position=t
    if engine.players[p].position < engine.players[p].position: engine.players[p].cash+=200
    return f"前进到商业街（{engine.get_cell(t).name}）"
def _chance_go_to_pos38(engine, p):
    player=engine.players[p]; t=38
    if t<player.position: player.cash+=200
    player.position=t; return f"前进到公园大道（{engine.get_cell(t).name}）"
def _chance_repairs(engine, p):
    player=engine.players[p]; cost=len(player.properties)*30; player.cash-=cost
    return f"房产维修，为 {len(player.properties)} 处地产支付 {cost} 元"
def _chance_lottery(engine, p): engine.players[p].cash+=200; return "中彩票，获得 200 元！"
def _chance_stock(engine, p): engine.players[p].cash+=300; return "股市大涨，获得 300 元！"

def _comm_go_to_start(engine, p): engine.players[p].position=0; engine.players[p].cash+=200; return "前进到起点，获得 200 元！"
def _comm_bank_error(engine, p): engine.players[p].cash+=200; return "银行出错，多给了 200 元！"
def _comm_doctor(engine, p): engine.players[p].cash-=50; return "看医生，支付 50 元"
def _comm_jail_free(engine, p): engine.players[p].jail_free_cards+=1; return "获得「出狱免费卡」一张！"
def _comm_go_to_jail(engine, p): return _go_to_jail(engine, p)
def _comm_birthday(engine, p):
    engine.players[1-p].cash-=50; engine.players[p].cash+=50
    return f"生日快乐！{engine.players[1-p].name} 给你 50 元"
def _comm_opera(engine, p):
    engine.players[1-p].cash-=30; engine.players[p].cash+=30
    return f"歌剧之夜，{engine.players[1-p].name} 支付 30 元"
def _comm_tax_refund(engine, p): engine.players[p].cash+=20; return "所得税退款，获得 20 元"
def _comm_insurance(engine, p): engine.players[p].cash+=100; return "人寿保险到期，获得 100 元"
def _comm_hospital(engine, p): engine.players[p].cash-=100; return "住院费用，支付 100 元"
def _comm_tuition(engine, p): engine.players[p].cash-=50; return "学费，支付 50 元"
def _comm_consult(engine, p): engine.players[p].cash+=25; return "咨询费，获得 25 元"
def _comm_street_repair(engine, p):
    player=engine.players[p]; cost=len(player.properties)*40; player.cash-=cost
    return f"街道维修，支付 {cost} 元"
def _comm_beauty(engine, p): engine.players[p].cash+=10; return "选美第二名，获得 10 元"
def _comm_inherit(engine, p): engine.players[p].cash+=100; return "继承遗产，获得 100 元"
def _comm_stock_sale(engine, p): engine.players[p].cash+=50; return "股票出售，获得 50 元"


def create_chance_deck() -> CardDeck:
    cards = [
        Card(CardType.CHANCE, "前进到起点", "前进到起点，获得 200 元", _chance_go_to_start),
        Card(CardType.CHANCE, "前进", "前进到餐厅(¥240)，无人可买/否则双倍过路费", _chance_go_to_pos25),
        Card(CardType.CHANCE, "前进", "前进到银行(¥320)，无人可买/否则10倍骰子", _chance_go_to_pos35),
        Card(CardType.CHANCE, "股息", "银行支付你股息 50 元", _chance_dividend),
        Card(CardType.CHANCE, "出狱免费", "出狱免费卡（可保留使用）", _chance_jail_free, keepable=True),
        Card(CardType.CHANCE, "后退", "后退 3 格", _chance_go_back_3),
        Card(CardType.CHANCE, "进监狱", "直接进监狱，不经过起点", lambda e, p: _go_to_jail(e, p)),
        Card(CardType.CHANCE, "超速罚款", "超速罚款 15 元", _chance_speed_fine),
        Card(CardType.CHANCE, "董事会主席", "向每位玩家支付 50 元", _chance_pay_each),
        Card(CardType.CHANCE, "贷款到期", "建筑贷款到期，获得 150 元", _chance_loan),
        Card(CardType.CHANCE, "填字比赛", "赢得填字比赛，获得 100 元", _chance_crossword),
        Card(CardType.CHANCE, "前进", "前进到商场(¥260)", _chance_go_to_pos26),
        Card(CardType.CHANCE, "前进", "前进到摩天大楼(¥400)", _chance_go_to_pos38),
        Card(CardType.CHANCE, "维修", "每处地产支付 30 元维修费", _chance_repairs),
        Card(CardType.CHANCE, "彩票", "中彩票，获得 200 元", _chance_lottery),
        Card(CardType.CHANCE, "股市大涨", "股市大涨，获得 300 元", _chance_stock),
    ]
    return CardDeck(cards)


def create_community_deck() -> CardDeck:
    cards = [
        Card(CardType.COMMUNITY_CHEST, "前进到起点", "前进到起点，获得 200 元", _comm_go_to_start),
        Card(CardType.COMMUNITY_CHEST, "银行出错", "银行出错，多给了你 200 元", _comm_bank_error),
        Card(CardType.COMMUNITY_CHEST, "看医生", "看医生，支付 50 元", _comm_doctor),
        Card(CardType.COMMUNITY_CHEST, "出狱免费", "出狱免费卡（可保留使用）", _comm_jail_free, keepable=True),
        Card(CardType.COMMUNITY_CHEST, "进监狱", "直接进监狱，不经过起点", _comm_go_to_jail),
        Card(CardType.COMMUNITY_CHEST, "生日", "从每位玩家获得 50 元生日礼金", _comm_birthday),
        Card(CardType.COMMUNITY_CHEST, "歌剧之夜", "向每位玩家收取 30 元门票费", _comm_opera),
        Card(CardType.COMMUNITY_CHEST, "退税", "所得税退款，获得 20 元", _comm_tax_refund),
        Card(CardType.COMMUNITY_CHEST, "人寿保险", "人寿保险到期，获得 100 元", _comm_insurance),
        Card(CardType.COMMUNITY_CHEST, "住院", "住院费用，支付 100 元", _comm_hospital),
        Card(CardType.COMMUNITY_CHEST, "学费", "学费，支付 50 元", _comm_tuition),
        Card(CardType.COMMUNITY_CHEST, "咨询费", "咨询费，获得 25 元", _comm_consult),
        Card(CardType.COMMUNITY_CHEST, "街道维修", "每处地产支付 40 元维修费", _comm_street_repair),
        Card(CardType.COMMUNITY_CHEST, "选美比赛", "选美比赛第二名，获得 10 元", _comm_beauty),
        Card(CardType.COMMUNITY_CHEST, "继承遗产", "继承遗产，获得 100 元", _comm_inherit),
        Card(CardType.COMMUNITY_CHEST, "股票出售", "股票出售，获得 50 元", _comm_stock_sale),
    ]
    return CardDeck(cards)


# ==================== Game Engine ====================

class GameEngine:
    """Pure game logic, independent of UI."""

    CARD_CELLS = {7: CellType.CHANCE, 22: CellType.CHANCE,
                  12: CellType.COMMUNITY_CHEST, 36: CellType.COMMUNITY_CHEST}
    CARD_CELL_NAMES = {7: ("机遇", CellType.CHANCE), 22: ("机遇", CellType.CHANCE),
                       12: ("命运", CellType.COMMUNITY_CHEST), 36: ("命运", CellType.COMMUNITY_CHEST)}

    PROPERTY_DEFS = {
        1: ("村庄", 60), 2: ("农田", 60), 3: ("果园", 80), 4: ("渔村", 80),
        5: ("牧场", 100), 6: ("林场", 100), 8: ("集市", 100), 9: ("小商店", 120),
        11: ("面包店", 120), 13: ("书店", 140), 14: ("花店", 160), 15: ("服装店", 160),
        16: ("药店", 180), 17: ("小餐馆", 180), 18: ("电影院", 200), 19: ("健身房", 200),
        21: ("超市", 200), 23: ("医院", 220), 24: ("学校", 240), 25: ("餐厅", 240),
        26: ("商场", 260), 27: ("写字楼", 260), 28: ("体育馆", 280), 29: ("剧院", 280),
        31: ("博物馆", 280), 32: ("图书馆", 280), 33: ("游泳馆", 300), 34: ("大酒店", 300),
        35: ("银行", 320), 37: ("游乐园", 380), 38: ("摩天大楼", 400), 39: ("宫殿", 400),
    }
    CORNER_DEFS = {0: ("起点", CellType.START), 10: ("破产", CellType.BANKRUPTCY),
                   20: ("免费停车", CellType.FREE_PARKING), 30: ("监狱", CellType.JAIL)}

    def __init__(self, audio: Optional[AudioManager] = None):
        self.audio = audio
        self.players: List[Player] = []
        self.board: List[BoardCell] = []
        self.current_player_idx: int = 0
        self.dice1: int = 0
        self.dice2: int = 0
        self.log: List[str] = []
        self.game_over: bool = False
        self.winner: Optional[Player] = None
        self.chance_deck = create_chance_deck()
        self.community_deck = create_community_deck()
        self.last_drawn_card: Optional[Card] = None
        self._init_board()
        self._init_players()

    def _init_board(self):
        self.board = []
        for pos in range(40):
            row, col = self._pos_to_grid(pos)
            if pos in self.CORNER_DEFS:
                name, cell_type = self.CORNER_DEFS[pos]; price = 0
            elif pos in self.CARD_CELLS:
                name, cell_type = self.CARD_CELL_NAMES[pos]; price = 0
            else:
                name, price = self.PROPERTY_DEFS.get(pos, ("未知", 0))
                cell_type = CellType.PROPERTY
            self.board.append(BoardCell(name=name, price=price, cell_type=cell_type, row=row, col=col))

    def _init_players(self):
        self.players = [
            Player(name="玩家 1", color=PLAYER1_COLOR, light_color=PLAYER1_LIGHT),
            Player(name="玩家 2", color=PLAYER2_COLOR, light_color=PLAYER2_LIGHT),
        ]
        self.current_player_idx = 0; self.game_over = False; self.winner = None

    @staticmethod
    def _pos_to_grid(pos: int) -> Tuple[int, int]:
        if pos <= 10: return (10, pos)
        elif pos <= 20: return (20 - pos, 10)
        elif pos <= 30: return (0, 30 - pos)
        else: return (pos - 30, 0)

    @property
    def current_player(self) -> Player: return self.players[self.current_player_idx]

    def get_cell(self, pos: int) -> BoardCell: return self.board[pos]

    def roll_dice(self) -> Tuple[int, int]:
        self.dice1 = random.randint(1, 6); self.dice2 = random.randint(1, 6)
        self.add_log(f"{self.current_player.name} 掷出了 [{self.dice1}] 和 [{self.dice2}]，共 {self.dice1 + self.dice2} 点")
        return self.dice1, self.dice2

    def draw_card(self, cell_type: CellType) -> Card:
        deck = self.chance_deck if cell_type == CellType.CHANCE else self.community_deck
        card = deck.draw(); self.last_drawn_card = card
        card_name = "机遇卡" if cell_type == CellType.CHANCE else "命运卡"
        self.add_log(f"🃏 {self.current_player.name} 抽到 {card_name}：「{card.title}」— {card.description}")
        return card

    def use_jail_free_card(self, player_idx: int) -> bool:
        player = self.players[player_idx]
        if player.jail_free_cards > 0:
            player.jail_free_cards -= 1; player.skip_turn = False
            self.add_log(f"🃏 {player.name} 使用了出狱免费卡！"); return True
        return False

    def execute_card_effect(self, player_idx: int, card: Card) -> str:
        result = card.effect(self, player_idx); self.add_log(f"  → {result}"); return result

    # ── Mortgage System ──

    def mortgage_property(self, player_idx: int, pos: int) -> Tuple[bool, str]:
        """Mortgage a property. Returns (success, message)."""
        player = self.players[player_idx]
        if pos not in player.properties:
            return False, "你不是该地产的拥有者。"
        cell = self.get_cell(pos)
        if cell.mortgaged:
            return False, "该地产已被抵押。"
        if cell.cell_type != CellType.PROPERTY:
            return False, "只有地产可以抵押。"
        mortgage_value = int(cell.price * 0.5)
        cell.mortgaged = True
        player.cash += mortgage_value
        self.add_log(f"🏚️ {player.name} 抵押了 {cell.name}，获得 {mortgage_value} 元")
        return True, f"成功抵押 {cell.name}，获得 ¥{mortgage_value}"

    def redeem_property(self, player_idx: int, pos: int) -> Tuple[bool, str]:
        """Redeem a mortgaged property. Returns (success, message)."""
        player = self.players[player_idx]
        if pos not in player.properties:
            return False, "你不是该地产的拥有者。"
        cell = self.get_cell(pos)
        if not cell.mortgaged:
            return False, "该地产未被抵押。"
        mortgage_value = int(cell.price * 0.5)
        redeem_cost = int(mortgage_value * 1.1)
        if player.cash < redeem_cost:
            return False, f"现金不足！赎回需要 ¥{redeem_cost}，你只有 ¥{player.cash}"
        player.cash -= redeem_cost
        cell.mortgaged = False
        self.add_log(f"🏠 {player.name} 赎回 {cell.name}，支付 ¥{redeem_cost}（本金+10%利息）")
        return True, f"成功赎回 {cell.name}，支付 ¥{redeem_cost}"

    def get_mortgageable_properties(self, player_idx: int) -> List[int]:
        """Get list of property positions that can be mortgaged."""
        player = self.players[player_idx]
        return [p for p in player.properties if not self.get_cell(p).mortgaged]

    def get_mortgaged_properties(self, player_idx: int) -> List[int]:
        """Get list of property positions that are currently mortgaged."""
        player = self.players[player_idx]
        return [p for p in player.properties if self.get_cell(p).mortgaged]

    def get_mortgage_value(self, pos: int) -> int:
        return int(self.get_cell(pos).price * 0.5)

    def get_redeem_cost(self, pos: int) -> int:
        return int(self.get_cell(pos).price * 0.5 * 1.1)

    # ── Core game logic ──

    def process_landing(self) -> str:
        player = self.current_player; cell = self.get_cell(player.position)

        if cell.cell_type == CellType.START:
            player.cash += 200
            self.add_log(f"🎉 {player.name} 到达起点，获得 200 元奖励！"); return "start"
        elif cell.cell_type == CellType.JAIL:
            player.skip_turn = True
            self.add_log(f"🔒 {player.name} 进入监狱，暂停一回合！"); return "jail"
        elif cell.cell_type == CellType.FREE_PARKING:
            self.add_log(f"🅿️ {player.name} 在免费停车，什么都不做。"); return "parking"
        elif cell.cell_type == CellType.BANKRUPTCY:
            penalty = 150; player.cash -= penalty
            self.add_log(f"💸 {player.name} 走到破产格，缴纳 {penalty} 元罚金！")
            if player.cash < 0 and not self._can_avoid_bankruptcy(player):
                self._declare_bankruptcy(player); return "bankrupt"
            return "penalty"
        elif cell.cell_type in (CellType.CHANCE, CellType.COMMUNITY_CHEST):
            return "chance" if cell.cell_type == CellType.CHANCE else "community"
        elif cell.cell_type == CellType.PROPERTY:
            if cell.owner is None: return "buyable"
            elif cell.owner == self.current_player_idx:
                self.add_log(f"🏠 这是 {player.name} 自己的地产。"); return "own"
            else:
                if cell.mortgaged:
                    self.add_log(f"🏚️ {cell.name} 已被抵押，无需支付过路费。"); return "own"
                rent = max(1, int(cell.price * 0.1)); player.cash -= rent
                self.players[cell.owner].cash += rent
                self.add_log(f"💰 {player.name} 向 {self.players[cell.owner].name} 支付了 {rent} 元过路费！")
                if player.cash < 0 and not self._can_avoid_bankruptcy(player):
                    self._declare_bankruptcy(player); return "bankrupt"
                return "rent"
        return "unknown"

    def _can_avoid_bankruptcy(self, player: Player) -> bool:
        """Check if player can avoid bankruptcy by mortgaging properties."""
        mortgageable = [p for p in player.properties if not self.get_cell(p).mortgaged]
        return len(mortgageable) > 0

    def buy_property(self) -> Tuple[bool, str]:
        player = self.current_player; cell = self.get_cell(player.position)
        if cell.cell_type != CellType.PROPERTY: return False, "当前位置不是地产。"
        if cell.owner is not None: return False, "该地产已被购买。"
        if cell.mortgaged: return False, "该地产已被抵押，无法购买。"
        if player.cash < cell.price: return False, f"现金不足！需要 {cell.price} 元，你只有 {player.cash} 元。"
        player.cash -= cell.price; cell.owner = self.current_player_idx
        player.properties.append(player.position)
        self.add_log(f"🏠 {player.name} 购买了 {cell.name}，花费 {cell.price} 元！")
        return True, f"成功购买 {cell.name}！"

    def _declare_bankruptcy(self, player: Player):
        # Foreclose all mortgaged properties
        for pos in player.properties:
            cell = self.get_cell(pos)
            if cell.mortgaged:
                cell.mortgaged = False; cell.owner = None
                self.add_log(f"🏚️ 银行收回了 {cell.name}")
        player.properties.clear()
        self.game_over = True
        self.winner = self.players[1 - self.players.index(player)]
        self.add_log(f"💀 {player.name} 破产了！{self.winner.name} 获胜！🎉")

    def next_turn(self):
        self.current_player_idx = 1 - self.current_player_idx
        self.dice1 = 0; self.dice2 = 0
        if not self.game_over: self.add_log(f"➡️ 轮到 {self.current_player.name} 行动")

    def check_jail_skip(self) -> bool:
        player = self.current_player
        if player.skip_turn:
            if player.jail_free_cards > 0: return False
            player.skip_turn = False
            self.add_log(f"🔒 {player.name} 在监狱中，本回合跳过！"); return True
        return False

    def reset(self):
        self.chance_deck = create_chance_deck(); self.community_deck = create_community_deck()
        self.last_drawn_card = None
        self._init_board(); self._init_players()
        self.log.clear(); self.dice1 = 0; self.dice2 = 0
        self.add_log("🎮 游戏开始！双人大富翁（含卡片/抵押/音效）！")
        self.add_log(f"➡️ 轮到 {self.current_player.name} 行动")

    def add_log(self, message: str): self.log.append(message)

    def get_total_property_value(self, player_idx: int) -> int:
        return sum(self.board[p].price for p in self.players[player_idx].properties)


# ==================== Board Canvas ====================

class BoardCanvas(tk.Canvas):
    def __init__(self, parent, engine: GameEngine, **kwargs):
        super().__init__(parent, width=BOARD_SIZE, height=BOARD_SIZE, bg="#2C1810", highlightthickness=0, **kwargs)
        self.engine = engine; self.piece_ids: dict = {}; self.cell_rects: dict = {}
        self.dice1_text: int = 0; self.dice2_text: int = 0
        self._draw_all()

    def _draw_all(self): self._draw_board(); self._draw_center(); self._draw_pieces()

    def _draw_board(self):
        for pos in range(40): self._draw_cell(self.engine.get_cell(pos), pos)

    def _draw_cell(self, cell: BoardCell, pos: int):
        x1 = cell.col * CELL_SIZE; y1 = cell.row * CELL_SIZE; x2 = x1 + CELL_SIZE; y2 = y1 + CELL_SIZE

        if cell.owner is not None:
            fill = self.engine.players[cell.owner].light_color
        elif cell.cell_type == CellType.START: fill = CELL_BG_START
        elif cell.cell_type == CellType.JAIL: fill = CELL_BG_JAIL
        elif cell.cell_type == CellType.FREE_PARKING: fill = CELL_BG_PARKING
        elif cell.cell_type == CellType.BANKRUPTCY: fill = CELL_BG_BANKRUPTCY
        elif cell.cell_type == CellType.CHANCE: fill = CELL_BG_CHANCE
        elif cell.cell_type == CellType.COMMUNITY_CHEST: fill = CELL_BG_COMMUNITY
        else: fill = CELL_BG_DEFAULT

        rect_id = self.create_rectangle(x1 + 1, y1 + 1, x2 - 1, y2 - 1, fill=fill,
                                         outline=BOARD_BORDER, width=2, tags="cell")
        self.cell_rects[pos] = rect_id

        # Mortgage overlay
        if cell.mortgaged:
            self.create_rectangle(x1 + 1, y1 + 1, x2 - 1, y2 - 1,
                                  fill="", outline="#FF0000", width=3, stipple="gray25", tags="cell")
            cx_m = x1 + CELL_SIZE // 2; cy_m = y1 + CELL_SIZE // 2
            self.create_text(cx_m, cy_m - 25, text="已抵押", font=("Microsoft YaHei", 11, "bold"),
                             fill="#C62828", tags="cell")

        if cell.owner is not None:
            self.create_rectangle(x1 + 1, y1 + 1, x2 - 1, y1 + 8,
                                  fill=self.engine.players[cell.owner].color, outline="", tags="cell")

        cx = x1 + CELL_SIZE // 2; name_y = y1 + CELL_SIZE // 2 - 14
        self.create_text(cx, name_y, text=cell.name, font=FONT_CELL_NAME, fill="#333333", tags="cell")

        price_y = y1 + CELL_SIZE // 2 + 14
        if cell.cell_type == CellType.PROPERTY:
            txt = f"¥{cell.price}" if not cell.mortgaged else f"¥{cell.price} [押]"
            self.create_text(cx, price_y, text=txt, font=FONT_CELL_PRICE, fill="#666666", tags="cell")
        elif cell.cell_type == CellType.START: self.create_text(cx, price_y, text="← 出发", font=FONT_CELL_PRICE, fill="#2E7D32", tags="cell")
        elif cell.cell_type == CellType.JAIL: self.create_text(cx, price_y, text="暂停一回合", font=FONT_CELL_PRICE, fill="#E65100", tags="cell")
        elif cell.cell_type == CellType.FREE_PARKING: self.create_text(cx, price_y, text="休息一下", font=FONT_CELL_PRICE, fill="#616161", tags="cell")
        elif cell.cell_type == CellType.BANKRUPTCY: self.create_text(cx, price_y, text="罚金 ¥150", font=FONT_CELL_PRICE, fill="#C62828", tags="cell")
        elif cell.cell_type == CellType.CHANCE: self.create_text(cx, price_y, text="🃏 机遇", font=FONT_CELL_PRICE, fill="#E65100", tags="cell")
        elif cell.cell_type == CellType.COMMUNITY_CHEST: self.create_text(cx, price_y, text="📦 命运", font=FONT_CELL_PRICE, fill="#1565C0", tags="cell")

    def _draw_center(self):
        ix1, iy1 = 1 * CELL_SIZE + 2, 1 * CELL_SIZE + 2; ix2, iy2 = 10 * CELL_SIZE - 2, 10 * CELL_SIZE - 2
        self.create_rectangle(ix1, iy1, ix2, iy2, fill=CENTER_BG, outline=BOARD_BORDER, width=3, tags="center")
        cx, cy_top = ix1 + (ix2 - ix1) // 2, iy1 + 160
        self.create_text(cx, cy_top - 60, text="🎲 双人大富翁 🎲", font=FONT_CENTER_TITLE, fill="#8B4513", tags="center")
        self.create_text(cx, cy_top, text="Two-Player Monopoly", font=FONT_CENTER_SUB, fill="#A0826D", tags="center")
        dice_y = cy_top + 80
        self.create_rectangle(cx - 180, dice_y, cx + 180, dice_y + 260, fill="#F5F5DC", outline="#8B4513", width=2, tags="center")
        self.create_text(cx, dice_y + 30, text="🎯 骰子", font=("Microsoft YaHei", 20, "bold"), fill="#8B4513", tags="center")
        self.create_rectangle(cx - 130, dice_y + 60, cx - 10, dice_y + 200, outline="#8B4513", width=3, tags="center")
        self.create_rectangle(cx + 10, dice_y + 60, cx + 130, dice_y + 200, outline="#8B4513", width=3, tags="center")
        self.dice1_text = self.create_text(cx - 70, dice_y + 130, text="?", font=FONT_DICE_NUM, fill="#999999", tags="center")
        self.dice2_text = self.create_text(cx + 70, dice_y + 130, text="?", font=FONT_DICE_NUM, fill="#999999", tags="center")
        self.total_text = self.create_text(cx, dice_y + 245, text="", font=("Microsoft YaHei", 22, "bold"), fill="#8B4513", tags="center")

    def _draw_pieces(self):
        for idx, player in enumerate(self.engine.players): self._draw_piece(idx, player)

    def _draw_piece(self, player_idx: int, player: Player):
        cell = self.engine.get_cell(player.position)
        cx, cy = cell.col * CELL_SIZE + CELL_SIZE // 2, cell.row * CELL_SIZE + CELL_SIZE // 2
        px = cx - PIECE_OFFSET if player_idx == 0 else cx + PIECE_OFFSET - PIECE_SIZE
        py = cy - PIECE_OFFSET if player_idx == 0 else cy + PIECE_OFFSET - PIECE_SIZE
        if player_idx in self.piece_ids: self.delete(self.piece_ids[player_idx])
        piece_id = self.create_oval(px, py, px + PIECE_SIZE, py + PIECE_SIZE,
                                     fill=player.color, outline="white", width=3, tags="piece")
        self.create_text(px + PIECE_SIZE // 2, py + PIECE_SIZE // 2, text=str(player_idx + 1),
                         font=("Microsoft YaHei", 18, "bold"), fill="white", tags="piece")
        self.piece_ids[player_idx] = piece_id

    def update_display(self):
        self.delete("cell"); self.delete("piece"); self.cell_rects.clear()
        for pos in range(40): self._draw_cell(self.engine.get_cell(pos), pos)
        self._update_dice(); self.piece_ids.clear(); self._draw_pieces(); self.tag_raise("piece")

    def _update_dice(self):
        if self.engine.dice1 > 0:
            self.itemconfig(self.dice1_text, text=str(self.engine.dice1), fill="#333333")
            self.itemconfig(self.dice2_text, text=str(self.engine.dice2), fill="#333333")
            self.itemconfig(self.total_text, text=f"合计: {self.engine.dice1 + self.engine.dice2} 步")
        else:
            self.itemconfig(self.dice1_text, text="?", fill="#999999")
            self.itemconfig(self.dice2_text, text="?", fill="#999999")
            self.itemconfig(self.total_text, text="")

    def animate_move(self, from_pos: int, steps: int, on_complete: callable):
        positions = [(from_pos + i) % 40 for i in range(1, steps + 1)]
        def step_animate(idx: int):
            if idx >= len(positions): on_complete(); return
            self.engine.current_player.position = positions[idx]; self.update_display()
            self.after(60 + idx * 5, lambda n=idx + 1: step_animate(n))
        step_animate(0)


# ==================== Mortgage Dialog ====================

class MortgageDialog(tk.Toplevel):
    """Dialog for mortgaging and redeeming properties."""

    def __init__(self, parent, engine: GameEngine, player_idx: int,
                 on_close: Callable = None):
        super().__init__(parent)
        self.engine = engine
        self.player_idx = player_idx
        self.on_close = on_close
        self.selected: List[int] = []
        self.mode = "mortgage"  # or "redeem"
        self._build()
        self.transient(parent)
        self.grab_set()

        dw, dh = 680, 700
        sx = (self.winfo_screenwidth() - dw) // 2
        sy = (self.winfo_screenheight() - dh) // 2
        self.geometry(f"{dw}x{dh}+{sx}+{sy}")
        self.resizable(False, False)
        self.title("地产管理 - 抵押 / 赎回")

    def _build(self):
        self.configure(bg="#FFF8E1")
        player = self.engine.players[self.player_idx]

        tk.Label(self, text=f"🏠 {player.name} - 地产管理",
                 font=FONT_MORTGAGE_TITLE, bg="#FFF8E1", fg="#5D4037").pack(pady=(15, 5))

        # Cash info
        self.cash_label = tk.Label(self, text=f"💰 当前现金: ¥{player.cash:,}",
                                   font=("Microsoft YaHei", 16, "bold"), bg="#FFF8E1", fg="#333333")
        self.cash_label.pack(pady=(0, 8))

        # Tab buttons
        tab_frame = tk.Frame(self, bg="#FFF8E1")
        tab_frame.pack(fill="x", padx=30, pady=5)
        self.mortgage_btn = tk.Button(tab_frame, text="🏚️ 抵押地产", font=("Microsoft YaHei", 16, "bold"),
                                       bg="#FF7043", fg="white", bd=0, padx=25, pady=10,
                                       command=lambda: self._switch_tab("mortgage"))
        self.mortgage_btn.pack(side="left", padx=5)
        self.redeem_btn = tk.Button(tab_frame, text="💰 赎回地产", font=("Microsoft YaHei", 16, "bold"),
                                     bg="#43A047", fg="white", bd=0, padx=25, pady=10,
                                     command=lambda: self._switch_tab("redeem"))
        self.redeem_btn.pack(side="left", padx=5)

        # List area
        list_frame = tk.Frame(self, bg="#FFFDE7", bd=2, relief="solid")
        list_frame.pack(fill="both", expand=True, padx=30, pady=10)

        self.canvas = tk.Canvas(list_frame, bg="#FFFDE7", highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg="#FFFDE7")
        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Action bar
        action_frame = tk.Frame(self, bg="#FFF8E1")
        action_frame.pack(fill="x", padx=30, pady=(5, 15))
        self.action_label = tk.Label(action_frame, text="", font=("Microsoft YaHei", 14), bg="#FFF8E1", fg="#C62828")
        self.action_label.pack(side="left")
        tk.Button(action_frame, text="执行", font=("Microsoft YaHei", 16, "bold"),
                  fg="white", bg="#5D4037", bd=0, padx=30, pady=10,
                  command=self._execute).pack(side="right")
        tk.Button(action_frame, text="关闭", font=("Microsoft YaHei", 14),
                  fg="#333", bg="#BDBDBD", bd=0, padx=20, pady=8,
                  command=self.destroy).pack(side="right", padx=10)

        self._switch_tab("mortgage")

    def _switch_tab(self, mode: str):
        self.mode = mode; self.selected = []
        if mode == "mortgage":
            self.mortgage_btn.configure(bg="#E65100"); self.redeem_btn.configure(bg="#43A047")
        else:
            self.mortgage_btn.configure(bg="#FF7043"); self.redeem_btn.configure(bg="#2E7D32")
        self._refresh_list()

    def _refresh_list(self):
        for w in self.scroll_frame.winfo_children(): w.destroy()
        self.check_vars = {}

        if self.mode == "mortgage":
            props = self.engine.get_mortgageable_properties(self.player_idx)
            title_text = "可抵押地产"
        else:
            props = self.engine.get_mortgaged_properties(self.player_idx)
            title_text = "已抵押地产（可赎回）"

        tk.Label(self.scroll_frame, text=f"📋 {title_text} ({len(props)} 处)",
                 font=("Microsoft YaHei", 15, "bold"), bg="#FFFDE7", fg="#5D4037").pack(anchor="w", padx=15, pady=8)

        if not props:
            tk.Label(self.scroll_frame, text="  暂无可用地产", font=("Microsoft YaHei", 14),
                     bg="#FFFDE7", fg="#999999").pack(padx=20, pady=20)
        else:
            for pos in props:
                self._add_item(pos)

        self._update_total()

    def _add_item(self, pos: int):
        cell = self.engine.get_cell(pos)
        item_frame = tk.Frame(self.scroll_frame, bg="white", bd=1, relief="solid")
        item_frame.pack(fill="x", padx=15, pady=3)

        var = tk.BooleanVar(value=False)
        self.check_vars[pos] = var

        cb = tk.Checkbutton(item_frame, variable=var, bg="white",
                            command=lambda p=pos: self._on_toggle(p))
        cb.pack(side="left", padx=5)

        if self.mode == "mortgage":
            value = self.engine.get_mortgage_value(pos)
            info = f"{cell.name}  |  原价: ¥{cell.price:,}  |  可抵押: ¥{value:,}"
        else:
            cost = self.engine.get_redeem_cost(pos)
            value = self.engine.get_mortgage_value(pos)
            info = f"{cell.name}  |  原价: ¥{cell.price:,}  |  赎回费用: ¥{cost:,} (本金 ¥{value:,} + 10%利息)"

        tk.Label(item_frame, text=info, font=FONT_MORTGAGE_ITEM,
                 bg="white", fg="#333333").pack(side="left", padx=15, pady=8)

    def _on_toggle(self, pos: int):
        if self.check_vars[pos].get():
            self.selected.append(pos)
        else:
            if pos in self.selected: self.selected.remove(pos)
        self._update_total()

    def _update_total(self):
        total = 0
        for pos in self.selected:
            if self.mode == "mortgage":
                total += self.engine.get_mortgage_value(pos)
            else:
                total += self.engine.get_redeem_cost(pos)
        player = self.engine.players[self.player_idx]
        if self.mode == "mortgage":
            txt = f"选择 {len(self.selected)} 处，共获得 ¥{total:,}"
        else:
            txt = f"选择 {len(self.selected)} 处，共支付 ¥{total:,}  (余额: ¥{player.cash:,})"
            if total > player.cash:
                txt += " ⚠ 余额不足！"
        self.action_label.config(text=txt)

    def _execute(self):
        if not self.selected:
            messagebox.showwarning("提示", "请至少选择一个地产。", parent=self)
            return

        player = self.engine.players[self.player_idx]
        if self.mode == "mortgage":
            success, failed = 0, 0
            for pos in self.selected:
                ok, _ = self.engine.mortgage_property(self.player_idx, pos)
                if ok: success += 1
                else: failed += 1
            msg = f"成功抵押 {success} 处地产"
            if failed: msg += f"，{failed} 处失败"
            messagebox.showinfo("抵押完成", msg, parent=self)
        else:
            total_cost = sum(self.engine.get_redeem_cost(p) for p in self.selected)
            if total_cost > player.cash:
                messagebox.showwarning("余额不足", f"赎回需要 ¥{total_cost:,}，但你只有 ¥{player.cash:,}。", parent=self)
                return
            success, failed = 0, 0
            for pos in self.selected:
                ok, _ = self.engine.redeem_property(self.player_idx, pos)
                if ok: success += 1
                else: failed += 1
            msg = f"成功赎回 {success} 处地产"
            if failed: msg += f"，{failed} 处失败"
            messagebox.showinfo("赎回完成", msg, parent=self)

        self._refresh_list()
        if self.on_close: self.on_close()


# ==================== Player Panel ====================

class PlayerPanel(tk.Frame):
    CARD_HEIGHT = 205; AVATAR_SIZE = 80; CIRCLE_R = 32

    def __init__(self, parent, engine: GameEngine, **kwargs):
        super().__init__(parent, width=PANEL_WIDTH, height=PANEL_HEIGHT, bg="#F5F0E8", **kwargs)
        self.engine = engine; self.pack_propagate(False)
        self.p1_frame = self.p2_frame = None
        self.p1_cash = self.p1_prop = self.p1_pos = self.p1_status = None
        self.p2_cash = self.p2_prop = self.p2_pos = self.p2_status = None
        self.turn_label = self.log_text = None
        self.card_frame = self.card_icon = self.card_title = self.card_desc = None
        self._card_fade_job = None
        self._build()

    def _build(self):
        tk.Label(self, text="📋 玩家信息", font=FONT_SUBTITLE, bg="#F5F0E8", fg="#5D4037").pack(pady=(12, 6))
        self.p1_frame = self._make_card_frame(); self.p1_frame.pack(fill="x", padx=18, pady=6)
        self._build_card_content(self.p1_frame, 0)
        self.p2_frame = self._make_card_frame(); self.p2_frame.pack(fill="x", padx=18, pady=6)
        self._build_card_content(self.p2_frame, 1)
        self.turn_label = tk.Label(self, text="", font=FONT_STATUS, bg="#F5F0E8", fg="#5D4037")
        self.turn_label.pack(pady=4)
        self._build_card_display()
        tk.Frame(self, height=2, bg="#BDBDBD").pack(fill="x", padx=25, pady=4)
        tk.Label(self, text="📜 游戏日志", font=FONT_SUBTITLE, bg="#F5F0E8", fg="#5D4037").pack(pady=(4, 2))
        self.log_text = ScrolledText(self, font=FONT_LOG, bg="#FFFDE7", fg="#333333",
                                      wrap=tk.WORD, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=18, pady=(0, 15))

    def _make_card_frame(self) -> tk.Frame:
        f = tk.Frame(self, bg="white", bd=2, relief="solid",
                     highlightbackground="#BDBDBD", highlightthickness=1)
        f.pack_propagate(False); f.configure(height=self.CARD_HEIGHT); return f

    def _build_card_content(self, frame: tk.Frame, player_idx: int):
        player = self.engine.players[player_idx]; card_w = PANEL_WIDTH - 36
        avatar_size = self.AVATAR_SIZE
        avatar = tk.Canvas(frame, width=avatar_size, height=avatar_size, bg="white", highlightthickness=0)
        avatar.place(x=18, y=(self.CARD_HEIGHT - avatar_size) // 2)
        r = self.CIRCLE_R; cx_a = cy_a = avatar_size // 2
        avatar.create_oval(cx_a - r, cy_a - r, cx_a + r, cy_a + r, fill=player.color, outline=player.color, width=2)
        avatar.create_oval(cx_a - r + 2, cy_a - r + 2, cx_a + r - 2, cy_a + r - 2, fill="", outline="#FFFFFF", width=1)
        avatar.create_text(cx_a, cy_a, text=str(player_idx + 1), font=("Microsoft YaHei", 26, "bold"), fill="white")

        info_x, line_h = 130, 36
        tk.Label(frame, text=player.name, font=FONT_PLAYER, bg="white", fg=player.color, anchor="w").place(
            x=info_x, y=18, width=card_w - info_x - 15)

        cash_lbl = tk.Label(frame, text="", font=FONT_PLAYER_INFO, bg="white", fg="#333333", anchor="w")
        cash_lbl.place(x=info_x, y=18 + line_h, width=card_w - info_x - 15)
        prop_lbl = tk.Label(frame, text="", font=FONT_PLAYER_SMALL, bg="white", fg="#555555", anchor="w")
        prop_lbl.place(x=info_x, y=18 + line_h * 2, width=card_w - info_x - 15)
        pos_lbl = tk.Label(frame, text="", font=FONT_PLAYER_SMALL, bg="white", fg="#888888", anchor="w")
        pos_lbl.place(x=info_x, y=18 + line_h * 3, width=card_w - info_x - 15)
        status_lbl = tk.Label(frame, text="", font=("Microsoft YaHei", 13, "bold"), bg="white", fg="#E65100", anchor="w")
        status_lbl.place(x=info_x, y=18 + line_h * 4, width=card_w - info_x - 15)

        if player_idx == 0:
            self.p1_cash, self.p1_prop, self.p1_pos, self.p1_status = cash_lbl, prop_lbl, pos_lbl, status_lbl
        else:
            self.p2_cash, self.p2_prop, self.p2_pos, self.p2_status = cash_lbl, prop_lbl, pos_lbl, status_lbl
        self._set_card_values(player_idx, cash_lbl, prop_lbl, pos_lbl, status_lbl)

    def _build_card_display(self):
        self.card_frame = tk.Frame(self, bg="#F5F0E8", height=0)

    def show_card(self, card: Card):
        self._hide_card()
        card_bg = CARD_BG_CHANCE if card.card_type == CardType.CHANCE else CARD_BG_COMMUNITY
        card_border = CARD_BORDER_CHANCE if card.card_type == CardType.CHANCE else CARD_BORDER_COMMUNITY
        card_label = "🃏 机遇卡" if card.card_type == CardType.CHANCE else "📦 命运卡"
        icon_text = "🃏" if card.card_type == CardType.CHANCE else "📦"

        self.card_frame = tk.Frame(self, bg=card_bg, bd=3, relief="solid",
                                    highlightbackground=card_border, highlightthickness=3)
        self.card_frame.pack(fill="x", padx=18, pady=6, before=self.log_text.master)
        inner = tk.Frame(self.card_frame, bg=card_bg); inner.pack(fill="both", expand=True, padx=15, pady=12)
        self.card_icon = tk.Label(inner, text=icon_text, font=FONT_CARD_ICON, bg=card_bg)
        self.card_icon.pack(side="left", padx=(0, 12))
        text_area = tk.Frame(inner, bg=card_bg); text_area.pack(side="left", fill="both", expand=True)
        self.card_title = tk.Label(text_area, text=f"{card_label}：{card.title}",
                                    font=FONT_CARD_TITLE, bg=card_bg, fg=card_border, anchor="w")
        self.card_title.pack(fill="x")
        self.card_desc = tk.Label(text_area, text=card.description, font=FONT_CARD_BODY,
                                   bg=card_bg, fg="#333333", anchor="w", justify="left")
        self.card_desc.pack(fill="x", pady=(4, 0))
        self._card_fade_job = self.after(CARD_DISPLAY_MS, self._start_fade_out)

    def _start_fade_out(self):
        if self.card_frame is None or not self.card_frame.winfo_exists(): return
        self._fade_step = 0; self._do_fade_step()

    def _do_fade_step(self):
        if self.card_frame is None or not self.card_frame.winfo_exists(): return
        self._fade_step += 1
        if self._fade_step >= CARD_FADE_STEPS: self._hide_card(); return
        self.card_frame.configure(bg="#F0EAD8"); self.after(80, self._do_fade_step)

    def _hide_card(self):
        if self._card_fade_job is not None: self.after_cancel(self._card_fade_job); self._card_fade_job = None
        if self.card_frame is not None and self.card_frame.winfo_exists():
            self.card_frame.destroy(); self.card_frame = None
        self.card_icon = self.card_title = self.card_desc = None

    def update_display(self):
        self._set_card_values(0, self.p1_cash, self.p1_prop, self.p1_pos, self.p1_status)
        self._set_card_values(1, self.p2_cash, self.p2_prop, self.p2_pos, self.p2_status)
        if self.engine.game_over:
            self.turn_label.config(text=f"🏆 {self.engine.winner.name} 获胜！游戏结束！", fg="#2E7D32")
            self.p1_frame.configure(highlightbackground="#BDBDBD", highlightthickness=1)
            self.p2_frame.configure(highlightbackground="#BDBDBD", highlightthickness=1)
        else:
            current = self.engine.current_player
            self.turn_label.config(text=f"🎯 当前行动: {current.name}", fg=current.color)
            if self.engine.current_player_idx == 0:
                self.p1_frame.configure(highlightbackground=PLAYER1_COLOR, highlightthickness=4)
                self.p2_frame.configure(highlightbackground="#BDBDBD", highlightthickness=1)
            else:
                self.p2_frame.configure(highlightbackground=PLAYER2_COLOR, highlightthickness=4)
                self.p1_frame.configure(highlightbackground="#BDBDBD", highlightthickness=1)
        self._update_log()

    def _set_card_values(self, idx, cash_lbl, prop_lbl, pos_lbl, status_lbl):
        player = self.engine.players[idx]
        cash_lbl.config(text=f"💰 现金: ¥{player.cash:,}")
        prop_val = self.engine.get_total_property_value(idx)
        mortgaged_count = len(self.engine.get_mortgaged_properties(idx))
        jail_info = f"  🔑×{player.jail_free_cards}" if player.jail_free_cards > 0 else ""
        mtg_info = f"  [押×{mortgaged_count}]" if mortgaged_count > 0 else ""
        prop_lbl.config(text=f"🏠 地产: {len(player.properties)} 处 (总价 ¥{prop_val:,}){jail_info}{mtg_info}")
        pos_lbl.config(text=f"📍 {self.engine.get_cell(player.position).name}")
        if player.skip_turn:
            status_lbl.config(text="⚠ 下回合暂停（监狱中）")
        elif player.jail_free_cards > 0:
            status_lbl.config(text=f"🔑 持有 {player.jail_free_cards} 张出狱免费卡")
        else:
            status_lbl.config(text="")

    def _update_log(self):
        self.log_text.configure(state="normal"); self.log_text.delete("1.0", tk.END)
        for entry in self.engine.log[-60:]: self.log_text.insert(tk.END, entry + "\n")
        self.log_text.see(tk.END); self.log_text.configure(state="disabled")


# ==================== Main Application ====================

class RichManApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("双人大富翁 - Two-Player Monopoly")
        self.configure(bg="#3E2723")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        # Audio
        self.audio = AudioManager()

        # Engine
        self.engine = GameEngine(audio=self.audio)

        # State
        self._can_roll = True; self._can_buy = False; self._animating = False
        self._pending_card = False
        self._pending_end_id: Optional[str] = None
        self._btn_widgets: dict = {}
        self._muted = False

        self._build_ui()
        self.engine.reset()
        self.refresh_all()
        self.audio.sfx_game_start()
        self.audio.start_bgm()

        # Center window
        self.update_idletasks()
        screen_w = self.winfo_screenwidth(); screen_h = self.winfo_screenheight()
        actual_w = self.winfo_width(); actual_h = self.winfo_height()
        if actual_w > screen_w:
            ratio = screen_w / actual_w
            self.geometry(f"{int(screen_w * 0.78)}x{int(actual_h * ratio * 0.82)}")
            self.update_idletasks()
            actual_w = self.winfo_width(); actual_h = self.winfo_height()
        self.geometry(f"+{max(0, (screen_w - actual_w) // 2)}+{max(0, (screen_h - actual_h) // 2)}")

    # ======== UI Construction ========

    def _build_ui(self):
        # Title bar
        title_frame = tk.Frame(self, bg="#4E342E", height=65)
        title_frame.pack(fill="x", side="top"); title_frame.pack_propagate(False)

        # Title label (centered)
        title_inner = tk.Frame(title_frame, bg="#4E342E")
        title_inner.pack(expand=True, fill="both")
        tk.Label(title_inner, text="🎲 双 人 大 富 翁 🎲", font=FONT_TITLE,
                 bg="#4E342E", fg="#FFCC80").place(relx=0.5, rely=0.5, anchor="center")

        # Mute button (top-right corner)
        self.mute_btn = tk.Button(title_inner, text="🔊", font=("Microsoft YaHei", 18),
                                   bg=BTN_MUTE_OFF, fg="white", bd=0, padx=12, pady=4,
                                   cursor="hand2", command=self._toggle_mute)
        self.mute_btn.place(relx=0.98, rely=0.5, anchor="e")

        # Content
        content = tk.Frame(self, bg="#3E2723")
        content.pack(fill="both", expand=True, side="top")
        self.board_canvas = BoardCanvas(content, self.engine)
        self.board_canvas.place(x=BOARD_X, y=BOARD_Y)
        self.player_panel = PlayerPanel(content, self.engine)
        self.player_panel.place(x=PANEL_X, y=PANEL_Y)

        # Bottom bar
        bottom_frame = tk.Frame(self, bg="#3E2723", height=160)
        bottom_frame.pack(fill="x", side="bottom"); bottom_frame.pack_propagate(False)
        self.status_label = tk.Label(bottom_frame, text="", font=FONT_STATUS,
                                     bg="#3E2723", fg="#FFCC80")
        self.status_label.pack(pady=(10, 4))
        btn_container = tk.Frame(bottom_frame, bg="#3E2723"); btn_container.pack(expand=True)

        buttons_spec = [
            ("roll", "🎲 掷骰子", BTN_ROLL, self.on_roll),
            ("buy", "🏠 购买地产", BTN_BUY, self.on_buy),
            ("end", "⏭️ 结束回合", BTN_END, self.on_end_turn),
            ("mortgage", "🏚️ 抵押地产", BTN_MORTGAGE, self.on_mortgage),
            ("jail_free", "🔑 出狱卡", "#8D6E63", self.on_use_jail_card),
            ("restart", "🔄 重新开始", BTN_RESTART, self.on_restart),
            ("rules", "📖 规则说明", BTN_RULES, self.on_rules),
        ]
        for key, text, color, cmd in buttons_spec:
            btn = self._make_button(btn_container, text, color, cmd)
            btn.pack(side="left", padx=8)
            self._btn_widgets[key] = btn

    def _make_button(self, parent, text, color, command):
        btn = tk.Button(parent, text=text, font=FONT_BUTTON, fg="white", bg=color,
                        activeforeground="white", activebackground=self._darken(color, 0.85),
                        bd=0, padx=20, pady=16, cursor="hand2", command=command, width=9,
                        disabledforeground="#CCCCCC")
        def on_enter(e, b=btn, c=color):
            if str(b.cget("state")) != "disabled": b.configure(bg=self._lighten(c, 0.2))
        def on_leave(e, b=btn, c=color):
            if str(b.cget("state")) != "disabled": b.configure(bg=c)
        btn.bind("<Enter>", on_enter); btn.bind("<Leave>", on_leave)
        return btn

    @staticmethod
    def _lighten(h, f): c=h.lstrip('#'); r,g,b=int(c[0:2],16),int(c[2:4],16),int(c[4:6],16); return f"#{min(255,int(r+(255-r)*f)):02x}{min(255,int(g+(255-g)*f)):02x}{min(255,int(b+(255-b)*f)):02x}"
    @staticmethod
    def _darken(h, f): c=h.lstrip('#'); r,g,b=int(c[0:2],16),int(c[2:4],16),int(c[4:6],16); return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"

    # ======== Mute Toggle ========

    def _toggle_mute(self):
        self.audio.sfx_click()
        new_muted = self.audio.toggle_mute()
        self._muted = new_muted
        if new_muted:
            self.mute_btn.configure(text="🔇", bg=BTN_MUTE_ON)
        else:
            self.mute_btn.configure(text="🔊", bg=BTN_MUTE_OFF)

    # ======== Button States ========

    def _update_button_states(self):
        player = self.engine.current_player
        has_jail_card = player.jail_free_cards > 0
        in_jail = player.skip_turn
        has_props = len(player.properties) > 0

        if self.engine.game_over:
            self._set_buttons(roll=False, buy=False, end=False, mortgage=False,
                              jail_free=False, restart=True, rules=True)
            self.status_label.config(text="🏆 游戏结束！点击「重新开始」再来一局")
        elif self._animating:
            self._set_buttons(roll=False, buy=False, end=False, mortgage=False,
                              jail_free=False, restart=False, rules=True)
            self.status_label.config(text="🎲 移动中...")
        elif self._can_roll:
            self._set_buttons(roll=True, buy=False, end=False, mortgage=has_props,
                              jail_free=has_jail_card and in_jail, restart=True, rules=True)
            self.status_label.config(text=f"🎯 {player.name} 的回合，请掷骰子！")
        elif self._can_buy:
            self._set_buttons(roll=False, buy=True, end=True, mortgage=has_props,
                              jail_free=False, restart=True, rules=True)
            cell = self.engine.get_cell(player.position)
            self.status_label.config(text=f"💡 可购买「{cell.name}」(¥{cell.price})，或结束回合")
        elif self._pending_card:
            self._set_buttons(roll=False, buy=False, end=False, mortgage=False,
                              jail_free=False, restart=False, rules=True)
            self.status_label.config(text="🃏 正在展示卡片...")
        else:
            self._set_buttons(roll=False, buy=False, end=True, mortgage=False,
                              jail_free=False, restart=True, rules=True)
            self.status_label.config(text="点击「结束回合」继续")

    def _set_buttons(self, roll, buy, end, mortgage, jail_free, restart, rules):
        states = {"roll": roll, "buy": buy, "end": end, "mortgage": mortgage,
                  "jail_free": jail_free, "restart": restart, "rules": rules}
        colors = {"roll": BTN_ROLL, "buy": BTN_BUY, "end": BTN_END,
                  "mortgage": BTN_MORTGAGE, "jail_free": "#8D6E63",
                  "restart": BTN_RESTART, "rules": BTN_RULES}
        for key, enabled in states.items():
            if key in self._btn_widgets:
                btn = self._btn_widgets[key]
                btn.configure(state=tk.NORMAL if enabled else tk.DISABLED,
                              bg=colors[key] if enabled else "#666666")

    # ======== Scheduling ========

    def _schedule_end_turn(self, delay_ms):
        self._cancel_pending_end()
        self._pending_end_id = self.after(delay_ms, self._end_turn_scheduled)

    def _cancel_pending_end(self):
        if self._pending_end_id is not None:
            self.after_cancel(self._pending_end_id); self._pending_end_id = None

    def _end_turn_scheduled(self):
        self._pending_end_id = None; self._end_turn()

    # ======== Handlers ========

    def on_roll(self):
        if not self._can_roll or self._animating or self.engine.game_over: return
        self.audio.sfx_click()

        player = self.engine.current_player
        if self.engine.check_jail_skip():
            self._can_roll = False; self.refresh_all(); self._schedule_end_turn(1000); return

        self._can_roll = False; self._animating = True; self._can_buy = False; self._pending_card = False

        d1, d2 = self.engine.roll_dice(); steps = d1 + d2
        from_pos = self.engine.current_player.position
        self.audio.sfx_roll_dice()
        self.refresh_all()

        self.after(500, lambda: self.board_canvas.animate_move(
            from_pos, steps, on_complete=self._on_move_complete
        ))

    def _on_move_complete(self):
        self._animating = False
        self.audio.sfx_move()
        result = self.engine.process_landing()

        if self.engine.game_over:
            self.audio.sfx_bankrupt()
            self.refresh_all(); self.update()
            messagebox.showinfo("游戏结束",
                                f"💀 {self.engine.current_player.name} 破产了！\n\n🏆 {self.engine.winner.name} 获胜！")
            self.audio.sfx_win(); return

        if result in ("chance", "community"):
            self.audio.sfx_card_draw()
            cell_type = CellType.CHANCE if result == "chance" else CellType.COMMUNITY_CHEST
            card = self.engine.draw_card(cell_type)
            if card.card_type == CardType.CHANCE: self.audio.sfx_chance()
            else: self.audio.sfx_community()
            self.player_panel.show_card(card)
            self._pending_card = True; self.refresh_all()
            self.after(CARD_DISPLAY_MS, lambda: self._execute_card_effect(card))
        elif result == "buyable":
            self._can_buy = True
            self.engine.add_log("💡 你可以购买当前地产，或选择结束回合。"); self.refresh_all()
        elif result == "rent":
            self.audio.sfx_rent()
            if self.engine.game_over: self.audio.sfx_bankrupt()
            self._can_buy = False; self.refresh_all(); self._schedule_end_turn(800)
        elif result == "jail":
            self.audio.sfx_jail()
            self._can_buy = False; self.refresh_all(); self._schedule_end_turn(800)
        else:
            self._can_buy = False; self.refresh_all(); self._schedule_end_turn(800)

    def _execute_card_effect(self, card: Card):
        self._pending_card = False
        if card.keepable:
            self.engine.execute_card_effect(self.engine.current_player_idx, card)
        else:
            self.engine.execute_card_effect(self.engine.current_player_idx, card)
        player = self.engine.current_player
        if player.cash < 0:
            if self.engine._can_avoid_bankruptcy(player):
                self.engine.add_log(f"⚠ {player.name} 现金不足！可以考虑抵押地产来避免破产。")
                player.cash = max(0, player.cash)  # Give a chance to mortgage
                self.refresh_all()
                self._schedule_end_turn(500); return
            self.engine._declare_bankruptcy(player)
        if self.engine.game_over:
            self.audio.sfx_bankrupt(); self.refresh_all(); self.update()
            messagebox.showinfo("游戏结束",
                                f"💀 {player.name} 破产了！\n\n🏆 {self.engine.winner.name} 获胜！")
            self.audio.sfx_win(); return
        self.refresh_all(); self._schedule_end_turn(600)

    def on_mortgage(self):
        """Open mortgage dialog."""
        self.audio.sfx_click()
        if self._animating: return
        player = self.engine.current_player
        if len(player.properties) == 0:
            messagebox.showinfo("提示", "你没有地产可以抵押。", parent=self); return

        def on_dialog_close():
            self.refresh_all()

        MortgageDialog(self, self.engine, self.engine.current_player_idx, on_close=on_dialog_close)

    def on_use_jail_card(self):
        self.audio.sfx_click()
        player = self.engine.current_player
        if player.jail_free_cards <= 0: return
        if not player.skip_turn:
            messagebox.showinfo("提示", "你当前不在监狱中，无需使用出狱卡。", parent=self); return
        self.engine.use_jail_free_card(self.engine.current_player_idx)
        self.audio.sfx_jail_free()
        self.refresh_all()
        messagebox.showinfo("出狱成功", f"{player.name} 使用出狱免费卡，重获自由！", parent=self)

    def on_buy(self):
        if not self._can_buy or self.engine.game_over: return
        self.audio.sfx_click()
        success, msg = self.engine.buy_property()
        if success:
            self.audio.sfx_buy(); self._can_buy = False
            self.refresh_all(); self._schedule_end_turn(500)
        else:
            messagebox.showwarning("购买失败", msg, parent=self)

    def on_end_turn(self):
        if self._animating or self.engine.game_over: return
        self.audio.sfx_click()
        if self._can_buy:
            self.engine.add_log(f"{self.engine.current_player.name} 选择不购买，结束回合。")
            self._can_buy = False
        if not self._can_roll: self._end_turn()

    def _end_turn(self):
        self._cancel_pending_end()
        if self.engine.game_over: return
        self.engine.next_turn(); self._can_roll = True; self._can_buy = False
        self._pending_card = False; self.refresh_all()

    def on_restart(self):
        if self._animating: return
        self.audio.sfx_click()
        ok = messagebox.askyesno("重新开始", "确定要重新开始游戏吗？\n当前进度将丢失。", parent=self)
        if ok:
            self._cancel_pending_end(); self.engine.reset()
            self._can_roll = True; self._can_buy = False; self._animating = False
            self._pending_card = False
            self.player_panel._hide_card()
            self.refresh_all()
            self.audio.sfx_game_start()

    def on_rules(self):
        self.audio.sfx_click()
        rules_text = """\
╔══════════════════════════════════════════╗
║      📖 双人大富翁 - 完整游戏规则       ║
╚══════════════════════════════════════════╝

🎯 游戏目标: 让你的对手破产！

🎮 游戏流程
━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 两名玩家轮流掷骰子行动
2. 棋子按骰子点数之和移动
3. 根据停留的格子触发不同效果

🏠 地产系统
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 走到空地时可购买（32处地产）
• 对手走到你的地产 → 支付10%过路费
• 已抵押地产不收过路费

🏚️ 抵押系统 (NEW!)
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 点击「抵押地产」管理地产
• 抵押获得地产价格50%的现金
• 赎回需支付本金+10%利息
• 资金不足时可抵押避免破产

🃏 卡片系统
━━━━━━━━━━━━━━━━━━━━━━━━━━
机遇卡(橙)第7/22格 | 命运卡(蓝)第12/36格
• 抽到出狱免费卡可保留使用
• 在监狱中点击「出狱卡」按钮

🔊 音效系统 (NEW!)
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 右上角 🔊/🔇 按钮控制静音
• 背景音乐循环播放
• 每个操作都有对应音效

🎁 特殊格子
━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 起点(+200) 🔒 监狱(暂停) 🅿️ 免费停车
🔴 破产格(-150) 🃏 机遇卡 📦 命运卡
"""
        dialog = tk.Toplevel(self); dialog.title("游戏规则说明"); dialog.configure(bg="#FFF8E1")
        dw, dh = 750, 850
        sx = (self.winfo_screenwidth() - dw) // 2; sy = (self.winfo_screenheight() - dh) // 2
        dialog.geometry(f"{dw}x{dh}+{sx}+{sy}")
        dialog.resizable(False, False); dialog.transient(self); dialog.grab_set()
        tk.Label(dialog, text="📖 双人大富翁 - 完整规则", font=FONT_RULES_TITLE,
                 bg="#FFF8E1", fg="#5D4037").pack(pady=15)
        text_widget = ScrolledText(dialog, font=FONT_RULES_BODY, bg="#FFFDE7",
                                    fg="#333333", wrap=tk.WORD, width=65, height=30)
        text_widget.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        text_widget.insert("1.0", rules_text); text_widget.configure(state="disabled")
        tk.Button(dialog, text="我知道了", font=FONT_BUTTON, fg="white", bg="#795548",
                  bd=0, padx=40, pady=12, cursor="hand2", command=dialog.destroy).pack(pady=(0, 20))

    def refresh_all(self):
        self.board_canvas.update_display(); self.player_panel.update_display()
        self._update_button_states()


# ==================== Main Entry Point ====================

def main():
    app = RichManApp()
    app.mainloop()


if __name__ == "__main__":
    main()
