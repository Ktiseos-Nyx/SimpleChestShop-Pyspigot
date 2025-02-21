import os
import sqlite3
from java.sql import Connection, DriverManager, SQLException

# LuckPerms
from net.luckperms.api import LuckPerms

# Placeholder API
from me.clip.placeholderapi import PlaceholderAPI

# Third-party imports
import pyspigot as ps
from net.milkbowl.vault2.economy import Economy
from net.milkbowl.vault2.permission import Permission
from net.milkbowl.vault2.chat import Chat
from com.palmergames.bukkit.towny import TownyUniverse
from net.milkbowl.vaultunlocked.api import VaultUnlockedAPI

# Bukkit API imports
from org.bukkit.plugin.java import JavaPlugin
from org.bukkit.Material import Material
from org.bukkit.block import Sign
from org.bukkit.entity import Player
from org.bukkit.event import EventHandler, Listener
from org.bukkit.inventory import ItemStack
from org.bukkit import Bukkit
from org.bukkit.event.player import PlayerInteractEvent
from org.bukkit.event.block import BlockBreakEvent
from org.bukkit.event.block import SignChangeEvent
from org.bukkit.command import CommandSender
from org.bukkit import ChatColor
from org.bukkit.permissions import Permission

# GUI imports
from org.bukkit.inventory import Inventory
from org.bukkit.event.inventory import InventoryType
from org.bukkit.event.inventory import InventoryClickEvent
from org.bukkit.event.inventory import InventoryCloseEvent
from org.bukkit import ChatColor

# Geyser API imports
from org.geysermc.api.GeyserApi import GeyserApi
from org.geysermc.floodgate.api.FloodgateApi import FloodgateApi

# Pyspigot Configuration Manager
from pyspigot import ConfigurationManager

# YAML Config
import ruamel.yaml as yaml

CONFIG_FILE = "config.yml"
SHOP_CHEST_MATERIAL_CONFIG_KEY = "shop_chest_material"
SHOP_IDENTIFIER_SIGN_TEXT_CONFIG_KEY = "shop_identifier_sign_text"

DEFAULT_SHOP_CHEST_MATERIAL = "CHEST"
DEFAULT_SHOP_IDENTIFIER_SIGN_TEXT = "[Shop]"

