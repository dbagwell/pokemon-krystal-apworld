from .data.items import ITEMS
from .data.locations import LOCATIONS

GAME_NAME = "Pokemon Krystal"
PATCH_SUFFIX = ".apkrystal"
EXPECTED_ROM_NAME = "KOVOLTA_PCR"

ROM_NAME_ROM_ADDRESS = 0x134
MART_TABLE_BANK_ROM_OFFSET = 0x10000
MART_TABLE_OFFSET_ROM_ADDRESS = MART_TABLE_BANK_ROM_OFFSET + 0x5B3D
AUTH_ROM_OFFSET = 0x1FC000

EVENT_FLAGS_WRAM_ADDRESS = 0x1A72
REGULAR_ITEM_QUEUE_WRAM_ADDRESS = 0x1C3A
SPECIAL_ITEM_QUEUE_WRAM_ADDRESS = 0x1C3D
VERBOSE_FLAG_WRAM_ADDRESS = 0x1D00
CURRENT_MAP_GROUP_WRAM_ADDRESS = 0x1CB5
CURRENT_MAP_NUMBER_WRAM_ADDRESS = 0x1CB6
CURRENT_Y_COORD_WRAM_ADDRESS = 0x1CB7
CURRENT_X_COORD_WRAM_ADDRESS = 0x1CB8
LAST_VIEWED_MART_INDEX_WRAM_ADDRESS = 0x1039
MONEY_WRAM_ADDRESS = 0x184E
POKEMON_CAUGHT_WRAM_ADDRESS = 0x1E99
UNOWNDEX_WRAM_ADDRESS = 0x1ED9
PHONEBOOK_WRAM_ADDRESS = 0x1C7C

NUMBER_OF_EVENT_FLAGS_BYTES = 0x100
INITIALIZED_FLAG_INDEX = 54
MET_MANAGER_AT_POWER_PLANT_FLAG_INDEX = 202
BASE_MART_FLAG_INDEX = 261
BEAT_RED_FLAG_INDEX = 938
NUMBER_OF_POKEMON_CAUGHT_BYTES = 32
NUMBER_OF_UNOWNDEX_BYTES = 26
NUMBER_OF_PHONEBOOK_BYTES = 10

MAX_MONEY = 999999

NUMBER_OF_ITEMS_IN_ROOFTOP_SALE_SHOP_1 = 5
NUMBER_OF_ITEMS_IN_ROOFTOP_SALE_SHOP_2 = 5

BADGE_ITEM_NAMES = { value["name"] for value in ITEMS.values() if value["category"] == "BADGES" }
REGULAR_ITEM_NAMES = { value["name"] for value in ITEMS.values() if value["category"] == "REGULAR_ITEMS" }
BALL_ITEM_NAMES = { value["name"] for value in ITEMS.values() if value["category"] == "BALLS" }
TM_ITEM_NAMES = { value["name"] for value in ITEMS.values() if value["category"] == "TMS" }
CONSUMABLE_ITEM_NAMES = TM_ITEM_NAMES | REGULAR_ITEM_NAMES | BALL_ITEM_NAMES
USEFUL_ITEM_NAMES = { value["name"] for value in ITEMS.values() if value["isUseful"] }
REGULAR_ITEM_NUMERIC_IDS = { value["numericId"] for value in ITEMS.values() if value["category"] == "REGULAR_ITEMS" }
SPECIAL_ITEM_NUMERIC_IDS = { value["numericId"] for value in ITEMS.values() if value["category"] != "REGULAR_ITEMS" }

ITEM_NAMES_TO_NUMERIC_IDS = { value["name"]: value["numericId"] for value in ITEMS.values() } | { "Progressive Rod": 58 }
ITEM_NAMES_TO_IDS = { value["name"]: key for key, value in ITEMS.items() } | { "Progressive Rod": "OLD_ROD" }

LOCATION_NAMES_TO_NUMERIC_IDS = { value["name"]: value["numericId"] for value in LOCATIONS.values() }
LOCATION_NAMES_TO_IDS = { value["name"]: key for key, value in LOCATIONS.items() }
LOCATION_NUMERIC_IDS_TO_IDS = { value["numericId"]: key for key, value in LOCATIONS.items() }

