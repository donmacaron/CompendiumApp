from __future__ import annotations

import json
import math
import random
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk


APP_DIR = Path(__file__).resolve().parent

ATTRIBUTES = [
    ("Strength", "Str"),
    ("Dexterity", "Dex"),
    ("Constitution", "Con"),
    ("Intelligence", "Int"),
    ("Willpower", "Will"),
    ("Perception", "Perc"),
    ("Charisma", "Cha"),
]
ATTRIBUTE_NAMES = [name for name, _short in ATTRIBUTES]
DEFAULT_ARRAY = [16, 14, 13, 11, 10, 8, 7]
UNIQUE_LEVELS = [3, 6, 9, 12]

PARCHMENT = "#d7c39a"
PARCHMENT_DARK = "#b99d63"
PANEL = "#ead9af"
INK = "#1b100b"
INK_MUTED = "#46342a"
BLOOD = "#7d241d"
IRON = "#342822"
BLACK = "#0f0906"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def clean_md(value: str) -> str:
    value = value.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    value = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    value = re.sub(r"\*(.*?)\*", r"\1", value)
    value = re.sub(r"`(.*?)`", r"\1", value)
    value = value.replace("&amp;", "&")
    return value.strip()


def md_cells(line: str) -> List[str]:
    if not line.strip().startswith("|"):
        return []
    cells = [clean_md(cell) for cell in line.strip().strip("|").split("|")]
    return cells


def is_separator_row(line: str) -> bool:
    cells = md_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{2,}:?", cell.strip()) for cell in cells)


def title_from_heading(raw: str) -> str:
    raw = clean_md(raw).strip()
    raw = re.sub(r"^\d+\.\s*", "", raw)
    return raw.title() if raw.isupper() else raw


def normalize_class_name(name: str) -> str:
    name = clean_md(name)
    name = re.sub(r"\s+Class\s+Guide\s*$", "", name, flags=re.I).strip()
    name = name.replace("Artificier", "Artificer")
    return name


def score_modifier(score: int) -> int:
    if score <= 4:
        return -3
    if score <= 6:
        return -2
    if score <= 8:
        return -1
    if score <= 12:
        return 0
    if score <= 14:
        return 1
    if score <= 16:
        return 2
    if score <= 18:
        return 3
    return 4 + max(0, score - 19) // 2


