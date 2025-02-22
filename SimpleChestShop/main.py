import os
import java.net.HttpURLConnection as HttpURLConnection
import java.net.URL as URL
import java.io.BufferedReader as BufferedReader
import java.io.InputStreamReader as InputStreamReader
import java.sql.Connection as Connection
from java.sql import DriverManager, SQLException
from java.util.logging import Logger
# from java.util.logging import Level #Unused
# from java.util.logging import LogRecord #Unused

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
# from net.milkbowl.vaultunlocked.api import VaultUnlockedAPI

# Bukkit API imports
from org.bukkit.plugin.java import JavaPlugin
from org.bukkit import Material
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
# from org.bukkit.permissions import Permission
from org.bukkit.plugin import RegisteredServiceProvider

# GUI imports
from org.bukkit.inventory import Inventory
from org.bukkit.event.inventory import InventoryType
from org.bukkit.event.inventory import InventoryClickEvent
from org.bukkit.event.inventory import InventoryCloseEvent

# Pyspigot Configuration Manager
# from pyspigot import ConfigurationManager

# YAML Config
#import ruamel.yaml as yaml

CONFIG_FILE = "config.yml"
SHOP_CHEST_MATERIAL_CONFIG_KEY = "shop_chest_material"
SHOP_IDENTIFIER_SIGN_TEXT_CONFIG_KEY = "shop_identifier_sign_text"

DEFAULT_SHOP_CHEST_MATERIAL = "CHEST"
DEFAULT_SHOP_IDENTIFIER_SIGN_TEXT = "[Shop]"

