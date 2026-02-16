last_grill_message_id = None

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from collections import defaultdict
import json

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)


from discord import app_commands

@bot.tree.command(name="help", description="Show help for all commands")
async def help_command(interaction: discord.Interaction):
    msg = (
        "**Available Commands:**\n"
        "/additem <name> <price> [category] - Add an item with a price and optional category to the grill.\n"
        "/removeitem <name> - Remove an item from the market.\n"
        "/marketprice <name> - Show min, max, and average price for an item.\n"
        "/grill - List all items in the grill.\n"
        "/save - Save the current market data.\n"
        "/help - Show this help message.\n\n"
        "---\nCredit: itriick"
    )
    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="save", description="Save the current market data.")
async def save_command(interaction: discord.Interaction):
    save_data()
    save_categories()
    await interaction.response.send_message('Market data has been saved!', ephemeral=True)


DATA_FILE = 'data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return defaultdict(list, {k: v for k, v in data.items()})
    return defaultdict(list)

# Store categories: {item_name: category}
category_map = {}
CATEGORY_FILE = 'categories.json'

def load_categories():
    if os.path.exists(CATEGORY_FILE):
        with open(CATEGORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_categories():
    with open(CATEGORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(category_map, f, ensure_ascii=False)

category_map = load_categories()

# Store listing amount in JSON
def save_listing_amount(name, amount):
    if name.lower() not in item_prices:
        item_prices[name.lower()] = []
    if 'amount' not in category_map:
        category_map['amount'] = {}
    if name.lower() not in category_map['amount']:
        category_map['amount'][name.lower()] = 0
    category_map['amount'][name.lower()] += amount
    item_prices[name.lower()].append(price_value)
    category_map[name.lower()] = category
    save_data()
    save_categories()

def save_data():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(item_prices, f, ensure_ascii=False)

item_prices = load_data()


@bot.tree.command(name="additem", description="Add an item with a price and optional category to the grill.")
@app_commands.describe(name="Item name", price="Price", category="Category (optional)")
async def add_item(interaction: discord.Interaction, name: str, price: float, category: str = "general"):
    global last_grill_message_id
    category = category.lower()
    if not isinstance(item_prices[name.lower()], list):
        item_prices[name.lower()] = []
    item_prices[name.lower()].append(price)
    category_map[name.lower()] = category
    save_data()
    save_categories()
    price_str = f"{int(price):,}".replace(",", " ")
    msg = await interaction.channel.send(f'Added {name} for {price_str} Archons! (Category: {category})')
    import asyncio
    await asyncio.sleep(10)
    try:
        await msg.delete()
    except Exception:
        pass
    # Build cat_items with normalized categories only once
    normalized_category_map = {k.lower(): v.lower() for k, v in category_map.items() if isinstance(v, str)}
    from collections import defaultdict
    cat_items = defaultdict(list)
    for item, prices in item_prices.items():
        cat = normalized_category_map.get(item.lower(), 'general')
        cat_items[cat].append((item, prices))
    grill_channel_id = 1472854000616607891
    grill_channel = await bot.fetch_channel(grill_channel_id)
    if grill_channel and item_prices:
        global last_grill_message_id
        if isinstance(last_grill_message_id, list):
            for msg_id in last_grill_message_id:
                try:
                    prev_msg = await grill_channel.fetch_message(msg_id)
                    await prev_msg.delete()
                except Exception:
                    pass
            last_grill_message_id = []
        elif last_grill_message_id:
            try:
                prev_msg = await grill_channel.fetch_message(last_grill_message_id)
                await prev_msg.delete()
            except Exception:
                pass
            last_grill_message_id = []
        grill_emoji = "🍖"
        header = f"{grill_emoji}  **The Market Grill**  {grill_emoji}"
        header_msg = await grill_channel.send(header)
        sent_msgs = [header_msg]
        for cat, items in cat_items.items():
            import random
            color_emojis = ["🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "🟫", "⬛", "⬜"]
            color_emoji = random.choice(color_emojis)
            msg = f"{color_emoji} **[{cat.title()}]**\n"
            table = "```\n{:<20} | {:<8} | {:<15}\n".format('Item', 'Listings', 'Avg Price')
            table += "-"*50 + "\n"
            item_group = {}
            for item, prices in items:
                key = item.lower()
                if key not in item_group:
                    item_group[key] = []
                item_group[key].extend(prices)
            for item_name, prices in item_group.items():
                listing_count = len(prices)
                avg = sum(prices) / len(prices) if prices else 0
                avg_str = f"{int(avg):,}".replace(",", " ") + " Archons"
                table += "{:<20} | {:<8} | {:<15}\n".format(item_name.title(), listing_count, avg_str)
            table += "```"
            sent_msg = await grill_channel.send(msg + table)
            sent_msgs.append(sent_msg)
        if sent_msgs:
            last_grill_message_id = [msg.id for msg in sent_msgs]
    elif item_prices:
        grill_emoji = "🍖"
        header = f"{grill_emoji}  **The Market Grill**  {grill_emoji}\n"
        table = "```\n{:<20} | {:<8} | {:<15} | {:<10}\n".format('Item', 'Listings', 'Avg Price', 'Category')
        table += "-"*65 + "\n"
        for item, prices in item_prices.items():
            avg = sum(prices) / len(prices)
            avg_str = f"{int(avg):,}".replace(",", " ") + " Archons"
            cat = category_map.get(item, 'general')
            table += "{:<20} | {:<8} | {:<15} | {:<10}\n".format(item.title(), len(prices), avg_str, cat)
        table += "```"
        await interaction.channel.send(header + table)
    await interaction.response.send_message(f"Added {name} for {price_str} Archons! (Category: {category})", ephemeral=True)


@bot.tree.command(name="marketprice", description="Show min, max, and average price for an item.")
@app_commands.describe(name="Item name")
async def market_price(interaction: discord.Interaction, name: str):
    prices = item_prices.get(name.lower())
    if not prices:
        await interaction.response.send_message(f'No prices found for {name}.', ephemeral=True)
    else:
        avg = sum(prices) / len(prices)
        msg = f"Market price for {name}:\nMin: {min(prices):.2f}\nMax: {max(prices):.2f}\nAvg: {avg:.2f}"
        await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="grill", description="List all items in the grill.")
async def grill(interaction: discord.Interaction):
    if not item_prices:
        await interaction.response.send_message('No items in the grill.', ephemeral=True)
        return
    grill_emoji = "🍖"
    header = f"{grill_emoji}  **The Market Grill**  {grill_emoji}\n"
    table = "```\n{:<20} | {:<8} | {:<15} | {:<10}\n".format('Item', 'Listings', 'Avg Price', 'Category')
    table += "-"*65 + "\n"
    for item, prices in item_prices.items():
        avg = sum(prices) / len(prices)
        avg_str = f"{int(avg):,}".replace(",", " ") + " Archons"
        cat = category_map.get(item, 'general')
        table += "{:<20} | {:<8} | {:<15} | {:<10}\n".format(item.title(), len(prices), avg_str, cat)
    table += "```"
    await interaction.response.send_message(header + table, ephemeral=True)


@bot.tree.command(name="removeitem", description="Remove an item from the market.")
@app_commands.describe(name="Item name")
async def remove_item(interaction: discord.Interaction, name: str):
    name_key = name.lower()
    removed = False
    if name_key in item_prices:
        del item_prices[name_key]
        removed = True
    if name_key in category_map:
        del category_map[name_key]
        removed = True
    if removed:
        save_data()
        save_categories()
        msg = await interaction.channel.send(f'Removed {name.title()} from the market.')
        import asyncio
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except Exception:
            pass
    await interaction.response.send_message(f'Removed {name.title()} from the market.', ephemeral=True)

        # UPDATE THIS ID TO YOUR GRILL CHANNEL ID 
        grill_channel_id = 1472854000616607891


        grill_channel = await bot.fetch_channel(grill_channel_id)
        # Delete previous grill messages if they exist
        global last_grill_message_id
        if isinstance(last_grill_message_id, list):
            for msg_id in last_grill_message_id:
                try:
                    prev_msg = await grill_channel.fetch_message(msg_id)
                    await prev_msg.delete()
                except Exception:
                    pass
            last_grill_message_id = []
        elif last_grill_message_id:
            try:
                prev_msg = await grill_channel.fetch_message(last_grill_message_id)
                await prev_msg.delete()
            except Exception:
                pass
            last_grill_message_id = []
        # Send updated grill
        if item_prices:
            grill_emoji = "🍖"
            header = f"{grill_emoji}  **The Market Grill**  {grill_emoji}"
            header_msg = await grill_channel.send(header)
            sent_msgs = [header_msg]
            cat_items = defaultdict(list)
            for item, prices in item_prices.items():
                cat = category_map.get(item.lower(), 'general').lower()
                cat_items[cat].append((item, prices))
            for cat, items in cat_items.items():
                import random
                color_emojis = ["🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "🟫", "⬛", "⬜"]
                color_emoji = random.choice(color_emojis)
                msg = f"{color_emoji} **[{cat.title()}]**\n"
                table = "```\n{:<20} | {:<8} | {:<15}\n".format('Item', 'Listings', 'Avg Price')
                table += "-"*50 + "\n"
                # Aggregate items by name (case-insensitive)
                item_group = {}
                for item, prices in items:
                    key = item.lower()
                    if key not in item_group:
                        item_group[key] = []
                    item_group[key].extend(prices)
                for item_name, prices in item_group.items():
                    listing_count = len(prices)
                    avg = sum(prices) / len(prices) if prices else 0
                    avg_str = f"{int(avg):,}".replace(",", " ") + " Archons"
                    table += "{:<20} | {:<8} | {:<15}\n".format(item_name.title(), listing_count, avg_str)
                table += "```"
                msg += table
                sent_msg = await grill_channel.send(msg)
                sent_msgs.append(sent_msg)
            if sent_msgs:
                last_grill_message_id = [msg.id for msg in sent_msgs ]
        else:
            await grill_channel.send("No items in the grill.")
    else:
        await ctx.send(f'Item {name.title()} not found in the market.')
        try:
            await ctx.message.delete()
        except Exception:
            pass

bot.run(TOKEN)
