import base64
import json
import math
import os
import settings
import subprocess
import tempfile
import typing
import yaml
import zipfile

from dataclasses import dataclass
from functools import reduce

from BaseClasses import Item, ItemClassification, Location, MultiWorld, Region
from Options import OptionDict, OptionSet, PerGameCommonOptions
from rule_builder.rules import And, False_, Has, HasFromListUnique, Rule, True_
from settings import get_settings
from typing import (Any, Dict)
from worlds.AutoWorld import World
from worlds.Files import APAutoPatchInterface
from worlds.generic.Rules import add_item_rule, forbid_items_for_player

from . import constants
from .client import KrystalClient
from .data.items import ITEMS
from .data.locations import LOCATIONS

class KrystalSettings(settings.Group):
    class PokemonCrystalRomFile(settings.UserFilePath):
        """File path of your Pokemon Crystal Version 1.1 ROM"""
        description = "Pokemon Crystal ROM File"
        copy_to = "Pokemon - Crystal Version (UE) [C][!].gbc"
    
    class PokemonCrystalRandomizerPath(settings.UserFilePath):
        """File path of your Pokemon Crystal Randomizer App"""
        description = "Pokemon Crystal Randomizer App"
    
    rom_file: PokemonCrystalRomFile = PokemonCrystalRomFile(PokemonCrystalRomFile.copy_to)
    pcr_path: PokemonCrystalRandomizerPath = PokemonCrystalRandomizerPath(os.path.expandvars("%LOCALAPPDATA%/Programs/Pokemon Crystal Randomizer/Pokemon Crystal Randomizer.exe"))
  
@dataclass
class KrystalGameOptions(PerGameCommonOptions):
    
    class Settings(OptionDict):
        """The settings to pass to the Pokemon Crystal Randomizer during the generation process."""
        display_name = "Settings"
        
    class AutoSellItems(OptionSet):
        """A set of items to automatically convert to money when received from the server instead of getting added to the inventory."""
        display_name = "AutoSellItems"
        
    settings: Settings
    auto_sell_items: AutoSellItems
    
    value_key = "VALUE"
    settings_key = "SETTINGS"
    limit_game_corner_key = "LIMIT_GAME_CORNER_ITEM_STOCK"
    limit_blue_card_key = "LIMIT_BLUE_CARD_REWARDS_STOCK"
    start_with_items_key = "START_WITH_ITEMS"
    amount_key = "AMOUNT"
    progressive_rods_key = "PROGRESSIVE_RODS"
    shuffle_items_key = "SHUFFLE_ITEMS"
    improved_consumables_key = "IMPROVED_CONSUMABLE_ACCESS_LOGIC"
    prevent_shop_items_key = "PREVENT_SHOP_ITEMS"
    prevent_item_placements_key = "PREVENT_ITEM_PLACEMENTS"
    randomize_show_and_tell_pokemon_key = "RANDOMIZE_SHOW_AND_TELL_POKEMON"
    buyable_evolution_stones_key = "BUYABLE_EVOLUTION_STONES"
    randomize_miltank_berries_key = "RANDOMIZE_NUMBER_OF_BERRIES_FOR_MILTANK"
    range_key = "RANGE"
    max_key = "MAX"
    early_goldenrod_mart_tms_key = "EARLY_GOLDENROD_MART_TMS"
    climb_tin_for_ho_oh_chamber_key = "CLIMB_TIN_TOWER_FOR_HO_OH_CHAMBER"
    remove_route_30_roadblock_key = "REMOVE_ROUTE_30_ROADBLOCK"
    item_categories = { "BADGES", "MENU_ITEMS", "HMS", "KEY_ITEMS", "TMS", "REGULAR_ITEMS", "BALLS" }
    
    def is_limit_game_corner_enabled(self):
        return self.settings.get(self.limit_game_corner_key)
        
    def is_limit_blue_card_enabled(self):
        return self.settings.get(self.limit_blue_card_key)
    
    def starting_items_and_amounts(self):
        if self.settings.get(self.start_with_items_key) and self.settings.get(self.start_with_items_key).get(self.value_key):
            return [ 
                item_info 
                for category in [ 
                    x[1]
                    for x in self.settings.get(self.start_with_items_key).get(self.settings_key).items()
                    if x[0] in self.item_categories
                ]
                for item_info in (
                    [ (item, 1) for item in category ] 
                    if isinstance(category, list) 
                    else [ (item_info[0], item_info[1][self.amount_key]) for item_info in category.items() ]
                )
            ]
        else:
            return []
    
    def is_progressive_rods_enabled(self):
        return self.settings.get(self.progressive_rods_key)
    
    def shuffle_items_settings(self):
        if self.settings.get(self.shuffle_items_key) and self.settings.get(self.shuffle_items_key).get(self.value_key):
            return self.settings.get(self.shuffle_items_key).get(self.settings_key)
        else:
            return None
    
    def is_improved_consumables_enabled(self):
        return self.shuffle_items_settings().get(self.improved_consumables_key)
    
    def items_to_exclude_from_shops(self):
        return self.shuffle_items_settings().get(self.prevent_shop_items_key) or []
    
    def item_placements_to_prevent(self):
        return self.shuffle_items_settings().get(self.prevent_item_placements_key) or []
    
    def is_randomize_show_and_tell_pokemon_enabled(self):
        return self.settings.get(self.randomize_show_and_tell_pokemon_key).get(self.value_key)
    
    def are_evolution_stones_buyable(self):
        return self.settings.get(self.buyable_evolution_stones_key)
    
    def are_field_tms_always_buyable(self):
        return self.settings.get(self.early_goldenrod_mart_tms_key)
    
    def miltank_requires_berries(self):
        return (
            not self.settings.get(self.randomize_miltank_berries_key).get(self.value_key)
            or self.settings.get(self.randomize_miltank_berries_key).get(self.settings_key).get(self.range_key).get(self.max_key) > 0
        )
    
    def is_climb_tin_for_ho_oh_chamber_enabled(self):
        return self.settings.get(self.climb_tin_for_ho_oh_chamber_key)
    
    def is_remove_route_30_roadblock_enabled(self):
        return self.settings.get(self.remove_route_30_roadblock_key)

