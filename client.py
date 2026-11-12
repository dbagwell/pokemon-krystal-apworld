import json
import math

from NetUtils import ClientStatus
import Utils
import worlds._bizhawk as bizhawk
from worlds._bizhawk.client import BizHawkClient

from . import constants
from .data.events import EVENT_IDS_TO_NUMERIC_IDS, PHONE_FLAGS
from .data.pokemon import POKEMON_IDS

class KrystalClient(BizHawkClient):
    game = constants.GAME_NAME
    system = "GBC"
    patch_suffix = constants.PATCH_SUFFIX
    
    async def validate_rom(self, ctx: "BizHawkClientContext") -> bool:
        try:
            rom_name = (await self.read_rom(ctx, constants.ROM_NAME_ROM_ADDRESS, len(constants.EXPECTED_ROM_NAME))).decode("ascii")
            if rom_name != constants.EXPECTED_ROM_NAME:
                return False
            
            self.mart_names_to_event_flag_offsets = {}
            mart_table_rom_address = constants.MART_TABLE_BANK_ROM_OFFSET + int.from_bytes(await self.read_rom(ctx, constants.MART_TABLE_OFFSET_ROM_ADDRESS, 2), "little")
            current_offset = constants.BASE_MART_FLAG_INDEX
            
            for index, mart_id in enumerate(constants.MART_IDS):
                offset = int.from_bytes(await self.read_rom(ctx, mart_table_rom_address + index * 2, 2), "little")
                mart_size = (await self.read_rom(ctx, constants.MART_TABLE_BANK_ROM_OFFSET + offset, 1))[0]
                
                if mart_size > 0:
                    self.mart_names_to_event_flag_offsets[mart_id] = current_offset
                
                current_offset += mart_size
                
            self.mart_names_to_event_flag_offsets["GOLDENROD_DEPT_STORE_ROOF_SHOP_1"] = current_offset
            current_offset += constants.NUMBER_OF_ITEMS_IN_ROOFTOP_SALE_SHOP_1
            self.mart_names_to_event_flag_offsets["GOLDENROD_DEPT_STORE_ROOF_SHOP_2"] = current_offset
            current_offset += constants.NUMBER_OF_ITEMS_IN_ROOFTOP_SALE_SHOP_2
            self.mart_names_to_event_flag_offsets["GOLDENROD_UNDERGROUND_BARGAIN_SHOP"] = current_offset
        except:
            return False
        
        ctx.game = self.game
        ctx.watcher_timeout = 0.125
        ctx.want_slot_data = True
        ctx.items_handling = 0b001
        ctx.connected = False

        return True

    async def set_auth(self, ctx: "BizHawkClientContext") -> None:
        from CommonClient import logger
        
        try:
            ctx.auth = (await self.read_rom(ctx, constants.AUTH_ROM_OFFSET, 16)).decode("ascii")
        except:
            logger.error("Timed out reading from Bizhawk.")
            
    def on_package(self, ctx: "BizHawkClientContext", cmd: str, args: dict) -> None:
        if cmd == "Connected":
            ctx.collected_events = []
            ctx.viewed_mart_names = []
            ctx.pokemon_caught = []
            ctx.unown_caught = 0
            ctx.phone_numbers_registered = []
            ctx.phone_calls_received = []
            ctx.last_map_info = {
                "group": -1,
                "number": -1,
            }
            
            ctx.collected_events_key = f"pokemon_krystal_collected_events_{ctx.team}_{ctx.slot}"
            ctx.current_map_key = f"pokemon_krystal_current_map_{ctx.team}_{ctx.slot}"
            ctx.viewed_shops_key = f"pokemon_krystal_viewed_shops_{ctx.team}_{ctx.slot}"
            ctx.pokemon_caught_key = f"pokemon_krystal_pokemon_caught_{ctx.team}_{ctx.slot}"
            ctx.unown_caught_key = f"pokemon_krystal_unown_caught_{ctx.team}_{ctx.slot}"
            ctx.phone_numbers_registered_key = f"pokemon_krystal_phone_numbers_registered_{ctx.team}_{ctx.slot}"
            ctx.phone_calls_received_key = f"pokemon_krystal_phone_calls_received_{ctx.team}_{ctx.slot}"
            
            ctx.connected = True
        
            Utils.async_start(ctx.send_msgs([{
                "cmd": "Get",
                "keys": [
                    ctx.collected_events_key,
                    ctx.pokemon_caught_key,
                    ctx.unown_caught_key,
                    ctx.phone_numbers_registered_key,
                    ctx.phone_calls_received_key,
                ],
            }]))
        elif cmd == "Retrieved":
            if ctx.collected_events_key in args["keys"]:
                ctx.collected_events = args["keys"][ctx.collected_events_key] or []
            if ctx.pokemon_caught_key in args["keys"]:
                ctx.pokemon_caught = args["keys"][ctx.pokemon_caught_key] or []
            if ctx.unown_caught_key in args["keys"]:
                ctx.unown_caught = args["keys"][ctx.unown_caught_key] or 0
            if ctx.phone_numbers_registered_key in args["keys"]:
                ctx.phone_numbers_registered = args["keys"][ctx.phone_numbers_registered_key] or []
            if ctx.phone_calls_received_key in args["keys"]:
                ctx.phone_calls_received = args["keys"][ctx.phone_calls_received_key] or []
            
    async def game_watcher(self, ctx: "BizHawkClientContext") -> None:
        from CommonClient import logger
        
        if not ctx.connected or not ctx.server or not ctx.server.socket.open or ctx.server.socket.closed or not ctx.slot_data:
            ctx.connected = False
            return
        
        try:
            data = await self.read_ram(ctx, [
                (constants.EVENT_FLAGS_WRAM_ADDRESS, constants.NUMBER_OF_EVENT_FLAGS_BYTES),
                (constants.REGULAR_ITEM_QUEUE_WRAM_ADDRESS, 1),
                (constants.REGULAR_ITEM_QUEUE_WRAM_ADDRESS + 1, 2),
                (constants.SPECIAL_ITEM_QUEUE_WRAM_ADDRESS, 1),
                (constants.SPECIAL_ITEM_QUEUE_WRAM_ADDRESS + 1, 2),
                (constants.CURRENT_MAP_GROUP_WRAM_ADDRESS, 1),
                (constants.CURRENT_MAP_NUMBER_WRAM_ADDRESS, 1),
                (constants.CURRENT_Y_COORD_WRAM_ADDRESS, 1),
                (constants.CURRENT_X_COORD_WRAM_ADDRESS, 1),
                (constants.LAST_VIEWED_MART_INDEX_WRAM_ADDRESS, 1),
                (constants.MONEY_WRAM_ADDRESS, 3),
                (constants.POKEMON_CAUGHT_WRAM_ADDRESS, constants.NUMBER_OF_POKEMON_CAUGHT_BYTES),
                (constants.UNOWNDEX_WRAM_ADDRESS, constants.NUMBER_OF_UNOWNDEX_BYTES),
                (constants.PHONEBOOK_WRAM_ADDRESS, constants.NUMBER_OF_PHONEBOOK_BYTES),
                (PHONE_FLAGS["REMATCHES"]["WRAM_ADDRESS"], PHONE_FLAGS["REMATCHES"]["NUMBER_OF_BYTES"]),
                (PHONE_FLAGS["ITEMS"]["WRAM_ADDRESS"], PHONE_FLAGS["ITEMS"]["NUMBER_OF_BYTES"]),
                (PHONE_FLAGS["OTHERS"]["WRAM_ADDRESS"], PHONE_FLAGS["OTHERS"]["NUMBER_OF_BYTES"]),
            ])
        except:
            logger.error("Timed out reading from Bizhawk.")
            return
        
        event_flags = data[0]
        existing_regular_item_in_queue = data[1][0]
        index_of_last_regular_item_in_queue = int.from_bytes(data[2], "little")
        existing_special_item_in_queue = data[3][0]
        index_of_last_special_item_in_queue = int.from_bytes(data[4], "little")
        current_map_group = data[5][0]
        current_map_number = data[6][0]
        current_y_coord = data[7][0]
        current_x_coord = data[8][0]
        last_viewed_mart_index = data[9][0]
        current_money = int.from_bytes(data[10], "big")
        pokemon_caught_flags = data[11]
        unowndex = data[12]
        phonebook = data[13]
        rematch_flags = data[14]
        phone_item_flags = data[15]
        other_phone_flags = data[16]
        
        if self.is_flag_set(event_flags, constants.INITIALIZED_FLAG_INDEX):
            
            # Locations
            
            new_checked_locations = [] 
            for location_numeric_id in ctx.missing_locations:
                location_id = constants.LOCATION_NUMERIC_IDS_TO_IDS[location_numeric_id]
                if "groupId" in location_id:
                    location_info = json.loads(location_id)
                    group_id = location_info["groupId"]
                    item_index = location_info["itemIndex"]
                    
                    location_checked = False
                    for mart in constants.MART_IDS:
                        if group_id in mart and mart in self.mart_names_to_event_flag_offsets and self.is_flag_set(event_flags, self.mart_names_to_event_flag_offsets[mart] + item_index):
                            location_checked = True
                    
                    if location_checked:
                        new_checked_locations.append(location_numeric_id)
                    
                elif "GOLDENROD_UNDERGROUND_BARGAIN_SHOP" in location_id:
                    item_index = json.loads(location_id)["itemIndex"]
                    if self.is_flag_set(event_flags, self.mart_names_to_event_flag_offsets["GOLDENROD_UNDERGROUND_BARGAIN_SHOP"] + item_index):
                        new_checked_locations.append(location_numeric_id)
                    
                elif "GOLDENROD_DEPT_STORE_ROOF_SHOP" in location_id:
                    location_info = json.loads(location_id)
                    shop_id = location_info["shopId"]
                    item_index = location_info["itemIndex"]
                    if self.is_flag_set(event_flags, self.mart_names_to_event_flag_offsets[shop_id] + item_index):
                        new_checked_locations.append(location_numeric_id)
                    
                else:
                    if location_id == "CERULEAN_GYM_HIDDEN_ITEM":
                        if not self.is_flag_set(event_flags, constants.MET_MANAGER_AT_POWER_PLANT_FLAG_INDEX):
                            continue
                    
                    if self.is_flag_set(event_flags, location_numeric_id):
                        new_checked_locations.append(location_numeric_id)
            
            await ctx.check_locations(new_checked_locations)
            
            # Items
            
            await self.update_item_queue(
                ctx, 
                existing_regular_item_in_queue, 
                index_of_last_regular_item_in_queue, 
                constants.REGULAR_ITEM_NUMERIC_IDS, 
                constants.REGULAR_ITEM_QUEUE_WRAM_ADDRESS,
                False,
                current_money,
            )
            
            await self.update_item_queue(
                ctx, 
                existing_special_item_in_queue,
                index_of_last_special_item_in_queue,
                constants.SPECIAL_ITEM_NUMERIC_IDS, 
                constants.SPECIAL_ITEM_QUEUE_WRAM_ADDRESS,
                True,
                current_money,
            )
            
            # Events
            
            new_events = [
                event_id
                for event_id, event_numeric_id in EVENT_IDS_TO_NUMERIC_IDS.items()
                if event_id not in ctx.collected_events and (
                    event_id != "ROUTE_25_MET_MISTY"
                    and self.is_flag_set(event_flags, event_numeric_id)
                    or event_id == "ROUTE_25_MET_MISTY"
                    and not self.is_flag_set(event_flags, event_numeric_id)
                )
            ]
            
            if len(new_events) > 0:
                ctx.collected_events = ctx.collected_events + new_events
                await ctx.send_msgs([{
                    "cmd": "Set",
                    "key": ctx.collected_events_key,
                    "default": [],
                    "want_reply": False,
                    "operations": [{
                        "operation": "update",
                        "value": new_events,
                    }],
                }])
            
            # Map
            
            if current_x_coord >= 44 and current_map_group == 7 and current_map_number == 13:
                current_map_number = 14 # Change the west part of route 9 to be part of route 10 north
            
            if (
                (
                    ctx.last_map_info["group"] != current_map_group 
                    or ctx.last_map_info["number"] != current_map_number
                )
                and (current_map_group != 3 or current_map_number != 54 or current_y_coord < 15) # Don't update the map if we are in the goldenrod undergound entrances
            ):
                ctx.last_map_info = {
                    "group": current_map_group,
                    "number": current_map_number,
                }
                
                await ctx.send_msgs([{
                    "cmd": "Set",
                    "key": ctx.current_map_key,
                    "default": {},
                    "want_reply": False,
                    "operations": [{
                        "operation": "update",
                        "value": ctx.last_map_info,
                    }],
                }])
            
            # Viewed Shops
            
            if last_viewed_mart_index < len(constants.MART_NAMES):
                last_viewed_mart_name = constants.MART_NAMES[last_viewed_mart_index]
                
                if last_viewed_mart_name == "Goldenrod Dept. Store Roof - Shop 1" and self.is_flag_set(event_flags, EVENT_IDS_TO_NUMERIC_IDS["HALL_OF_FAME_ENTERED"]):
                    last_viewed_mart_name = "Goldenrod Dept. Store Roof - Shop 2"
                
                if last_viewed_mart_name and last_viewed_mart_name not in ctx.viewed_mart_names:
                    ctx.viewed_mart_names.append(last_viewed_mart_name)
                    await ctx.send_msgs([{
                        "cmd": "Set",
                        "key": ctx.viewed_shops_key,
                        "default": [],
                        "want_reply": False,
                        "operations": [{
                            "operation": "update",
                            "value": ctx.viewed_mart_names,
                        }],
                    }])
            
            # Pokemon
            
            new_pokemon = [
                pokemon_id
                for index, pokemon_id in enumerate(POKEMON_IDS)
                if pokemon_id not in ctx.pokemon_caught and self.is_flag_set(pokemon_caught_flags, index)
            ]
            
            if len(new_pokemon) > 0:
                ctx.pokemon_caught = ctx.pokemon_caught + new_pokemon
                await ctx.send_msgs([{
                    "cmd": "Set",
                    "key": ctx.pokemon_caught_key,
                    "default": [],
                    "want_reply": False,
                    "operations": [{
                        "operation": "update",
                        "value": new_pokemon,
                    }],
                }])
            
            # Unown
            
            number_of_unown_forms_registered = len([letter for letter in unowndex if letter != 0])
            if number_of_unown_forms_registered != ctx.unown_caught:
                ctx.unown_caught = number_of_unown_forms_registered
                await ctx.send_msgs([{
                    "cmd": "Set",
                    "key": ctx.unown_caught_key,
                    "default": 0,
                    "want_reply": False,
                    "operations": [{
                        "operation": "replace",
                        "value": number_of_unown_forms_registered,
                    }],
                }])
            
            # Phone Numbers
            
            new_phone_numbers = [
                phone_number_id
                for phone_number_id, phone_number_numeric_id in constants.PHONE_NUMBER_IDS_TO_NUMERIC_IDS.items()
                if phone_number_id not in ctx.phone_numbers_registered and phone_number_numeric_id in phonebook
            ]
            
            if len(new_phone_numbers) > 0:
                ctx.phone_numbers_registered = ctx.phone_numbers_registered + new_phone_numbers
                await ctx.send_msgs([{
                    "cmd": "Set",
                    "key": ctx.phone_numbers_registered_key,
                    "default": [],
                    "want_reply": False,
                    "operations": [{
                        "operation": "update",
                        "value": new_phone_numbers,
                    }],
                }])
            
            # Phone Calls
            
            new_phone_calls = [
                phone_call_id
                for phone_call_id, flag_numeric_id in PHONE_FLAGS["REMATCHES"]["FLAG_IDS_TO_NUMERIC_IDS"].items()
                if phone_call_id not in ctx.phone_calls_received and self.is_flag_set(rematch_flags, flag_numeric_id)
            ] + [
                phone_call_id
                for phone_call_id, flag_numeric_id in PHONE_FLAGS["ITEMS"]["FLAG_IDS_TO_NUMERIC_IDS"].items()
                if phone_call_id not in ctx.phone_calls_received and self.is_flag_set(phone_item_flags, flag_numeric_id)
            ] + [
                phone_call_id
                for phone_call_id, flag_numeric_id in PHONE_FLAGS["OTHERS"]["FLAG_IDS_TO_NUMERIC_IDS"].items()
                if phone_call_id not in ctx.phone_calls_received and self.is_flag_set(other_phone_flags, flag_numeric_id)
            ]
            
            if len(new_phone_calls) > 0:
                ctx.phone_calls_received = ctx.phone_calls_received + new_phone_calls
                await ctx.send_msgs([{
                    "cmd": "Set",
                    "key": ctx.phone_calls_received_key,
                    "default": [],
                    "want_reply": False,
                    "operations": [{
                        "operation": "update",
                        "value": new_phone_calls,
                    }],
                }])
            
            # Goal
            
            if not ctx.finished_game and self.is_flag_set(event_flags, constants.BEAT_RED_FLAG_INDEX):
                await ctx.send_msgs([{ "cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL }])
                ctx.finished_game = True
    
    async def update_item_queue(
        self, 
        ctx, 
        existing_item_in_queue, 
        index_of_last_item_in_queue, 
        item_filter, 
        wram_address,
        udpate_verbose_flag,
        current_money,
    ):
        if existing_item_in_queue:
            return
            
        next_item_index = next((
            index
            for index, value in enumerate([None] + ctx.items_received)
            if (
                index > index_of_last_item_in_queue
                and value.item in item_filter
            )
        ), None)
        
        if not next_item_index:
            return
        
        next_item = ctx.items_received[next_item_index - 1]
        sell_price = ctx.slot_data["auto_sell_items"][f"{next_item.item}"] if f"{next_item.item}" in ctx.slot_data["auto_sell_items"] else None
        
        try:
            if sell_price:
                write_result = await bizhawk.guarded_write(
                    ctx.bizhawk_ctx,
                    [
                        (
                            constants.MONEY_WRAM_ADDRESS,
                            list(min(current_money + sell_price, constants.MAX_MONEY).to_bytes(3, "big")),
                            "WRAM"
                        ),
                        (
                            wram_address + 1,
                            list(next_item_index.to_bytes(2, "little")),
                            "WRAM"
                        ),
                    ],
                    [
                        (
                            constants.MONEY_WRAM_ADDRESS,
                            list(current_money.to_bytes(3, "big")),
                            "WRAM"
                        ),
                    ],
                )
                
            else:
                await bizhawk.write(
                    ctx.bizhawk_ctx,
                    [
                        (
                            wram_address,
                            [next_item.item] + list(next_item_index.to_bytes(2, "little")),
                            "WRAM",
                        ),
                    ] + ([
                        (
                            constants.VERBOSE_FLAG_WRAM_ADDRESS,
                            [1 if next_item.flags & 1 else 0],
                            "WRAM",
                        ),
                    ] if udpate_verbose_flag else []),
                )
        except:
            logger.error("Timed out writing to Bizhawk.")
                    
    async def read_rom(self, ctx, location, length):
        return (await bizhawk.read(ctx.bizhawk_ctx, [(location, length, "ROM")]))[0]
        
    async def read_ram(self, ctx, locations):
        return await bizhawk.read(ctx.bizhawk_ctx, [location + ("WRAM",) for location in locations])
    
    def is_flag_set(self, flags, flag_index):
        byte_index = math.floor(flag_index / 8)
        bit_index = flag_index % 8
        return self.is_bit_set(flags[byte_index], bit_index)
    
    def is_bit_set(self, byte, index):
        return (byte >> index) & 1