class ChestShop(JavaPlugin, Listener):
    def __init__(self):
        super(ChestShop, self).__init__()
        self.config_manager = ps.ConfigurationManager(self)  # Use ps.ConfigurationManager
        self.db_connection = None
        self.shop_chest_material = None
        self.shop_identifier_sign_text = None
        self.shop_locations = set()  # Set to store shop locations
        self.economy = None
        self.permission = None
        self.chat = None
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
        self.enable_geyser_integration = True  # Keep these flags for config if you want.
        self.enable_floodgate_integration = True  # But the actual API calls are removed.
        self.logger = self.getLogger()

    def onEnable(self):
        self.load_plugin_config()
        self.setup_database()
        self.load_shop_locations()
        self.setup_economy()
        self.setup_permissions()
        self.register_events()
        self.setup_placeholder_api()
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
        self.gui_title = self.config_manager.get("gui_title", "&aChest Shop")
        self.gui_size = self.config_manager.get("gui_size", 27)
        self.default_items = self.config_manager.get("default_items", {})
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
        self.allow_admin_shops = self.config_manager.set("allow_admin_shops", self.allow_admin_shops)
        self.config_manager.set("gui_title", self.gui_title)
        self.config_manager.set("gui_size", self.gui_size)
        self.config_manager.set("default_items", self.default_items)
        self.config_manager.save_config("config.yml")
        self.logger.info("Configuration saved to '{}'".format(CONFIG_FILE))

    def setup_database(self):
        try:
            self.db_connection = DriverManager.getConnection("jdbc:sqlite:E:/1.19.4/plugins/PySpigot/scripts/database.db")
            statement = self.db_connection.createStatement()
            create_table_sql = "CREATE TABLE IF NOT EXISTS shops (id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT, location TEXT UNIQUE, item TEXT, price REAL, is_admin_shop INTEGER)"
            statement.executeUpdate(create_table_sql)
            create_table_sql = "CREATE TABLE IF NOT EXISTS gui_items (slot INTEGER PRIMARY KEY, material_name TEXT)"
            statement.executeUpdate(create_table_sql)
            self.db_connection.close()
            self.logger.info("Database and tables created successfully.")
        except SQLException, e:
            self.logger.severe("An error occurred: {}".format(e.getMessage()))

    def load_shop_locations(self):
        self.shop_locations.clear()
        shops = self.get_shops()
        for shop in shops:
            self.shop_locations.add(shop[2])

    def get_shops(self):
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT id, owner, location, item, price, is_admin_shop FROM shops")
        shops = cursor.fetchall()
        cursor.close()
        return shops

    def add_shop(self, owner, location, item, price):
        cursor = self.db_connection.cursor()
        cursor.execute("INSERT INTO shops (owner, location, item, price) VALUES (?, ?, ?, ?)", (owner, location, item, price))
        self.db_connection.commit()
        cursor.close()
        self.load_shop_locations()

    def remove_shop(self, shop_id):
        cursor = self.db_connection.cursor()
        cursor.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
        self.db_connection.commit()
        cursor.close()
        self.load_shop_locations()

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
        if not has_vault:
            self.permission = None
            self.logger.warning("Vault permission provider not enabled due to import failure!")
            return

        registered_permission = self.getServer().getServicesManager().getRegistration(Permission)
        if registered_permission:
            self.permission = registered_permission.getProvider()
            self.logger.info("Vault permission provider found: {}".format(self.permission.getName()))
        else:
            self.permission = None
            self.logger.warning("No Vault permission provider found!")

    def register_events(self):
        pm = self.getServer().getPluginManager()
        pm.registerEvents(self, self)

    def setup_placeholder_api(self):
        PlaceholderAPI.registerPlaceholder("shop_balance", self.get_shop_balance)

    def get_shop_balance(self, player):
        return str(self.vault_unlocked_api.getBalance(player))

    def colorize(self, message):
        """Colorizes a message using Bukkit color codes."""
        return ChatColor.translateAlternateColorCodes('&', message)

    def has_permission(self, player, permission_node):
        """Checks if a player has a permission using Vault or Bukkit."""
        if has_luckperms and self.luckperms: #Check for both bool and not null
            user = self.luckperms.getUserManager().getUser(player.getUniqueId())
            if user:
                return user.getCachedData().getPermissionData().checkPermission(permission_node).asBoolean()
            else:
                self.logger.warning("User not found in LuckPerms: {}".format(player.getName()))
                return False #Or return player.hasPermission(permission_node) as fallback
        elif self.permission and has_vault:
            return self.permission.has(player, permission_node)  # Use Vault Permissions
        else:
            return player.hasPermission(permission_node)  # Fallback to Bukkit Permissions

    @EventHandler
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
        if block.getType() == self.shop_chest_material:
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

    @EventHandler
    def onSignChange(self, event):
        sign = event.getSign()
        sign_text = sign.getLine(0)
        if sign_text == self.shop_identifier_sign_text:
            block_below = sign.getBlock().getRelative(0, -1, 0)
            if block_below.getType() == self.shop_chest_material:
                player = event.getPlayer()
                if self.has_permission(player, "chestshop.create"):
                    self.create_shop(player.getName(), str(block_below.getLocation()), "item_name", 1.0, is_admin_shop=False) # Example Price
                    player.sendMessage(self.colorize("&aSign placed on shop.")) #Customizable Vault error message
                else:
                    player.sendMessage(self.colorize(self.message_no_permission)) #Customizable Vault error message

    @EventHandler
    def onBlockBreak(self, event):
        block = event.getBlock()
        player = event.getPlayer()
        if block.getType() == self.shop_chest_material:
            event.setCancelled(True)
            player.sendMessage(self.colorize("&c&lYou cannot break shop chests!")) #Customizable Vault error message
            player.sendMessage(self.colorize("&7Use /removeshop to remove a shop.")) #Customizable Vault error message

    def onCommand(self, sender, command, label, args):
        if command.getName().lower() == "createshop":
            return self.handle_createshop_command(sender, args)
        elif command.getName().lower() == "removeshop":
            return self.handle_removeshop_command(sender, args)
        elif command.getName().lower() == "shopinfo":
            return self.handle_shopinfo_command(sender, args)
        elif command.getName().lower() == "setprice":
            return self.handle_setprice_command(sender, args)
        elif command.getName().lower() == "shopgui":
            return self.handle_shopgui_command(sender, args)
        elif command.getName().lower() == "buy":
            return self.handle_buy_command(sender, args)
        elif command.getName().lower() == "createadminshop":
            return self.handle_createadminshop_command(sender, args)
        return False

    def handle_createshop_command(self, sender, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.colorize("&cThis command can only be used by players.")) #Customizable Vault error message
            return True

        player = sender

        if not self.has_permission(player, "chestshop.create"):
            sender.sendMessage(self.colorize(self.message_no_permission)) #Customizable Vault error message
            return True

        if len(args) != 2:
            sender.sendMessage(self.colorize(self.message_invalid_arguments).replace("{usage}", "/createshop <item> <price>")) #Customizable Vault error message
            return True

        item_name = args[0]
        try:
            price = float(args[1])
        except ValueError:
            sender.sendMessage(self.colorize("&cInvalid price: {}".format(args[1]))) #Customizable Vault error message
            return True

        is_admin_shop = self.has_permission(player, "chestshop.admin")

        if is_admin_shop and not self.allow_admin_shops:
            sender.sendMessage(self.colorize(self.message_no_permission)) #Customizable Vault error message
            return True

        target_block = player.getTargetBlock(None, 5)
        if target_block is None or target_block.getType() != Material.CHEST:
            sender.sendMessage(self.colorize(self.message_no_permission)) #Customizable Vault error message
            return True

        location = target_block.getLocation()

        if self.is_shop_location(location):
            sender.sendMessage(self.colorize(self.message_no_permission)) #Customizable Vault error message
            return True

        if not self.is_in_valid_town(sender):
            sender.sendMessage(self.colorize("&cYou must be in a valid town to create a shop.")) #Customizable Vault error message
            return True

        if is_admin_shop:
            owner = None
            sender.sendMessage(self.colorize(self.message_admin_shop_created).replace("{item}", item_name)) #Customizable Vault error message
        else:
            owner = player.getName()
            sender.sendMessage(self.colorize(self.message_shop_created).replace("{item}", item_name)) #Customizable Vault error message

        self.create_shop(owner, location, item_name, price, is_admin_shop)

        return True  # Command handled

    def create_shop(self, owner, location, item, price, is_admin_shop):
        cursor = self.db_connection.cursor()
        cursor.execute("INSERT INTO shops (owner, location, item, price, is_admin_shop) VALUES (?, ?, ?, ?, ?)",
                       (owner, str(location), item, price, is_admin_shop))
        self.db_connection.commit()
        self.shop_locations.add(location)
        self.logger.info("Shop created at {}".format(location))

    def is_shop_location(self, location):
        return location in self.shop_locations

    def handle_shopinfo_command(self, sender, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.colorize("&cThis command can only be used by players in-game.")) #Customizable Vault error message
            return True

        player = sender
        block = player.getTargetBlock(None, 5)

        if block.getType() != self.shop_chest_material:
            player.sendMessage(self.colorize("&cYou must be looking at a chest to get shop info.")) #Customizable Vault error message
            return True

        location = block.getLocation()
        shops = self.get_shops()
        for shop in shops:
            if shop[2] == str(location):
                player.sendMessage(self.colorize("&aShop found: Owner: {}, Item: {}, Price: {}".format(shop[1], shop[3], shop[4]))) #Customizable Vault error message
                return True

        player.sendMessage(self.colorize("&cNo shop found at this location.")) #Customizable Vault error message
        return True

    def handle_removeshop_command(self, sender, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.colorize("&cThis command can only be used by players in-game.")) #Customizable Vault error message
            return True

        player = sender
        if not self.has_permission(player, "chestshop.removeshop"):
             sender.sendMessage(self.colorize(self.message_no_permission)) #Customizable Vault error message
             return True

        target_block = player.getTargetBlock(None, 5)
        if not target_block or target_block.getType() != self.shop_chest_material:
            player.sendMessage(self.colorize("&cYou must be looking at a shop chest to use /removeshop.")) #Customizable Vault error message
            return True

        location = target_block.getLocation()
        shops = self.get_shops()
        for shop in shops:
            if shop[2] == str(location):
                if shop[1] == player.getName() or self.allow_admin_shops:
                    self.remove_shop(shop[0])
                    player.sendMessage(self.colorize("&aShop removed at this location.")) #Customizable Vault error message
                    return True
                else:
                    player.sendMessage(self.colorize("&cYou do not own this shop.")) #Customizable Vault error message
                    return True

        player.sendMessage(self.colorize("&cNo shop found at this location.")) #Customizable Vault error message
        return True

    def handle_setprice_command(self, sender, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.colorize(self.message_no_permission)) #Customizable Vault error message
            return True

        player = sender

        if not self.has_permission(player, "chestshop.setprice"):
            sender.sendMessage(self.colorize(self.message_no_permission)) #Customizable Vault error message
            return True

        if len(args) < 2:
            player.sendMessage(self.colorize(self.message_invalid_arguments).replace("{usage}", "/setprice <location> <new_price>")) #Customizable Vault error message
            return True

        location = args[0]
        new_price = float(args[1])
        shops = self.get_shops()
        for shop in shops:
            if shop[2] == location:
                self.remove_shop(shop[0])
                self.add_shop(shop[1], location, shop[3], new_price)

                player.sendMessage(self.colorize("&aPrice updated for shop at {}: New Price: {}".format(location, new_price))) #Customizable Vault error message
                return True
        player.sendMessage(self.colorize("&cNo shop found at that location.")) #Customizable Vault error message
        return True

    def handle_buy_command(self, sender, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.colorize("&cThis command can only be used by players.")) #Customizable Vault error message
            return True

        if len(args) != 1:
            sender.sendMessage(self.colorize("&cUsage: /buy <item>")) #Customizable Vault error message
            return True

        item_name = args[0]

        shops = self.get_shops()
        for shop in shops:
            if shop[3] == item_name:
                player = sender
                location = shop[2]
                price = shop[4]
                if self.economy and has_vault:
                    if self.economy.has(player, price):
                        try:
                            result = self.economy.withdrawPlayer(player, price)
                            if result.transactionSuccess():
                                item_stack = ItemStack(Material.getMaterial(item_name), 1)
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
                    return True #Exit
                return True #Exit
        sender.sendMessage(self.colorize("&cNo shop found with item {}".format(item_name))) #Customizable Vault error message
        return True #Exit

    def handle_createadminshop_command(self, sender, args):
        if not isinstance(sender, Player):
            sender.sendMessage(self.colorize("&cThis command can only be used by players.")) #Customizable Vault error message
            return True

        player = sender

        if not self.has_permission(player, "chestshop.admin"):
            sender.sendMessage(self.colorize("&cYou do not have permission to create admin shops.")) #Customizable Vault error message
            return True

        if len(args) != 2:
            sender.sendMessage(self.colorize("&cUsage: /createadminshop <item> <price>")) #Customizable Vault error message
            return True

        item_name = args[0]
        try:
            price = float(args[1])
        except ValueError:
            sender.sendMessage(self.colorize("&cInvalid price: {}".format(args[1]))) #Customizable Vault error message
            return True

        target_block = player.getTargetBlock(None, 5)
        if target_block is None or target_block.getType() != Material.CHEST:
            sender.sendMessage(self.colorize("&cYou must be looking at a chest to create an admin shop.")) #Customizable Vault error message
            return True

        location = target_block.getLocation()

        if self.is_shop_location(location):
            sender.sendMessage(self.colorize("&cA shop already exists at this location.")) #Customizable Vault error message
            return True

        self.create_shop(None, location, item_name, price, True)
        sender.sendMessage(self.colorize("&aAdmin shop created at this location.")) #Customizable Vault error message
        return True

    def is_in_valid_town(self, player):
        if not self.enable_towny_integration:
            return True

        towny_player = TownyUniverse.getPlayer(player.getName())
        if towny_player.hasTown():
            return True
        return False

    def open_shop_gui(self, player):
        num_rows = self.gui_size / 9
        if not (num_rows in range(1, 7)):
            self.logger.warning("Invalid gui_size in config.yml. Must be a multiple of 9 between 9 and 54. Defaulting to 27.")
            self.gui_size = 27

        inventory = Bukkit.createInventory(None, self.gui_size, ChatColor.translateAlternateColorCodes('&', self.gui_title))

        if self.default_items:
            for slot, item_name in self.default_items.items():
                material = Material.getMaterial(item_name)
                if material:
                    item_stack = ItemStack(material, 1)
                    inventory.setItem(int(slot), item_stack)

        player.openInventory(inventory)

    @EventHandler
    def on_inventory_click(self, event):
        if event.getInventory().getName() == ChatColor.translateAlternateColorCodes('&', self.gui_title):
            event.setCancelled(True)
            player = event.getWhoClicked()
            clicked_item = event.getCurrentItem()
            if clicked_item is not None and clicked_item.getType() == Material.DIAMOND:
                player.sendMessage(self.colorize("&aYou clicked on a diamond!")) #Customizable Vault error message

    @EventHandler
    def on_inventory_close(self, event):
        if event.getInventory().getName() == ChatColor.translateAlternateColorCodes('&', self.gui_title):
            player = event.getPlayer()
            inventory = event.getInventory()

            for slot in range(inventory.getSize()):
                item_stack = inventory.getItem(slot)
                if item_stack is not None:
                    material_name = item_stack.getType().name()
                    self.save_item_
