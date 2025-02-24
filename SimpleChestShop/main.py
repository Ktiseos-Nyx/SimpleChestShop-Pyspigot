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

class AddShopItemCommand(CommandExecutor):
    def __init__(self, plugin):
        self.plugin = plugin

    def onCommand(self, sender, command, label, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.plugin.colorize("&cThis command can only be used by players."))
            return True

        if len(args) < 2:
            sender.sendMessage(self.plugin.colorize("&cUsage: /shopadd <item> <quantity>"))
            return True

        try:
            quantity = int(args[1])
            if quantity <= 0:
                raise ValueError
        except ValueError:
            sender.sendMessage(self.plugin.colorize("&cQuantity must be a positive integer."))
            return True

        target_block = sender.getTargetBlock(None, 5)
        if not target_block or target_block.getType() != self.plugin.shop_chest_material:
            sender.sendMessage(self.plugin.colorize("&cYou must be looking at a shop chest."))
            return True

        location = target_block.getLocation()
        shop = self.plugin.get_shop_by_location(str(location))
        if not shop:
            sender.sendMessage(self.plugin.colorize("&cNo shop found at this location."))
            return True

        if shop['owner'] != sender.getName() and not sender.hasPermission("chestshop.admin"):
            sender.sendMessage(self.plugin.colorize("&cYou can only modify your own shops."))
            return True

        self.plugin.add_items_to_shop(shop['id'], {args[0]: quantity})
        sender.sendMessage(self.plugin.colorize("&aAdded {} {} to your shop.".format(quantity, args[0])))
        return True

class RemoveShopItemCommand(CommandExecutor):
    def __init__(self, plugin):
        self.plugin = plugin

    def onCommand(self, sender, command, label, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.plugin.colorize("&cThis command can only be used by players."))
            return True

        if len(args) < 1:
            sender.sendMessage(self.plugin.colorize("&cUsage: /shopremove <item>"))
            return True

        target_block = sender.getTargetBlock(None, 5)
        if not target_block or target_block.getType() != self.plugin.shop_chest_material:
            sender.sendMessage(self.plugin.colorize("&cYou must be looking at a shop chest."))
            return True

        location = target_block.getLocation()
        shop = self.plugin.get_shop_by_location(str(location))
        if not shop:
            sender.sendMessage(self.plugin.colorize("&cNo shop found at this location."))
            return True

        if shop['owner'] != sender.getName() and not sender.hasPermission("chestshop.admin"):
            sender.sendMessage(self.plugin.colorize("&cYou can only modify your own shops."))
            return True

        self.plugin.remove_items_from_shop(shop['id'], args)
        sender.sendMessage(self.plugin.colorize("&aRemoved {} from your shop.".format(', '.join(args))))
        return True

class UpdateShopItemCommand(CommandExecutor):
    def __init__(self, plugin):
        self.plugin = plugin

    def onCommand(self, sender, command, label, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.plugin.colorize("&cThis command can only be used by players."))
            return True

        if len(args) < 3:
            sender.sendMessage(self.plugin.colorize("&cUsage: /shopupdate <item> <quantity> <price>"))
            return True

        try:
            quantity = int(args[1])
            price = float(args[2])
            if quantity <= 0 or price < 0:
                raise ValueError
        except ValueError:
            sender.sendMessage(self.plugin.colorize("&cQuantity must be a positive integer and price must be a non-negative number."))
            return True

        target_block = sender.getTargetBlock(None, 5)
        if not target_block or target_block.getType() != self.plugin.shop_chest_material:
            sender.sendMessage(self.plugin.colorize("&cYou must be looking at a shop chest."))
            return True

        location = target_block.getLocation()
        shop = self.plugin.get_shop_by_location(str(location))
        if not shop:
            sender.sendMessage(self.plugin.colorize("&cNo shop found at this location."))
            return True

        if shop['owner'] != sender.getName() and not sender.hasPermission("chestshop.admin"):
            sender.sendMessage(self.plugin.colorize("&cYou can only modify your own shops."))
            return True

        self.plugin.update_shop_items(shop['id'], {args[0]: (quantity, price)})
        sender.sendMessage(self.plugin.colorize("&aUpdated {} in your shop to quantity {} and price ${}.".format(args[0], quantity, price)))
        return True

