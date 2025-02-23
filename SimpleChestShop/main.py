import os
import java.net.HttpURLConnection as HttpURLConnection
import java.net.URL as URL
import java.io.BufferedReader as BufferedReader
import java.io.InputStreamReader as InputStreamReader
import java.sql.Connection as Connection
from java.sql import DriverManager, SQLException
from java.util.logging import Logger

# Bukkit API imports
from org.bukkit.plugin.java import JavaPlugin
from org.bukkit import Material
from org.bukkit.block import Sign
from org.bukkit.entity import Player
from org.bukkit.event import Listener  # Listener is needed
from org.bukkit.inventory import ItemStack
from org.bukkit import Bukkit
from org.bukkit.event.player import PlayerInteractEvent
from org.bukkit.event.block import BlockBreakEvent
from org.bukkit.event.block import SignChangeEvent
from org.bukkit.command import CommandSender, CommandExecutor  # Corrected import
from org.bukkit import ChatColor
from org.bukkit.plugin import RegisteredServiceProvider
from org.bukkit.block import Chest, BlockFace  # Import BlockFace
from org.bukkit import GameMode
from org.bukkit.event.player import AsyncPlayerChatEvent  # For chat listener

# Pyspigot Configuration Manager
# from pyspigot import ConfigurationManager # Already imported as ps

# LuckPerms
try:
    from net.luckperms.api import LuckPerms
    has_luckperms = True
except ImportError:
    has_luckperms = False
    LuckPerms = None
    print "[ChestShop] LuckPerms not found. Disabling LuckPerms integration."  # Correct Python 2 print

# Third-party imports
import pyspigot as ps

# Vault Imports
Economy = None
Permission = None
Chat = None

try:
    from net.milkbowl.vault2.economy import Economy
    from net.milkbowl.vault2.permission import Permission
    from net.milkbowl.vault2.chat import Chat
    has_vault = True
except ImportError:
    has_vault = False
    print "[ChestShop] Vault not found. Disabling Economy, Permission and Chat integration."  # Correct Python 2 print

from com.palmergames.bukkit.towny import TownyUniverse
# from net.milkbowl.vaultunlocked.api import VaultUnlockedAPI # If you use it

CONFIG_FILE = "config.yml"
SHOP_CHEST_MATERIAL_CONFIG_KEY = "shop_chest_material"
SHOP_IDENTIFIER_SIGN_TEXT_CONFIG_KEY = "shop_identifier_sign_text"

DEFAULT_SHOP_CHEST_MATERIAL = "CHEST"
DEFAULT_SHOP_IDENTIFIER_SIGN_TEXT = "[Shop]"

