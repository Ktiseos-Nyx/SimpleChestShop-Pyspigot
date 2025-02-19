# coding=utf-8
import os  # Standard library imports FIRST
import pyspigot as ps  # Correct pyspigot import
import sqlite3  # Import SQLite module

# Third-party plugin API imports (Vault, Towny)
from net.milkbowl.vault2.economy import Economy  # CORRECT Vault import (note 'vault2')
from com.palmergames.bukkit.towny import TownyUniverse # Towny API

from org.bukkit.plugin.java import JavaPlugin
from org.bukkit.event import Listener
from org.bukkit.event import EventHandler
from org.bukkit.event.player import PlayerInteractEvent
from org.bukkit.event.block import BlockBreakEvent
from org.bukkit import Material
from org.bukkit.block import Block
from org.bukkit.entity import Player
from org.bukkit.inventory import ItemStack
from org.bukkit.inventory.meta import ItemMeta
from org.bukkit.ChatColor import ChatColor
from org.bukkit import Location
from org.bukkit.block import Sign
from org.bukkit.command import Command # Import Command and CommandSender for command handling
from org.bukkit.command import CommandSender

# Yaml Config
import ruamel.yaml as yaml

# LuckPerms
from net.luckperms.api import LuckPerms

CONFIG_FILE = "config.yml"
SHOP_CHEST_MATERIAL_CONFIG_KEY = "shop_chest_material"
SHOP_IDENTIFIER_SIGN_TEXT_CONFIG_KEY = "shop_identifier_sign_text"
DEFAULT_SHOP_CHEST_MATERIAL = Material.CHEST
DEFAULT_SHOP_IDENTIFIER_SIGN_TEXT = "[Shop]"

