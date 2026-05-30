# -*- coding: utf-8 -*-
"""
双人大富翁 - Two-Player Monopoly Game (with Card System)
专门适配 Windows 3024×2056 高分辨率屏幕
窗口 2400×1600，UI 元素 2.5 倍缩放
包含完整的 机遇卡/命运卡 系统
"""

import ctypes

# ============ Windows High DPI Awareness ============
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI (Windows 8.1+)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()   # System DPI (Windows Vista+)
    except Exception:
        pass

import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Callable


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

# Player colors
PLAYER1_COLOR = "#1E88E5"       # Blue
PLAYER2_COLOR = "#E53935"       # Red
PLAYER1_LIGHT = "#BBDEFB"       # Light blue
PLAYER2_LIGHT = "#FFCDD2"       # Light red

# Board colors
BOARD_BG = "#F5F5DC"
BOARD_BORDER = "#8B4513"
CELL_BG_DEFAULT = "#FFF8DC"
CELL_BG_START = "#A5D6A7"
CELL_BG_JAIL = "#FFCC80"
CELL_BG_PARKING = "#E0E0E0"
CELL_BG_BANKRUPTCY = "#EF9A9A"
CELL_BG_CHANCE = "#FFE0B2"       # Light orange - 机遇卡
CELL_BG_COMMUNITY = "#BBDEFB"    # Light blue - 命运卡
CENTER_BG = "#FFF9E6"

# Button colors
BTN_ROLL = "#FF9800"
BTN_BUY = "#4CAF50"
BTN_END = "#2196F3"
BTN_RESTART = "#9E9E9E"
BTN_RULES = "#795548"

# Card display colors
CARD_BG_CHANCE = "#FFF3E0"       # Orange tint for 机遇卡
CARD_BORDER_CHANCE = "#E65100"
CARD_BG_COMMUNITY = "#E3F2FD"    # Blue tint for 命运卡
CARD_BORDER_COMMUNITY = "#1565C0"

# Fonts
FONT_TITLE = ("Microsoft YaHei", 32, "bold")
FONT_SUBTITLE = ("Microsoft YaHei", 20, "bold")
FONT_PLAYER = ("Microsoft YaHei", 22, "bold")
FONT_PLAYER_INFO = ("Microsoft YaHei", 18)
FONT_PLAYER_SMALL = ("Microsoft YaHei", 16)
FONT_NORMAL = ("Microsoft YaHei", 18)
FONT_BUTTON = ("Microsoft YaHei", 18, "bold")
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

PIECE_SIZE = 40
PIECE_OFFSET = 18
INITIAL_CASH = 1500
CARD_DISPLAY_MS = 3500      # How long card stays visible (ms)
CARD_FADE_STEPS = 6         # Number of fade-out steps


# ==================== Enums & Data Classes ====================

class CellType(Enum):
    START = "start"
    PROPERTY = "property"
    JAIL = "jail"
    FREE_PARKING = "free_parking"
    BANKRUPTCY = "bankruptcy"
    CHANCE = "chance"                # 机遇卡
    COMMUNITY_CHEST = "community"    # 命运卡


class CardType(Enum):
    CHANCE = "chance"
    COMMUNITY_CHEST = "community"


@dataclass
class Card:
    """A single chance or community chest card."""
    card_type: CardType
    title: str
    description: str
    # Effect function: (engine, player_idx) -> str (result message)
    effect: Callable[['GameEngine', int], str]
    keepable: bool = False   # True for "出狱免费卡"


@dataclass
class BoardCell:
    """Represents one cell on the board."""
    name: str
    price: int
    cell_type: CellType
    row: int
    col: int
    owner: Optional[int] = None


@dataclass
class Player:
    """Represents a player."""
    name: str
    color: str
    light_color: str
    cash: int = INITIAL_CASH
    position: int = 0
    properties: List[int] = field(default_factory=list)
    skip_turn: bool = False
    jail_free_cards: int = 0     # Number of "出狱免费卡" held


# ==================== Card Deck ====================

class CardDeck:
    """Manages a deck of cards with shuffle and auto-reshuffle."""

    def __init__(self, cards: List[Card]):
        self._all_cards = list(cards)
        self._draw_pile: List[Card] = []
        self._discard: List[Card] = []
        self.shuffle()

    def shuffle(self):
        """Shuffle all cards back into the draw pile."""
        combined = self._all_cards + self._discard
        # Keep keepable cards in the deck for reshuffling
        self._draw_pile = list(combined)
        random.shuffle(self._draw_pile)
        self._discard = []

    def draw(self) -> Optional[Card]:
        """Draw a card from the deck. Auto-reshuffles if empty."""
        if not self._draw_pile:
            self.shuffle()
        if self._draw_pile:
            card = self._draw_pile.pop(0)
            if not card.keepable:
                self._discard.append(card)
            # keepable cards are NOT discarded (they stay with the player)
            return card
        return None

    def return_keepable(self, card: Card):
        """Return a keepable card to the deck (when used by player)."""
        self._discard.append(card)


# ==================== Card Effect Functions ====================
# Each returns a status message string.

def _move_to(engine: 'GameEngine', player_idx: int, target_pos: int,
             collect_start: bool = True, extra_msg: str = "") -> str:
    """Helper: move player to a target position, optionally collecting start bonus."""
    player = engine.players[player_idx]
    old_pos = player.position
    if target_pos >= old_pos:
        # Moving forward
        if collect_start and target_pos < old_pos:
            # wrapped around - shouldn't happen with forward move
            pass
        player.position = target_pos
    else:
        # Moving backward
        player.position = target_pos

    cell = engine.get_cell(target_pos)
    return f"移动到 {cell.name}" + (f"，{extra_msg}" if extra_msg else "")


def _go_to_jail(engine: 'GameEngine', player_idx: int) -> str:
    """Send player directly to jail."""
    player = engine.players[player_idx]
    player.position = 30  # Jail position
    player.skip_turn = True
    return "直接进监狱，不经过起点，暂停一回合！"


# ── 机遇卡 (Chance) effects ──

