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


@bot.command(name='help')
async def help_command(ctx):
    msg = (
        "**Available Commands:**\n"
        "!additem <name> <price> [category] - Add an item with a price and optional category to the grill.\n"
        "!removeitem <name> - Remove an item from the market.\n"
        "!marketprice <name> - Show min, max, and average price for an item.\n"
        "!grill - List all items in the grill.\n"
        "!save - Save the current market data.\n"
        "!help - Show this help message.\n\n"
        "---\nCredit: itriick"
    )
    await ctx.send(msg)

@bot.command(name='save')
async def save_command(ctx):
    save_data()
    save_categories()
    await ctx.send('Market data has been saved!')


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

@bot.command(name='additem')
async def add_item(ctx, *, args: str):
    global last_grill_message_id
    # Try to parse: <item name> <price> [category]
    try:
        *name_parts, price = args.rsplit(' ', 2)[-2:]
        rest = args.rsplit(' ', 2)
        if len(rest) == 3:
            name = rest[0]
            price = rest[1]
            category = rest[2]
        else:
            *name_parts, price = args.rsplit(' ', 1)
            name = ' '.join(name_parts)
            category = 'general'
        price_value = float(price)
    except Exception:
        await ctx.send('Usage: !additem <item name> <price> [category]\nExample: !additem Morning Dew Pearl 75000 scroll')
        return
    # Normalize category name for all items
    category = category.lower()
    # Ensure item_prices[name.lower()] is always a list
    if not isinstance(item_prices[name.lower()], list):
        item_prices[name.lower()] = []
    item_prices[name.lower()].append(price_value)
    category_map[name.lower()] = category
    save_data()
    save_categories()
    price_str = f"{int(price_value):,}".replace(",", " ")
    msg = await ctx.send(f'Added {name} for {price_str} Archons! (Category: {category})')
    import asyncio
    await asyncio.sleep(10)
    try:
        await msg.delete()
    except Exception:
        pass
    try:
        await ctx.message.delete()
    except Exception:
        pass
    # Build cat_items with normalized categories only once
    normalized_category_map = {k.lower(): v.lower() for k, v in category_map.items() if isinstance(v, str)}
    cat_items = defaultdict(list)
    for item, prices in item_prices.items():
        cat = normalized_category_map.get(item.lower(), 'general')
        cat_items[cat].append((item, prices))
    # Send updated grill to the grill channel
    grill_channel_id = 1472854000616607891  # Updated channel ID
    grill_channel = await bot.fetch_channel(grill_channel_id)
    if grill_channel and item_prices:
        # Always clear previous grill messages
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
        # Send header only once at the top
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
            last_grill_message_id = [msg.id for msg in sent_msgs]
    elif item_prices:
        # fallback: send to current channel if grill channel not found
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
        await ctx.send(header + table)

@bot.command(name='marketprice')
async def market_price(ctx, *, name: str):
    prices = item_prices.get(name.lower())
    import discord
    try:
        if not prices:
            await ctx.author.send(f'No prices found for {name}.')
        else:
            avg = sum(prices) / len(prices)
            msg = f"Market price for {name}:\nMin: {min(prices):.2f}\nMax: {max(prices):.2f}\nAvg: {avg:.2f}"
            await ctx.author.send(msg)
    except discord.Forbidden:
        # Only notify about DM failure, do not include the answer
        await ctx.send(f"{ctx.author.mention}, I couldn't DM you. Please check your privacy settings.")
    finally:
        try:
            await ctx.message.delete()
        except Exception:
            pass

@bot.command(name='grill')
async def grill(ctx):
    if not item_prices:
        await ctx.send('No items in the grill.')
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
    await ctx.send(header + table)

@bot.command(name='removeitem')
async def remove_item(ctx, *, name: str):
    name_key = name.lower()
    removed = False
    # Remove item from item_prices and category_map
    if name_key in item_prices:
        del item_prices[name_key]
        removed = True
    if name_key in category_map:
        del category_map[name_key]
        removed = True
    if removed:
        save_data()
        save_categories()
        await ctx.send(f'Removed {name.title()} from the market.')
        try:
            await ctx.message.delete()
        except Exception:
            pass
        # Update grill channel
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