MART_IDS = [
    "CHERRYGROVE_MART_SHOP_1",
    "CHERRYGROVE_MART_SHOP_2",
    "VIOLET_MART_SHOP",
    "AZALEA_MART_SHOP",
    "CIANWOOD_PHARMACY_SHOP",
    "GOLDENROD_DEPT_STORE_2F_SHOP_1",
    "GOLDENROD_DEPT_STORE_2F_SHOP_2",
    "GOLDENROD_DEPT_STORE_3F_SHOP",
    "GOLDENROD_DEPT_STORE_4F_SHOP",
    "GOLDENROD_DEPT_STORE_5F_SHOP_1",
    "GOLDENROD_DEPT_STORE_5F_SHOP_2",
    "GOLDENROD_DEPT_STORE_5F_SHOP_3",
    "GOLDENROD_DEPT_STORE_5F_SHOP_4",
    "OLIVINE_MART_SHOP",
    "ECRUTEAK_MART_SHOP",
    "MAHOGANY_MART_1F_SHOP_1",
    "MAHOGANY_MART_1F_SHOP_2",
    "BLACKTHORN_MART_SHOP",
    "VIRIDIAN_MART_SHOP",
    "PEWTER_MART_SHOP",
    "CERULEAN_MART_SHOP",
    "LAVENDER_MART_SHOP",
    "VERMILION_MART_SHOP",
    "CELADON_DEPT_STORE_2F_SHOP_1",
    "CELADON_DEPT_STORE_2F_SHOP_2",
    "CELADON_DEPT_STORE_3F_SHOP",
    "CELADON_DEPT_STORE_4F_SHOP",
    "CELADON_DEPT_STORE_5F_SHOP_1",
    "CELADON_DEPT_STORE_5F_SHOP_2",
    "FUCHSIA_MART_SHOP",
    "SAFFRON_MART_SHOP",
    "MOUNT_MOON_GIFT_SHOP_SHOP",
    "INDIGO_PLATEAU_POKECENTER_1F_SHOP",
    "GOLDENROD_UNDERGROUND_HERB_SHOP",
    "GOLDENROD_DEPT_STORE_5F_SHOP_5",
    "GOLDENROD_DEPT_STORE_5F_SHOP_6",
    "GOLDENROD_DEPT_STORE_5F_SHOP_7",
    "GOLDENROD_DEPT_STORE_5F_SHOP_8",
]

MART_NAMES = [
    None,
    "Cherrygrove Mart - Shop",
    "Violet Mart - Shop",
    "Azalea Mart - Shop",
    "Cianwood Pharmacy - Shop",
    "Goldenrod Dept. Store - 2F - Shop 1",
    "Goldenrod Dept. Store - 2F - Shop 2",
    "Goldenrod Dept. Store - 3F - Shop",
    "Goldenrod Dept. Store - 4F - Shop",
    None,
    None,
    None,
    None,
    "Olivine Mart - Shop",
    "Ecruteak Mart - Shop",
    "Mahogany Gift Shop - Shop 1",
    "Mahogany Gift Shop - Shop 2",
    "Blackthorn Mart - Shop",
    "Viridian Mart - Shop",
    "Pewter Mart - Shop",
    "Cerulean Mart - Shop",
    "Lavender Mart - Shop",
    "Vermilion Mart - Shop",
    "Celadon Dept. Store - 2F - Shop 1",
    "Celadon Dept. Store - 2F - Shop 2",
    "Celadon Dept. Store - 3F - Shop",
    "Celadon Dept. Store - 4F - Shop",
    "Celadon Dept. Store - 5F - Shop 1",
    "Celadon Dept. Store - 5F - Shop 2",
    "Fuchsia Mart - Shop",
    "Saffron Mart - Shop",
    "Mount Moon Gift Shop - Shop",
    "Indigo Plateau Pokecenter - 1F - Shop",
    "Goldenrod Underground - Herb Shop",
    None,
    None,
    None,
    "Goldenrod Dept. Store - 5F - Shop",
    "Goldenrod Dept. Store Roof - Shop 1",
    "Goldenrod Underground - Bargain Shop",
    "Goldenrod Dept. Store - 6F - Vending Machines",
    "Celadon Dept. Store - 6F - Vending Machines",
    "Goldenrod Game Corner - Item Shop",
    "Celadon Game Corner - Item Shop",
    "Radio Tower - 2F - Blue Card Shop",
    "Route 39 - Farmhouse - Shop",
    "Mahogany Town - Street Vendor",
]

PHONE_NUMBER_IDS_TO_NUMERIC_IDS = {
    "BEVERLY": 6,
    "HUEY": 7,
    "JOSE": 13,
    "JOEY": 15,
    "WADE": 16,
    "TODD": 20,
    "GINA": 21,
    "ALAN": 24,
    "DANA": 26,
    "DEREK": 28,
    "TULLY": 29,
    "TIFFANY": 31,
    "VANCE": 32,
    "WILTON": 33,
    "PARRY": 35,
    "ERIN": 36,
}