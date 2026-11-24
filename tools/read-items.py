#! /usr/bin/env python3
# %%
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, TypedDict
from xml.etree.ElementTree import Element

import numpy as np
import pandas as pd

ENCODING = "utf-8"

ARMOR_TYPES = [
    "HandArmor",
    "BodyArmor",
    "HeadArmor",
    "headArmor",
    "LegArmor",
    "HorseHarness",
    "Cape",
    "Shield",
]
BASE_MODULES = ["Native", "SandBoxCore", "Sandbox", "StoryMode"]


class ItemMainAttrib(TypedDict):
    id: str
    name: str
    type: str
    subtype: Optional[str]
    item_category: Optional[str]  # sub type only for horses
    culture: str
    weight: float
    appearance: float
    difficulty: float


class ArmorAttrib(TypedDict):
    head_armor: float
    body_armor: float
    leg_armor: float
    arm_armor: float
    covers_body: bool
    modifier_group: str
    material_type: str


class HorseAttrib(TypedDict):
    monster: str
    maneuver: float
    speed: float
    charge_damage: float
    body_length: float
    is_mountable: bool
    extra_health: float
    modifier_group: str


class WeaponAttrib(TypedDict):
    weapon_class: str
    wepon_balance: Optional[float]
    missile_speed: Optional[float]
    weapon_armor: Optional[float]
    thrust_speed: float
    thrust_damage: Optional[float]
    thrust_damage_type: Optional[str]
    swing_damage: Optional[float]
    swing_damage_type: Optional[str]
    speed_rating: float
    physics_material: str
    item_usage: str
    weapon_length: float
    hit_points: float
    accuracy: Optional[float]


class FlagAttrib(TypedDict):
    civilian: bool


class NullDict(TypedDict):
    pass


def float_nullable(x: str | None) -> float | None:
    """
    float(None) ができないので作った.
    """
    if x is None:
        return None
    else:
        return float(x)


def read_itemcompo_armor(elm: Optional[Element]) -> ArmorAttrib | NullDict:
    if elm is None:
        return {}

    attribs = {
        "head_armor": float(elm.attrib.get("head_armor", 0)),
        "body_armor": float(elm.attrib.get("body_armor", 0)),
        "arm_armor": float(elm.attrib.get("arm_armor", 0)),
        "leg_armor": float(elm.attrib.get("leg_armor", 0)),
        "covers_body": elm.attrib.get("covers_body", "false") == "true",
        "modifier_group": elm.attrib.get("modifier_group", ""),
        "material_type": elm.attrib["material_type"],
    }
    return attribs


def read_itemcompo_horse(elm: Optional[Element]) -> HorseAttrib | NullDict:
    if elm is None:
        return {}
    attribs = {
        "monster": elm.attrib["monster"],
        "maneuver": float(elm.attrib["maneuver"]),
        "speed": float(elm.attrib["speed"]),
        "charge_damage": float(elm.attrib["charge_damage"]),
        "body_length": float(elm.attrib["body_length"]),
        "is_mountable": elm.attrib.get("is_mountable", "false") == "true",
        "extra_health": float(elm.attrib.get("extra_health", 0)),
        "modifier_group": elm.attrib.get("modifier_group", ""),
    }
    return attribs


def read_itemcompo_weapon(elm: Optional[Element]):
    if elm is None:
        return {}
    attribs = {
        "weapon_class": elm.attrib["weapon_class"],
        "weapon_balance": float_nullable(elm.attrib.get("weapon_balance", None)),
        "missile_speed": float_nullable(elm.attrib.get("missile_speed", None)),
        "weapon_armor": float_nullable(elm.attrib.get("body_armor", None)),
        "thrust_speed": float_nullable(elm.attrib.get("thrust_speed", None)),
        "thrust_damage": float_nullable(elm.attrib.get("thrust_damage", None)),
        "thrust_damage_type": elm.attrib.get("thrust_damage_type", None),
        "swing_speed": float_nullable(elm.attrib.get("swing_speed", None)),
        "swing_damage": float_nullable(elm.attrib.get("swing_damage", None)),
        "swing_damage_type": elm.attrib.get("swing_damage_type", None),
        "speed_rating": float(elm.attrib["speed_rating"]),
        "weapon_length": float(elm.attrib["weapon_length"]),
        "physics_material": elm.attrib["physics_material"],
        "item_usage": elm.attrib["item_usage"],
        "hit_points": float_nullable(elm.attrib.get("hit_points", None)),
        "modifier_group": elm.attrib.get(
            "modifier_group", ""
        ),  # これがnullableって本当か??
    }
    return attribs


def read_flags(elm: Optional[Element]) -> FlagAttrib:
    if elm is None:
        return {"civilian": False}
    return {"civilian": elm.attrib.get("Civilian", "none") == "true"}