def great_success(score: int) -> int:
    return max(1, score // 2)


def terrible_failure(score: int) -> int:
    return min(20, score + score // 2 + 1)


def starting_luck(level: int, race: str = "") -> int:
    base = 10 + math.ceil(max(1, level) / 2)
    if race.lower() == "halflings" or race.lower() == "halfling":
        base += 1
    return base


def starting_reroll(level: int, race: str = "") -> int:
    base = max(1, level)
    if race.lower() == "humans" or race.lower() == "human":
        base += 1
    return base


def unique_feature_slots(level: int) -> int:
    return sum(1 for threshold in UNIQUE_LEVELS if level >= threshold)


def new_skill_slots(level: int) -> int:
    return (1 if level >= 4 else 0) + (1 if level >= 8 else 0)


def roll_ndm(count: int, sides: int) -> Tuple[int, List[int]]:
    rolls = [random.randint(1, sides) for _ in range(max(0, count))]
    return sum(rolls), rolls


def roll_stat_array(use_3d6: bool = False) -> Tuple[List[int], str]:
    values = []
    details = []
    for _ in range(6):
        if use_3d6:
            total, rolls = roll_ndm(3, 6)
            values.append(total)
            details.append(f"3d6 {rolls} = {total}")
        else:
            _total, rolls = roll_ndm(4, 6)
            kept = sorted(rolls, reverse=True)[:3]
            total = sum(kept)
            values.append(total)
            details.append(f"4d6 drop lowest {rolls}, keep {kept} = {total}")
    values.append(15)
    details.append("automatic score = 15")
    return values, "; ".join(details)


def safe_eval_arithmetic(expr: str) -> int:
    expr = expr.strip()
    if not re.fullmatch(r"[0-9+\-*/(). ]+", expr):
        raise ValueError(f"Unsafe dice expression: {expr}")
    return int(eval(expr, {"__builtins__": {}}, {}))


def roll_dice_expression(expr: str) -> Tuple[int, str]:
    original = expr
    expr = expr.lower()
    expr = expr.replace("gp", "")
    expr = expr.replace("+", " + ")
    expr = expr.replace("-", " - ")
    expr = expr.replace("x", "*").replace("×", "*")
    expr = expr.replace(",", "")
    expr = re.sub(r"[^0-9d+\-*/(). ]", "", expr)
    details: List[str] = []

    def replace_dice(match: re.Match[str]) -> str:
        count_text, sides_text = match.groups()
        count = int(count_text) if count_text else 1
        sides = int(sides_text)
        total, rolls = roll_ndm(count, sides)
        details.append(f"{count}d{sides}{rolls}={total}")
        return str(total)

    numeric_expr = re.sub(r"(\d*)d(\d+)", replace_dice, expr)
    numeric_expr = re.sub(r"\s+", " ", numeric_expr).strip()
    if not numeric_expr:
        raise ValueError(f"No dice expression found in {original!r}")
    total = safe_eval_arithmetic(numeric_expr)
    detail = f"{original.strip()} -> {numeric_expr} = {total}"
    if details:
        detail += " (" + ", ".join(details) + ")"
    return total, detail


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def extract_section(text: str, heading_regex: str, level: str = "##") -> str:
    pattern = re.compile(rf"^{re.escape(level)}\s+{heading_regex}.*$", re.I | re.M)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    stop = re.search(rf"^{re.escape(level)}\s+", text[start:], re.M)
    end = start + stop.start() if stop else len(text)
    return text[start:end].strip()


def extract_any_heading_section(text: str, heading_text: str) -> str:
    pattern = re.compile(rf"^#+\s+{re.escape(heading_text)}.*$", re.I | re.M)
    match = pattern.search(text)
    if not match:
        return ""
    hashes = re.match(r"^(#+)", match.group(0)).group(1)
    start = match.end()
    stop = re.search(rf"^{hashes}\s+", text[start:], re.M)
    end = start + stop.start() if stop else len(text)
    return text[start:end].strip()


def parse_markdown_table(section: str) -> List[List[str]]:
    rows: List[List[str]] = []
    for line in section.splitlines():
        if is_separator_row(line):
            continue
        cells = md_cells(line)
        if not cells:
            continue
        if any(cell.lower() in {"item", "skill", "level", "#", "number", "trick", "style"} for cell in cells):
            rows.append(cells)
        else:
            rows.append(cells)
    return rows


@dataclass
class GearItem:
    name: str
    rarity: str
    price_expr: str
    quantity: str = "1"
    description: str = ""


@dataclass
class SpellRule:
    name: str
    level: int
    description: str = "Description not provided."
    range_text: str = ""
    duration: str = ""


@dataclass
class ClassRule:
    name: str
    source_file: str
    text: str
    key_attributes: str = ""
    hp_text: str = ""
    equipment_text: str = ""
    fixed_skills: List[str] = field(default_factory=list)
    skill_options: List[str] = field(default_factory=list)
    skill_choose: int = 0
    attack_bonus: Dict[int, int] = field(default_factory=dict)
    spell_uses: Dict[int, Dict[int, int]] = field(default_factory=dict)
    options: Dict[str, List[str]] = field(default_factory=dict)


class RuleBook:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.texts: Dict[str, str] = {}
        self.races: Dict[str, str] = {}
        self.skills: Dict[str, Dict[str, str]] = {}
        self.gear: List[GearItem] = []
        self.gear_packs: Dict[str, str] = {}
        self.spells_by_level: Dict[int, List[str]] = {}
        self.spells: Dict[str, SpellRule] = {}
        self.unique_features: Dict[str, str] = {}
        self.classes: Dict[str, ClassRule] = {}
        self.load()

    def load(self) -> None:
        for name in ["character creating.md", "races.md", "skills.md", "gear.md", "spells.md", "unique features.md"]:
            self.texts[name] = read_text(self.base_dir / name)
        self.parse_races()
        self.parse_skills()
        self.parse_gear()
        self.parse_spells()
        self.parse_unique_features()
        self.parse_classes()

    def parse_races(self) -> None:
        text = self.texts.get("races.md", "")
        for match in re.finditer(r"^#\s+(.+?)\s*$\n(.*?)(?=^#\s+|\Z)", text, re.M | re.S):
            name = title_from_heading(match.group(1))
            self.races[name] = clean_md(match.group(2))

    def parse_skills(self) -> None:
        text = self.texts.get("skills.md", "")
        for line in text.splitlines():
            if is_separator_row(line):
                continue
            cells = md_cells(line)
            if len(cells) < 3 or cells[0].lower() == "skill":
                continue
            self.skills[cells[0]] = {"attribute": cells[1], "when": cells[2]}

    def parse_gear(self) -> None:
        text = self.texts.get("gear.md", "")
        current_rarity = ""
        in_packs = False
        pack_name = ""
        pack_lines: List[str] = []
        for line in text.splitlines():
            heading = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
            if heading:
                level, raw = heading.groups()
                title = clean_md(raw)
                if title.upper() == "GEAR PACKS":
                    in_packs = True
                    current_rarity = ""
                    continue
                if in_packs and level == "##":
                    if pack_name:
                        self.gear_packs[normalize_class_name(pack_name)] = " ".join(pack_lines).strip()
                    pack_name = normalize_class_name(title)
                    pack_lines = []
                    continue
                if "Common Gear" in title:
                    current_rarity = "Common"
                elif "Uncommon Equipment" in title:
                    current_rarity = "Uncommon"
                elif "Rare Equipment" in title:
                    current_rarity = "Rare"
                else:
                    current_rarity = ""
                continue
            if in_packs:
                if line.strip():
                    pack_lines.append(clean_md(line))
                continue
            if not current_rarity or is_separator_row(line):
                continue
            cells = md_cells(line)
            if not cells:
                continue
            if cells[0].lower() == "item":
                continue
            if current_rarity == "Common" and len(cells) >= 3:
                self.gear.append(GearItem(cells[0], "Common", cells[2], cells[1]))
            elif current_rarity == "Uncommon" and len(cells) >= 2:
                self.gear.append(GearItem(cells[0], "Uncommon", cells[1], "1"))
            elif current_rarity == "Rare" and len(cells) >= 2:
                desc = cells[2] if len(cells) >= 3 else ""
                self.gear.append(GearItem(cells[0], "Rare", cells[1], "1", desc))
        if pack_name:
            self.gear_packs[normalize_class_name(pack_name)] = " ".join(pack_lines).strip()

    def parse_spells(self) -> None:
        text = self.texts.get("spells.md", "")
        for level_match in re.finditer(
            r"^###\s+Level\s+(\d+)\s+Spells\s*$\n(.*?)(?=^###\s+Level\s+\d+\s+Spells|^##\s+Spell Descriptions|\Z)",
            text,
            re.M | re.S,
        ):
            level = int(level_match.group(1))
            names: List[str] = []
            for line in level_match.group(2).splitlines():
                if is_separator_row(line):
                    continue
                cells = md_cells(line)
                if len(cells) < 2 or cells[0] == "#":
                    continue
                for idx in range(0, len(cells) - 1, 2):
                    if cells[idx].isdigit():
                        name = cells[idx + 1]
                        if name and name.lower() != "spell name":
                            names.append(name)
                            self.spells.setdefault(name, SpellRule(name, level))
            self.spells_by_level[level] = names

        desc_text = extract_any_heading_section(text, "Spell Descriptions (Alphabetical Order)")
        if not desc_text:
            desc_text = text
        for match in re.finditer(r"^###\s+(.+?)\s*$\n(.*?)(?=^---\s*$\n\s*^###\s+|^###\s+|\Z)", desc_text, re.M | re.S):
            name = clean_md(match.group(1))
            if name.lower().startswith("level "):
                continue
            body = clean_md(match.group(2))
            level = self.spells.get(name, SpellRule(name, 0)).level
            level_line = re.search(r"Level:\*\*\s*(\d+)", match.group(2))
            if level_line and not level:
                level = int(level_line.group(1))
            range_text = ""
            duration = ""
            meta = re.search(r"\*\*Level:\*\*.*?\|\s*\*\*Range:\*\*\s*(.*?)\s*\|\s*\*\*Duration:\*\*\s*(.*)", match.group(2))
            if meta:
                range_text = clean_md(meta.group(1))
                duration = clean_md(meta.group(2).splitlines()[0])
            self.spells[name] = SpellRule(name, level, body or "Description not provided.", range_text, duration)

    def parse_unique_features(self) -> None:
        text = self.texts.get("unique features.md", "")
        for match in re.finditer(r"^###\s+(.+?)\s*$\n(.*?)(?=^###\s+|\Z)", text, re.M | re.S):
            name = clean_md(match.group(1))
            if name:
                self.unique_features[name] = clean_md(match.group(2))

    def parse_classes(self) -> None:
        class_dir = self.base_dir / "classes"
        for path in sorted(class_dir.glob("*.md")):
            text = read_text(path)
            heading = re.search(r"^#\s+(.+?)\s*$", text, re.M)
            if not heading:
                continue
            name = normalize_class_name(heading.group(1))
            rule = ClassRule(name=name, source_file=str(path.relative_to(self.base_dir)), text=text)
            rule.key_attributes = extract_any_heading_section(text, "Key Attributes")
            rule.hp_text = extract_any_heading_section(text, "Hit Points")
            rule.equipment_text = extract_any_heading_section(text, "Equipment")
            skills_text = self._extract_skills_section(text)
            rule.fixed_skills, rule.skill_options, rule.skill_choose = self._parse_class_skills(skills_text)
            rule.attack_bonus, rule.spell_uses = self._parse_attack_and_spell_tables(text)
            rule.options = self._parse_class_options(name, text)
            self.classes[name] = rule

    def _extract_skills_section(self, text: str) -> str:
        match = re.search(r"^###\s+Skills.*$", text, re.I | re.M)
        if not match:
            return ""
        start = match.start()
        stop = re.search(r"^---\s*$|^##\s+", text[match.end():], re.M)
        end = match.end() + stop.start() if stop else len(text)
        return text[start:end]

    def _parse_class_skills(self, section: str) -> Tuple[List[str], List[str], int]:
        fixed: List[str] = []
        options: List[str] = []
        choose = 0
        if not section:
            return fixed, options, choose
        heading_count = re.search(r"Choose\s+any\s+(\d+)", section, re.I)
        if heading_count:
            choose = int(heading_count.group(1))
        prof = re.search(r"\*\*Proficient:\*\*\s*(.+)", section, re.I)
        if prof:
            fixed = [clean_md(part) for part in prof.group(1).split(",") if clean_md(part)]
        add = re.search(r"\*\*Additional\s*\(\+(\d+)\):\*\*\s*(.+)", section, re.I)
        if add:
            choose = int(add.group(1))
            options = [clean_md(part) for part in add.group(2).split(",") if clean_md(part)]
        elif heading_count:
            bullets = re.findall(r"^-\s+(.+)$", section, re.M)
            if bullets:
                options = [clean_md(part) for part in ",".join(bullets).split(",") if clean_md(part)]
        return fixed, options, choose

    def _parse_attack_and_spell_tables(self, text: str) -> Tuple[Dict[int, int], Dict[int, Dict[int, int]]]:
        attack: Dict[int, int] = {}
        spell_uses: Dict[int, Dict[int, int]] = {}
        lines = text.splitlines()
        for i, line in enumerate(lines):
            cells = md_cells(line)
            if not cells:
                continue
            if cells[:2] == ["Level", "Attack Bonus"]:
                for row in lines[i + 2:]:
                    row_cells = md_cells(row)
                    if not row_cells or not row_cells[0].isdigit():
                        if row.strip().startswith("---") or row.startswith("##"):
                            break
                        continue
                    level = int(row_cells[0])
                    attack[level] = parse_int(row_cells[1])
                    uses: Dict[int, int] = {}
                    for spell_level, value in enumerate(row_cells[2:8], start=1):
                        if value.strip() not in {"-", "--", "—", ""}:
                            uses[spell_level] = parse_int(value)
                    if uses:
                        spell_uses[level] = uses
            if cells and cells[0] == "Level" and all(cell.isdigit() for cell in cells[1:]):
                levels = [int(cell) for cell in cells[1:]]
                for j in range(i + 1, min(i + 6, len(lines))):
                    bonus_cells = md_cells(lines[j])
                    if bonus_cells and bonus_cells[0].lower() == "bonus":
                        for level, value in zip(levels, bonus_cells[1:]):
                            attack[level] = parse_int(value)
                        break
        return attack, spell_uses

    def _parse_class_options(self, name: str, text: str) -> Dict[str, List[str]]:
        options: Dict[str, List[str]] = {}
        if name == "Artificer":
            section = extract_any_heading_section(text, "Prototype Inventions")
            options["Inventions"] = re.findall(r"^####\s+(.+?)\s*$", section, re.M)
        elif name == "Fighter":
            section = extract_any_heading_section(text, "Fighter Style Examples")
            styles = []
            for line in section.splitlines():
                cells = md_cells(line)
                if len(cells) >= 2 and cells[0].lower() != "style" and not is_separator_row(line):
                    styles.append(cells[0])
            options["Fighter Style"] = styles
        elif name == "Bard":
            options["Silver Tongued Skill"] = ["Persuasion", "Deception"]
        elif name == "Cultist":
            blessings_section = extract_any_heading_section(text, "Available Blessings")
            options["Blessings"] = [
                clean_md(match.group(1))
                for match in re.finditer(r"^###\s+(.+?)\s*$", blessings_section, re.M)
                if not match.group(1).strip().isdigit()
            ]
            patrons = []
            for match in re.finditer(r"^###\s+\d+\.\s+(.+?)\s*$", text, re.M):
                patrons.append(clean_md(match.group(1)))
            options["Patron"] = patrons
        elif name == "Magic User":
            all_spells = []
            for level in sorted(self.spells_by_level):
                all_spells.extend([f"L{level}: {spell}" for spell in self.spells_by_level[level]])
            options["Spells"] = all_spells
        elif name == "Monk":
            section = extract_any_heading_section(text, "Technique List")
            techniques = []
            for line in section.splitlines():
                cells = md_cells(line)
                if len(cells) >= 3 and cells[0].isdigit():
                    techniques.append(cells[1])
            options["Techniques"] = techniques
        elif name == "Ranger":
            section = extract_any_heading_section(text, "Talent List")
            talents = []
            for line in section.splitlines():
                cells = md_cells(line)
                if len(cells) >= 3 and cells[0].isdigit():
                    talents.append(cells[1])
            options["Rangercraft Talents"] = talents
            options["Beast Companion"] = ["None", "Wolf", "Viper", "Owl"]
        elif name == "Rogue":
            section = extract_any_heading_section(text, "Trick List")
            tricks = []
            for line in section.splitlines():
                cells = md_cells(line)
                if len(cells) >= 2 and cells[0].lower() != "trick" and not is_separator_row(line):
                    tricks.append(cells[0])
            options["Tricks"] = tricks
        return {key: [clean_md(item) for item in values if clean_md(item)] for key, values in options.items()}

    def class_skill_summary(self, class_name: str) -> str:
        rule = self.classes.get(class_name)
        if not rule:
            return ""
        lines = []
        if rule.fixed_skills:
            lines.append("Fixed: " + ", ".join(rule.fixed_skills))
        if rule.skill_choose:
            lines.append(f"Choose {rule.skill_choose}: " + ", ".join(rule.skill_options))
        return "\n".join(lines)

    def available_spell_options_for_level(self, class_name: str, level: int) -> List[str]:
        rule = self.classes.get(class_name)
        if not rule or class_name != "Magic User":
            return []
        uses = rule.spell_uses.get(level, {})
        max_spell_level = max(uses.keys(), default=1)
        result = []
        for spell_level in range(1, max_spell_level + 1):
            for name in self.spells_by_level.get(spell_level, []):
                result.append(f"L{spell_level}: {name}")
        return result


@dataclass
class InventoryItem:
    name: str
    quantity: int = 1
    price: int = 0
    rarity: str = "Custom"
    notes: str = ""


@dataclass
class WeaponItem:
    name: str = ""
    hit: str = ""
    damage: str = ""
    properties: str = ""


@dataclass
class CharacterState:
    name: str = ""
    description: str = ""
    background: str = ""
    race: str = "Humans"
    class_name: str = "Fighter"
    level: int = 1
    attributes: Dict[str, int] = field(default_factory=lambda: {name: 10 for name in ATTRIBUTE_NAMES})
    skills: List[str] = field(default_factory=list)
    class_choices: Dict[str, Any] = field(default_factory=dict)
    unique_features: List[str] = field(default_factory=list)
    abilities_text: str = ""
    hp_current: int = 0
    hp_max: int = 0
    ac: int = 10
    luck_current: int = 0
    luck_max: int = 0
    reroll_current: int = 0
    reroll_max: int = 0
    gold: int = 0
    inventory: List[InventoryItem] = field(default_factory=list)
    weapons: List[WeaponItem] = field(default_factory=lambda: [WeaponItem() for _ in range(5)])
    notes: str = ""
    injuries: str = ""
    ddm: str = ""
    favour: bool = False
    rests: Dict[str, bool] = field(default_factory=lambda: {"3 x Will": False, "2 x Will": False, "1 x Will": False})
    overrides: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["schema"] = "lfg-character-v1"
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterState":
        data = dict(data)
        data.pop("schema", None)
        inv = data.get("inventory", [])
        data["inventory"] = [InventoryItem(**item) if isinstance(item, dict) else InventoryItem(str(item)) for item in inv]
        weapons = data.get("weapons", [])
        data["weapons"] = [WeaponItem(**item) if isinstance(item, dict) else WeaponItem(str(item)) for item in weapons]
        while len(data["weapons"]) < 5:
            data["weapons"].append(WeaponItem())
        attrs = data.get("attributes") or {}
        data["attributes"] = {name: parse_int(attrs.get(name, 10), 10) for name in ATTRIBUTE_NAMES}
        return cls(**{key: value for key, value in data.items() if key in cls.__dataclass_fields__})

    def recalc(self) -> None:
        level = max(1, min(12, parse_int(self.level, 1)))
        self.level = level
        dex_mod = score_modifier(self.attributes.get("Dexterity", 10))
        if not self.overrides.get("luck"):
            self.luck_max = starting_luck(level, self.race)
            self.luck_current = min(self.luck_current or self.luck_max, self.luck_max)
        if not self.overrides.get("reroll"):
            self.reroll_max = starting_reroll(level, self.race)
            self.reroll_current = min(self.reroll_current or self.reroll_max, self.reroll_max)
        if not self.overrides.get("ac"):
            self.ac = 10 + dex_mod + (1 if self.race.lower().startswith("halfling") else 0)


def roll_starting_gold(class_name: str) -> Tuple[int, str]:
    expr = "5d6 x 10" if class_name == "Fighter" else "3d6 x 10"
    return roll_dice_expression(expr)


def hp_formula_for_class(class_name: str) -> Tuple[int, int, int]:
    if class_name in {"Artificer", "Magic User"}:
        return 3, 3, 1
    if class_name in {"Bard", "Cultist", "Monk", "Ranger", "Rogue"}:
        return 4, 4, 2
    if class_name == "Fighter":
        return 5, 5, 3
    if class_name == "Barbarian":
        return 6, 6, 4
    return 4, 4, 2


def roll_hp(class_name: str, level: int, con_score: int) -> Tuple[int, str]:
    die, base, post_nine = hp_formula_for_class(class_name)
    con_bonus = max(0, score_modifier(con_score))
    total = 0
    details = []
    for current_level in range(1, min(level, 9) + 1):
        roll = random.randint(1, die)
        add = roll + base + con_bonus
        total += add
        details.append(f"L{current_level}: 1d{die}({roll})+{base}+Con({con_bonus})={add}")
    for current_level in range(10, level + 1):
        total += post_nine
        details.append(f"L{current_level}: +{post_nine}")
    return max(1, total), "; ".join(details)


def roll_single_level_hp(class_name: str, new_level: int, con_score: int) -> Tuple[int, str]:
    _die, _base, post_nine = hp_formula_for_class(class_name)
    if new_level >= 10:
        return post_nine, f"L{new_level}: +{post_nine}"
    return roll_hp(class_name, 1, con_score)


class ScrollFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=PARCHMENT, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="Parchment.TFrame")
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_configure(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if self.winfo_viewable():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class LFGApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Low Fantasy Gaming Character Generator")
        self.geometry("1280x860")
        self.minsize(1040, 720)
        self.rulebook = RuleBook(APP_DIR)
        self.character = CharacterState(
            race=next(iter(self.rulebook.races), "Humans"),
            class_name="Fighter" if "Fighter" in self.rulebook.classes else next(iter(self.rulebook.classes), ""),
        )
        self.character.recalc()
        self.dice_log: List[str] = []
        self.builder_choice_widgets: Dict[str, Tuple[tk.Listbox, int]] = {}
        self.builder_single_vars: Dict[str, tk.StringVar] = {}
        self.shop_rows: Dict[str, Dict[str, Any]] = {}
        self._setup_styles()
        self._build_menu()
        self._build_ui()
        self.refresh_all_views()

    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=PARCHMENT, foreground=INK, fieldbackground=PANEL)
        style.configure("TFrame", background=PARCHMENT)
        style.configure("Parchment.TFrame", background=PARCHMENT)
        style.configure("Panel.TFrame", background=PANEL, borderwidth=2, relief="ridge")
        style.configure("TLabel", background=PARCHMENT, foreground=INK)
        style.configure("Panel.TLabel", background=PANEL, foreground=INK)
        style.configure("Title.TLabel", background=PARCHMENT, foreground=BLACK, font=("Georgia", 18, "bold"))
        style.configure("Header.TLabel", background=PANEL, foreground=BLACK, font=("Georgia", 12, "bold"))
        style.configure("Warn.TLabel", background=PANEL, foreground=BLOOD)
        style.configure("TButton", background=PARCHMENT_DARK, foreground=INK, padding=5)
        style.map("TButton", background=[("active", "#cfb77e")])
        style.configure("TNotebook", background=IRON)
        style.configure("TNotebook.Tab", background=PARCHMENT_DARK, foreground=INK, padding=(12, 6))
        style.map("TNotebook.Tab", background=[("selected", PANEL)])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=INK, rowheight=24)
        style.configure("Treeview.Heading", background=PARCHMENT_DARK, foreground=INK, font=("Georgia", 10, "bold"))

    def _build_menu(self) -> None:
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="New Blank Character", command=self.new_blank_character)
        file_menu.add_command(label="Save Character JSON", command=self.save_character)
        file_menu.add_command(label="Load Character JSON", command=self.load_character)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        self.configure(menu=menu)

    def _build_ui(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.builder_tab = ScrollFrame(self.notebook)
        self.sheet_tab = ScrollFrame(self.notebook)
        self.inventory_tab = ttk.Frame(self.notebook, style="Parchment.TFrame")
        self.rules_tab = ttk.Frame(self.notebook, style="Parchment.TFrame")
        self.dice_tab = ttk.Frame(self.notebook, style="Parchment.TFrame")

        self.notebook.add(self.builder_tab, text="Builder")
        self.notebook.add(self.sheet_tab, text="Character Sheet")
        self.notebook.add(self.inventory_tab, text="Inventory & Shop")
        self.notebook.add(self.rules_tab, text="Rules Reference")
        self.notebook.add(self.dice_tab, text="Dice Log")

        self._build_builder()
        self._build_inventory_shop()
        self._build_rules_reference()
        self._build_dice_log()

    def panel(self, parent: tk.Widget, title: str, row: int, column: int, colspan: int = 1, sticky: str = "nsew") -> ttk.Frame:
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=10)
        frame.grid(row=row, column=column, columnspan=colspan, padx=8, pady=8, sticky=sticky)
        ttk.Label(frame, text=title, style="Header.TLabel").pack(anchor="w")
        ttk.Separator(frame).pack(fill="x", pady=(4, 8))
        return frame

    def _build_builder(self) -> None:
        root = self.builder_tab.inner
        for column in range(3):
            root.columnconfigure(column, weight=1)

        ttk.Label(root, text="Low Fantasy Gaming Character Builder", style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(12, 4)
        )

        identity = self.panel(root, "Identity", 1, 0)
        self.builder_name = tk.StringVar()
        self.builder_race = tk.StringVar()
        self.builder_class = tk.StringVar()
        self.builder_level = tk.IntVar(value=1)
        self.builder_gear_mode = tk.StringVar(value="shop")
        self.builder_gold = tk.IntVar(value=0)
        self._form_entry(identity, "Name", self.builder_name)
        self._combo(identity, "Race", self.builder_race, sorted(self.rulebook.races) or ["Humans"])
        self._combo(identity, "Class", self.builder_class, sorted(self.rulebook.classes) or ["Fighter"])
        self._spin(identity, "Level", self.builder_level, 1, 12)
        ttk.Label(identity, text="Description", style="Panel.TLabel").pack(anchor="w")
        self.builder_description = tk.Text(identity, height=4, width=44, bg=PANEL, fg=INK, wrap="word")
        self.builder_description.pack(fill="x", pady=(0, 8))
        ttk.Label(identity, text="Background", style="Panel.TLabel").pack(anchor="w")
        self.builder_background = tk.Text(identity, height=4, width=44, bg=PANEL, fg=INK, wrap="word")
        self.builder_background.pack(fill="x")

        attrs = self.panel(root, "Attributes", 1, 1)
        self.builder_attr_vars: Dict[str, tk.IntVar] = {}
        for name, short in ATTRIBUTES:
            var = tk.IntVar(value=10)
            self.builder_attr_vars[name] = var
            row = ttk.Frame(attrs, style="Panel.TFrame")
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"{name} ({short})", style="Panel.TLabel", width=18).pack(side="left")
            spin = tk.Spinbox(row, from_=3, to=20, textvariable=var, width=5, command=self.update_builder_choices)
            spin.pack(side="left")
            spin.bind("<KeyRelease>", lambda _event: self.after_idle(self.update_builder_choices))
        ttk.Button(attrs, text="Roll 4d6 Drop Lowest + 15", command=lambda: self.roll_builder_stats(False)).pack(fill="x", pady=(8, 2))
        ttk.Button(attrs, text="Roll 3d6 + 15", command=lambda: self.roll_builder_stats(True)).pack(fill="x", pady=2)
        ttk.Button(attrs, text="Use Alternative Array", command=self.use_alternative_array).pack(fill="x", pady=2)
        ttk.Label(attrs, text="Rolled arrays fill in order; edit freely to assign scores.", style="Panel.TLabel", wraplength=360).pack(anchor="w", pady=(8, 0))

        derived = self.panel(root, "Starting Resources", 1, 2)
        ttk.Radiobutton(derived, text="Roll gold and shop", value="shop", variable=self.builder_gear_mode).pack(anchor="w")
        ttk.Radiobutton(derived, text="Use class gear pack", value="pack", variable=self.builder_gear_mode).pack(anchor="w")
        ttk.Button(derived, text="Roll Starting Gold", command=self.roll_builder_gold).pack(fill="x", pady=(8, 2))
        ttk.Label(derived, textvariable=self.builder_gold, style="Header.TLabel").pack(anchor="w", pady=(4, 8))
        ttk.Button(derived, text="Apply / Rebuild Character", command=self.apply_builder).pack(fill="x", pady=(12, 2))
        ttk.Button(derived, text="Save JSON", command=self.save_character).pack(fill="x", pady=2)
        ttk.Button(derived, text="Load JSON", command=self.load_character).pack(fill="x", pady=2)
        self.builder_summary = ttk.Label(derived, text="", style="Panel.TLabel", wraplength=330, justify="left")
        self.builder_summary.pack(anchor="w", fill="x", pady=(8, 0))

        skills = self.panel(root, "Skills", 2, 0, colspan=1)
        self.builder_fixed_skills = ttk.Label(skills, text="", style="Panel.TLabel", wraplength=390, justify="left")
        self.builder_fixed_skills.pack(anchor="w", fill="x")
        ttk.Label(skills, text="Class skill choices", style="Panel.TLabel").pack(anchor="w", pady=(8, 2))
        self.builder_skill_list = tk.Listbox(skills, selectmode="multiple", height=10, bg=PANEL, fg=INK, exportselection=False)
        self.builder_skill_list.pack(fill="both", expand=True)
        ttk.Label(skills, text="New skill picks at levels 4 and 8", style="Panel.TLabel").pack(anchor="w", pady=(8, 2))
        self.builder_extra_skill_list = tk.Listbox(skills, selectmode="multiple", height=6, bg=PANEL, fg=INK, exportselection=False)
        self.builder_extra_skill_list.pack(fill="both", expand=True)

        choices = self.panel(root, "Class Choices", 2, 1, colspan=1)
        self.builder_choices_frame = ttk.Frame(choices, style="Panel.TFrame")
        self.builder_choices_frame.pack(fill="both", expand=True)

        ufs = self.panel(root, "Unique Features", 2, 2, colspan=1)
        self.builder_uf_label = ttk.Label(ufs, text="", style="Panel.TLabel", wraplength=360)
        self.builder_uf_label.pack(anchor="w")
        self.builder_uf_list = tk.Listbox(ufs, selectmode="multiple", height=15, bg=PANEL, fg=INK, exportselection=False)
        self.builder_uf_list.pack(fill="both", expand=True)

        self.builder_class.trace_add("write", lambda *_args: self.update_builder_choices())
        self.builder_level.trace_add("write", lambda *_args: self.update_builder_choices())

    def _form_entry(self, parent: tk.Widget, label: str, variable: tk.Variable) -> None:
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=12, style="Panel.TLabel").pack(side="left")
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)

    def _combo(self, parent: tk.Widget, label: str, variable: tk.StringVar, values: List[str]) -> None:
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=12, style="Panel.TLabel").pack(side="left")
        combo = ttk.Combobox(row, textvariable=variable, values=values, state="readonly")
        combo.pack(side="left", fill="x", expand=True)
        if values and not variable.get():
            variable.set(values[0])

    def _spin(self, parent: tk.Widget, label: str, variable: tk.IntVar, min_value: int, max_value: int) -> None:
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=12, style="Panel.TLabel").pack(side="left")
        spin = tk.Spinbox(row, from_=min_value, to=max_value, textvariable=variable, width=5, command=self.update_builder_choices)
        spin.pack(side="left")
        spin.bind("<KeyRelease>", lambda _event: self.after_idle(self.update_builder_choices))

    def roll_builder_stats(self, use_3d6: bool) -> None:
        values, detail = roll_stat_array(use_3d6)
        for (name, _short), value in zip(ATTRIBUTES, values):
            self.builder_attr_vars[name].set(value)
        self.add_dice_log(detail)
        self.update_builder_choices()

    def use_alternative_array(self) -> None:
        for (name, _short), value in zip(ATTRIBUTES, DEFAULT_ARRAY):
            self.builder_attr_vars[name].set(value)
        self.add_dice_log("Alternative array applied: " + ", ".join(map(str, DEFAULT_ARRAY)))
        self.update_builder_choices()

    def roll_builder_gold(self) -> None:
        class_name = self.builder_class.get() or self.character.class_name
        total, detail = roll_starting_gold(class_name)
        self.builder_gold.set(total)
        self.add_dice_log("Starting gold: " + detail)

    def update_builder_choices(self) -> None:
        class_name = self.builder_class.get()
        level = max(1, min(12, parse_int(self.builder_level.get(), 1)))
        rule = self.rulebook.classes.get(class_name)
        attrs = {name: parse_int(var.get(), 10) for name, var in self.builder_attr_vars.items()}
        self.builder_summary.configure(
            text=f"Luck {starting_luck(level, self.builder_race.get())}, Reroll {starting_reroll(level, self.builder_race.get())}, "
            f"UF slots {unique_feature_slots(level)}, new skill slots {new_skill_slots(level)}."
        )
        self.builder_fixed_skills.configure(text=self.rulebook.class_skill_summary(class_name))
        self.builder_skill_list.delete(0, "end")
        self.builder_extra_skill_list.delete(0, "end")
        if rule:
            for skill in rule.skill_options:
                self.builder_skill_list.insert("end", skill)
        for skill in sorted(self.rulebook.skills):
            self.builder_extra_skill_list.insert("end", skill)

        for child in self.builder_choices_frame.winfo_children():
            child.destroy()
        self.builder_choice_widgets.clear()
        self.builder_single_vars.clear()
        if rule:
            self._add_class_choice_widgets(rule, level, attrs)

        self.builder_uf_label.configure(text=f"Choose {unique_feature_slots(level)} Unique Feature(s). You may also manually note '+1 attribute instead'.")
        self.builder_uf_list.delete(0, "end")
        for feature in sorted(self.rulebook.unique_features):
            self.builder_uf_list.insert("end", feature)

    def _add_class_choice_widgets(self, rule: ClassRule, level: int, attrs: Dict[str, int]) -> None:
        def add_list(title: str, options: List[str], needed: int) -> None:
            frame = ttk.Frame(self.builder_choices_frame, style="Panel.TFrame")
            frame.pack(fill="x", pady=5)
            ttk.Label(frame, text=f"{title} - choose {needed}", style="Panel.TLabel").pack(anchor="w")
            box = tk.Listbox(frame, selectmode="multiple", height=min(8, max(3, len(options))), bg=PANEL, fg=INK, exportselection=False)
            box.pack(fill="x", expand=True)
            for item in options:
                box.insert("end", item)
            self.builder_choice_widgets[title] = (box, needed)

        def add_single(title: str, options: List[str]) -> None:
            frame = ttk.Frame(self.builder_choices_frame, style="Panel.TFrame")
            frame.pack(fill="x", pady=5)
            var = tk.StringVar(value=options[0] if options else "")
            ttk.Label(frame, text=title, style="Panel.TLabel").pack(anchor="w")
            ttk.Combobox(frame, textvariable=var, values=options, state="readonly").pack(fill="x")
            self.builder_single_vars[title] = var

        class_name = rule.name
        if class_name == "Artificer":
            count = max(0, score_modifier(attrs.get("Intelligence", 10))) + max(0, level - 1)
            add_list("Inventions", rule.options.get("Inventions", []), count)
        elif class_name == "Magic User":
            int_mod = max(0, score_modifier(attrs.get("Intelligence", 10)))
            count = 1 + int_mod * level
            add_list("Spells", self.rulebook.available_spell_options_for_level(class_name, level), count)
        elif class_name == "Cultist":
            will_mod = max(0, score_modifier(attrs.get("Willpower", 10)))
            count = will_mod + max(0, level - 1)
            add_single("Patron", rule.options.get("Patron", ["Custom Patron"]))
            add_list("Blessings", rule.options.get("Blessings", []), count)
        elif class_name == "Monk":
            will_mod = max(0, score_modifier(attrs.get("Willpower", 10)))
            add_list("Techniques", rule.options.get("Techniques", []), will_mod + max(0, level - 1))
        elif class_name == "Ranger":
            perc_mod = max(0, score_modifier(attrs.get("Perception", 10)))
            add_single("Beast Companion", rule.options.get("Beast Companion", ["None"]))
            add_list("Rangercraft Talents", rule.options.get("Rangercraft Talents", []), perc_mod + max(0, level - 1))
        elif class_name == "Rogue":
            dex_mod = max(0, score_modifier(attrs.get("Dexterity", 10)))
            add_list("Tricks", rule.options.get("Tricks", []), dex_mod + max(0, level - 1))
        elif class_name == "Fighter":
            add_single("Fighter Style", rule.options.get("Fighter Style", ["Custom Style"]))
        elif class_name == "Bard":
            add_single("Silver Tongued Skill", rule.options.get("Silver Tongued Skill", ["Persuasion", "Deception"]))

    def selected_listbox_values(self, box: tk.Listbox) -> List[str]:
        return [box.get(idx) for idx in box.curselection()]

    def apply_builder(self) -> None:
        class_name = self.builder_class.get()
        rule = self.rulebook.classes.get(class_name)
        level = max(1, min(12, parse_int(self.builder_level.get(), 1)))
        attrs = {name: max(1, parse_int(var.get(), 10)) for name, var in self.builder_attr_vars.items()}
        warnings = []
        skills: List[str] = []
        if rule:
            skills.extend(rule.fixed_skills)
            picked = self.selected_listbox_values(self.builder_skill_list)
            if len(picked) != rule.skill_choose:
                warnings.append(f"{class_name} should choose {rule.skill_choose} class skill(s); selected {len(picked)}.")
            skills.extend(picked)
        extra_picked = self.selected_listbox_values(self.builder_extra_skill_list)
        extra_slots = new_skill_slots(level)
        if len(extra_picked) != extra_slots:
            warnings.append(f"Level {level} should choose {extra_slots} extra skill(s); selected {len(extra_picked)}.")
        skills.extend(extra_picked)

        class_choices: Dict[str, Any] = {}
        for title, var in self.builder_single_vars.items():
            class_choices[title] = var.get()
        for title, (box, needed) in self.builder_choice_widgets.items():
            values = self.selected_listbox_values(box)
            class_choices[title] = values
            if needed and len(values) != needed:
                warnings.append(f"{title} should have {needed} selection(s); selected {len(values)}.")

        unique_features = self.selected_listbox_values(self.builder_uf_list)
        uf_slots = unique_feature_slots(level)
        if len(unique_features) != uf_slots:
            warnings.append(f"Level {level} should have {uf_slots} Unique Feature(s); selected {len(unique_features)}.")

        if warnings:
            proceed = messagebox.askyesno(
                "Guided validation",
                "The app found unusual or incomplete choices:\n\n" + "\n".join(warnings) + "\n\nContinue anyway?",
            )
            if not proceed:
                return

        hp, hp_detail = roll_hp(class_name, level, attrs.get("Constitution", 10))
        gold = parse_int(self.builder_gold.get(), 0)
        if gold <= 0 and self.builder_gear_mode.get() == "shop":
            gold, gold_detail = roll_starting_gold(class_name)
            self.add_dice_log("Starting gold: " + gold_detail)
        inventory: List[InventoryItem] = []
        if self.builder_gear_mode.get() == "pack":
            pack = self.rulebook.gear_packs.get(class_name, "")
            for item in [part.strip() for part in pack.split(",") if part.strip()]:
                inventory.append(InventoryItem(name=item, quantity=1, price=0, rarity="Gear Pack"))
        self.character = CharacterState(
            name=self.builder_name.get(),
            description=self.builder_description.get("1.0", "end").strip(),
            background=self.builder_background.get("1.0", "end").strip(),
            race=self.builder_race.get(),
            class_name=class_name,
            level=level,
            attributes=attrs,
            skills=sorted(set(skills)),
            class_choices=class_choices,
            unique_features=unique_features,
            hp_current=hp,
            hp_max=hp,
            gold=gold,
            inventory=inventory,
        )
        self.character.recalc()
        self.add_dice_log("HP rolled: " + hp_detail)
        self.refresh_all_views()
        self.notebook.select(self.sheet_tab)

    def new_blank_character(self) -> None:
        self.character = CharacterState(
            race=next(iter(self.rulebook.races), "Humans"),
            class_name="Fighter" if "Fighter" in self.rulebook.classes else next(iter(self.rulebook.classes), ""),
        )
        self.character.recalc()
        self.refresh_all_views()

    def save_character(self) -> None:
        self.commit_sheet_edits(silent=True)
        path = filedialog.asksaveasfilename(
            title="Save LFG character",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self.character.to_dict(), indent=2), encoding="utf-8")
            messagebox.showinfo("Saved", f"Character saved to:\n{path}")
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))

    def load_character(self) -> None:
        path = filedialog.askopenfilename(
            title="Load LFG character",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.character = CharacterState.from_dict(data)
            self.character.recalc()
            self.refresh_all_views()
            self.notebook.select(self.sheet_tab)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            messagebox.showerror("Load failed", str(exc))

    def refresh_all_views(self) -> None:
        self._sync_builder_from_character()
        self._build_sheet()
        self.populate_inventory()
        self.populate_shop()
        self.update_dice_log_text()

    def _sync_builder_from_character(self) -> None:
        ch = self.character
        self.builder_name.set(ch.name)
        self.builder_race.set(ch.race if ch.race in self.rulebook.races else next(iter(self.rulebook.races), ch.race))
        self.builder_class.set(ch.class_name if ch.class_name in self.rulebook.classes else next(iter(self.rulebook.classes), ch.class_name))
        self.builder_level.set(ch.level)
        self.builder_gold.set(ch.gold)
        for name, var in self.builder_attr_vars.items():
            var.set(ch.attributes.get(name, 10))
        self.builder_description.delete("1.0", "end")
        self.builder_description.insert("1.0", ch.description)
        self.builder_background.delete("1.0", "end")
        self.builder_background.insert("1.0", ch.background)
        self.update_builder_choices()

    def _build_sheet(self) -> None:
        root = self.sheet_tab.inner
        for child in root.winfo_children():
            child.destroy()
        for col in range(4):
            root.columnconfigure(col, weight=1)
        ch = self.character
        ttk.Label(root, text="Interactive Character Sheet", style="Title.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", padx=12, pady=12)

        top = ttk.Frame(root, style="Panel.TFrame", padding=10)
        top.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=8, pady=8)
        for col in range(4):
            top.columnconfigure(col, weight=1)
        self.sheet_vars: Dict[str, tk.Variable] = {}
        self._sheet_entry(top, "Name", "name", ch.name, 0, 0)
        self._sheet_entry(top, "Race", "race", ch.race, 0, 1)
        self._sheet_entry(top, "Class", "class_name", ch.class_name, 0, 2)
        self._sheet_entry(top, "Level", "level", str(ch.level), 0, 3)
        ttk.Label(top, text="Description", style="Panel.TLabel").grid(row=2, column=0, sticky="w")
        self.sheet_description = tk.Text(top, height=4, bg=PANEL, fg=INK, wrap="word")
        self.sheet_description.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=(0, 6))
        self.sheet_description.insert("1.0", ch.description)
        ttk.Label(top, text="Background", style="Panel.TLabel").grid(row=2, column=2, sticky="w")
        self.sheet_background = tk.Text(top, height=4, bg=PANEL, fg=INK, wrap="word")
        self.sheet_background.grid(row=3, column=2, columnspan=2, sticky="nsew")
        self.sheet_background.insert("1.0", ch.background)

        attr_panel = self.panel(root, "Attributes", 2, 0, colspan=2)
        table = ttk.Frame(attr_panel, style="Panel.TFrame")
        table.pack(fill="x")
        for col, label in enumerate(["Attribute", "Score", "Mod", "GS", "TF"]):
            ttk.Label(table, text=label, style="Header.TLabel", width=14).grid(row=0, column=col, sticky="ew", padx=2, pady=2)
        self.sheet_attr_vars: Dict[str, tk.IntVar] = {}
        for row, (name, _short) in enumerate(ATTRIBUTES, start=1):
            score = ch.attributes.get(name, 10)
            var = tk.IntVar(value=score)
            self.sheet_attr_vars[name] = var
            ttk.Label(table, text=name.upper(), style="Panel.TLabel").grid(row=row, column=0, sticky="w", padx=2, pady=2)
            tk.Spinbox(table, from_=1, to=30, textvariable=var, width=6).grid(row=row, column=1, sticky="w", padx=2, pady=2)
            ttk.Label(table, text=f"{score_modifier(score):+d}", style="Panel.TLabel").grid(row=row, column=2, sticky="w")
            ttk.Label(table, text=str(great_success(score)), style="Panel.TLabel").grid(row=row, column=3, sticky="w")
            ttk.Label(table, text=str(terrible_failure(score)), style="Panel.TLabel").grid(row=row, column=4, sticky="w")

        stats = self.panel(root, "Core Stats", 2, 2)
        for key, label, value in [
            ("ac", "AC", ch.ac),
            ("hp_current", "HP Current", ch.hp_current),
            ("hp_max", "HP Max", ch.hp_max),
            ("luck_current", "Luck Current", ch.luck_current),
            ("luck_max", "Luck Max", ch.luck_max),
            ("reroll_current", "Reroll Current", ch.reroll_current),
            ("reroll_max", "Reroll Max", ch.reroll_max),
            ("gold", "Gold", ch.gold),
        ]:
            self._sheet_entry(stats, label, key, str(value), len(self.sheet_vars), 0, packed=True)
        ttk.Label(stats, text="Attack bonus: " + str(self.rulebook.classes.get(ch.class_name, ClassRule("", "", "")).attack_bonus.get(ch.level, "?")), style="Panel.TLabel").pack(anchor="w", pady=(6, 0))

        rest_panel = self.panel(root, "Rests / Effects", 2, 3)
        self.rest_vars: Dict[str, tk.BooleanVar] = {}
        for key in ["3 x Will", "2 x Will", "1 x Will"]:
            var = tk.BooleanVar(value=ch.rests.get(key, False))
            self.rest_vars[key] = var
            ttk.Checkbutton(rest_panel, text=key, variable=var).pack(anchor="w")
        self.sheet_favour = tk.BooleanVar(value=ch.favour)
        ttk.Checkbutton(rest_panel, text="Favour", variable=self.sheet_favour).pack(anchor="w", pady=(8, 0))

        weapons = self.panel(root, "Weapons", 3, 0, colspan=4)
        weapon_grid = ttk.Frame(weapons, style="Panel.TFrame")
        weapon_grid.pack(fill="x")
        self.weapon_vars: List[Dict[str, tk.StringVar]] = []
        headers = ["Name", "Hit", "Damage", "Properties"]
        for col, header in enumerate(headers):
            ttk.Label(weapon_grid, text=header, style="Header.TLabel").grid(row=0, column=col, sticky="ew", padx=2, pady=2)
            weapon_grid.columnconfigure(col, weight=2 if col in {0, 3} else 1)
        for row in range(5):
            weapon = ch.weapons[row] if row < len(ch.weapons) else WeaponItem()
            row_vars = {}
            for col, key in enumerate(["name", "hit", "damage", "properties"]):
                var = tk.StringVar(value=getattr(weapon, key))
                row_vars[key] = var
                ttk.Entry(weapon_grid, textvariable=var).grid(row=row + 1, column=col, sticky="ew", padx=2, pady=2)
            self.weapon_vars.append(row_vars)

        abilities = self.panel(root, "Class Abilities & Skills", 4, 0, colspan=2)
        self.sheet_abilities = tk.Text(abilities, height=14, bg=PANEL, fg=INK, wrap="word")
        self.sheet_abilities.pack(fill="both", expand=True)
        if ch.abilities_text:
            abilities_text = ch.abilities_text
        else:
            choices_text = []
            choices_text.append("Skills: " + ", ".join(ch.skills))
            for key, value in ch.class_choices.items():
                if isinstance(value, list):
                    choices_text.append(f"{key}: " + ", ".join(value))
                else:
                    choices_text.append(f"{key}: {value}")
            choices_text.append("Unique Features: " + ", ".join(ch.unique_features))
            abilities_text = "\n".join(choices_text)
        self.sheet_abilities.insert("1.0", abilities_text)

        equip = self.panel(root, "Equipment", 4, 2)
        inventory_text = "\n".join(f"{item.quantity} x {item.name} ({item.rarity}) {item.notes}".strip() for item in ch.inventory)
        self.sheet_equipment = tk.Text(equip, height=14, bg=PANEL, fg=INK, wrap="word")
        self.sheet_equipment.pack(fill="both", expand=True)
        self.sheet_equipment.insert("1.0", inventory_text)
        ttk.Label(equip, text="Inventory edits are managed in Inventory & Shop.", style="Panel.TLabel").pack(anchor="w")

        notes = self.panel(root, "Notes / Injuries / DDM", 4, 3)
        ttk.Label(notes, text="Notes", style="Panel.TLabel").pack(anchor="w")
        self.sheet_notes = tk.Text(notes, height=6, bg=PANEL, fg=INK, wrap="word")
        self.sheet_notes.pack(fill="both", expand=True)
        self.sheet_notes.insert("1.0", ch.notes)
        ttk.Label(notes, text="Injuries & Effects", style="Panel.TLabel").pack(anchor="w")
        self.sheet_injuries = tk.Text(notes, height=5, bg=PANEL, fg=INK, wrap="word")
        self.sheet_injuries.pack(fill="both", expand=True)
        self.sheet_injuries.insert("1.0", ch.injuries)
        ttk.Label(notes, text="DDM", style="Panel.TLabel").pack(anchor="w")
        self.sheet_ddm = tk.Text(notes, height=4, bg=PANEL, fg=INK, wrap="word")
        self.sheet_ddm.pack(fill="both", expand=True)
        self.sheet_ddm.insert("1.0", ch.ddm)

        buttons = ttk.Frame(root, style="Parchment.TFrame")
        buttons.grid(row=5, column=0, columnspan=4, sticky="ew", padx=8, pady=10)
        ttk.Button(buttons, text="Commit Sheet Edits", command=self.commit_sheet_edits).pack(side="left", padx=4)
        ttk.Button(buttons, text="Level Up +1", command=self.level_up).pack(side="left", padx=4)
        ttk.Button(buttons, text="Recalculate Derived Stats", command=self.recalculate_character).pack(side="left", padx=4)
        ttk.Button(buttons, text="Open Shop", command=lambda: self.notebook.select(self.inventory_tab)).pack(side="left", padx=4)

    def _sheet_entry(
        self,
        parent: tk.Widget,
        label: str,
        key: str,
        value: str,
        row: int,
        col: int,
        packed: bool = False,
    ) -> None:
        var = tk.StringVar(value=str(value))
        self.sheet_vars[key] = var
        if packed:
            frame = ttk.Frame(parent, style="Panel.TFrame")
            frame.pack(fill="x", pady=2)
            ttk.Label(frame, text=label, width=16, style="Panel.TLabel").pack(side="left")
            ttk.Entry(frame, textvariable=var, width=12).pack(side="left", fill="x", expand=True)
            return
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.grid(row=row, column=col, sticky="ew", padx=4, pady=2)
        ttk.Label(frame, text=label, style="Panel.TLabel").pack(anchor="w")
        ttk.Entry(frame, textvariable=var).pack(fill="x")

    def commit_sheet_edits(self, silent: bool = False) -> None:
        ch = self.character
        if not hasattr(self, "sheet_vars"):
            return
        ch.name = self.sheet_vars.get("name", tk.StringVar(value=ch.name)).get()
        ch.race = self.sheet_vars.get("race", tk.StringVar(value=ch.race)).get()
        ch.class_name = normalize_class_name(self.sheet_vars.get("class_name", tk.StringVar(value=ch.class_name)).get())
        ch.level = max(1, min(12, parse_int(self.sheet_vars.get("level", tk.StringVar(value=ch.level)).get(), ch.level)))
        ch.description = self.sheet_description.get("1.0", "end").strip()
        ch.background = self.sheet_background.get("1.0", "end").strip()
        for name, var in self.sheet_attr_vars.items():
            ch.attributes[name] = parse_int(var.get(), ch.attributes.get(name, 10))
        for key in ["ac", "hp_current", "hp_max", "luck_current", "luck_max", "reroll_current", "reroll_max", "gold"]:
            if key in self.sheet_vars:
                setattr(ch, key, parse_int(self.sheet_vars[key].get(), getattr(ch, key)))
        ch.weapons = [WeaponItem(**{key: var.get() for key, var in row_vars.items()}) for row_vars in self.weapon_vars]
        ch.abilities_text = self.sheet_abilities.get("1.0", "end").strip()
        ch.notes = self.sheet_notes.get("1.0", "end").strip()
        ch.injuries = self.sheet_injuries.get("1.0", "end").strip()
        ch.ddm = self.sheet_ddm.get("1.0", "end").strip()
        ch.favour = bool(self.sheet_favour.get())
        ch.rests = {key: bool(var.get()) for key, var in self.rest_vars.items()}
        if not silent:
            self.refresh_all_views()
            messagebox.showinfo("Character updated", "Sheet edits committed.")

    def level_up(self) -> None:
        self.commit_sheet_edits(silent=True)
        if self.character.level >= 12:
            messagebox.showinfo("Level cap", "The loaded class tables go to level 12.")
            return
        old_level = self.character.level
        self.character.level += 1
        hp_gain, detail = roll_single_level_hp(
            self.character.class_name,
            self.character.level,
            self.character.attributes.get("Constitution", 10),
        )
        self.character.hp_max += hp_gain
        self.character.hp_current += hp_gain
        self.character.recalc()
        self.add_dice_log(f"Level up {old_level}->{self.character.level}; HP gain {hp_gain}. {detail}")
        messagebox.showinfo(
            "Level up",
            "Level increased by 1. Check Builder for new skill, Unique Feature, spell, blessing, talent, trick, or invention choices.",
        )
        self.refresh_all_views()

    def recalculate_character(self) -> None:
        self.commit_sheet_edits(silent=True)
        self.character.overrides = {}
        self.character.recalc()
        self.refresh_all_views()

    def _build_inventory_shop(self) -> None:
        root = self.inventory_tab
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(1, weight=1)
        ttk.Label(root, text="Inventory & Shop", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=12)

        inv_frame = ttk.Frame(root, style="Panel.TFrame", padding=10)
        inv_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        inv_frame.rowconfigure(1, weight=1)
        ttk.Label(inv_frame, text="Inventory", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        self.inventory_tree = ttk.Treeview(inv_frame, columns=("qty", "rarity", "price", "notes"), show="tree headings")
        self.inventory_tree.heading("#0", text="Item")
        for col, label in [("qty", "Qty"), ("rarity", "Rarity"), ("price", "Price"), ("notes", "Notes")]:
            self.inventory_tree.heading(col, text=label)
        self.inventory_tree.grid(row=1, column=0, sticky="nsew", pady=8)
        inv_buttons = ttk.Frame(inv_frame, style="Panel.TFrame")
        inv_buttons.grid(row=2, column=0, sticky="ew")
        ttk.Button(inv_buttons, text="Add Custom Item", command=self.add_custom_item).pack(side="left", padx=2)
        ttk.Button(inv_buttons, text="Remove Selected", command=self.remove_inventory_item).pack(side="left", padx=2)
        ttk.Button(inv_buttons, text="Sell Selected", command=self.sell_inventory_item).pack(side="left", padx=2)

        shop_frame = ttk.Frame(root, style="Panel.TFrame", padding=10)
        shop_frame.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)
        shop_frame.columnconfigure(0, weight=1)
        shop_frame.rowconfigure(2, weight=1)
        ttk.Label(shop_frame, text="Shop", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        controls = ttk.Frame(shop_frame, style="Panel.TFrame")
        controls.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.shop_filter = tk.StringVar(value="All")
        self.shop_search = tk.StringVar()
        ttk.Label(controls, text="Rarity", style="Panel.TLabel").pack(side="left")
        ttk.Combobox(controls, textvariable=self.shop_filter, values=["All", "Common", "Uncommon", "Rare"], state="readonly", width=12).pack(side="left", padx=4)
        ttk.Label(controls, text="Search", style="Panel.TLabel").pack(side="left", padx=(12, 2))
        ttk.Entry(controls, textvariable=self.shop_search, width=24).pack(side="left")
        ttk.Button(controls, text="Refresh", command=self.populate_shop).pack(side="left", padx=4)
        ttk.Button(controls, text="Roll Stock", command=self.roll_shop_stock).pack(side="left", padx=4)
        self.gold_label = ttk.Label(controls, text="", style="Header.TLabel")
        self.gold_label.pack(side="right", padx=6)

        self.shop_tree = ttk.Treeview(shop_frame, columns=("rarity", "qty", "price", "rolled", "stock", "wait"), show="tree headings")
        self.shop_tree.heading("#0", text="Item")
        for col, label in [("rarity", "Rarity"), ("qty", "Qty"), ("price", "Price"), ("rolled", "Rolled"), ("stock", "Stock"), ("wait", "Wait")]:
            self.shop_tree.heading(col, text=label)
        self.shop_tree.grid(row=2, column=0, sticky="nsew")
        buttons = ttk.Frame(shop_frame, style="Panel.TFrame")
        buttons.grid(row=3, column=0, sticky="ew", pady=8)
        ttk.Button(buttons, text="Roll Selected Price", command=self.roll_selected_shop_price).pack(side="left", padx=2)
        ttk.Button(buttons, text="Buy Selected", command=self.buy_selected_shop_item).pack(side="left", padx=2)
        ttk.Button(buttons, text="Add Manual Shop Item", command=self.add_custom_item).pack(side="left", padx=2)
        self.shop_filter.trace_add("write", lambda *_args: self.populate_shop())
        self.shop_search.trace_add("write", lambda *_args: self.populate_shop())

    def populate_inventory(self) -> None:
        if not hasattr(self, "inventory_tree"):
            return
        for item_id in self.inventory_tree.get_children():
            self.inventory_tree.delete(item_id)
        for idx, item in enumerate(self.character.inventory):
            self.inventory_tree.insert("", "end", iid=str(idx), text=item.name, values=(item.quantity, item.rarity, item.price, item.notes))
        if hasattr(self, "gold_label"):
            self.gold_label.configure(text=f"Gold: {self.character.gold}")

    def populate_shop(self) -> None:
        if not hasattr(self, "shop_tree"):
            return
        rarity_filter = self.shop_filter.get() if hasattr(self, "shop_filter") else "All"
        search = self.shop_search.get().lower() if hasattr(self, "shop_search") else ""
        for item_id in self.shop_tree.get_children():
            self.shop_tree.delete(item_id)
        for idx, item in enumerate(self.rulebook.gear):
            if rarity_filter != "All" and item.rarity != rarity_filter:
                continue
            if search and search not in item.name.lower() and search not in item.description.lower():
                continue
            key = str(idx)
            state = self.shop_rows.setdefault(key, {"rolled": "", "stock": "Available" if item.rarity == "Common" else "", "wait": ""})
            self.shop_tree.insert(
                "",
                "end",
                iid=key,
                text=item.name,
                values=(item.rarity, item.quantity, item.price_expr, state.get("rolled", ""), state.get("stock", ""), state.get("wait", "")),
            )
        if hasattr(self, "gold_label"):
            self.gold_label.configure(text=f"Gold: {self.character.gold}")

    def roll_shop_stock(self) -> None:
        for idx, item in enumerate(self.rulebook.gear):
            key = str(idx)
            state = self.shop_rows.setdefault(key, {})
            if item.rarity == "Common":
                state["stock"] = "Available"
                state["wait"] = "Available"
            elif item.rarity == "Uncommon":
                stock, stock_detail = roll_dice_expression("2d4")
                wait, wait_detail = roll_dice_expression("1d6")
                state["stock"] = str(stock)
                state["wait"] = f"{wait} days"
                self.add_dice_log(f"Uncommon stock {item.name}: {stock_detail}; wait {wait_detail} days")
            elif item.rarity == "Rare":
                stock, stock_detail = roll_dice_expression("1d3")
                wait, wait_detail = roll_dice_expression("1d6")
                state["stock"] = str(stock)
                state["wait"] = f"{wait} weeks"
                self.add_dice_log(f"Rare stock {item.name}: {stock_detail}; wait {wait_detail} weeks")
            else:
                state["stock"] = "1"
                state["wait"] = ""
        self.populate_shop()

    def selected_shop_item(self) -> Optional[Tuple[str, GearItem, Dict[str, Any]]]:
        selected = self.shop_tree.selection()
        if not selected:
            messagebox.showinfo("Shop", "Select an item first.")
            return None
        key = selected[0]
        idx = int(key)
        item = self.rulebook.gear[idx]
        state = self.shop_rows.setdefault(key, {})
        return key, item, state

    def roll_selected_shop_price(self) -> None:
        selected = self.selected_shop_item()
        if not selected:
            return
        key, item, state = selected
        try:
            price, detail = roll_dice_expression(item.price_expr)
        except ValueError as exc:
            messagebox.showerror("Price roll failed", str(exc))
            return
        state["rolled"] = price
        self.add_dice_log(f"Shop price {item.name}: {detail}")
        self.populate_shop()
        self.shop_tree.selection_set(key)

    def buy_selected_shop_item(self) -> None:
        selected = self.selected_shop_item()
        if not selected:
            return
        _key, item, state = selected
        if not state.get("rolled"):
            try:
                price, detail = roll_dice_expression(item.price_expr)
                state["rolled"] = price
                self.add_dice_log(f"Shop price {item.name}: {detail}")
            except ValueError:
                price = simpledialog.askinteger("Manual price", f"Enter price for {item.name}", minvalue=0)
                if price is None:
                    return
                state["rolled"] = price
        price = parse_int(state.get("rolled"), 0)
        qty = simpledialog.askinteger("Buy quantity", f"How many {item.name}?", minvalue=1, initialvalue=1)
        if qty is None:
            return
        total = price * qty
        if total > self.character.gold:
            proceed = messagebox.askyesno("Not enough gold", f"This costs {total} gp, but the character has {self.character.gold} gp. Buy anyway?")
            if not proceed:
                return
        self.character.gold -= total
        self.character.inventory.append(InventoryItem(item.name, qty, total, item.rarity, item.description))
        self.add_dice_log(f"Bought {qty} x {item.name} for {total} gp.")
        self.populate_inventory()
        self.populate_shop()

    def add_custom_item(self) -> None:
        name = simpledialog.askstring("Custom item", "Item name:")
        if not name:
            return
        qty = simpledialog.askinteger("Custom item", "Quantity:", minvalue=1, initialvalue=1)
        if qty is None:
            return
        price = simpledialog.askinteger("Custom item", "Total value / price:", minvalue=0, initialvalue=0)
        if price is None:
            return
        notes = simpledialog.askstring("Custom item", "Notes:", initialvalue="") or ""
        self.character.inventory.append(InventoryItem(name=name, quantity=qty, price=price, rarity="Custom", notes=notes))
        self.populate_inventory()
        self.refresh_all_views()

    def remove_inventory_item(self) -> None:
        selected = self.inventory_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if 0 <= idx < len(self.character.inventory):
            del self.character.inventory[idx]
        self.populate_inventory()
        self.refresh_all_views()

    def sell_inventory_item(self) -> None:
        selected = self.inventory_tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        if not (0 <= idx < len(self.character.inventory)):
            return
        item = self.character.inventory[idx]
        price = simpledialog.askinteger("Sell item", f"Sale price for {item.name}:", minvalue=0, initialvalue=max(0, item.price))
        if price is None:
            return
        self.character.gold += price
        del self.character.inventory[idx]
        self.add_dice_log(f"Sold {item.name} for {price} gp.")
        self.populate_inventory()
        self.populate_shop()
        self.refresh_all_views()

    def _build_rules_reference(self) -> None:
        root = self.rules_tab
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)
        ttk.Label(root, text="Rules Reference", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=12)
        self.rules_list = tk.Listbox(root, bg=PANEL, fg=INK, width=32, exportselection=False)
        self.rules_list.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        self.rules_text = tk.Text(root, bg=PANEL, fg=INK, wrap="word")
        self.rules_text.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)
        categories = [
            "Character Creation",
            "Races",
            "Skills",
            "Gear",
            "Spells",
            "Unique Features",
        ] + [f"Class: {name}" for name in sorted(self.rulebook.classes)]
        for category in categories:
            self.rules_list.insert("end", category)
        self.rules_list.bind("<<ListboxSelect>>", lambda _event: self.show_rule_reference())
        if categories:
            self.rules_list.selection_set(0)
            self.show_rule_reference()

    def show_rule_reference(self) -> None:
        selected = self.rules_list.curselection()
        if not selected:
            return
        category = self.rules_list.get(selected[0])
        text = ""
        if category == "Character Creation":
            text = self.rulebook.texts.get("character creating.md", "")
        elif category == "Races":
            text = self.rulebook.texts.get("races.md", "")
        elif category == "Skills":
            text = self.rulebook.texts.get("skills.md", "")
        elif category == "Gear":
            text = self.rulebook.texts.get("gear.md", "")
        elif category == "Spells":
            text = self.rulebook.texts.get("spells.md", "")
        elif category == "Unique Features":
            text = self.rulebook.texts.get("unique features.md", "")
        elif category.startswith("Class: "):
            class_name = category.split(": ", 1)[1]
            text = self.rulebook.classes.get(class_name, ClassRule("", "", "")).text
        self.rules_text.delete("1.0", "end")
        self.rules_text.insert("1.0", text or "No rules text loaded.")

    def _build_dice_log(self) -> None:
        root = self.dice_tab
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)
        ttk.Label(root, text="Dice Log", style="Title.TLabel").grid(row=0, column=0, sticky="w", padx=12, pady=12)
        controls = ttk.Frame(root, style="Panel.TFrame", padding=8)
        controls.grid(row=1, column=0, sticky="ew", padx=8)
        self.dice_expr = tk.StringVar(value="1d20")
        ttk.Label(controls, text="Formula", style="Panel.TLabel").pack(side="left")
        ttk.Entry(controls, textvariable=self.dice_expr, width=18).pack(side="left", padx=4)
        ttk.Button(controls, text="Roll", command=self.roll_custom_dice).pack(side="left", padx=2)
        for formula in ["1d20", "1d6", "1d100", "3d6", "4d6"]:
            ttk.Button(controls, text=formula, command=lambda f=formula: self.quick_roll(f)).pack(side="left", padx=2)
        self.dice_text = tk.Text(root, bg=PANEL, fg=INK, wrap="word")
        self.dice_text.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)

    def quick_roll(self, formula: str) -> None:
        self.dice_expr.set(formula)
        self.roll_custom_dice()

    def roll_custom_dice(self) -> None:
        try:
            _total, detail = roll_dice_expression(self.dice_expr.get())
            self.add_dice_log(detail)
        except ValueError as exc:
            messagebox.showerror("Dice roll failed", str(exc))

    def add_dice_log(self, line: str) -> None:
        self.dice_log.append(line)
        self.update_dice_log_text()

    def update_dice_log_text(self) -> None:
        if not hasattr(self, "dice_text"):
            return
        self.dice_text.delete("1.0", "end")
        self.dice_text.insert("1.0", "\n".join(self.dice_log[-300:]))
        self.dice_text.see("end")


def run_self_tests() -> None:
    random.seed(7)
    rules = RuleBook(APP_DIR)
    assert rules.races, "races did not load"
    assert "Fighter" in rules.classes, "fighter class missing"
    assert rules.skills.get("Athletics"), "skills did not parse"
    assert rules.gear, "gear did not parse"
    assert rules.spells_by_level.get(1), "spell tables did not parse"
    assert rules.unique_features, "unique features did not parse"
    assert score_modifier(16) == 2
    assert great_success(14) == 7
    assert terrible_failure(10) == 16
    total, _detail = roll_dice_expression("3d6 x 10")
    assert 30 <= total <= 180
    ch = CharacterState(name="Test", class_name="Fighter", race="Humans", level=3)
    ch.attributes["Dexterity"] = 14
    ch.recalc()
    assert ch.luck_max == 12
    assert ch.reroll_max == 4
    loaded = CharacterState.from_dict(ch.to_dict())
    assert loaded.name == "Test"
    assert loaded.attributes["Dexterity"] == 14
    print("Self-test passed.")


def main() -> None:
    if "--self-test" in sys.argv:
        run_self_tests()
        return
    app = LFGApp()
    app.mainloop()


if __name__ == "__main__":
    main()