def _chance_go_to_start(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    player.position = 0
    player.cash += 200
    return "前进到起点，获得 200 元！"

def _chance_go_to_pos25(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    target = 25
    old_pos = player.position
    # Collect start bonus if passing through
    if target < old_pos:
        player.cash += 200
    player.position = target
    cell = engine.get_cell(target)
    if cell.owner is None:
        return f"前进到 {cell.name}(¥{cell.price})，可以购买此地产"
    elif cell.owner == player_idx:
        return f"前进到 {cell.name}，这是你的地产"
    else:
        rent = max(1, int(cell.price * 0.1)) * 2  # double rent
        player.cash -= rent
        engine.players[cell.owner].cash += rent
        return f"前进到 {cell.name}，支付双倍过路费 ¥{rent}"

def _chance_go_to_pos35(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    target = 35
    old_pos = player.position
    if target < old_pos:
        player.cash += 200
    player.position = target
    cell = engine.get_cell(target)
    if cell.owner is None:
        return f"前进到 {cell.name}(¥{cell.price})，可以购买此地产"
    elif cell.owner == player_idx:
        return f"前进到 {cell.name}，这是你的地产"
    else:
        fee = (engine.dice1 + engine.dice2) * 10
        player.cash -= fee
        engine.players[cell.owner].cash += fee
        return f"前进到 {cell.name}，支付 10倍骰子点数 ¥{fee}"

def _chance_dividend(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 50
    return "银行支付股息 50 元！"

def _chance_jail_free(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].jail_free_cards += 1
    return "获得「出狱免费卡」一张！（可保留使用）"

def _chance_go_back_3(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    player.position = (player.position - 3) % 40
    return "后退 3 格"

def _chance_speed_fine(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash -= 15
    return "超速罚款 15 元"

def _chance_pay_each(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    other = engine.players[1 - player_idx]
    player.cash -= 50
    other.cash += 50
    return f"向 {other.name} 支付 50 元"

def _chance_loan(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 150
    return "建筑贷款到期，获得 150 元"

def _chance_crossword(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 100
    return "赢得填字比赛，获得 100 元"

def _chance_go_to_pos26(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    target = 26
    if target < player.position:
        player.cash += 200
    player.position = target
    return f"前进到商业街（{engine.get_cell(target).name}）"

def _chance_go_to_pos38(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    target = 38
    if target < player.position:
        player.cash += 200
    player.position = target
    return f"前进到公园大道（{engine.get_cell(target).name}）"

def _chance_repairs(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    cost = len(player.properties) * 30
    player.cash -= cost
    return f"房产维修，为 {len(player.properties)} 处地产支付 {cost} 元"

def _chance_lottery(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 200
    return "中彩票，获得 200 元！"

def _chance_stock(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 300
    return "股市大涨，获得 300 元！"


# ── 命运卡 (Community Chest) effects ──

def _comm_go_to_start(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    player.position = 0
    player.cash += 200
    return "前进到起点，获得 200 元！"

def _comm_bank_error(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 200
    return "银行出错，多给了 200 元！"

def _comm_doctor(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash -= 50
    return "看医生，支付 50 元"

def _comm_jail_free(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].jail_free_cards += 1
    return "获得「出狱免费卡」一张！（可保留使用）"

def _comm_go_to_jail(engine: 'GameEngine', player_idx: int) -> str:
    return _go_to_jail(engine, player_idx)

def _comm_birthday(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    other = engine.players[1 - player_idx]
    other.cash -= 50
    player.cash += 50
    return f"生日快乐！{other.name} 给你 50 元"

def _comm_opera(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    other = engine.players[1 - player_idx]
    other.cash -= 30
    player.cash += 30
    return f"歌剧之夜，{other.name} 支付 30 元门票费"

def _comm_tax_refund(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 20
    return "所得税退款，获得 20 元"

def _comm_insurance(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 100
    return "人寿保险到期，获得 100 元"

def _comm_hospital(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash -= 100
    return "住院费用，支付 100 元"

def _comm_tuition(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash -= 50
    return "学费，支付 50 元"

def _comm_consult(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 25
    return "咨询费，获得 25 元"

def _comm_street_repair(engine: 'GameEngine', player_idx: int) -> str:
    player = engine.players[player_idx]
    cost = len(player.properties) * 40
    player.cash -= cost
    return f"街道维修，支付 {cost} 元"

def _comm_beauty(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 10
    return "选美比赛第二名，获得 10 元"

def _comm_inherit(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 100
    return "继承遗产，获得 100 元"

def _comm_stock_sale(engine: 'GameEngine', player_idx: int) -> str:
    engine.players[player_idx].cash += 50
    return "股票出售，获得 50 元"


# ==================== Create Card Decks ====================

def create_chance_deck() -> CardDeck:
    """Create the 机遇卡 (Chance) deck with 16 cards."""
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
    """Create the 命运卡 (Community Chest) deck with 16 cards."""
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

    # Card cell positions: 7, 22 = 机遇卡; 12, 36 = 命运卡
    CARD_CELLS = {
        7:  CellType.CHANCE,
        22: CellType.CHANCE,
        12: CellType.COMMUNITY_CHEST,
        36: CellType.COMMUNITY_CHEST,
    }

    PROPERTY_DEFS = {
        # Bottom row (positions 1-9, except 7=CHANCE)
        1: ("村庄", 60),    2: ("农田", 60),    3: ("果园", 80),
        4: ("渔村", 80),    5: ("牧场", 100),   6: ("林场", 100),
        # 7: CHANCE cell
        8: ("集市", 100),   9: ("小商店", 120),
        # Right column (positions 11-19, except 12=COMMUNITY)
        11: ("面包店", 120),
        # 12: COMMUNITY cell
        13: ("书店", 140),   14: ("花店", 160),   15: ("服装店", 160),
        16: ("药店", 180),   17: ("小餐馆", 180), 18: ("电影院", 200),
        19: ("健身房", 200),
        # Top row (positions 21-29, except 22=CHANCE)
        21: ("超市", 200),
        # 22: CHANCE cell
        23: ("医院", 220),   24: ("学校", 240),   25: ("餐厅", 240),
        26: ("商场", 260),   27: ("写字楼", 260), 28: ("体育馆", 280),
        29: ("剧院", 280),
        # Left column (positions 31-39, except 36=COMMUNITY)
        31: ("博物馆", 280), 32: ("图书馆", 280), 33: ("游泳馆", 300),
        34: ("大酒店", 300), 35: ("银行", 320),
        # 36: COMMUNITY cell
        37: ("游乐园", 380), 38: ("摩天大楼", 400), 39: ("宫殿", 400),
    }

    CORNER_DEFS = {
        0:  ("起点", CellType.START),
        10: ("破产", CellType.BANKRUPTCY),
        20: ("免费停车", CellType.FREE_PARKING),
        30: ("监狱", CellType.JAIL),
    }

    CARD_CELL_NAMES = {
        7:  ("机遇", CellType.CHANCE),
        22: ("机遇", CellType.CHANCE),
        12: ("命运", CellType.COMMUNITY_CHEST),
        36: ("命运", CellType.COMMUNITY_CHEST),
    }

    def __init__(self):
        self.players: List[Player] = []
        self.board: List[BoardCell] = []
        self.current_player_idx: int = 0
        self.dice1: int = 0
        self.dice2: int = 0
        self.log: List[str] = []
        self.game_over: bool = False
        self.winner: Optional[Player] = None

        # Card decks
        self.chance_deck: CardDeck = create_chance_deck()
        self.community_deck: CardDeck = create_community_deck()

        # Last drawn card (for UI display)
        self.last_drawn_card: Optional[Card] = None

        self._init_board()
        self._init_players()

    def _init_board(self):
        """Initialize the 40-cell board."""
        self.board = []
        for pos in range(40):
            row, col = self._pos_to_grid(pos)
            if pos in self.CORNER_DEFS:
                name, cell_type = self.CORNER_DEFS[pos]
                price = 0
            elif pos in self.CARD_CELLS:
                name, cell_type = self.CARD_CELL_NAMES[pos]
                price = 0
            else:
                name, price = self.PROPERTY_DEFS.get(pos, ("未知", 0))
                cell_type = CellType.PROPERTY
            self.board.append(BoardCell(
                name=name, price=price, cell_type=cell_type,
                row=row, col=col
            ))

    def _init_players(self):
        """Initialize two players."""
        self.players = [
            Player(name="玩家 1", color=PLAYER1_COLOR, light_color=PLAYER1_LIGHT),
            Player(name="玩家 2", color=PLAYER2_COLOR, light_color=PLAYER2_LIGHT),
        ]
        self.current_player_idx = 0
        self.game_over = False
        self.winner = None

    @staticmethod
    def _pos_to_grid(pos: int) -> Tuple[int, int]:
        """Convert board position (0-39) to grid coordinates (row, col)."""
        if pos <= 10:
            return (10, pos)
        elif pos <= 20:
            return (20 - pos, 10)
        elif pos <= 30:
            return (0, 30 - pos)
        else:
            return (pos - 30, 0)

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_idx]

    def get_cell(self, pos: int) -> BoardCell:
        return self.board[pos]

    def roll_dice(self) -> Tuple[int, int]:
        """Roll two dice."""
        self.dice1 = random.randint(1, 6)
        self.dice2 = random.randint(1, 6)
        self.add_log(f"{self.current_player.name} 掷出了 [{self.dice1}] 和 [{self.dice2}]，"
                     f"共 {self.dice1 + self.dice2} 点")
        return self.dice1, self.dice2

    def draw_card(self, cell_type: CellType) -> Card:
        """Draw a card from the appropriate deck."""
        if cell_type == CellType.CHANCE:
            deck = self.chance_deck
        else:
            deck = self.community_deck
        card = deck.draw()
        self.last_drawn_card = card
        card_name = "机遇卡" if cell_type == CellType.CHANCE else "命运卡"
        self.add_log(f"🃏 {self.current_player.name} 抽到 {card_name}：「{card.title}」— {card.description}")
        return card

    def use_jail_free_card(self, player_idx: int) -> bool:
        """Use a jail free card. Returns True if successful."""
        player = self.players[player_idx]
        if player.jail_free_cards > 0:
            player.jail_free_cards -= 1
            player.skip_turn = False
            self.add_log(f"🃏 {player.name} 使用了出狱免费卡！")
            return True
        return False

    def execute_card_effect(self, player_idx: int, card: Card) -> str:
        """Execute a card's effect and return result message."""
        result = card.effect(self, player_idx)
        self.add_log(f"  → {result}")
        return result

    def process_landing(self) -> str:
        """
        Process what happens when current player lands on their cell.
        Returns: 'start','jail','parking','bankrupt','penalty','buyable',
                 'own','rent','chance','community','card_done'
        """
        player = self.current_player
        cell = self.get_cell(player.position)

        if cell.cell_type == CellType.START:
            player.cash += 200
            self.add_log(f"🎉 {player.name} 到达起点，获得 200 元奖励！")
            return "start"

        elif cell.cell_type == CellType.JAIL:
            player.skip_turn = True
            self.add_log(f"🔒 {player.name} 进入监狱，暂停一回合！")
            return "jail"

        elif cell.cell_type == CellType.FREE_PARKING:
            self.add_log(f"🅿️ {player.name} 在免费停车，什么都不做。")
            return "parking"

        elif cell.cell_type == CellType.BANKRUPTCY:
            penalty = 150
            player.cash -= penalty
            self.add_log(f"💸 {player.name} 走到破产格，缴纳 {penalty} 元罚金！")
            if player.cash < 0:
                self._declare_bankruptcy(player)
                return "bankrupt"
            return "penalty"

        elif cell.cell_type in (CellType.CHANCE, CellType.COMMUNITY_CHEST):
            return "chance" if cell.cell_type == CellType.CHANCE else "community"

        elif cell.cell_type == CellType.PROPERTY:
            if cell.owner is None:
                return "buyable"
            elif cell.owner == self.current_player_idx:
                self.add_log(f"🏠 这是 {player.name} 自己的地产。")
                return "own"
            else:
                rent = max(1, int(cell.price * 0.1))
                player.cash -= rent
                owner_player = self.players[cell.owner]
                owner_player.cash += rent
                self.add_log(f"💰 {player.name} 向 {owner_player.name} "
                             f"支付了 {rent} 元过路费！")
                if player.cash < 0:
                    self._declare_bankruptcy(player)
                    return "bankrupt"
                return "rent"

        return "unknown"

    def buy_property(self) -> Tuple[bool, str]:
        """Current player attempts to buy the property they're standing on."""
        player = self.current_player
        cell = self.get_cell(player.position)

        if cell.cell_type != CellType.PROPERTY:
            return False, "当前位置不是地产，无法购买。"
        if cell.owner is not None:
            return False, "该地产已被购买。"
        if player.cash < cell.price:
            return False, f"现金不足！需要 {cell.price} 元，你只有 {player.cash} 元。"

        player.cash -= cell.price
        cell.owner = self.current_player_idx
        player.properties.append(player.position)
        self.add_log(f"🏠 {player.name} 购买了 {cell.name}，花费 {cell.price} 元！")
        return True, f"成功购买 {cell.name}！"

    def _declare_bankruptcy(self, player: Player):
        """Declare a player bankrupt."""
        self.game_over = True
        self.winner = self.players[1 - self.players.index(player)]
        self.add_log(f"💀 {player.name} 破产了！{self.winner.name} 获胜！🎉")

    def next_turn(self):
        """Advance to the next player's turn."""
        self.current_player_idx = 1 - self.current_player_idx
        self.dice1 = 0
        self.dice2 = 0
        if not self.game_over:
            self.add_log(f"➡️ 轮到 {self.current_player.name} 行动")

    def check_jail_skip(self) -> bool:
        """Check if current player should skip their turn due to jail."""
        player = self.current_player
        if player.skip_turn:
            # Check for jail free card
            if player.jail_free_cards > 0:
                return False  # Don't skip — player can use card
            player.skip_turn = False
            self.add_log(f"🔒 {player.name} 在监狱中，本回合跳过！")
            return True
        return False

    def reset(self):
        """Reset the entire game."""
        self.chance_deck = create_chance_deck()
        self.community_deck = create_community_deck()
        self.last_drawn_card = None
        self._init_board()
        self._init_players()
        self.log.clear()
        self.dice1 = 0
        self.dice2 = 0
        self.add_log("🎮 游戏开始！双人大富翁（含机遇卡/命运卡）！")
        self.add_log(f"➡️ 轮到 {self.current_player.name} 行动")

    def add_log(self, message: str):
        """Add a message to the game log."""
        self.log.append(message)

    def get_total_property_value(self, player_idx: int) -> int:
        """Get total value of a player's properties."""
        player = self.players[player_idx]
        return sum(self.board[p].price for p in player.properties)


# ==================== Board Canvas ====================

class BoardCanvas(tk.Canvas):
    """Canvas widget that draws the game board."""

    def __init__(self, parent, engine: GameEngine, **kwargs):
        super().__init__(parent, width=BOARD_SIZE, height=BOARD_SIZE,
                         bg="#2C1810", highlightthickness=0, **kwargs)
        self.engine = engine
        self.piece_ids: dict = {}
        self.cell_rects: dict = {}
        self.dice1_text: int = 0
        self.dice2_text: int = 0

        self._draw_all()

    def _draw_all(self):
        """Full initial draw."""
        self._draw_board()
        self._draw_center()
        self._draw_pieces()

    def _draw_board(self):
        """Draw all 40 cells on the board."""
        for pos in range(40):
            cell = self.engine.get_cell(pos)
            self._draw_cell(cell, pos)

    def _draw_cell(self, cell: BoardCell, pos: int):
        """Draw a single cell."""
        x1 = cell.col * CELL_SIZE
        y1 = cell.row * CELL_SIZE
        x2 = x1 + CELL_SIZE
        y2 = y1 + CELL_SIZE

        # Fill color
        if cell.owner is not None:
            fill = self.engine.players[cell.owner].light_color
        elif cell.cell_type == CellType.START:
            fill = CELL_BG_START
        elif cell.cell_type == CellType.JAIL:
            fill = CELL_BG_JAIL
        elif cell.cell_type == CellType.FREE_PARKING:
            fill = CELL_BG_PARKING
        elif cell.cell_type == CellType.BANKRUPTCY:
            fill = CELL_BG_BANKRUPTCY
        elif cell.cell_type == CellType.CHANCE:
            fill = CELL_BG_CHANCE
        elif cell.cell_type == CellType.COMMUNITY_CHEST:
            fill = CELL_BG_COMMUNITY
        else:
            fill = CELL_BG_DEFAULT

        # Background rect
        rect_id = self.create_rectangle(
            x1 + 1, y1 + 1, x2 - 1, y2 - 1,
            fill=fill, outline=BOARD_BORDER, width=2, tags="cell"
        )
        self.cell_rects[pos] = rect_id

        # Owner strip
        if cell.owner is not None:
            owner_color = self.engine.players[cell.owner].color
            self.create_rectangle(
                x1 + 1, y1 + 1, x2 - 1, y1 + 8,
                fill=owner_color, outline="", tags="cell"
            )

        # Cell name
        cx = x1 + CELL_SIZE // 2
        name_y = y1 + CELL_SIZE // 2 - 14
        self.create_text(cx, name_y, text=cell.name,
                         font=FONT_CELL_NAME, fill="#333333", tags="cell")

        # Price or corner label
        price_y = y1 + CELL_SIZE // 2 + 14
        if cell.cell_type == CellType.PROPERTY:
            self.create_text(cx, price_y, text=f"¥{cell.price}",
                             font=FONT_CELL_PRICE, fill="#666666", tags="cell")
        elif cell.cell_type == CellType.START:
            self.create_text(cx, price_y, text="← 出发",
                             font=FONT_CELL_PRICE, fill="#2E7D32", tags="cell")
        elif cell.cell_type == CellType.JAIL:
            self.create_text(cx, price_y, text="暂停一回合",
                             font=FONT_CELL_PRICE, fill="#E65100", tags="cell")
        elif cell.cell_type == CellType.FREE_PARKING:
            self.create_text(cx, price_y, text="休息一下",
                             font=FONT_CELL_PRICE, fill="#616161", tags="cell")
        elif cell.cell_type == CellType.BANKRUPTCY:
            self.create_text(cx, price_y, text="罚金 ¥150",
                             font=FONT_CELL_PRICE, fill="#C62828", tags="cell")
        elif cell.cell_type == CellType.CHANCE:
            self.create_text(cx, price_y, text="🃏 机遇",
                             font=FONT_CELL_PRICE, fill="#E65100", tags="cell")
        elif cell.cell_type == CellType.COMMUNITY_CHEST:
            self.create_text(cx, price_y, text="📦 命运",
                             font=FONT_CELL_PRICE, fill="#1565C0", tags="cell")

    def _draw_center(self):
        """Draw the inner 9x9 area with title and dice display."""
        ix1 = 1 * CELL_SIZE + 2
        iy1 = 1 * CELL_SIZE + 2
        ix2 = 10 * CELL_SIZE - 2
        iy2 = 10 * CELL_SIZE - 2

        self.create_rectangle(ix1, iy1, ix2, iy2,
                              fill=CENTER_BG, outline=BOARD_BORDER,
                              width=3, tags="center")

        cx = ix1 + (ix2 - ix1) // 2
        cy_top = iy1 + 160

        self.create_text(cx, cy_top - 60, text="🎲 双人大富翁 🎲",
                         font=FONT_CENTER_TITLE, fill="#8B4513", tags="center")
        self.create_text(cx, cy_top, text="Two-Player Monopoly",
                         font=FONT_CENTER_SUB, fill="#A0826D", tags="center")

        dice_y = cy_top + 80
        self.create_rectangle(cx - 180, dice_y, cx + 180, dice_y + 260,
                              fill="#F5F5DC", outline="#8B4513",
                              width=2, tags="center")
        self.create_text(cx, dice_y + 30, text="🎯 骰子",
                         font=("Microsoft YaHei", 20, "bold"),
                         fill="#8B4513", tags="center")

        self.create_rectangle(cx - 130, dice_y + 60, cx - 10, dice_y + 200,
                              outline="#8B4513", width=3, tags="center")
        self.create_rectangle(cx + 10, dice_y + 60, cx + 130, dice_y + 200,
                              outline="#8B4513", width=3, tags="center")

        self.dice1_text = self.create_text(
            cx - 70, dice_y + 130, text="?",
            font=FONT_DICE_NUM, fill="#999999", tags="center"
        )
        self.dice2_text = self.create_text(
            cx + 70, dice_y + 130, text="?",
            font=FONT_DICE_NUM, fill="#999999", tags="center"
        )

        self.total_text = self.create_text(
            cx, dice_y + 245, text="",
            font=("Microsoft YaHei", 22, "bold"), fill="#8B4513", tags="center"
        )

    def _draw_pieces(self):
        """Draw player pieces."""
        for idx, player in enumerate(self.engine.players):
            self._draw_piece(idx, player)

    def _draw_piece(self, player_idx: int, player: Player):
        """Draw a single player piece."""
        cell = self.engine.get_cell(player.position)
        cx = cell.col * CELL_SIZE + CELL_SIZE // 2
        cy = cell.row * CELL_SIZE + CELL_SIZE // 2

        if player_idx == 0:
            px = cx - PIECE_OFFSET
            py = cy - PIECE_OFFSET
        else:
            px = cx + PIECE_OFFSET - PIECE_SIZE
            py = cy + PIECE_OFFSET - PIECE_SIZE

        if player_idx in self.piece_ids:
            self.delete(self.piece_ids[player_idx])

        piece_id = self.create_oval(
            px, py, px + PIECE_SIZE, py + PIECE_SIZE,
            fill=player.color, outline="white", width=3, tags="piece"
        )
        self.create_text(
            px + PIECE_SIZE // 2, py + PIECE_SIZE // 2,
            text=str(player_idx + 1),
            font=("Microsoft YaHei", 18, "bold"),
            fill="white", tags="piece"
        )
        self.piece_ids[player_idx] = piece_id

    def update_display(self):
        """Refresh the entire board display."""
        self.delete("cell")
        self.delete("piece")
        self.cell_rects.clear()

        for pos in range(40):
            cell = self.engine.get_cell(pos)
            self._draw_cell(cell, pos)

        self._update_dice()
        self.piece_ids.clear()
        self._draw_pieces()
        self.tag_raise("piece")

    def _update_dice(self):
        """Update dice values."""
        if self.engine.dice1 > 0:
            self.itemconfig(self.dice1_text, text=str(self.engine.dice1),
                            fill="#333333")
            self.itemconfig(self.dice2_text, text=str(self.engine.dice2),
                            fill="#333333")
            total = self.engine.dice1 + self.engine.dice2
            self.itemconfig(self.total_text, text=f"合计: {total} 步")
        else:
            self.itemconfig(self.dice1_text, text="?", fill="#999999")
            self.itemconfig(self.dice2_text, text="?", fill="#999999")
            self.itemconfig(self.total_text, text="")

    def animate_move(self, from_pos: int, steps: int, on_complete: callable):
        """Animate player piece moving step by step."""
        positions = [(from_pos + i) % 40 for i in range(1, steps + 1)]

        def step_animate(idx: int):
            if idx >= len(positions):
                on_complete()
                return
            pos = positions[idx]
            self.engine.current_player.position = pos
            self.update_display()
            delay = 60 + idx * 5
            self.after(delay, lambda n=idx + 1: step_animate(n))

        step_animate(0)


# ==================== Player Panel ====================

class PlayerPanel(tk.Frame):
    """Right-side panel showing player info, card display, and game log."""

    CARD_HEIGHT = 215
    AVATAR_SIZE = 80
    CIRCLE_R = 32

    def __init__(self, parent, engine: GameEngine, **kwargs):
        super().__init__(parent, width=PANEL_WIDTH, height=PANEL_HEIGHT,
                         bg="#F5F0E8", **kwargs)
        self.engine = engine
        self.pack_propagate(False)

        # Widget refs
        self.p1_frame: Optional[tk.Frame] = None
        self.p2_frame: Optional[tk.Frame] = None
        self.p1_cash: Optional[tk.Label] = None
        self.p2_cash: Optional[tk.Label] = None
        self.p1_prop: Optional[tk.Label] = None
        self.p2_prop: Optional[tk.Label] = None
        self.p1_pos: Optional[tk.Label] = None
        self.p2_pos: Optional[tk.Label] = None
        self.p1_status: Optional[tk.Label] = None
        self.p2_status: Optional[tk.Label] = None
        self.p1_jail_card: Optional[tk.Label] = None
        self.p2_jail_card: Optional[tk.Label] = None
        self.turn_label: Optional[tk.Label] = None
        self.log_text: Optional[ScrolledText] = None

        # Card display area
        self.card_frame: Optional[tk.Frame] = None
        self.card_icon: Optional[tk.Label] = None
        self.card_title: Optional[tk.Label] = None
        self.card_desc: Optional[tk.Label] = None
        self._card_fade_job: Optional[str] = None

        self._build()

    def _build(self):
        """Build all panel widgets."""
        tk.Label(self, text="📋 玩家信息", font=FONT_SUBTITLE,
                 bg="#F5F0E8", fg="#5D4037").pack(pady=(12, 6))

        # Player 1 card
        self.p1_frame = self._make_card_frame()
        self.p1_frame.pack(fill="x", padx=18, pady=6)
        self._build_card_content(self.p1_frame, 0)

        # Player 2 card
        self.p2_frame = self._make_card_frame()
        self.p2_frame.pack(fill="x", padx=18, pady=6)
        self._build_card_content(self.p2_frame, 1)

        # Turn indicator
        self.turn_label = tk.Label(self, text="", font=FONT_STATUS,
                                    bg="#F5F0E8", fg="#5D4037")
        self.turn_label.pack(pady=4)

        # Card display area
        self._build_card_display()

        # Separator
        tk.Frame(self, height=2, bg="#BDBDBD").pack(fill="x", padx=25, pady=4)

        # Log section
        tk.Label(self, text="📜 游戏日志", font=FONT_SUBTITLE,
                 bg="#F5F0E8", fg="#5D4037").pack(pady=(4, 2))

        self.log_text = ScrolledText(self, font=FONT_LOG, bg="#FFFDE7",
                                      fg="#333333", wrap=tk.WORD,
                                      state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=18, pady=(0, 15))

    def _make_card_frame(self) -> tk.Frame:
        frame = tk.Frame(self, bg="white", bd=2, relief="solid",
                         highlightbackground="#BDBDBD", highlightthickness=1)
        frame.pack_propagate(False)
        frame.configure(height=self.CARD_HEIGHT)
        return frame

    def _build_card_content(self, frame: tk.Frame, player_idx: int):
        """Build player card content."""
        player = self.engine.players[player_idx]
        card_w = PANEL_WIDTH - 36

        avatar_size = self.AVATAR_SIZE
        avatar = tk.Canvas(frame, width=avatar_size, height=avatar_size,
                           bg="white", highlightthickness=0)
        avatar.place(x=18, y=(self.CARD_HEIGHT - avatar_size) // 2)

        r = self.CIRCLE_R
        cx_a = avatar_size // 2
        cy_a = avatar_size // 2
        avatar.create_oval(cx_a - r, cy_a - r, cx_a + r, cy_a + r,
                           fill=player.color, outline=player.color, width=2)
        avatar.create_oval(cx_a - r + 2, cy_a - r + 2, cx_a + r - 2, cy_a + r - 2,
                           fill="", outline="#FFFFFF", width=1)
        avatar.create_text(cx_a, cy_a, text=str(player_idx + 1),
                           font=("Microsoft YaHei", 26, "bold"), fill="white")

        info_x = 130
        line_h = 38

        tk.Label(frame, text=player.name, font=FONT_PLAYER,
                 bg="white", fg=player.color, anchor="w").place(
            x=info_x, y=20, width=card_w - info_x - 15)

        cash_lbl = tk.Label(frame, text="", font=FONT_PLAYER_INFO,
                            bg="white", fg="#333333", anchor="w")
        cash_lbl.place(x=info_x, y=20 + line_h, width=card_w - info_x - 15)

        prop_lbl = tk.Label(frame, text="", font=FONT_PLAYER_SMALL,
                            bg="white", fg="#555555", anchor="w")
        prop_lbl.place(x=info_x, y=20 + line_h * 2, width=card_w - info_x - 15)

        pos_lbl = tk.Label(frame, text="", font=FONT_PLAYER_SMALL,
                           bg="white", fg="#888888", anchor="w")
        pos_lbl.place(x=info_x, y=20 + line_h * 3, width=card_w - info_x - 15)

        status_lbl = tk.Label(frame, text="", font=("Microsoft YaHei", 14, "bold"),
                              bg="white", fg="#E65100", anchor="w")
        status_lbl.place(x=info_x, y=20 + line_h * 4, width=card_w - info_x - 15)

        if player_idx == 0:
            self.p1_cash = cash_lbl
            self.p1_prop = prop_lbl
            self.p1_pos = pos_lbl
            self.p1_status = status_lbl
        else:
            self.p2_cash = cash_lbl
            self.p2_prop = prop_lbl
            self.p2_pos = pos_lbl
            self.p2_status = status_lbl

        self._set_card_values(player_idx, cash_lbl, prop_lbl, pos_lbl, status_lbl)

    def _build_card_display(self):
        """Build the card display area (shown when a card is drawn)."""
        self.card_frame = tk.Frame(self, bg="#F5F0E8", height=0)
        # Don't pack initially — will be shown/hidden

    def show_card(self, card: Card):
        """Display a card in the card area, auto-hide after CARD_DISPLAY_MS."""
        self._hide_card()

        card_bg = CARD_BG_CHANCE if card.card_type == CardType.CHANCE else CARD_BG_COMMUNITY
        card_border = CARD_BORDER_CHANCE if card.card_type == CardType.CHANCE else CARD_BORDER_COMMUNITY
        card_label = "🃏 机遇卡" if card.card_type == CardType.CHANCE else "📦 命运卡"
        icon_text = "🃏" if card.card_type == CardType.CHANCE else "📦"

        self.card_frame = tk.Frame(self, bg=card_bg, bd=3, relief="solid",
                                    highlightbackground=card_border,
                                    highlightthickness=3)
        self.card_frame.pack(fill="x", padx=18, pady=6, before=self.log_text.master)

        # Card content
        inner = tk.Frame(self.card_frame, bg=card_bg)
        inner.pack(fill="both", expand=True, padx=15, pady=12)

        self.card_icon = tk.Label(inner, text=icon_text, font=FONT_CARD_ICON, bg=card_bg)
        self.card_icon.pack(side="left", padx=(0, 12))

        text_area = tk.Frame(inner, bg=card_bg)
        text_area.pack(side="left", fill="both", expand=True)

        self.card_title = tk.Label(text_area, text=f"{card_label}：{card.title}",
                                    font=FONT_CARD_TITLE, bg=card_bg,
                                    fg=card_border, anchor="w")
        self.card_title.pack(fill="x")

        self.card_desc = tk.Label(text_area, text=card.description,
                                   font=FONT_CARD_BODY, bg=card_bg,
                                   fg="#333333", anchor="w", justify="left")
        self.card_desc.pack(fill="x", pady=(4, 0))

        # Schedule fade-out
        self._card_fade_job = self.after(CARD_DISPLAY_MS, self._start_fade_out)

    def _start_fade_out(self):
        """Begin fade-out animation on the card display."""
        if self.card_frame is None or not self.card_frame.winfo_exists():
            return
        self._fade_step = 0
        self._do_fade_step()

    def _do_fade_step(self):
        """Perform one step of fade-out."""
        if self.card_frame is None or not self.card_frame.winfo_exists():
            return
        self._fade_step += 1
        if self._fade_step >= CARD_FADE_STEPS:
            self._hide_card()
            return
        # Reduce opacity by shifting background toward parent bg
        self.card_frame.configure(bg="#F0EAD8")
        self.after(80, self._do_fade_step)

    def _hide_card(self):
        """Remove the card display."""
        if self._card_fade_job is not None:
            self.after_cancel(self._card_fade_job)
            self._card_fade_job = None
        if self.card_frame is not None and self.card_frame.winfo_exists():
            self.card_frame.destroy()
            self.card_frame = None
        self.card_icon = None
        self.card_title = None
        self.card_desc = None

    def update_display(self):
        """Refresh all panel information."""
        self._update_card(0, self.p1_cash, self.p1_prop, self.p1_pos, self.p1_status)
        self._update_card(1, self.p2_cash, self.p2_prop, self.p2_pos, self.p2_status)

        if self.engine.game_over:
            self.turn_label.config(
                text=f"🏆 {self.engine.winner.name} 获胜！游戏结束！", fg="#2E7D32")
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

    def _set_card_values(self, idx: int, cash_lbl, prop_lbl, pos_lbl, status_lbl):
        player = self.engine.players[idx]
        cash_lbl.config(text=f"💰 现金: ¥{player.cash:,}")
        prop_val = self.engine.get_total_property_value(idx)
        jail_info = f"  🔑×{player.jail_free_cards}" if player.jail_free_cards > 0 else ""
        prop_lbl.config(text=f"🏠 地产: {len(player.properties)} 处 (总价 ¥{prop_val:,}){jail_info}")
        pos_lbl.config(text=f"📍 {self.engine.get_cell(player.position).name}")
        if player.skip_turn:
            status_lbl.config(text="⚠ 下回合暂停（监狱中）")
        elif player.jail_free_cards > 0:
            status_lbl.config(text=f"🔑 持有 {player.jail_free_cards} 张出狱免费卡")
        else:
            status_lbl.config(text="")

    def _update_card(self, idx, cash_lbl, prop_lbl, pos_lbl, status_lbl):
        self._set_card_values(idx, cash_lbl, prop_lbl, pos_lbl, status_lbl)

    def _update_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        for entry in self.engine.log[-60:]:
            self.log_text.insert(tk.END, entry + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")


# ==================== Main Application ====================

class RichManApp(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("双人大富翁 - Two-Player Monopoly")
        self.configure(bg="#3E2723")

        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        self.engine = GameEngine()

        self._can_roll = True
        self._can_buy = False
        self._animating = False
        self._pending_card: bool = False  # True when waiting for card to be shown
        self._pending_end_id: Optional[str] = None
        self._btn_widgets: dict = {}

        self._build_ui()
        self.engine.reset()
        self.refresh_all()

        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        actual_w = self.winfo_width()
        actual_h = self.winfo_height()

        if actual_w > screen_w:
            ratio = screen_w / actual_w
            fit_w = int(screen_w * 0.78)
            fit_h = int(actual_h * ratio * 0.82)
            self.geometry(f"{fit_w}x{fit_h}")
            self.update_idletasks()
            actual_w = self.winfo_width()
            actual_h = self.winfo_height()

        x = max(0, (screen_w - actual_w) // 2)
        y = max(0, (screen_h - actual_h) // 2)
        self.geometry(f"+{x}+{y}")

    # ======== UI Construction ========

    def _build_ui(self):
        """Build the complete UI layout."""
        title_frame = tk.Frame(self, bg="#4E342E", height=65)
        title_frame.pack(fill="x", side="top")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="🎲 双 人 大 富 翁 🎲",
                 font=FONT_TITLE, bg="#4E342E", fg="#FFCC80").pack(expand=True)

        content = tk.Frame(self, bg="#3E2723")
        content.pack(fill="both", expand=True, side="top")

        self.board_canvas = BoardCanvas(content, self.engine)
        self.board_canvas.place(x=BOARD_X, y=BOARD_Y)

        self.player_panel = PlayerPanel(content, self.engine)
        self.player_panel.place(x=PANEL_X, y=PANEL_Y)

        bottom_frame = tk.Frame(self, bg="#3E2723", height=155)
        bottom_frame.pack(fill="x", side="bottom")
        bottom_frame.pack_propagate(False)

        self.status_label = tk.Label(bottom_frame, text="",
                                     font=FONT_STATUS, bg="#3E2723", fg="#FFCC80")
        self.status_label.pack(pady=(10, 4))

        btn_container = tk.Frame(bottom_frame, bg="#3E2723")
        btn_container.pack(expand=True)

        buttons_spec = [
            ("roll", "🎲 掷骰子", BTN_ROLL, self.on_roll),
            ("buy", "🏠 购买地产", BTN_BUY, self.on_buy),
            ("end", "⏭️ 结束回合", BTN_END, self.on_end_turn),
            ("jail_free", "🔑 出狱卡", BTN_RULES, self.on_use_jail_card),
            ("restart", "🔄 重新开始", BTN_RESTART, self.on_restart),
            ("rules", "📖 规则说明", BTN_RULES, self.on_rules),
        ]

        for key, text, color, cmd in buttons_spec:
            btn = self._make_button(btn_container, text, color, cmd)
            btn.pack(side="left", padx=10)
            self._btn_widgets[key] = btn

    def _make_button(self, parent, text: str, color: str,
                     command: callable) -> tk.Button:
        """Create a styled button."""
        btn = tk.Button(
            parent, text=text, font=FONT_BUTTON,
            fg="white", bg=color,
            activeforeground="white",
            activebackground=self._darken(color, 0.85),
            bd=0, padx=28, pady=18, cursor="hand2",
            command=command, width=10,
            disabledforeground="#CCCCCC",
        )
        def on_enter(e, b=btn, c=color):
            if str(b.cget("state")) != "disabled":
                b.configure(bg=self._lighten(c, 0.2))
        def on_leave(e, b=btn, c=color):
            if str(b.cget("state")) != "disabled":
                b.configure(bg=c)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    @staticmethod
    def _lighten(hex_color: str, factor: float) -> str:
        c = hex_color.lstrip('#')
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        c = hex_color.lstrip('#')
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"

    # ======== Button State Management ========

    def _update_button_states(self):
        """Enable/disable buttons based on game state."""
        player = self.engine.current_player
        has_jail_card = player.jail_free_cards > 0
        in_jail = player.skip_turn

        if self.engine.game_over:
            self._set_buttons(roll=False, buy=False, end=False,
                              jail_free=False, restart=True, rules=True)
            self.status_label.config(text="🏆 游戏结束！点击「重新开始」再来一局")
        elif self._animating:
            self._set_buttons(roll=False, buy=False, end=False,
                              jail_free=False, restart=False, rules=True)
            self.status_label.config(text="🎲 移动中...")
        elif self._can_roll:
            self._set_buttons(roll=True, buy=False, end=False,
                              jail_free=has_jail_card and in_jail,
                              restart=True, rules=True)
            if in_jail:
                self.status_label.config(
                    text=f"🔒 {player.name} 在监狱中！使用出狱卡或掷骰子")
            else:
                self.status_label.config(
                    text=f"🎯 {player.name} 的回合，请掷骰子！")
        elif self._can_buy:
            self._set_buttons(roll=False, buy=True, end=True,
                              jail_free=False, restart=True, rules=True)
            cell = self.engine.get_cell(player.position)
            self.status_label.config(
                text=f"💡 可购买「{cell.name}」(¥{cell.price})，或结束回合")
        elif self._pending_card:
            self._set_buttons(roll=False, buy=False, end=False,
                              jail_free=False, restart=False, rules=True)
            self.status_label.config(text="🃏 正在展示卡片...")
        else:
            self._set_buttons(roll=False, buy=False, end=True,
                              jail_free=False, restart=True, rules=True)
            self.status_label.config(text="点击「结束回合」继续")

    def _set_buttons(self, roll: bool, buy: bool, end: bool,
                     jail_free: bool, restart: bool, rules: bool):
        """Set button enabled/disabled states."""
        states = {
            "roll": tk.NORMAL if roll else tk.DISABLED,
            "buy": tk.NORMAL if buy else tk.DISABLED,
            "end": tk.NORMAL if end else tk.DISABLED,
            "jail_free": tk.NORMAL if jail_free else tk.DISABLED,
            "restart": tk.NORMAL if restart else tk.DISABLED,
            "rules": tk.NORMAL if rules else tk.DISABLED,
        }
        colors = {
            "roll": BTN_ROLL, "buy": BTN_BUY, "end": BTN_END,
            "jail_free": "#8D6E63", "restart": BTN_RESTART, "rules": BTN_RULES,
        }
        for key, state in states.items():
            if key in self._btn_widgets:
                btn = self._btn_widgets[key]
                btn.configure(state=state)
                btn.configure(bg="#666666" if state == tk.DISABLED else colors[key])

    # ======== End-Turn Scheduling ========

    def _schedule_end_turn(self, delay_ms: int):
        self._cancel_pending_end()
        self._pending_end_id = self.after(delay_ms, self._end_turn_scheduled)

    def _cancel_pending_end(self):
        if self._pending_end_id is not None:
            self.after_cancel(self._pending_end_id)
            self._pending_end_id = None

    def _end_turn_scheduled(self):
        self._pending_end_id = None
        self._end_turn()

    # ======== Button Handlers ========

    def on_roll(self):
        """Handle roll dice button click."""
        if not self._can_roll or self._animating or self.engine.game_over:
            return

        player = self.engine.current_player
        if player.skip_turn and player.jail_free_cards > 0:
            # In jail with card — should use jail card instead
            return

        if self.engine.check_jail_skip():
            self._can_roll = False
            self.refresh_all()
            self._schedule_end_turn(1000)
            return

        self._can_roll = False
        self._animating = True
        self._can_buy = False
        self._pending_card = False

        d1, d2 = self.engine.roll_dice()
        steps = d1 + d2
        from_pos = self.engine.current_player.position
        self.refresh_all()

        self.after(500, lambda: self.board_canvas.animate_move(
            from_pos, steps, on_complete=self._on_move_complete
        ))

    def _on_move_complete(self):
        """Called after movement animation finishes."""
        self._animating = False
        result = self.engine.process_landing()

        if self.engine.game_over:
            self.refresh_all()
            self.update()
            messagebox.showinfo("游戏结束",
                                f"💀 {self.engine.current_player.name} 破产了！\n\n"
                                f"🏆 {self.engine.winner.name} 获胜！")
            return

        if result in ("chance", "community"):
            self._process_card_landing(result)
        elif result == "buyable":
            self._can_buy = True
            self.engine.add_log("💡 你可以购买当前地产，或选择结束回合。")
            self.refresh_all()
        else:
            self._can_buy = False
            self.refresh_all()
            self._schedule_end_turn(800)

    def _process_card_landing(self, result: str):
        """Handle landing on a card cell."""
        cell_type = CellType.CHANCE if result == "chance" else CellType.COMMUNITY_CHEST
        card = self.engine.draw_card(cell_type)

        # Show card in panel
        self.player_panel.show_card(card)
        self._pending_card = True
        self.refresh_all()

        # After card display time, execute effect
        self.after(CARD_DISPLAY_MS, lambda: self._execute_card_effect(card))

    def _execute_card_effect(self, card: Card):
        """Execute the card effect after display time."""
        self._pending_card = False

        if card.keepable:
            # "出狱免费卡" — already added to player inventory by effect
            self.engine.execute_card_effect(self.engine.current_player_idx, card)
        else:
            self.engine.execute_card_effect(self.engine.current_player_idx, card)

        # Check bankruptcy after card effect
        player = self.engine.current_player
        if player.cash < 0:
            self.engine._declare_bankruptcy(player)

        if self.engine.game_over:
            self.refresh_all()
            self.update()
            messagebox.showinfo("游戏结束",
                                f"💀 {player.name} 破产了！\n\n"
                                f"🏆 {self.engine.winner.name} 获胜！")
            return

        self.refresh_all()
        self._schedule_end_turn(600)

    def on_use_jail_card(self):
        """Handle use jail-free card button."""
        player = self.engine.current_player
        if player.jail_free_cards <= 0:
            return
        if not player.skip_turn:
            messagebox.showinfo("提示", "你当前不在监狱中，无需使用出狱卡。", parent=self)
            return

        self.engine.use_jail_free_card(self.engine.current_player_idx)
        self.refresh_all()
        messagebox.showinfo("出狱成功", f"{player.name} 使用出狱免费卡，重获自由！", parent=self)

    def on_buy(self):
        """Handle buy property button click."""
        if not self._can_buy or self.engine.game_over:
            return

        success, msg = self.engine.buy_property()
        if success:
            self._can_buy = False
            self.refresh_all()
            self._schedule_end_turn(500)
        else:
            messagebox.showwarning("购买失败", msg, parent=self)

    def on_end_turn(self):
        """Handle end turn button click."""
        if self._animating or self.engine.game_over:
            return

        if self._can_buy:
            self.engine.add_log(
                f"{self.engine.current_player.name} 选择不购买，结束回合。")
            self._can_buy = False

        if not self._can_roll:
            self._end_turn()

    def _end_turn(self):
        """Internal: end current player's turn and advance."""
        self._cancel_pending_end()
        if self.engine.game_over:
            return
        self.engine.next_turn()
        self._can_roll = True
        self._can_buy = False
        self._pending_card = False
        self.refresh_all()

    def on_restart(self):
        """Handle restart button click."""
        if self._animating:
            return
        ok = messagebox.askyesno("重新开始",
                                 "确定要重新开始游戏吗？\n当前进度将丢失。",
                                 parent=self)
        if ok:
            self._cancel_pending_end()
            self.engine.reset()
            self._can_roll = True
            self._can_buy = False
            self._animating = False
            self._pending_card = False
            self.player_panel._hide_card()
            self.refresh_all()

    def on_rules(self):
        """Show game rules dialog."""
        rules_text = """\
╔══════════════════════════════════════════╗
║      📖 双人大富翁 - 完整游戏规则       ║
╚══════════════════════════════════════════╝

🎯 游戏目标
━━━━━━━━━━━━━━━━━━━━━━━━━━
让你的对手破产，成为最终赢家！

🎮 游戏流程
━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 两名玩家轮流掷骰子行动
2. 棋子按骰子点数之和移动对应步数
3. 根据停留的格子触发不同效果

🏠 地产系统
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 走到空地时可购买 → 点击「购买地产」
• 对手走到你的地产 → 支付 10% 过路费
• 共 32 处可购买地产

🃏 卡片系统 (NEW!)
━━━━━━━━━━━━━━━━━━━━━━━━━━
机遇卡（橙色格子）— 第7格、第22格
  • 可能获得金钱、移动位置、特殊效果

命运卡（蓝色格子）— 第12格、第36格
  • 生活事件，有喜有忧

出狱免费卡
  • 抽到后可保留在手中
  • 在监狱中点击「出狱卡」按钮使用
  • 每位玩家最多持有多张

🎁 特殊格子
━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 起点(第0格)：到达获得 200 元
🔒 监狱(第30格)：暂停一回合
🅿️  免费停车(第20格)：什么都不做
🔴 破产格(第10格)：缴纳 150 元
🟠 机遇卡(第7、22格)：抽取机遇卡
🔵 命运卡(第12、36格)：抽取命运卡

💀 破产条件
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 现金 < 0 时立即破产，对手获胜
"""

        dialog = tk.Toplevel(self)
        dialog.title("游戏规则说明")
        dialog.configure(bg="#FFF8E1")

        dw, dh = 750, 850
        sx = (self.winfo_screenwidth() - dw) // 2
        sy = (self.winfo_screenheight() - dh) // 2
        dialog.geometry(f"{dw}x{dh}+{sx}+{sy}")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="📖 双人大富翁 - 完整规则",
                 font=FONT_RULES_TITLE, bg="#FFF8E1", fg="#5D4037").pack(pady=15)

        text_widget = ScrolledText(dialog, font=FONT_RULES_BODY,
                                    bg="#FFFDE7", fg="#333333",
                                    wrap=tk.WORD, width=65, height=30)
        text_widget.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        text_widget.insert("1.0", rules_text)
        text_widget.configure(state="disabled")

        tk.Button(dialog, text="我知道了", font=FONT_BUTTON,
                  fg="white", bg="#795548", bd=0,
                  padx=40, pady=12, cursor="hand2",
                  command=dialog.destroy).pack(pady=(0, 20))

    def refresh_all(self):
        """Refresh the entire UI."""
        self.board_canvas.update_display()
        self.player_panel.update_display()
        self._update_button_states()


# ==================== Main Entry Point ====================

def main():
    """Launch the game."""
    app = RichManApp()
    app.mainloop()


if __name__ == "__main__":
    main()