class ChestShop(JavaPlugin, Listener):  # Correctly implements Listener

    def __init__(self):
        super(ChestShop, self).__init__()
        self.config_manager = ps.ConfigurationManager(self)  # Use ps.ConfigurationManager
        self.db_connection = None
        self.shop_chest_material = None
        self.shop_identifier_sign_text = None
        self.shop_locations = set()  # Set to store shop locations
        self.economy = None
        self.permission = None  # Will hold the Vault Permission provider
        self.chat = None
        self.luckperms = None
        self.allow_admin_shops = False
        self.message_shop_created = "&aShop created for {item}"
        self.message_admin_shop_created = "&aAdmin shop created for {item}"
        self.message_no_permission = "&cYou do not have permission to perform this action."
        self.message_invalid_arguments = "&cInvalid arguments. Usage: {usage}"
        self.currency_symbol = "$"
        self.enable_towny_integration = True
        self.enable_luckperms_integration = True
        self.enable_geyser_integration = True  # Keep these flags for config if you want.
        self.enable_floodgate_integration = True  # But the actual API calls are removed.
        self.logger = self.getLogger()  # Get the plugin's logger
        self.pending_price_settings = {} #For price setting

    def onEnable(self):
        super(ChestShop, self).onEnable() # Call super
        self.load_plugin_config()
        self.setup_database()
        self.load_shop_locations()
        self.setup_economy()
        self.setup_permissions()  # Get Vault Permission provider

        # Register event listeners *correctly*
        pm = self.getServer().getPluginManager()
        pm.registerEvents(self, self)  # Register THIS class as the listener

        # Register commands
        self.getCommand("createshop").setExecutor(CreateShopCommand(self))  # Pass the plugin instance
        self.getCommand("shopinfo").setExecutor(ShopInfoCommand(self)) #Pass plugin instance
        self.getCommand("removeshop").setExecutor(RemoveShopCommand(self)) #Pass plugin instance

        self.vault_unlocked_api = VaultUnlockedAPI()
        self.logger.info("ChestShop plugin enabled.")

    def onDisable(self):
        if self.db_connection:
            self.db_connection.close()
        self.logger.info("ChestShop plugin disabled.")

    def load_plugin_config(self):
        self.config_manager.load_config("config.yml")
        self.shop_chest_material = self.config_manager.get("shop_chest_material", "CHEST")
        self.shop_identifier_sign_text = self.config_manager.get("shop_identifier_sign_text", "[Shop]")
        self.allow_admin_shops = self.config_manager.get("allow_admin_shops", False)
        self.message_shop_created = self.config_manager.get("message_shop_created", "&aShop created for {item}")
        self.message_admin_shop_created = self.config_manager.get("message_admin_shop_created", "&aAdmin shop created for {item}")
        self.message_no_permission = self.config_manager.get("message_no_permission", "&cYou do not have permission to perform this action.")
        self.message_invalid_arguments = self.config_manager.get("message_invalid_arguments", "&cInvalid arguments. Usage: {usage}")
        self.currency_symbol = self.config_manager.get("currency_symbol", "$")
        self.enable_towny_integration = self.config_manager.get("enable_towny_integration", True)
        self.enable_luckperms_integration = self.config_manager.get("enable_luckperms_integration", True)
        self.enable_geyser_integration = self.config_manager.get("enable_geyser_integration", True)
        self.enable_floodgate_integration = self.config_manager.get("enable_floodgate_integration", True)
        self.logger.info("Configuration loaded from '{}'".format(CONFIG_FILE))
        self.logger.info("Shop chest material: '{}'".format(self.shop_chest_material))
        self.logger.info("Shop identifier sign text: '{}'".format(self.shop_identifier_sign_text))

    def save_plugin_config(self):
        self.config_manager.set("shop_chest_material", self.shop_chest_material)
        self.config_manager.set("shop_identifier_sign_text", self.shop_identifier_sign_text)
        self.config_manager.set("allow_admin_shops", self.allow_admin_shops)
        self.config_manager.save_config("config.yml")
        self.logger.info("Configuration saved to '{}'".format(CONFIG_FILE))

    def setup_database(self):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:E:/1.19.4/plugins/PySpigot/scripts/database.db")  # Use a consistent path
            statement = self.db_connection.createStatement()
            create_table_sql = "CREATE TABLE IF NOT EXISTS shops (id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT, location TEXT UNIQUE, item TEXT, price REAL, is_admin_shop INTEGER)"
            statement.executeUpdate(create_table_sql)
            create_table_sql = "CREATE TABLE IF NOT EXISTS gui_items (slot INTEGER PRIMARY KEY, material_name TEXT)"  # If you use this
            statement.executeUpdate(create_table_sql)
            self.db_connection.close()
            self.logger.info("Database and tables created successfully.")
        except SQLException, e:
            self.logger.severe("An error occurred setting up the database: {}".format(e.getMessage()))

    def load_shop_locations(self):
        self.shop_locations.clear()
        shops = self.get_shops()
        for shop in shops:
            self.shop_locations.add(shop[2])

    def get_shops(self):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:E:/1.19.4/plugins/PySpigot/scripts/database.db")
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT id, owner, location, item, price, is_admin_shop FROM shops")
            shops = cursor.fetchall()
            cursor.close()
            return shops
        except SQLException, e:
            self.logger.severe("SQL error: {}".format(e.getMessage()))
            return [] # Return an empty list on error
        finally:
            if self.db_connection:
                try:
                    self.db_connection.close()
                except SQLException, e:
                    self.logger.severe("Failed to close database connection: {}".format(e.getMessage()))

    def add_shop(self, owner, location, item, price, is_admin_shop):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:E:/1.19.4/plugins/PySpigot/scripts/database.db")
            cursor = self.db_connection.cursor()
            cursor.execute("INSERT INTO shops (owner, location, item, price, is_admin_shop) VALUES (?, ?, ?, ?, ?)", (owner, str(location), item, price, is_admin_shop))
            self.db_connection.commit()
            cursor.close()
            self.load_shop_locations()  # Reload shop locations after adding
        except SQLException, e:
            self.logger.severe("SQL error creating shop: {}".format(e.getMessage()))
        finally:
            if self.db_connection:
                try:
                    self.db_connection.close()
                except SQLException, e:
                    self.logger.severe("Failed to close database connection: {}".format(e.getMessage()))

    def remove_shop(self, shop_id):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:E:/1.19.4/plugins/PySpigot/scripts/database.db")
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
            self.db_connection.commit()
            cursor.close()
            self.load_shop_locations()  # Reload shop locations after removing
        except SQLException, e:
            self.logger.severe("SQL error removing shop: {}".format(e.getMessage()))
        finally:
            if self.db_connection:
                try:
                    self.db_connection.close()
                except SQLException, e:
                    self.logger.severe("Failed to close database connection: {}".format(e.getMessage()))

    def setup_economy(self):
        if not has_vault:
            self.economy = None
            self.logger.warning("Vault economy provider not enabled due to import failure!")
            return

        registered_economy = self.getServer().getServicesManager().getRegistration(Economy)
        if registered_economy:
            self.economy = registered_economy.getProvider()
            self.logger.info("Vault economy provider found: {}".format(self.economy.getName()))
        else:
            self.economy = None
            self.logger.warning("No Vault economy provider found!")

    def setup_permissions(self):
        if has_luckperms:
            try:
                self.luckperms = LuckPerms.getApi()
                self.logger.info("LuckPerms API found and enabled.")
            except Exception, e:
                self.logger.warning("LuckPerms API not found! Disabling LuckPerms integration. Error: {}".format(e))
                self.luckperms = None
        elif has_vault:
            registered_permission = self.getServer().getServicesManager().getRegistration(Permission)
            if registered_permission:
                self.permission = registered_permission.getProvider()
                self.logger.info("Vault permission provider found: {}".format(self.permission.getName()))
            else:
                self.permission = None
                self.logger.warning("No Vault permission provider found!")
        else:
            self.logger.warning("No permission provider (LuckPerms or Vault) found!")


    def setup_placeholder_api(self):
        # PlaceholderAPI setup (if you actually use it)
        pass

    def get_shop_balance(self, player):
        # PlaceholderAPI method (if you actually use it)
        return "0.00"  # Placeholder

    def colorize(self, message):
        """Colorizes a message using Bukkit color codes."""
        return ChatColor.translateAlternateColorCodes('&', message)

    def has_permission(self, player, permission_node):
        """Checks if a player has a permission, using LuckPerms, Vault, or Bukkit."""
        if has_luckperms and self.luckperms:
            user = self.luckperms.getUserManager().getUser(player.getUniqueId())
            if user:
                return user.getCachedData().getPermissionData().checkPermission(permission_node).asBoolean()
            else:
                self.logger.warning("User not found in LuckPerms: {}".format(player.getName()))
                # Fallback to Vault or Bukkit permissions if LuckPerms user not found
        if self.permission and has_vault:
            return self.permission.has(player, permission_node)
        return player.hasPermission(permission_node)

    # No @EventHandler decorator!
    def onPlayerInteract(self, event):
        action = event.getAction()
        block = event.getClickedBlock()
        player = event.getPlayer()

        if action == PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK and block.getType() == self.shop_chest_material:
            if self.is_shop_chest(block):
                self.handle_shop_interaction(player, block)
            else:
                player.sendMessage(self.colorize( "&7This is just a regular {}.".format(self.shop_chest_material.name().lower().replace('_', ' '))))

        elif action == PlayerInteractEvent.Action.LEFT_CLICK_BLOCK and block.getType() == self.shop_chest_material:
            if self.is_shop_chest(block):
                self.handle_shop_break_attempt(player, block)
            else:
                player.sendMessage(self.colorize("&7You left-clicked a regular {}.".format(self.shop_chest_material.name().lower().replace('_', ' '))))

    def is_shop_chest(self, block):
        # Check for adjacent sign with correct text
        for face in [BlockFace.NORTH, BlockFace.EAST, BlockFace.SOUTH, BlockFace.WEST]:
            relative_block = block.getRelative(face)
            if relative_block.getType() == Material.SIGN or relative_block.getType() == Material.WALL_SIGN:
                sign = relative_block.getState()
                if sign.getLine(0) == self.shop_identifier_sign_text:
                    return True
        return False

    def handle_shop_interaction(self, player, chest_block):
        location = chest_block.getLocation()
        shops = self.get_shops()
        for shop in shops:
            if shop[2] == str(location):
                item = shop[3]
                price = shop[4]
                if self.economy and has_vault:
                    if self.economy.has(player, price):
                        try:
                            result = self.economy.withdrawPlayer(player, price)
                            if result.transactionSuccess():
                                item_stack = ItemStack(Material.getMaterial(item), 1)
                                overflow = player.getInventory().addItem(item_stack)  # Handle inventory overflow
                                if overflow and not overflow.isEmpty():
                                    for item in overflow.values():
                                        player.getWorld().dropItem(player.getLocation(), item)
                                    player.sendMessage(self.colorize("&cYour inventory is full! Some items were dropped.")) #Customizable Vault error message
                                player.sendMessage(self.colorize("&aYou have purchased the item for ${}".format(price))) #Customizable Vault error message
                            else:
                                player.sendMessage(self.colorize("&cVault Error: {}".format(result.errorMessage))) #Customizable Vault error message
                                self.logger.warning("Vault transaction failed for {}: {}".format(player.getName(), result.errorMessage)) #Customizable Vault error message
                        except Exception, e:
                            player.sendMessage(self.colorize("&cAn error occurred during the transaction: {}".format(e.getMessage()))) #Customizable Vault error message
                            self.logger.severe("An error occurred during the transaction for {}: {}".format(player.getName(), e.getMessage())) #Customizable Vault error message
                    else:
                        player.sendMessage(self.colorize("&cYou do not have enough money to purchase this item.")) #Customizable Vault error message
                elif not has_vault:
                    player.sendMessage(self.colorize("&cVault is not installed on this server!")) #Customizable Vault error message
                    self.logger.warning("handle_shop_interaction called without Vault!")
                    return
                return
        player.sendMessage(self.colorize("&cNo shop found at this location."))

    def handle_shop_break_attempt(self, player, chest_block):
        player.sendMessage(self.colorize("&c&lYou cannot break shop chests directly!"))
        player.sendMessage(self.colorize("&7Interact (right-click) to use the shop."))

    # No @EventHandler decorator!
    def onSignChange(self, event):
        player = event.getPlayer()
        sign = event.getSign()
        sign_text = event.getLine(0)

        if sign_text != self.shop_identifier_sign_text:
            return

        block_below = sign.getBlock().getRelative(BlockFace.DOWN)
        if block_below.getType() != self.shop_chest_material:
            player.sendMessage(self.colorize("&cYou must place the sign directly on a chest."))
            event.setCancelled(True)
            return

        if not self.has_permission(player, "chestshop.create"):
            player.sendMessage(self.colorize(self.message_no_permission))
            event.setCancelled(True)
            return

        chest = block_below.getState()
        if not isinstance(chest, Chest):  # Ensure it's a Chest
            player.sendMessage(self.colorize("&cYou must place the sign on a chest."))
            event.setCancelled(True)
            return

        inventory = chest.getInventory()
        item_stack = inventory.getItem(0)  # Get the first item (slot 0)

        if item_stack is None:
            player.sendMessage