class CreateShopCommand(CommandExecutor):
    def __init__(self, plugin):
        self.plugin = plugin

    def onCommand(self, sender, command, label, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.plugin.colorize("&cThis command can only be used by players."))
            return True

        if not self.plugin.has_permission(sender, "chestshop.create"):
            sender.sendMessage(self.plugin.colorize(self.plugin.message_no_permission))
            return True

        if len(args) != 2:
            sender.sendMessage(self.plugin.colorize("&cUsage: /createshop <item> <price>"))
            return True

        item = args[0]
        try:
            price = float(args[1])
        except ValueError:
            sender.sendMessage(self.plugin.colorize("&cInvalid price. Please enter a number."))
            return True

        target_block = sender.getTargetBlock(None, 5)
        if target_block is None or target_block.getType() != Material.CHEST:
            sender.sendMessage(self.plugin.colorize("&cYou must be looking at a chest to create a shop."))
            return True

        location = target_block.getLocation()
        self.plugin.create_shop(sender.getName(), str(location), {item: 1}, price, False)
        sender.sendMessage(self.plugin.colorize("&aShop created for {}".format(item)))
        return True

class ShopInfoCommand(CommandExecutor):
    def __init__(self, plugin):
        self.plugin = plugin

    def onCommand(self, sender, command, label, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.plugin.colorize("&cThis command can only be used by players."))
            return True

        target_block = sender.getTargetBlock(None, 5)
        if target_block is None or target_block.getType() != Material.CHEST:
            sender.sendMessage(self.plugin.colorize("&cYou must be looking at a chest to get shop info."))
            return True

        location = target_block.getLocation()
        shops = self.plugin.get_shops()
        for shop in shops:
            if shop[2] == str(location):
                sender.sendMessage(self.plugin.colorize("&aShop found: Owner: {}, Item: {}, Price: {}".format(shop[1], shop[3], shop[4])))
                sender.sendMessage(self.plugin.colorize("&aThis shop is owned by {} and is located at {}".format(shop[1], shop[2])))
                sender.sendMessage(self.plugin.colorize("&aShop ownership and location: {} - {}".format(shop[1], shop[2])))
                return True

        sender.sendMessage(self.plugin.colorize("&cNo shop found at this location."))
        return True

