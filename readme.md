# Pokemon Krystal APWorld

A custom Archipelago World for generating and playing multiworlds with Pokémon Crystal.

## Usage

### Prerequisites

- A Pokémon Crystal Version 1.1 ROM
- [Pokemon Crystal Randomizer](https://dbagwell.github.io/pokemon-crystal-randomizer/) Version 7.0.0 or higher (make a note of the installation location for later)
- [Archipelago](https://archipelago.gg) Version 0.6.7 or higher
- [BizHawk](https://tasvideos.org/BizHawk/ReleaseHistory) Version 2.7 or higher (only required for playing, not for generating)

### Installation

1. Download the `pokemon_krystal.apworld` from the [latest release](https://github.com/dbagwell/pokemon-krystal-apworld/releases/latest).
1. Place the `pokemon_krystal.apworld` file in the `custom_worlds` folder of your Archipelago installation.

### Player Yaml Creation

1. Launch the Pokemon Crystal Randomizer app.
1. Select your desired settings.
1. Click on `Export Archipelago`.
1. Enter your desired slot name and select your desired settings.
1. Click `Export` and save the generated `.yaml` file.

### Multiworld Generation

1. Place your all the player yaml files that you want to include in the multiworld in the `Players` folder of your Archipelago installation (you can include yaml files for other games, but make sure to also install the .apworld files for them if they aren't one of Archipelago's Core games as well as any of their prerequisites).
1. Run the `ArchipelagoGenerate` program or use the `Generate` option from the `ArchipelagoLauncher` program.
1. When prompted specify the location of your Pokémon Crystal Version 1.1 ROM file (this step may not be necessary if the file already exists in the default expected location).
1. When prompted specify the location of your Pokemon Crystal Randomizer app as noted from before when you installed it (this step may not be necessary if you installed the app in the default expected location).
1. A `.archipelago` file will be created inside the `output` folder of your Archipelago installation.

### Hosting a Game

See the [documentation](https://archipelago.gg/tutorial/Archipelago/setup_en#hosting-an-archipelago-server) on the Archipelago website.

### Playing

1. Download and open the `.apkrystal` patch file from the server hosting the game.
1. When prompted for an application to open the file, specify the `ArchipelagoLauncher` program.
1. When prompted specify the location of your Pokémon Crystal Version 1.1 ROM file (this step may not be necessary if you've already provided the file to your Pokemon Crystal Randomizer app).
1. This will automatically launch the `ArchipelagoBizHawkClient` program and attempt to open the `.gbc` file (created in the same folder as the `.apkrystal` file).
   - The game must be played using the BizHawk Emulator. If prompted to specify an application to open the `.gbc` file with, specify EmuHawk (BizHawk). If your OS is set up to open `.gbc` files using something other than BizHawk (and you don't want to change it), then you will have to manually open the generated `.gbc` file (it should be located in the same folder as the `.apkrystal` file) with BizHawk.
1. If the `ArchipelagoBizHawkClient` didn't automatically connect to the multiworld server, specify the server host and port number and click connect.

### Tracking Items

See the [Pokemon Krystal Tracker](https://github.com/dbagwell/pokemon-krystal-tracker) for info on how to use PopTracker to help keep track of items and item locations.