def read_mainattrib(elm: Element) -> ItemMainAttrib:
    attribs = {
        "id": elm.attrib["id"],
        "name": elm.attrib["name"],
        "type": elm.attrib["Type"],
        "subtype": elm.attrib.get("subtype", None),
        "item_category": elm.attrib.get("item_category", None),
        "culture": elm.attrib.get(
            "culture", ""
        ),  # スキーマとか考えて作ってるのか怪しい
        "weight": float(elm.attrib["weight"]),
        "appearance": float(elm.attrib.get("appearance", 0)),
        "difficulty": float(elm.attrib.get("difficulty", 0)),
    }
    return attribs


def read_mainattrib_handy(elm: Element):
    attribs = {"item_holsters": elm.attrib.get("item_holsters", None)}
    return attribs


def read_item(elm: Element) -> dict:
    attribs = read_mainattrib(elm)
    armors = elm.findall("ItemComponent/Armor")
    if len(armors) == 0:
        armor = None
    elif len(armors) > 1:
        warnings.warn(f"{len(armors)} Armor tags found!")
        armor = armors[0]
    else:
        armor = armors[0]
    attribs_armor = read_itemcompo_armor(armor)
    del armor, armors
    horses = elm.findall("ItemComponent/Horse")
    if len(horses) == 0:
        horse = None
    elif len(horses) > 1:
        warnings.warn(f"{len(horses)} Horse tags found!")
        horse = horses[0]
    else:
        horse = horses[0]
    attribs_horse = read_itemcompo_horse(horse)
    del horse, horses
    weapons = elm.findall("ItemComponent/Weapon")
    if len(weapons) == 0:
        weapon = None
    elif len(weapons) > 1:
        warnings.warn(f"{len(weapons)} Weapon tags found!")
        weapon = weapons[0]
    else:
        weapon = weapons[0]
    attribs_weapon = read_itemcompo_weapon(weapon)
    del weapon, weapons
    flags = elm.find("Flags")
    attribs_civ = read_flags(flags)
    return attribs | attribs_armor | attribs_horse | attribs_weapon | attribs_civ


def read_items(elements: List[Element]) -> pd.DataFrame:
    def _read(element: Element) -> dict:
        print(f"""reading {element.attrib["id"]}""")
        return read_item(element)

    return pd.DataFrame([_read(elm) for elm in elements])


def read_module(dp_module: Path) -> pd.DataFrame:
    dfs = []
    dp_moduledata = dp_module.joinpath("ModuleData")
    for fp in dp_moduledata.rglob("*.xml"):
        if fp.relative_to(dp_moduledata).parts[0] == "Languages":
            continue
        print(f"reading {fp}")
        xml = ET.parse(fp).getroot()
        elms = xml.findall("Item")
        if len(elms) > 0 and xml.tag == "Items":
            df_items = read_items(elms).assign(file=fp.relative_to(dp_moduledata))
            dfs += [df_items]
        else:
            print("No Item entry found")

    if len(dfs) > 0:
        return pd.concat(dfs).assign(module=dp_module.name)
    else:
        return pd.DataFrame()


def tidy(data: pd.DataFrame) -> pd.DataFrame:
    data = data.assign(
        localization_id=lambda d: d["name"].str.extract(r"^\{=(.+?)\}"),
        name=lambda d: d["name"].str.replace(r"^\{=(.+?)\}(.+?)$", r"\2", regex=True),
        type=lambda d: np.where(d["type"] == "headArmor", "HeadArmor", d["type"]),
        culture=lambda d: d["culture"].str.replace(r"^Culture\.", "", regex=True),
    )
    return data


dir_vanilla_modules = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord\Modules"
)
dir_mo_modules = Path(
    r"C:\Users\ks\AppData\Local\ModOrganizer\Mount & Blade II Bannerlord\mods"
)

aho = ET.parse(
    Path(
        r"C:\Program Files (x86)\Steam\steamapps\common\Mount & Blade II Bannerlord\Modules\SandBoxCore\ModuleData\items\weapons.xml"
    )
)

# HOrseHarness
# Thrown
# Banner
# Bow, Crossbow

ahoroot = aho.getroot()
ahoroot.tag
aho.findall("//Items/Item")
ahoroot.findall("Item")

df_vanilla = tidy(
    pd.concat(
        [
            read_module(dir_vanilla_modules.joinpath("Native")),
            read_module(dir_vanilla_modules.joinpath("SandBoxCore")),
            read_module(dir_vanilla_modules.joinpath("Sandbox")),
            read_module(dir_vanilla_modules.joinpath("StoryMode")),
        ]
    )
)
df_vanilla.to_csv("")

df_rbm = tidy(read_module(dir_mo_modules.joinpath(r"Realistic Battle Mod/RBM")))

# %%