class RemoveShopCommand(CommandExecutor):
    def __init__(self, plugin):
        self.plugin = plugin

    def onCommand(self, sender, command, label, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.plugin.colorize("&cThis command can only be used by players."))
            return True

        if not self.plugin.has_permission(sender, "chestshop.removeshop"):
            sender.sendMessage(self.plugin.colorize(self.plugin.message_no_permission))
            return True

        target_block = sender.getTargetBlock(None, 5)
        if target_block is None or target_block.getType() != Material.CHEST:
            sender.sendMessage(self.plugin.colorize("&cYou must be looking at a shop chest to use /removeshop."))
            return True

        location = target_block.getLocation()
        shops = self.plugin.get_shops()
        for shop in shops:
            if shop[2] == str(location):
                if shop[1] == sender.getName() or self.plugin.allow_admin_shops:
                    self.plugin.remove_shop(shop[0])
                    sender.sendMessage(self.plugin.colorize("&aShop removed successfully."))
                    return True
                else:
                    sender.sendMessage(self.plugin.colorize("&cYou do not own this shop."))
                    return True

        sender.sendMessage(self.plugin.colorize("&cNo shop found at this location."))
        return True

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

        # New command registrations
        self.getCommand("shopadd").setExecutor(AddShopItemCommand(self))
        self.getCommand("shopremove").setExecutor(RemoveShopItemCommand(self))
        self.getCommand("shopupdate").setExecutor(UpdateShopItemCommand(self))
        self.getCommand("createshop").setExecutor(CreateShopCommand(self))
        self.getCommand("shopinfo").setExecutor(ShopInfoCommand(self))
        self.getCommand("removeshop").setExecutor(RemoveShopCommand(self))

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
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:plugins/PySpigot/scripts/SimpleChestShop/database.db")
            statement = self.db_connection.createStatement()
            
            # Create shops table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS shops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT,
                location TEXT UNIQUE,
                is_admin_shop INTEGER
            )
            """
            statement.executeUpdate(create_table_sql)
            
            # Create shop_items table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS shop_items (
                shop_id INTEGER,
                item TEXT,
                quantity INTEGER,
                price REAL,
                FOREIGN KEY(shop_id) REFERENCES shops(id)
            )
            """
            statement.executeUpdate(create_table_sql)
            
            self.db_connection.close()
            self.logger.info("Database and tables created successfully.")
        except SQLException, e:
            self.logger.severe("An error occurred setting up the database: {}".format(e.getMessage()))

    def with_database_connection(self, func, *args, **kwargs):
    try:
        self.db_connection = DriverManager.getConnection("jdbc:sqlite:plugins/PySpigot/scripts/SimpleChestShop/database.db")
        return func(self.db_connection, *args, **kwargs)
    except SQLException as e:
        self.logger.severe("SQL error: {}".format(e.getMessage()))
    finally:
        if self.db_connection:
            try:
                self.db_connection.close()
            except SQLException as e:
                self.logger.severe("Failed to close database connection: {}".format(e.getMessage()))

    def load_shop_locations(self):
        self.shop_locations.clear()
        shops = self.get_shops()
        for shop in shops:
            self.shop_locations.add(shop[2])

    def with_database_connection(self, func, *args, **kwargs):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:plugins/PySpigot/scripts/SimpleChestShop/database.db")
            return func(self.db_connection, *args, **kwargs)
        except SQLException as e:
            self.logger.severe("SQL error: {}".format(e.getMessage()))
        finally:
            if self.db_connection:
                try:
                    self.db_connection.close()
                except SQLException as e:
                    self.logger.severe("Failed to close database connection: {}".format(e.getMessage()))

    def get_shops(self):
        return self.with_database_connection(self._get_shops)

    def _get_shops(self, db_connection):
        try:
            cursor = db_connection.cursor()
            cursor.execute("SELECT id, owner, location, is_admin_shop FROM shops")
            shops = cursor.fetchall()
            cursor.close()
            return shops
        except SQLException as e:
            self.logger.severe("SQL error: {}".format(e.getMessage()))
            return []

    def add_shop(self, owner, location, is_admin_shop):
        return self.with_database_connection(self._add_shop, owner, location, is_admin_shop)

    def _add_shop(self, db_connection, owner, location, is_admin_shop):
        try:
            cursor = db_connection.cursor()
            cursor.execute("INSERT INTO shops (owner, location, is_admin_shop) VALUES (?, ?, ?)", (owner, location, is_admin_shop))
            shop_id = cursor.lastrowid
            cursor.close()
            self.load_shop_locations()
            self.logger.info("Shop created at {}".format(location))
        except SQLException as e:
            self.logger.severe("SQL error creating shop: {}".format(e.getMessage()))

    def remove_shop(self, shop_id):
        return self.with_database_connection(self._remove_shop, shop_id)

    def _remove_shop(self, db_connection, shop_id):
        try:
            cursor = db_connection.cursor()
            cursor.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
            cursor.close()
            self.logger.info("Shop removed with ID {}".format(shop_id))
        except SQLException as e:
            self.logger.severe("SQL error removing shop: {}".format(e.getMessage()))

    def create_shop(self, owner, location, items, price, is_admin_shop):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:plugins/PySpigot/scripts/SimpleChestShop/database.db")
            cursor = self.db_connection.cursor()
            
            # Insert shop
            cursor.execute("INSERT INTO shops (owner, location, is_admin_shop) VALUES (?, ?, ?)",
                          (owner, location, is_admin_shop))
            shop_id = cursor.lastrowid
            
            # Insert items
            for item, quantity in items.items():
                cursor.execute("INSERT INTO shop_items (shop_id, item, quantity, price) VALUES (?, ?, ?, ?)",
                              (shop_id, item, quantity, price))
            
            self.db_connection.commit()
            cursor.close()
            self.load_shop_locations()
            self.logger.info("Shop created at {}".format(location))
        except SQLException as e:
            self.logger.severe("SQL error creating shop: {}".format(e.getMessage()))
        finally:
            if self.db_connection:
                try:
                    self.db_connection.close()
                except SQLException as e:
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

    def scan_items_in_chest(self, inventory):
        items = {}
        for item_stack in inventory.getContents():
            if item_stack is not None:
                item_name = item_stack.getType().name()
                quantity = item_stack.getAmount()
                if item_name in items:
                    items[item_name] += quantity
                else:
                    items[item_name] = quantity
        return items

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
        if not isinstance(chest, Chest):
            player.sendMessage(self.colorize("&cYou must place the sign on a chest."))
            event.setCancelled(True)
            return

        inventory = chest.getInventory()
        items = self.scan_items_in_chest(inventory)

        if not items:
            player.sendMessage(self.colorize("&cYou must place items in the chest."))
            event.setCancelled(True)
            return

        # Store the shop location and items for price setting
        self.pending_price_settings[player.getName()] = {
            "location": str(block_below.getLocation()),
            "items": items,
            "sign": sign
        }

        player.sendMessage(self.colorize("&aShop sign created! Please enter the total price for all items in chat."))
        event.setCancelled(True)

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
                if self.economy and has_vault:
                    if self.economy.has(player, shop[4]):
                        try:
                            result = self.economy.withdrawPlayer(player, shop[4])
                            if result.transactionSuccess():
                                # Give items to player
                                for item in shop[3]:
                                    item_stack = ItemStack(Material.getMaterial(item['item']), item['quantity'])
                                    overflow = player.getInventory().addItem(item_stack)
                                    if overflow and not overflow.isEmpty():
                                        for item in overflow.values():
                                            player.getWorld().dropItem(player.getLocation(), item)
                                        player.sendMessage(self.colorize("&cYour inventory is full! Some items were dropped."))
                                player.sendMessage(self.colorize("&aYou have purchased the items for ${}".format(shop[4])))
                            else:
                                player.sendMessage(self.colorize("&cVault Error: {}".format(result.errorMessage)))
                                self.logger.warning("Vault transaction failed for {}: {}".format(player.getName(), result.errorMessage))
                        except Exception, e:
                            player.sendMessage(self.colorize("&cAn error occurred during the transaction: {}".format(e.getMessage())))
                            self.logger.severe("An error occurred during the transaction for {}: {}".format(player.getName(), e.getMessage()))
                else:
                    player.sendMessage(self.colorize("&cVault is not installed on this server!"))
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
        if not isinstance(chest, Chest):
            player.sendMessage(self.colorize("&cYou must place the sign on a chest."))
            event.setCancelled(True)
            return

        inventory = chest.getInventory()
        items = self.scan_items_in_chest(inventory)

        if not items:
            player.sendMessage(self.colorize("&cYou must place items in the chest."))
            event.setCancelled(True)
            return

        # Store the shop location and items for price setting
        self.pending_price_settings[player.getName()] = {
            "location": str(block_below.getLocation()),
            "items": items,
            "sign": sign
        }

        player.sendMessage(self.colorize("&aShop sign created! Please enter the total price for all items in chat."))
        event.setCancelled(True)

    def add_items_to_shop(self, shop_id, items):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:plugins/PySpigot/scripts/SimpleChestShop/database.db")
            cursor = self.db_connection.cursor()
            
            for item, quantity in items.items():
                # Check if item already exists
                cursor.execute("SELECT quantity FROM shop_items WHERE shop_id = ? AND item = ?", (shop_id, item))
                existing = cursor.fetchone()
                
                if existing:
                    # Update quantity
                    new_quantity = existing[0] + quantity
                    cursor.execute("UPDATE shop_items SET quantity = ? WHERE shop_id = ? AND item = ?", 
                                  (new_quantity, shop_id, item))
                else:
                    # Insert new item
                    cursor.execute("INSERT INTO shop_items (shop_id, item, quantity, price) VALUES (?, ?, ?, ?)",
                                  (shop_id, item, quantity, 0.0))  # Default price
        
            self.db_connection.commit()
            cursor.close()
            self.logger.info("Added items to shop {}".format(shop_id))
        except SQLException, e:
            self.logger.severe("SQL error adding items to shop: {}".format(e.getMessage()))
        finally:
            if self.db_connection:
                try:
                    self.db_connection.close()
                except SQLException, e:
                    self.logger.severe("Failed to close database connection: {}".format(e.getMessage()))

    def remove_items_from_shop(self, shop_id, items):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:plugins/PySpigot/scripts/SimpleChestShop/database.db")
            cursor = self.db_connection.cursor()
            
            for item in items:
                cursor.execute("DELETE FROM shop_items WHERE shop_id = ? AND item = ?", (shop_id, item))
            
            # Check if shop is now empty
            cursor.execute("SELECT COUNT(*) FROM shop_items WHERE shop_id = ?", (shop_id,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
            
            self.db_connection.commit()
            cursor.close()
            self.logger.info("Removed items from shop {}".format(shop_id))
        except SQLException, e:
            self.logger.severe("SQL error removing items from shop: {}".format(e.getMessage()))
        finally:
            if self.db_connection:
                try:
                    self.db_connection.close()
                except SQLException, e:
                    self.logger.severe("Failed to close database connection: {}".format(e.getMessage()))

    def update_shop_items(self, shop_id, items):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:plugins/PySpigot/scripts/SimpleChestShop/database.db")
            cursor = self.db_connection.cursor()
            
            for item, (quantity, price) in items.items():
                cursor.execute("UPDATE shop_items SET quantity = ?, price = ? WHERE shop_id = ? AND item = ?",
                              (quantity, price, shop_id, item))
            
            self.db_connection.commit()
            cursor.close()
            self.logger.info("Updated items in shop {}".format(shop_id))
        except SQLException, e:
            self.logger.severe("SQL error updating shop items: {}".format(e.getMessage()))
        finally:
            if self.db_connection:
                try:
                    self.db_connection.close()
                except SQLException, e:
                    self.logger.severe("Failed to close database connection: {}".format(e.getMessage()))

    def get_shop_by_location(self, location):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:plugins/PySpigot/scripts/SimpleChestShop/database.db")
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT id, owner, location, is_admin_shop FROM shops WHERE location = ?", (location,))
            shop = cursor.fetchone()
            cursor.close()
            if shop:
                shop_id = shop[0]
                cursor = self.db_connection.cursor()
                cursor.execute("SELECT item, quantity, price FROM shop_items WHERE shop_id = ?", (shop_id,))
                shop_items = cursor.fetchall()
                cursor.close()
                total_price = 0
                items = []
                for item in shop_items:
                    total_price += item[2]
                    items.append({
                        'item': item[0],
                        'quantity': item[1]
                    })
                return {
                    'id': shop_id,
                    'owner': shop[1],
                    'location': shop[2],
                    'is_admin_shop': shop[3],
                    'items': items,
                    'total_price': total_price
                }
            else:
                return None
        except SQLException, e:
            self.logger.severe("SQL error: {}".format(e.getMessage()))
            return None # Return None on error
        finally:
            if self.db_connection:
                try:
                    self.db_connection.close()
                except SQLException, e:
                    self.logger.severe("Failed to close database connection: {}".format(e.getMessage()))