class ChestShop(JavaPlugin, Listener):
    def __init__(self):
        super(ChestShop, self).__init__()
        self.config_manager = ConfigurationManager(self)
        self.db_connection = None
        self.shop_chest_material = None
        self.shop_identifier_sign_text = None
        self.shop_locations = set()  # Set to store shop locations
        self.economy = None
        self.luckperms = None
        self.allow_admin_shops = False
        self.gui_title = "&aChest Shop"  # Default GUI title
        self.gui_size = 27  # Default GUI size
        self.default_items = {}  # Dictionary to store default items in GUI
        self.vault_unlocked_api = None
        self.message_shop_created = "&aShop created for {item}"
        self.message_admin_shop_created = "&aAdmin shop created for {item}"
        self.message_no_permission = "&cYou do not have permission to perform this action."
        self.message_invalid_arguments = "&cInvalid arguments. Usage: {usage}"
        self.currency_symbol = "$"
        self.enable_towny_integration = True
        self.enable_luckperms_integration = True
        self.enable_geyser_integration = True
        self.enable_floodgate_integration = True

    def onEnable(self):
        # Called when the plugin is enabled
        self.load_plugin_config()  # Load plugin configuration
        self.setup_database()  # Setup database
        self.load_shop_locations()  # Load shop locations from database
        self.setup_economy()  # Setup economy integration
        self.setup_permissions()  # Setup permissions integration
        self.register_events()  # Register event listeners
        self.setup_placeholder_api()  # Setup PlaceholderAPI integration
        self.vault_unlocked_api = VaultUnlockedAPI()  # Initialize VaultUnlockedAPI

    def onDisable(self):
        # Called when the plugin is disabled
        if self.db_connection:
            self.db_connection.close()  # Close database connection

    def load_plugin_config(self):
        # Load configuration from config.yml using the Configuration Manager
        self.config_manager.load_config("config.yml")
        self.shop_chest_material = self.config_manager.get("shop_chest_material", "CHEST")
        self.shop_identifier_sign_text = self.config_manager.get("shop_identifier_sign_text", "[Shop]")
        self.allow_admin_shops = self.config_manager.get("allow_admin_shops", False)
        # Load GUI configuration
        self.gui_title = self.config_manager.get("gui_title", "&aChest Shop")
        self.gui_size = self.config_manager.get("gui_size", 27)
        self.default_items = self.config_manager.get("default_items", {})
        # Load messages
        self.message_shop_created = self.config_manager.get("message_shop_created", "&aShop created for {item}")
        self.message_admin_shop_created = self.config_manager.get("message_admin_shop_created", "&aAdmin shop created for {item}")
        self.message_no_permission = self.config_manager.get("message_no_permission", "&cYou do not have permission to perform this action.")
        self.message_invalid_arguments = self.config_manager.get("message_invalid_arguments", "&cInvalid arguments. Usage: {usage}")
        # Load currency
        self.currency_symbol = self.config_manager.get("currency_symbol", "$")
        # Load feature toggles
        self.enable_towny_integration = self.config_manager.get("enable_towny_integration", True)
        self.enable_luckperms_integration = self.config_manager.get("enable_luckperms_integration", True)
        self.enable_geyser_integration = self.config_manager.get("enable_geyser_integration", True)
        self.enable_floodgate_integration = self.config_manager.get("enable_floodgate_integration", True)
        self.getLogger().info("Configuration loaded from '{}'".format(CONFIG_FILE))
        self.getLogger().info("Shop chest material: '{}'".format(self.shop_chest_material))
        self.getLogger().info("Shop identifier sign text: '{}'".format(self.shop_identifier_sign_text))

    def save_plugin_config(self):
        # Save current configuration to config.yml
        self.config_manager.set("shop_chest_material", self.shop_chest_material)
        self.config_manager.set("shop_identifier_sign_text", self.shop_identifier_sign_text)
        self.config_manager.set("allow_admin_shops", self.allow_admin_shops)
        self.config_manager.set("gui_title", self.gui_title)
        self.config_manager.set("gui_size", self.gui_size)
        self.config_manager.set("default_items", self.default_items)
        self.config_manager.save_config("config.yml")
        self.getLogger().info("Configuration saved to '{}'".format(CONFIG_FILE))

    def setup_database(self):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:E:/1.19.4/plugins/PySpigot/scripts/database.db")
            statement = self.db_connection.createStatement()
            create_table_sql = "CREATE TABLE IF NOT EXISTS shops (id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT, location TEXT UNIQUE, item TEXT, price REAL, is_admin_shop INTEGER)"
            statement.executeUpdate(create_table_sql)
            create_table_sql = "CREATE TABLE IF NOT EXISTS gui_items (slot INTEGER PRIMARY KEY, material_name TEXT)"
            statement.executeUpdate(create_table_sql)
            self.db_connection.close()
            self.getLogger().info("Database and tables created successfully.")
        except SQLException as e:
            self.getLogger().severe("An error occurred: {}".format(e.getMessage()))

    def load_shop_locations(self):
        # Load shop locations from the database into memory
        self.shop_locations.clear()
        shops = self.get_shops()
        for shop in shops:
            self.shop_locations.add(shop[2])

    def get_shops(self):
        # Retrieve all shops from the database
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT id, owner, location, item, price, is_admin_shop FROM shops")
        shops = cursor.fetchall()
        cursor.close()
        return shops

    def add_shop(self, owner, location, item, price):
        # Add a new shop to the database
        cursor = self.db_connection.cursor()
        cursor.execute("INSERT INTO shops (owner, location, item, price) VALUES (?, ?, ?, ?)", (owner, location, item, price))
        self.db_connection.commit()
        cursor.close()
        self.load_shop_locations()  # Refresh shop locations

    def remove_shop(self, shop_id):
        # Remove a shop from the database
        cursor = self.db_connection.cursor()
        cursor.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
        self.db_connection.commit()
        cursor.close()
        self.load_shop_locations()  # Refresh shop locations

    def setup_economy(self):
        # Setup economy integration using Vault
        registered_economy = self.getServer().getServicesManager().getRegistration(Economy)
        if registered_economy:
            self.economy = registered_economy.getProvider()
            self.getLogger().info("Vault economy provider found: {}".format(self.economy.getName()))
        else:
            self.economy = None
            self.getLogger().warning("No Vault economy provider found!")
        return self.economy

    def setup_permissions(self):
        # Setup permissions integration using LuckPerms
        try:
            self.luckperms = LuckPerms.getApi()
            self.getLogger().info("LuckPerms API found and enabled.")
        except Exception as e:
            self.getLogger().warning("LuckPerms API not found! Disabling LuckPerms integration.")
            self.luckperms = None

    def register_events(self):
        # Register event listeners with the plugin manager
        pm = self.getServer().getPluginManager()
        pm.registerEvents(self, self)

    def setup_placeholder_api(self):
        # Setup PlaceholderAPI integration
        PlaceholderAPI.registerPlaceholder("shop_balance", self.get_shop_balance)

    def get_shop_balance(self, player):
        # Return the player's shop balance
        return str(self.vault_unlocked_api.getBalance(player))

    def is_bedrock_player(self, player):
        # Check if a player is using a Bedrock client
        geyser_api = GeyserApi.api()
        if geyser_api is not None and geyser_api.isBedrockPlayer(player):
            floodgate_api = FloodgateApi.api()
            if floodgate_api is not None and floodgate_api.isFloodgatePlayer(player.getUniqueId()):
                xuid = floodgate_api.getXuid(player.getUniqueId())
                return "Bedrock Player (Floodgate XUID: {})".format(xuid)
            return "Bedrock Player (Geyser)"
        return "Java Player"

    @EventHandler
    def onPlayerInteract(self, event):
        # Handle player interactions with blocks
        action = event.getAction()
        block = event.getClickedBlock()
        player = event.getPlayer()

        if action == PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK and block.getType() == self.shop_chest_material:
            if self.is_shop_chest(block):
                self.handle_shop_interaction(player, block)
            else:
                player.sendMessage(ChatColor.GRAY + "This is just a regular {}.".format(self.shop_chest_material.name().lower().replace('_', ' ')))

        elif action == PlayerInteractEvent.Action.LEFT_CLICK_BLOCK and block.getType() == self.shop_chest_material:
            if self.is_shop_chest(block):
                self.handle_shop_break_attempt(player, block)
            else:
                player.sendMessage(ChatColor.GRAY + "You left-clicked a regular {}.".format(self.shop_chest_material.name().lower().replace('_', ' ')))

    def is_shop_chest(self, block):
        # Check if a block is a shop chest
        if block.getType() == self.shop_chest_material:
            return True
        return False

    def handle_shop_interaction(self, player, chest_block):
        # Handle interactions with shop chests
        if self.is_bedrock_player(player):
            player.sendMessage(ChatColor.GREEN + self.is_bedrock_player(player))
        else:
            player.sendMessage(ChatColor.GREEN + "Java Player!")
        location = chest_block.getLocation()
        shops = self.get_shops()
        for shop in shops:
            if shop[2] == str(location):
                item = shop[3]
                price = shop[4]
                if self.economy.has(player, price):
                    try:
                        self.economy.withdrawPlayer(player, price)
                        # Give the item to the player
                        item_stack = ItemStack(Material.getMaterial(item), 1)  # Adjust quantity as needed
                        player.getInventory().addItem(item_stack)
                        player.sendMessage(ChatColor.GREEN + "You have purchased the item for ${}".format(price))
                    except Exception as e:
                        player.sendMessage(ChatColor.RED + "An error occurred during the transaction: {}".format(e.getMessage()))
                else:
                    player.sendMessage(ChatColor.RED + "You do not have enough money to purchase this item.")
                return
        player.sendMessage(ChatColor.RED + "No shop found at this location.")

    def handle_shop_break_attempt(self, player, chest_block):
        # Handle attempts to break shop chests
        player.sendMessage(ChatColor.RED + ChatColor.BOLD + "You cannot break shop chests directly!")
        player.sendMessage(ChatColor.RESET + ChatColor.GRAY + "Interact (right-click) to use the shop.")

    @EventHandler
    def onSignChange(self, event):
        # Handle sign change events
        sign = event.getSign()
        sign_text = sign.getLine(0)
        if sign_text == self.shop_identifier_sign_text:
            block_below = sign.getBlock().getRelative(0, -1, 0)
            if block_below.getType() == self.shop_chest_material:
                player = event.getPlayer()
                # Create the shop from the sign
                self.create_shop(player.getName(), str(block_below.getLocation()), "item_name", price, is_admin_shop=False)  # Define item_name and price accordingly
                player.sendMessage(ChatColor.GREEN + "Sign placed on shop.")

    @EventHandler
    def onBlockBreak(self, event):
        # Handle block break events
        block = event.getBlock()
        player = event.getPlayer()
        if block.getType() == self.shop_chest_material:
            event.setCancelled(True)
            player.sendMessage(ChatColor.RED + ChatColor.BOLD + "You cannot break shop chests!")
            player.sendMessage(ChatColor.RESET + ChatColor.GRAY + "Use /removeshop to remove a shop.")

    def onCommand(self, sender, command, label, args):
        # Handle commands issued by players
        if command.getName().lower() == "createshop":
            return self.handle_createshop_command(sender, args)  # Call handler for /createshop command
        elif command.getName().lower() == "removeshop":
            return self.handle_removeshop_command(sender, args)  # Call handler for /removeshop command
        elif command.getName().lower() == "shopinfo":
            return self.handle_shopinfo_command(sender, args)  # Call handler for /shopinfo command
        elif command.getName().lower() == "setprice":
            return self.handle_setprice_command(sender, args)  # Call handler for /setprice command
        elif command.getName().lower() == "shopgui":
            return self.handle_shopgui_command(sender, args)  # Call handler for /shopgui command
        elif command.getName().lower() == "buy":
            return self.handle_buy_command(sender, args)  # Call handler for /buy command
        elif command.getName().lower() == "createadminshop":
            return self.handle_createadminshop_command(sender, args)  # Call handler for /createadminshop command
        return False  # Return false if command is not handled

    def handle_createshop_command(self, sender, args):
        """Handles the /createshop command."""
        if not isinstance(sender, Player):
            sender.sendMessage(ChatColor.RED + "This command can only be used by players.")
            return

        if not sender.hasPermission("chestshop.create"):
            sender.sendMessage(ChatColor.translateAlternateColorCodes('&', self.message_no_permission))
            return

        if len(args) != 2:
            sender.sendMessage(ChatColor.translateAlternateColorCodes('&', self.message_invalid_arguments).replace("{usage}", "/createshop <item> <price>"))
            return

        item_name = args[0]
        try:
            price = float(args[1])
        except ValueError:
            sender.sendMessage(ChatColor.RED + "Invalid price: {}".format(args[1]))
            return

        # Check if the player is creating an admin shop
        is_admin_shop = sender.hasPermission("chestshop.admin")

        # Check if admin shops are allowed
        if is_admin_shop and not self.allow_admin_shops:
            sender.sendMessage(ChatColor.translateAlternateColorCodes('&', self.message_no_permission))
            return

        # Get the block the player is looking at
        target_block = sender.getTargetBlock(None, 5)
        if target_block is None or target_block.getType() != Material.CHEST:
            sender.sendMessage(ChatColor.translateAlternateColorCodes('&', self.message_no_permission))
            return

        location = target_block.getLocation()

        # Check if a shop already exists at this location
        if self.is_shop_location(location):
            sender.sendMessage(ChatColor.translateAlternateColorCodes('&', self.message_no_permission))
            return

        # Check if the player is in a valid town
        if not self.is_in_valid_town(sender):
            sender.sendMessage(ChatColor.RED + "You must be in a valid town to create a shop.")
            return

        # Create the shop
        if is_admin_shop:
            owner = None  # No owner for admin shops
            sender.sendMessage(ChatColor.translateAlternateColorCodes('&', self.message_admin_shop_created).replace("{item}", item_name))
        else:
            owner = sender.getName()
            sender.sendMessage(ChatColor.translateAlternateColorCodes('&', self.message_shop_created).replace("{item}", item_name))

        self.create_shop(owner, location, item_name, price, is_admin_shop)

    def create_shop(self, owner, location, item, price, is_admin_shop):
        # Add the shop to the database
        cursor = self.db_connection.cursor()
        cursor.execute("INSERT INTO shops (owner, location, item, price, is_admin_shop) VALUES (?, ?, ?, ?, ?)",
                       (owner, str(location), item, price, is_admin_shop))
        self.db_connection.commit()

        # Add the shop location to the cache
        self.shop_locations.add(location)

        self.getLogger().info("Shop created at {}".format(location))

    def is_shop_location(self, location):
        return location in self.shop_locations

    def handle_shopinfo_command(self, sender, args):
        """Handles the /shopinfo command."""
        if not isinstance(sender, Player):  # Command can only be used by players
            sender.sendMessage(ChatColor.RED + "This command can only be used by players in-game.")
            return True

        player = sender
        block = player.getTargetBlock(None, 5)  # Get the block the player is looking at

        if block.getType() != self.shop_chest_material:
            player.sendMessage(ChatColor.RED + "You must be looking at a chest to get shop info.")
            return True

        location = block.getLocation()  # Get the location of the chest
        shops = self.get_shops()  # Retrieve all shops from the database
        for shop in shops:
            if shop[2] == str(location):  # Check if location matches
                player.sendMessage(ChatColor.GREEN + "Shop found: Owner: {}, Item: {}, Price: {}".format(shop[1], shop[3], shop[4]))
                return True  # Shop found and info sent

        player.sendMessage(ChatColor.RED + "No shop found at this location.")
        return True  # Command handled successfully

    def handle_removeshop_command(self, sender, args):   
        """Handles the /removeshop command."""
        if not isinstance(sender, Player):  # Command can only be used by players
            sender.sendMessage(ChatColor.RED + "This command can only be used by players in-game.")
            return True

        player = sender
        if not self.luckperms.getUserManager().getUser(player.getUniqueId()).getCachedData().getPermissionData().checkPermission("simplechestshop.removeshop"):
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', self.message_no_permission))
            return True

        target_block = player.getTargetBlock(None, 5)  # Get the block the player is looking at
        if not target_block or target_block.getType() != self.shop_chest_material:
            player.sendMessage(ChatColor.RED + "You must be looking at a shop chest to use /removeshop.")
            return True

        location = target_block.getLocation()  # Get the location of the chest
        shops = self.get_shops()  # Retrieve all shops from the database
        for shop in shops:
            if shop[2] == str(location):  # Check if location matches
                if shop[1] == player.getName() or self.allow_admin_shops:  # Check if player owns the shop or is an admin
                    self.remove_shop(shop[0])  # Remove shop from the database
                    player.sendMessage(ChatColor.GREEN + "Shop removed at this location.")
                    return True  # Shop removed successfully
                else:
                    player.sendMessage(ChatColor.RED + "You do not own this shop.")
                    return True  # Player doesn't own the shop

        player.sendMessage(ChatColor.RED + "No shop found at this location.")
        return True  # Command handled successfully
    
    def handle_setprice_command(self, sender, args):
        """Handles the /setprice command."""
        if not isinstance(sender, Player):  # Command can only be used by players
            sender.sendMessage(ChatColor.translateAlternateColorCodes('&', self.message_no_permission))
            return True

        player = sender
        if not self.luckperms.getUserManager().getUser(player.getUniqueId()).getCachedData().getPermissionData().checkPermission("simplechestshop.setprice"):
            sender.sendMessage(ChatColor.translateAlternateColorCodes('&', self.message_no_permission))
            return True
        
        if len(args) < 2:
            player.sendMessage(ChatColor.translateAlternateColorCodes('&', self.message_invalid_arguments).replace("{usage}", "/setprice <location> <new_price>"))
            return True
    
        location = args[0]  # Get location from command arguments
        new_price = float(args[1])  # Get new price from command arguments
        shops = self.get_shops()  # Retrieve all shops from the database
        for shop in shops:
            if shop[2] == location:
                self.remove_shop(shop[0])  # Remove old shop entry
                self.add_shop(shop[1], location, shop[3], new_price)  # Add shop with new price
                
                player.sendMessage(ChatColor.GREEN + "Price updated for shop at {}: New Price: {}".format(location, new_price))
                return True  # Command handled successfully
        player.sendMessage(ChatColor.RED + "No shop found at that location.")
        return True  # Command handled successfully

    def handle_buy_command(self, sender, args):
        if not isinstance(sender, Player):
            sender.sendMessage(ChatColor.RED + "This command can only be used by players.")
            return

        if len(args) != 1:
            sender.sendMessage(ChatColor.RED + "Usage: /buy <item>")
            return

        item_name = args[0]

        # Find the shop with the specified item
        shops = self.get_shops()
        for shop in shops:
            if shop[3] == item_name:
                # Purchase the item
                player = sender
                location = shop[2]
                price = shop[4]
                if self.economy.has(player, price):
                    try:
                        self.economy.withdrawPlayer(player, price)
                        # Give the item to the player
                        item_stack = ItemStack(Material.getMaterial(item_name), 1)  # Adjust quantity as needed
                        player.getInventory().addItem(item_stack)
                        player.sendMessage(ChatColor.GREEN + "You have purchased the item for ${}".format(price))
                    except Exception as e:
                        player.sendMessage(ChatColor.RED + "An error occurred during the transaction: {}".format(e.getMessage()))
                else:
                    player.sendMessage(ChatColor.RED + "You do not have enough money to purchase this item.")
                return
        sender.sendMessage(ChatColor.RED + "No shop found with item {}".format(item_name))

    def handle_createadminshop_command(self, sender, args):
        if not isinstance(sender, Player):
            sender.sendMessage(ChatColor.RED + "This command can only be used by players.")
            return

        if not sender.hasPermission("chestshop.admin"):
            sender.sendMessage(ChatColor.RED + "You do not have permission to create admin shops.")
            return

        if len(args) != 2:
            sender.sendMessage(ChatColor.RED + "Usage: /createadminshop <item> <price>")
            return

        item_name = args[0]
        try:
            price = float(args[1])
        except ValueError:
            sender.sendMessage(ChatColor.RED + "Invalid price: {}".format(args[1]))
            return

        # Get the block the player is looking at
        target_block = sender.getTargetBlock(None, 5)
        if target_block is None or target_block.getType() != Material.CHEST:
            sender.sendMessage(ChatColor.RED + "You must be looking at a chest to create an admin shop.")
            return

        location = target_block.getLocation()

        # Check if a shop already exists at this location
        if self.is_shop_location(location):
            sender.sendMessage(ChatColor.RED + "A shop already exists at this location.")
            return

        # Create the admin shop
        self.create_shop(None, location, item_name, price, True)
        sender.sendMessage(ChatColor.GREEN + "Admin shop created at this location.")

    def is_in_valid_town(self, player):
        if not self.enable_towny_integration:
            return True  # Towny integration is disabled, so all players are considered in a valid town

        # Get the Towny player object
        towny_player = TownyUniverse.getPlayer(player.getName())
        if towny_player.hasTown():
            return True  # Player is in a valid town
        return False  # Player is not in a town

    def open_shop_gui(self, player):
        # Calculate the number of rows based on gui_size
        num_rows = self.gui_size / 9
        if not (num_rows in range(1, 7)):
            self.getLogger().warning("Invalid gui_size in config.yml. Must be a multiple of 9 between 9 and 54. Defaulting to 27.")
            self.gui_size = 27

        # Create a new inventory with the configured size
        inventory = Bukkit.createInventory(None, self.gui_size, ChatColor.translateAlternateColorCodes('&', self.gui_title))

        # Add default items to the inventory
        if self.default_items:
            for slot, item_name in self.default_items.items():
                material = Material.getMaterial(item_name)
                if material:
                    item_stack = ItemStack(material, 1)
                    inventory.setItem(int(slot), item_stack)

        # Open the inventory for the player
        player.openInventory(inventory)

    @EventHandler
    def on_inventory_click(self, event):
        if event.getInventory().getName() == ChatColor.translateAlternateColorCodes('&', self.gui_title):
            event.setCancelled(True)  # Prevent players from taking items
            player = event.getWhoClicked()
            clicked_item = event.getCurrentItem()
            if clicked_item is not None and clicked_item.getType() == Material.DIAMOND:
                # Perform the purchase
                player.sendMessage(ChatColor.GREEN + "You clicked on a diamond!")

    @EventHandler
    def on_inventory_close(self, event):
        if event.getInventory().getName() == ChatColor.translateAlternateColorCodes('&', self.gui_title):
            player = event.getPlayer()
            inventory = event.getInventory()

            # Gather items from the inventory
            for slot in range(inventory.getSize()):
                item_stack = inventory.getItem(slot)
                if item_stack is not None:
                    material_name = item_stack.getType().name()
                    # Save the item configuration to the database
                    self.save_item_to_database(slot, material_name)

    def save_item_to_database(self, slot, material_name):
        cursor = self.db_connection.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO gui_items (slot, material_name)
            VALUES (?, ?)
        ''', (slot, material_name))
        self.db_connection.commit()
        cursor.close()

    def handle_shopgui_command(self, sender, args):
        """Handles the /shopgui command."""
        if not isinstance(sender, Player):  # Command can only be used by players
            sender.sendMessage(ChatColor.RED + "This command can only be used by players in-game.")
            return True

        player = sender
        self.open_shop_gui(player)
        return True  # Command handled successfully