class ChestShop(JavaPlugin, Listener):

    def onEnable(self):
        self.initialize_database()  # Initialize the database
        self.load_plugin_config()
        self.getServer().getPluginManager().registerEvents(self, self)
        self.getLogger().info("SimpleChestShop plugin enabled!")
        self.shop_locations = set()  # Placeholder: Keep track of shop chest locations (not persistent yet)
        self.load_shop_locations()  # Load saved shop locations

        # --- Vault Economy Setup (Placeholder - Basic Initialization) ---
        self.economy = self.setup_economy()  # Try to setup Vault economy
        if self.economy:
            self.getLogger().info("Vault economy integration enabled (placeholder - not fully functional yet).")
        else:
            self.getLogger().warning("Vault economy provider not found. Economy features will be disabled.")

        # --- LuckPerms Setup ---
        self.luckperms = LuckPerms.getApi()

    # Initialize SQLite database
    def initialize_database(self):
        self.db_connection = sqlite3.connect('shops.db')  # Connect to SQLite database (creates if not exists)
        cursor = self.db_connection.cursor()
        # Create shops table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shops (
                id INTEGER PRIMARY KEY,
                owner TEXT,
                location TEXT,
                item TEXT,
                price REAL
            )
        ''')
        self.db_connection.commit()  # Commit changes
        cursor.close()

    # Method to add a shop
    def add_shop(self, owner, location, item, price):
        cursor = self.db_connection.cursor()
        cursor.execute('''
            INSERT INTO shops (owner, location, item, price)
            VALUES (?, ?, ?, ?)
        ''', (owner, location, item, price))
        self.db_connection.commit()
        cursor.close()

    # Method to retrieve all shops
    def get_shops(self):
        cursor = self.db_connection.cursor()
        cursor.execute('SELECT * FROM shops')
        shops = cursor.fetchall()
        cursor.close()
        return shops

    # Method to remove a shop
    def remove_shop(self, shop_id):
        cursor = self.db_connection.cursor()
        cursor.execute('DELETE FROM shops WHERE id = ?', (shop_id,))
        self.db_connection.commit()
        cursor.close()

    def onDisable(self):
        self.save_shop_locations()
        self.getLogger().info("SimpleChestShop plugin disabled!")
        self.db_connection.close()  # Close the database connection

    def load_plugin_config(self):
        config_path = self.getDataFolder().getAbsolutePath() + "/" + CONFIG_FILE
        try:
            with open(config_path, 'r') as f:
                config = yaml.YAML().load(f)
                if not config:
                    config = {}
        except IOError:
            config = {}

        material_name = config.get(SHOP_CHEST_MATERIAL_CONFIG_KEY, DEFAULT_SHOP_CHEST_MATERIAL.name())
        try:
            self.shop_chest_material = Material.valueOf(material_name.upper())
        except ValueError:
            self.shop_chest_material = DEFAULT_SHOP_CHEST_MATERIAL
            self.getLogger().warning(
    "Invalid shop_chest_material in config: '{}'. Using default: '{}'".format(
        material_name, 
        DEFAULT_SHOP_CHEST_MATERIAL.name()
    )
)

        self.shop_identifier_sign_text = config.get(SHOP_IDENTIFIER_SIGN_TEXT_CONFIG_KEY, DEFAULT_SHOP_IDENTIFIER_SIGN_TEXT)

        self.config = config
        self.getLogger().info("Configuration loaded from '{}'".format(CONFIG_FILE))
        self.getLogger().info("Shop chest material: '{}'".format(self.shop_chest_material.name()))
        self.getLogger().info("Shop identifier sign text: '{}'".format(self.shop_identifier_sign_text))

    def save_config(self):
        config_path = self.getDataFolder().getAbsolutePath() + "/" + CONFIG_FILE
        with open(config_path, 'w') as f:
            yaml.YAML().dump(self.config, f)
        self.getLogger().info("Configuration saved to '{}'".format(CONFIG_FILE))

    def load_shop_locations(self):
        """Load shop locations from the database into the shop_locations set."""
        self.shop_locations.clear()  # Clear existing locations
        shops = self.get_shops()  # Retrieve all shops from the database
        for shop in shops:
            self.shop_locations.add(shop[2])  # Add the location to the set

    def save_shop_locations(self):
        """Save the current shop locations to the database."""
        for location in self.shop_locations:
            # Retrieve shop details for the location
            shops = self.get_shops()  # Get all shops from the database
            for shop in shops:
                if shop[2] == location:  # Check if the location matches
                    owner = shop[1]  # Owner of the shop
                    item = shop[3]  # Item being sold
                    price = shop[4]  # Price of the item
                    
                    # Add or update the shop in the database
                    self.add_shop(owner, location, item, price)  # Save each location
                    break  # Exit the inner loop after processing the shop

    def is_shop_chest(self, block):
        if block.getType() == self.shop_chest_material:
            return True
        return False

    @EventHandler
    def onPlayerInteract(self, event):
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

    def handle_shop_interaction(self, player, chest_block):
        location = chest_block.getLocation()
        # Check for attached sign
        sign_block = chest_block.getRelative(0, 1, 0)  # Get the block above the chest
        if sign_block.getType() == Material.SIGN:
            sign = sign_block.getState()  # Get the sign state
            sign_text = sign.getLine(0)  # Read the first line of the sign
            if sign_text == self.shop_identifier_sign_text:
                # Retrieve shop details from the database
                shops = self.get_shops()  # Get all shops from the database
                for shop in shops:
                    if shop[2] == str(location):  # Check if location matches
                        player.sendMessage(ChatColor.GREEN + "Shop found: Item: {}, Price: {}".format(shop[3], shop[4]))
                        return
                player.sendMessage(ChatColor.RED + "No shop found at this location.")
            else:
                player.sendMessage(ChatColor.RED + "This sign does not identify a shop.")
        else:
            player.sendMessage(ChatColor.RED + "No sign found above this chest.")

    def create_shop_from_sign(self, player, chest_block):
        sign_block = chest_block.getRelative(0, 1, 0)  # Get the block above the chest
        if sign_block.getType() == Material.SIGN:
            sign = sign_block.getState()  # Get the sign state
            item = sign.getLine(1)  # Read the second line for item
            price = float(sign.getLine(2))  # Read the third line for price
            owner = player.getName()  # Get the shop owner's name
            location = str(chest_block.getLocation())  # Get the location as string
            
            # Add shop to the database
            self.add_shop(owner, location, item, price)  # Save shop details
            player.sendMessage(ChatColor.GREEN + "Shop created: Item: {}, Price: {}".format(item, price))
        else:
            player.sendMessage(ChatColor.RED + "No sign found above this chest.")

    def handle_shop_break_attempt(self, player, chest_block):
        player.sendMessage(ChatColor.RED + ChatColor.BOLD + "You cannot break shop chests directly!")
        player.sendMessage(ChatColor.RESET + ChatColor.GRAY + "Interact (right-click) to use the shop.")

    @EventHandler
    def onSignChange(self, event):
        sign = event.getSign()
        sign_text = sign.getLine(0)
        if sign_text == self.shop_identifier_sign_text:
            block_below = sign.getBlock().getRelative(0, -1, 0)
            if block_below.getType() == self.shop_chest_material:
                player = event.getPlayer()
                self.create_shop_from_sign(player, block_below)

    @EventHandler
    def onBlockBreak(self, event):
        block = event.getBlock()
        player = event.getPlayer()
        if block.getType() == self.shop_chest_material:
            if self.is_shop_chest(block):
                event.setCancelled(True)
                player.sendMessage(ChatColor.RED + ChatColor.BOLD + "You cannot break shop chests!")
                player.sendMessage(ChatColor.RESET + ChatColor.GRAY + "Use /removeshop to remove a shop (command not yet implemented).")

    # --- Vault Economy Setup (Placeholder Function) ---
    def setup_economy(self):
        """Sets up Vault economy integration if Vault is available."""
        if self.getServer().getPluginManager().getPlugin("Vault") is None:
            return False
        rsp = self.getServer().getServicesManager().getRegistration(Economy)
        if rsp is None:
            return False
        self.getLogger().info("Vault Economy service found: {}".format(rsp.getProvider().getName())) # Log Vault provider
        return rsp.getProvider()

    # --- Command Handling for /removeshop ---
    def onCommand(self, sender, command, label, args):
        if command.getName().lower() == "removeshop":
            return self.handle_removeshop_command(sender, args) # Call handler for /removeshop command
        elif command.getName().lower() == "createshop":
            return self.handle_createshop_command(sender, args)  # Call handler for /createshop command
        elif command.getName().lower() == "listshops":
            return self.handle_listshops_command(sender, args)  # Call handler for /listshops command
        elif command.getName().lower() == "shopinfo":
            return self.handle_shopinfo_command(sender, args)  # Call handler for /shopinfo command
        elif command.getName().lower() == "setprice":
            return self.handle_setprice_command(sender, args)  # Call handler for /setprice command
        return False # Return false if command is not handled

    def handle_removeshop_command(self, sender, args):
        """Handles the /removeshop command."""
        if not isinstance(sender, Player):  # Command can only be used by players
            sender.sendMessage(ChatColor.RED + "This command can only be used by players in-game.")
            return True

        player = sender
        if not self.luckperms.getUserManager().getUser(player.getUniqueId()).getCachedData().getPermissionData().checkPermission("simplechestshop.remove"):
            player.sendMessage(ChatColor.RED + "You do not have permission to remove shops.")
            return True

        target_block = player.getTargetBlock(None, 5)  # Get block player is looking at within 5 blocks range

        if not target_block or target_block.getType() != self.shop_chest_material:
            player.sendMessage(ChatColor.RED + "You must be looking at a shop chest to use /removeshop.")
            return True

        location = str(target_block.getLocation())  # Get location as string
        shops = self.get_shops()  # Retrieve all shops from the database

        # Check if the shop exists in the database
        for shop in shops:
            if shop[2] == location:  # Check if location matches
                # Refund logic (placeholder)
                # Example: self.economy.depositPlayer(shop[1], shop[4])  # Refund money
                self.remove_shop(shop[0])  # Remove shop from the database
                player.sendMessage(ChatColor.GREEN + "Shop removed at location: " + str(target_block.getLocation()))
                return

        player.sendMessage(ChatColor.YELLOW + "The block you are looking at is not registered as a shop.")
        return True  # Command handled successfully

    def handle_createshop_command(self, sender, args):
        """Handles the /createshop command."""
        if not isinstance(sender, Player):  # Command can only be used by players
            sender.sendMessage(ChatColor.RED + "This command can only be used by players in-game.")
            return True

        player = sender
        if not self.luckperms.getUserManager().getUser(player.getUniqueId()).getCachedData().getPermissionData().checkPermission("simplechestshop.create"):
            player.sendMessage(ChatColor.RED + "You do not have permission to create a shop.")
            return True

        target_block = player.getTargetBlock(None, 5)  # Get block player is looking at within 5 blocks range

        if not target_block or target_block.getType() != self.shop_chest_material:
            player.sendMessage(ChatColor.RED + "You must be looking at a shop chest to use /createshop.")
            return True

        # Check Towny integration
        if not self.is_in_valid_town(player):
            player.sendMessage(ChatColor.RED + "You can only create shops in your town.")
            return True

        self.create_shop_from_sign(player, target_block)  # Create shop from sign
        return True  # Command handled successfully

    def handle_listshops_command(self, sender, args):
        """Handles the /listshops command."""
        if not isinstance(sender, Player):  # Command can only be used by players
            sender.sendMessage(ChatColor.RED + "This command can only be used by players in-game.")
            return True

        player = sender
        if not self.luckperms.getUserManager().getUser(player.getUniqueId()).getCachedData().getPermissionData().checkPermission("simplechestshop.list"):
            player.sendMessage(ChatColor.RED + "You do not have permission to list shops.")
            return True

        owner = player.getName()  # Get the player's name
        shops = self.get_shops()  # Retrieve all shops from the database
        player.sendMessage(ChatColor.GREEN + "Your Shops:")
        for shop in shops:
            if shop[1] == owner:  # Check if the shop belongs to the player
                player.sendMessage(ChatColor.YELLOW + "Shop at {}: Item: {}, Price: {}".format(shop[2], shop[3], shop[4]))
        return True  # Command handled successfully

    def handle_shopinfo_command(self, sender, args):
        """Handles the /shopinfo command."""
        if not isinstance(sender, Player):  # Command can only be used by players
            sender.sendMessage(ChatColor.RED + "This command can only be used by players in-game.")
            return True

        player = sender
        if not self.luckperms.getUserManager().getUser(player.getUniqueId()).getCachedData().getPermissionData().checkPermission("simplechestshop.info"):
            player.sendMessage(ChatColor.RED + "You do not have permission to view shop info.")
            return True

        if len(args) < 1:
            player.sendMessage(ChatColor.RED + "Usage: /shopinfo <location>")
            return True

        location = args[0]  # Get location from command arguments
        shops = self.get_shops()  # Retrieve all shops from the database
        for shop in shops:
            if shop[2] == location:
                player.sendMessage(ChatColor.GREEN + "Shop Info: Item: {}, Price: {}".format(shop[3], shop[4]))
                return
        player.sendMessage(ChatColor.RED + "No shop found at that location.")
        return True  # Command handled successfully

    def handle_setprice_command(self, sender, args):
        """Handles the /setprice command."""
        if not isinstance(sender, Player):  # Command can only be used by players
            sender.sendMessage(ChatColor.RED + "This command can only be used by players in-game.")
            return True

        player = sender
        if not self.luckperms.getUserManager().getUser(player.getUniqueId()).getCachedData().getPermissionData().checkPermission("simplechestshop.setprice"):
            player.sendMessage(ChatColor.RED + "You do not have permission to set prices.")
            return True

        if len(args) < 2:
            player.sendMessage(ChatColor.RED + "Usage: /setprice <location> <new_price>")
            return True

        location = args[0]  # Get location from command arguments
        new_price = float(args[1])  # Get new price from command arguments
        shops = self.get_shops()  # Retrieve all shops from the database
        for shop in shops:
            if shop[2] == location:
                self.remove_shop(shop[0])  # Remove old shop entry
                self.add_shop(shop[1], location, shop[3], new_price)  # Add shop with new price
                player.sendMessage(ChatColor.GREEN + "Price updated for shop at {}: New Price: {}".format(location, new_price))
                return
        player.sendMessage(ChatColor.RED + "No shop found at that location.")
        return True  # Command handled successfully

    def is_in_valid_town(self, player):
        # Get the Towny player object
        towny_player = TownyUniverse.getPlayer(player.getName())
        if towny_player is None:
            return False  # Player is not a Towny player

        # Check if the player is in a town
        if towny_player.hasTown():
            return True  # Player is in a valid town
        return False  # Player is not in a town