class KrystalWorld(World):
    game = constants.GAME_NAME
    
    settings: typing.ClassVar[KrystalSettings]
    
    options_dataclass = KrystalGameOptions
    options: KrystalGameOptions
    
    goal_event_name = "SILVER_CAVE_ROOM_3_DEFEATED_RED"
    
    item_name_to_id = constants.ITEM_NAMES_TO_NUMERIC_IDS
    location_name_to_id = constants.LOCATION_NAMES_TO_NUMERIC_IDS
    
    @classmethod
    def stage_assert_generate(cls, multiworld: MultiWorld):
        rom_file = KrystalWorld.settings.rom_file
        if not os.path.exists(rom_file):
            raise FileNotFoundError(rom_file)
            
        pcr_path = KrystalWorld.settings.pcr_path
        if not os.path.exists(pcr_path):
            raise FileNotFoundError(pcr_path)
    
    def generate_early(self):
        self.temp_dir = tempfile.TemporaryDirectory(delete=False)
        self.settings_path = os.path.join(self.temp_dir.name, "settings.yml")
        self.base_temp_output_fileName = "output"
        self.base_temp_output_path = os.path.join(self.temp_dir.name, self.base_temp_output_fileName)
        self.game_data_path = self.base_temp_output_path + ".data.yml"
        self.pcr_seed = base64.b64encode(self.random.randbytes(16)).decode("ascii")
        
        with open(self.settings_path, "w") as file:
            file.write(yaml.safe_dump(self.options.settings.value))
        
        subprocess.run([
            self.settings.pcr_path,
            "generate",
            "--gameData",
            "--settings",
            self.settings_path,
            "--seed",
            self.pcr_seed,
            "--inputRom",
            self.settings.rom_file,
            "--ap",
            "--outputDir",
            self.temp_dir.name,
            "--name",
            self.base_temp_output_fileName,
            "--force",
        ])
        
        with open(self.game_data_path, "r") as file:
            self.game_data = yaml.safe_load(file)
        
        self.progression_item_names = set()
        self.all_item_locations = self.game_data["allItemLocations"]
        
        for location in self.all_item_locations:
            for option in location["accessOptions"]:
                for requirement in option:
                    if requirement == "INACCESSIBLE":
                        continue
                    elif type(requirement) is str:
                        self.progression_item_names.add(self.item_name_for_item_id(requirement))
                    elif type(requirement) is int:
                        self.progression_item_names.update(constants.BADGE_ITEM_NAMES)
                    else:
                        self.progression_item_names.add(self.item_name_for_item_id(requirement["item"]))
    
    def create_regions(self) -> None:
        region = Region(self.origin_region_name, self.player, self.multiworld)
        self.multiworld.regions.append(region)
        
        for location in self.all_item_locations:
            tracker_location_id = self.get_tracker_location_id(location)
            
            if (
                location["type"] == "EVENT"
                and location["id"] in self.progression_item_names
                and (
                    location["id"] != "ROUTE_35_GOLDENROD_GATE_GOT_KENYA"
                    or self.is_location_id_shuffled_and_accessible("ROUTE_31_MANS_GIFT_FOR_RANDYS_MAIL")
                )
                and (
                    location["id"] != "ELMS_LAB_GAVE_MYSTERY_EGG"
                    or not self.options.is_remove_route_30_roadblock_enabled()
                    or self.is_location_id_shuffled_and_accessible("ELMS_LAB_AIDES_GIFT_FOR_MYSTERY_EGG")
                )
                and (
                    location["id"] != "TIN_TOWER_ROOF_FOUGHT_HO_OH"
                    or self.options.is_climb_tin_for_ho_oh_chamber_enabled()
                    and (
                        self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_HO_OH_ITEM_ROOM_NE_ITEM_BALL")
                        or self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_HO_OH_ITEM_ROOM_NW_ITEM_BALL")
                        or self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_HO_OH_ITEM_ROOM_SE_ITEM_BALL")
                        or self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_HO_OH_ITEM_ROOM_SW_ITEM_BALL")
                    )
                )
                or location["id"] == "SILVER_CAVE_ROOM_3_DEFEATED_RED"
                or self.is_location_shuffled_and_accessible(location)
                or "itemId" in location
                and self.item_name_for_item_id(location["itemId"]) in self.progression_item_names
                and not self.is_location_inaccessible(location)
                and location["id"] != "AZALEA_TOWN_KURTS_GIFT_FOR_GS_BALL"
                and (
                    self.item_name_for_item_id(location["itemId"]) not in constants.CONSUMABLE_ITEM_NAMES
                    # Rock Smash
                    or tracker_location_id == "ROUTE_36_EAST_AREA_ROCK_SMASH_GUYS_GIFT"
                    or (
                        self.options.are_field_tms_always_buyable()
                        or self.is_location_id_shuffled_and_accessible("ROUTE_36_EAST_AREA_ROCK_SMASH_GUYS_GIFT")
                    )
                    and tracker_location_id == "GOLDENROD_DEPT_STORE_5F_SHOP"
                    # Escape Rope
                    or (
                        self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_KABUTO_ITEM_ROOM_NE_ITEM_BALL")
                        or self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_KABUTO_ITEM_ROOM_NW_ITEM_BALL")
                        or self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_KABUTO_ITEM_ROOM_SE_ITEM_BALL")
                        or self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_KABUTO_ITEM_ROOM_SW_ITEM_BALL")
                    )
                    and tracker_location_id == "VIOLET_MART_SHOP"
                    # Water Stone
                    or self.options.are_evolution_stones_buyable()
                    and (
                        self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_OMANYTE_ITEM_ROOM_NE_ITEM_BALL")
                        or self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_OMANYTE_ITEM_ROOM_NW_ITEM_BALL")
                        or self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_OMANYTE_ITEM_ROOM_SE_ITEM_BALL")
                        or self.is_location_id_shuffled_and_accessible("RUINS_OF_ALPH_OMANYTE_ITEM_ROOM_SW_ITEM_BALL")
                    )
                    and tracker_location_id == "GOLDENROD_DEPT_STORE_4F_SHOP"
                    # Eon Mail
                    or self.is_location_id_shuffled_and_accessible("GOLDENROD_POKECENTER_1F_LADYS_GIFT_FOR_EON_MAIL")
                    and tracker_location_id == "GOLDENROD_DEPT_STORE_5F_MYSTERY_GIFT_GIRLS_GIFT"
                    # Berry
                    or self.options.miltank_requires_berries()
                    and (
                        self.is_location_id_shuffled_and_accessible("ROUTE_39_FARMHOUSE_SHOP")
                        or self.is_location_id_shuffled_and_accessible("ROUTE_39_FARMHOUSE_LADYS_GIFT")
                    )
                    and location["itemId"] == "BERRY"
                )
            ):
                location_id = location["id"]
                location_name = self.location_name_for_location(location)
                location_numeric_id = (
                    constants.LOCATION_NAMES_TO_NUMERIC_IDS[location_name]
                    if location["type"] != "EVENT"
                    else None
                )
                
                ap_location = Location(self.player, location_name, location_numeric_id, region)
                region.locations.append(ap_location)
                
                if location["type"] == "EVENT":
                    item = self.create_item(location_name)
                    item.classification = ItemClassification.progression
                    ap_location.place_locked_item(item)
                elif not location["allowsAPShuffle"]:
                    location_type = location["type"]
                    item_name = self.item_name_for_item_id(location["itemId"])
                    item = self.create_item(item_name)
                    if location["shuffleGroupIndex"] == -1 or self.is_location_inaccessible(location):
                        if (
                            item_name in self.progression_item_names
                            and (
                                item_name not in constants.CONSUMABLE_ITEM_NAMES
                                or not self.options.is_improved_consumables_enabled()
                                or self.is_location_id_renewable_shop(location_id)
                            )
                        ):
                            item.classification = ItemClassification.progression
                    if location["isConsumableProgression"]:
                        item.classification = ItemClassification.progression
                    ap_location.place_locked_item(item)

    def set_rules(self) -> None:
        def rule_from_requirement(requirement) -> Rule:
            if requirement == "INACCESSIBLE":
                return False_()
            if type(requirement) is str:
                item_name = self.item_name_for_item_id(requirement)
                if item_name == "Progressive Rod" and requirement != "OLD_ROD":
                    return Has(item_name, count=2 if requirement == "GOOD_ROD" else 3)
                else:
                    return Has(item_name)
            elif type(requirement) is int:
                return HasFromListUnique(*constants.BADGE_ITEM_NAMES, count=requirement)
            else:
                item_name = self.item_name_for_item_id(requirement["item"])
                return Has(item_name, count=requirement["number"])
            
        def rule_from_requirements(requirements) -> Rule:
            return reduce(lambda result, requirement: And(result, rule_from_requirement(requirement)), requirements, True_())
            
        def rule_from_access_options(access_options) -> Rule:
            rules = map(lambda option: rule_from_requirements(option), access_options)
            return reduce(lambda result, rule: result | rule, rules)
            
        for location in self.all_item_locations:
            location_id = location["id"]
            ap_location = self.safe_get_location(LOCATIONS[location_id]["name"] if location_id in LOCATIONS else location_id)
            
            if ap_location is None:
                continue
            
            self.set_rule(ap_location, rule_from_access_options(location["accessOptions"]))
            
            if location["preventsProgression"]:
                add_item_rule(ap_location, lambda item: (item.classification & ItemClassification.progression) != ItemClassification.progression)
            
            if (location["type"] == "MART" or location["type"] == "SPECIAL_SHOP") and len(self.options.items_to_exclude_from_shops()) > 0:
                forbidden_items_names = { self.item_name_for_item_id(item_id) for item_id in self.options.items_to_exclude_from_shops() }
                forbid_items_for_player(ap_location, forbidden_items_names, self.player)
            
            for prevented_placements in self.options.item_placements_to_prevent():
                if location_id in prevented_placements["LOCATIONS"]:
                    forbidden_items_names = { self.item_name_for_item_id(item_id) for item_id in prevented_placements["ITEMS"] }
                    forbid_items_for_player(ap_location, forbidden_items_names, self.player)
        
        self.set_completion_rule(Has(self.goal_event_name))

    def create_items(self) -> None:
        for location in self.all_item_locations:
            if location["allowsAPShuffle"]:
                self.multiworld.itempool.append(self.create_item(self.item_name_for_item_id(location["itemId"])))
        
        for item_info in self.options.starting_items_and_amounts():
            for _ in range(item_info[1]):
                self.push_precollected(self.create_item(self.item_name_for_item_id(item_info[0])))
        
    def create_item(self, name: str) -> Item:
        numeric_id = None
        if name in constants.ITEM_NAMES_TO_NUMERIC_IDS:
            numeric_id = constants.ITEM_NAMES_TO_NUMERIC_IDS[name]
        
        item_classification = None
        if name in self.progression_item_names and (name not in constants.CONSUMABLE_ITEM_NAMES or not self.options.is_improved_consumables_enabled()):
            item_classification = ItemClassification.progression
        elif name in constants.USEFUL_ITEM_NAMES:
            item_classification = ItemClassification.useful
        else:
            item_classification = ItemClassification.filler
            
        return KrystalItem(name, item_classification, numeric_id, self.player)
        
    def get_filler_item_name(self) -> str:
        return "Berry"
    
    def finalize_multiworld(self) -> None:
        for ap_location in self.multiworld.get_filled_locations(self.player):
            if (
                self.options.is_improved_consumables_enabled() 
                and ap_location.item.player == self.player
                and ap_location.name in constants.LOCATION_NAMES_TO_IDS
                and self.is_location_id_renewable_shop(constants.LOCATION_NAMES_TO_IDS[ap_location.name])
                and ap_location.item.name in self.progression_item_names
            ):
                ap_location.item.classification = ItemClassification.progression
        
    def fill_slot_data(self) -> Dict[str, Any]:
        def get_rules(key):
            return {
                self.get_tracker_location_id(location): location[key]
                for location in self.all_item_locations
            }
        
        return {
            "logical_access_rules": get_rules("accessOptions"),
            "strict_access_rules": get_rules("strictAccessOptions"),
            "visibility_rules": {
                self.get_tracker_location_id(location): True
                for location in self.all_item_locations
                if self.safe_get_location(self.location_name_for_location(location))
            },
            "shop_item_counts": {
                mart_group["name"]: len(self.game_data["marts"][mart_group["primaryMartId"]]["items"])
                for mart_group in self.game_data["martGroups"].values()
            } | {
                shop["name"]: constants.NUMBER_OF_ITEMS_IN_ROOFTOP_SALE_SHOP_2 if shop["id"] == "GOLDENROD_DEPT_STORE_ROOF_SHOP_2" else len(shop["items"])
                for shop in self.game_data["specialShops"].values()
            },
            "shop_location_numeric_ids": [
                LOCATIONS[location["id"]]["numericId"]
                for location in self.all_item_locations
                if (location["type"] == "MART" or location["type"] == "SPECIAL_SHOP") and self.safe_get_location(LOCATIONS[location["id"]]["name"])
            ],
            "renewable_shops": [
                location_numeric_id
                for location_numeric_id, location_id in constants.LOCATION_NUMERIC_IDS_TO_IDS.items()
                if self.is_location_id_renewable_shop(location_id)
            ],
            "is_improved_consumables_enabled": self.options.is_improved_consumables_enabled(),
            "auto_sell_items": {
                ITEMS[item_id]["numericId"]: math.floor(self.game_data["items"][item_id]["price"] / 2)
                for item_id in self.options.auto_sell_items
            },
            "is_random_show_and_tell_enabled": self.options.is_randomize_show_and_tell_pokemon_enabled(),
            "show_and_tell_pokemon": self.game_data["showAndTellPokemon"],
        }
    
    def modify_multidata(self, multidata: Dict[str, Any]):
        multidata["connect_names"][self.pcr_seed[:16]] = multidata["connect_names"][self.player_name]
    
    def generate_output(self, output_directory: str) -> None:
        def item_id_for_item(item) -> str:
            if item.player == self.player:
                return constants.ITEM_NAMES_TO_IDS[item.name]
            elif (
                (item.classification & ItemClassification.progression) == ItemClassification.progression
                or (item.classification & ItemClassification.trap) == ItemClassification.trap
            ):
                return "AP_PROGRESSION_ITEM"
            elif (item.classification & ItemClassification.useful) == ItemClassification.useful:
                return "AP_USEFUL_ITEM"
            else:
                return "AP_FILLER_ITEM"
        
        item_locations = self.game_data["itemLocations"]
        
        for ap_location in self.multiworld.get_filled_locations(self.player):
            if ap_location.locked or ap_location.address is None or ap_location.name not in constants.LOCATION_NAMES_TO_IDS:
                continue
                
            location_id = constants.LOCATION_NAMES_TO_IDS[ap_location.name]
            item_id = item_id_for_item(ap_location.item)
            
            if location_id in item_locations and item_locations[location_id]:
                item_locations[location_id]["itemId"] = item_id
            else:
                location_data = json.loads(location_id)
                item_index = location_data["itemIndex"]
                if "groupId" in location_data:
                    group_id = location_data["groupId"]
                    for mart in [mart for mart in self.game_data["marts"].values() if mart["groupId"] == group_id]:
                        mart_items = mart["items"]
                        if len(mart_items) > item_index and mart_items[item_index] is not None:
                            mart_items[item_index] = item_id
                else:
                    shop_id = location_data["shopId"]
                    item_list = self.game_data["specialShops"][shop_id]["items"]
                    
                    if len(item_list) <= item_index or item_list[item_index] is None:
                        continue
                    
                    if shop_id == "GOLDENROD_DEPT_STORE_ROOF_SHOP_2":
                        item_index += constants.NUMBER_OF_ITEMS_IN_ROOFTOP_SALE_SHOP_1
                        
                    item_list[item_index]["itemId"] = item_id
                    
                    if "GAME_CORNER" in shop_id or "BLUE_CARD" in shop_id:
                        continue
                    
                    price = self.game_data["items"][item_id]["price"]
                    
                    if shop_id == "GOLDENROD_DEPT_STORE_ROOF_SHOP_1" or shop_id == "GOLDENROD_DEPT_STORE_ROOF_SHOP_2":
                        price = price * 0.8
                    elif shop_id == "GOLDENROD_UNDERGROUND_BARGAIN_SHOP":
                        price = price * 0.45
                    
                    item_list[item_index]["price"] = price
                  
        with open(self.game_data_path, "w") as file:
            file.write(yaml.safe_dump(self.game_data, sort_keys=False))
        
        subprocess.run([
            self.settings.pcr_path,
            "generate",
            "--patch",
            "--settings",
            self.settings_path,
            "--seed",
            self.pcr_seed,
            "--inputRom",
            self.settings.rom_file,
            "--inputGameData",
            self.game_data_path,
            "--ap",
            "--outputDir",
            self.temp_dir.name,
            "--name",
            self.base_temp_output_fileName,
            "--force",
        ])
        
        patch = KrystalPatch(player=self.player, player_name=self.player_name)
        patch.patch_file_path = self.base_temp_output_path + ".pcrp"
        patch.write(os.path.join(output_directory, self.multiworld.get_out_file_name_base(self.player) + patch.patch_file_ending))
        self.temp_dir.cleanup()

    def item_name_for_item_id(self, item_id):
        if self.options.is_progressive_rods_enabled() and item_id in ["OLD_ROD", "GOOD_ROD", "SUPER_ROD"]:
            return "Progressive Rod"
        elif item_id in ITEMS:
            return ITEMS[item_id]["name"]
        else:
            return item_id
    
    def is_location_id_renewable_shop(self, location_id):
        return (
            "groupId" in location_id
            or "shopId" in location_id and (
                "GAME_CORNER" not in location_id
                or not self.options.is_limit_game_corner_enabled()
            ) and (
                "BLUE_CARD" not in location_id
                or not self.options.is_limit_blue_card_enabled()
            )
        )
    
    def is_location_inaccessible(self, location):
        return all("INACCESSIBLE" in option for option in location["accessOptions"])
    
    def location_name_for_location(self, location):
        location_id = location["id"]
        return LOCATIONS[location_id]["name"] if location_id in LOCATIONS else location_id
    
    def is_location_id_shuffled_and_accessible(self, location_id):
        return next((
            self.is_location_shuffled_and_accessible(location) 
            for location in self.all_item_locations 
            if location["id"] == location_id
        ), False)
        
    def is_location_shuffled_and_accessible(self, location):
        return (
            location["shuffleGroupIndex"] != -1
            and not self.is_location_inaccessible(location)
        )
    
    def safe_get_location(self, location_name):
        return (
            self.get_location(location_name)
            if location_name in self.multiworld.regions.location_cache[self.player]
            else None
        )
    
    def get_tracker_location_id(self, location):
        return (
            json.loads(location["id"])["groupId"]
            if "groupId" in location["id"]
            else (
                json.loads(location["id"])["shopId"]
                if "shopId" in location["id"]
                else location["id"]
            )
        )

class KrystalLocation(Location):
    game = constants.GAME_NAME

class KrystalItem(Item):
    game = constants.GAME_NAME

class KrystalPatch(APAutoPatchInterface):
    game = constants.GAME_NAME
    patch_file_ending = constants.PATCH_SUFFIX
    result_file_ending = ".gbc"
    
    def write_contents(self, opened_zipfile: zipfile.ZipFile) -> None:
        super(KrystalPatch, self).write_contents(opened_zipfile)
        opened_zipfile.write(self.patch_file_path, "patch.pcrp", compress_type=zipfile.ZIP_STORED)
    
    def read_contents(self, opened_zipfile: zipfile.ZipFile) -> Dict[str, Any]:
        manifest = super(KrystalPatch, self).read_contents(opened_zipfile)
        for file in opened_zipfile.namelist():
            if file == "patch.pcrp":
                self.patch_data = opened_zipfile.read(file)
        return manifest
        
    def patch(self, target: str) -> None:
        self.read()
        with tempfile.TemporaryFile(suffix=".pcrp") as temp_file:
            temp_file.write(self.patch_data)
            subprocess.run([
                get_settings()["pokemon_krystal_options"]["pcr_path"],
                temp_file.name,
                target,
            ])