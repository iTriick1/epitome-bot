last_grill_message_id = None
leaderboard_message_id = None
ath_message_id = None  # Track the ATH message in the ATH channel

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from collections import defaultdict
import json
from datetime import datetime, timedelta

from datetime import datetime

DATE_FILE = 'dates.json'

LEADERBOARD_FILE = 'leaderboard.json'

# Leaderboard helpers at top-level

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_leaderboard(leaderboard):
    with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
        json.dump(leaderboard, f, ensure_ascii=False)


def load_dates():
    if os.path.exists(DATE_FILE):
        with open(DATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_dates():
    with open(DATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(dates, f, ensure_ascii=False)

dates = load_dates()

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)


@bot.command(name='help')
async def help_command(ctx):
    msg = (
        "**Available Commands:**\n"
        "!additem <name> <price> [category] - Add an item with a price and optional category to the list.\n"
        "!removeitem <name> - Remove an item from the list.\n"
        "!marketprice <name> - Show min, max, and average price for an item.\n"
        "!list - List all items in the list.\n"
        "!search <query> - Search for items in the list.\n"
        "!leaderboard - Show the leaderboard of users who added the most items.\n"
        "!save - Save the current list data.\n"
        "!help - Show this help message.\n\n"
        "---\nCredit: iTriick"
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

# Helper to extract float prices from a list of floats or dicts

def extract_prices(prices):
    return [p['price'] if isinstance(p, dict) and 'price' in p else p for p in prices]

# Function to update the leaderboard message in the grill channel
async def update_leaderboard_message(guild):
    global leaderboard_message_id
    leaderboard_channel_id = 1473216085242286234  # Correct leaderboard channel ID
    leaderboard_channel = guild.get_channel(leaderboard_channel_id) or await guild.fetch_channel(leaderboard_channel_id)
    leaderboard = load_leaderboard()
    if not leaderboard:
        leaderboard_text = 'No leaderboard data yet.'
    else:
        sorted_lb = sorted(leaderboard.items(), key=lambda x: x[1]['count'], reverse=True)
        leaderboard_text = '**🏆 Leaderboard: Most Items Added 🏆**\n'
        leaderboard_text += '```\n{:<4} {:<25} {:<10}\n'.format('Rank', 'User', 'Listings')
        leaderboard_text += '-'*45 + '\n'
        for idx, (user_id, entry) in enumerate(sorted_lb[:10], 1):
            leaderboard_text += '{:<4} {:<25} {:<10}\n'.format(idx, entry['name'], entry['count'])
        leaderboard_text += '```'
    # Delete previous leaderboard message if it exists
    if leaderboard_message_id:
        try:
            msg = await leaderboard_channel.fetch_message(leaderboard_message_id)
            await msg.delete()
        except Exception:
            pass
        leaderboard_message_id = None
    # Send new leaderboard message
    msg = await leaderboard_channel.send(leaderboard_text)
    leaderboard_message_id = msg.id

# Function to update the all-time high message in the specified channel ONLY if a new ATH is set
async def update_ath_message(guild):
    global ath_message_id, ath_cache
    ath_channel_id = 1469491210920919101  # ATH channel
    ath_channel = guild.get_channel(ath_channel_id) or await guild.fetch_channel(ath_channel_id)
    new_ath_lines = []
    updated = False
    for item, prices in item_prices.items():
        price_vals = extract_prices(prices)[1:]  # skip the first log
        if price_vals:
            ath = max(price_vals)
            prev_ath = ath_cache.get(item.lower())
            if prev_ath is None or ath > prev_ath:
                ath_cache[item.lower()] = ath
                new_ath_lines.append(f"{item.title()}: {int(ath):,} Archons")
                updated = True
    if updated and new_ath_lines:
        ath_text = '@everyone\n**🚀 New All Time High! 🚀**\n' + '\n'.join(new_ath_lines)
        # Delete previous ATH message if it exists
        if ath_message_id:
            try:
                msg = await ath_channel.fetch_message(ath_message_id)
                await msg.delete()
            except Exception:
                pass
            ath_message_id = None
        # Send new ATH message
        msg = await ath_channel.send(ath_text)
        ath_message_id = msg.id

def recalculate_leaderboard():
    leaderboard = {}
    for prices in item_prices.values():
        for entry in prices:
            if isinstance(entry, dict) and 'user_id' in entry:
                uid = str(entry['user_id'])
                uname = entry.get('user_name', str(uid))
                if uid not in leaderboard:
                    leaderboard[uid] = {'name': uname, 'count': 0}
                leaderboard[uid]['count'] += 1
    save_leaderboard(leaderboard)
    return leaderboard

# Track last known ATHs in memory
ath_cache = {}

@bot.command(name='additem')
async def add_item(ctx, *, args: str):
    global last_grill_message_id, leaderboard_message_id, ath_message_id
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
    # Add user info to price entry
    price_entry = {
        'price': price_value,
        'user_id': ctx.author.id,
        'user_name': str(ctx.author),
        'timestamp': datetime.now().isoformat()
    }
    item_prices[name.lower()].append(price_entry)
    category_map[name.lower()] = category
    # Add date for this price entry
    now_str = datetime.now().strftime('%Y-%m-%d')
    if name.lower() not in dates:
        dates[name.lower()] = []
    dates[name.lower()].append(now_str)

    save_dates()
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
        grill_emoji = "🗒️"
        header = f"{grill_emoji}  **The Market List**  {grill_emoji}"
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
                price_vals = extract_prices(prices)
                listing_count = len(price_vals)
                avg = sum(price_vals) / len(price_vals) if price_vals else 0
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
        grill_emoji = "🗒️"
        header = f"{grill_emoji}  **The Market List**  {grill_emoji}\n"
        table = "```\n{:<20} | {:<8} | {:<15} | {:<10}\n".format('Item', 'Listings', 'Avg Price', 'Category')
        table += "-"*65 + "\n"
        for item, prices in item_prices.items():
            purge_old_prices(item)
            filtered_prices = extract_prices(item_prices[item])
            if not filtered_prices:
                # Use all-time average if no recent listings
                all_prices = extract_prices(prices)
                avg = sum(all_prices) / len(all_prices) if all_prices else 0
                avg_str = f"{int(avg):,}".replace(",", " ") + " Archons (all-time avg)"
                count = 0
            else:
                avg = sum(filtered_prices) / len(filtered_prices)
                avg_str = f"{int(avg):,}".replace(",", " ") + " Archons"
                count = len(filtered_prices)
            cat = category_map.get(item, 'general')
            table += "{:<20} | {:<8} | {:<15} | {:<10}\n".format(item.title(), count, avg_str, cat)
        table += "```"
        await ctx.send(header + table)

    # After updating the grill, recalculate and update leaderboard
    recalculate_leaderboard()
    await update_leaderboard_message(ctx.guild)
    # After updating the grill and leaderboard, also update the ATH message
    await update_ath_message(ctx.guild)

@bot.command(name='marketprice')
async def market_price(ctx, *, name: str):
    item_name = name.lower()
    purge_old_prices(item_name)
    prices = item_prices.get(item_name, [])
    import discord
    try:
        if not prices:
            # If no recent prices, try to use all historical prices for average
            all_prices = prices if prices else []
            if not all_prices and item_name in item_prices:
                all_prices = item_prices.get(item_name, [])
            if all_prices:
                avg = sum(all_prices) / len(all_prices)
                msg = f"No recent listings for {name}. Using all-time average: {avg:.2f}"
            else:
                msg = f'No prices found for {name}.'
            await ctx.author.send(msg)
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

@bot.command(name='list')
async def list_items(ctx):
    if not item_prices:
        await ctx.send('No items in the list.')
        return
    grill_emoji = "🗒️"
    header = f"{grill_emoji}  **The Market List**  {grill_emoji}\n"
    table = "```\n{:<20} | {:<8} | {:<15} | {:<10}\n".format('Item', 'Listings', 'Avg Price', 'Category')
    table += "-"*65 + "\n"
    for item, prices in item_prices.items():
        purge_old_prices(item)
        filtered_prices = extract_prices(item_prices[item])
        if not filtered_prices:
            # Use all-time average if no recent listings
            all_prices = extract_prices(prices)
            avg = sum(all_prices) / len(all_prices) if all_prices else 0
            avg_str = f"{int(avg):,}".replace(",", " ") + " Archons (all-time avg)"
            count = 0
        else:
            avg = sum(filtered_prices) / len(filtered_prices)
            avg_str = f"{int(avg):,}".replace(",", " ") + " Archons"
            count = len(filtered_prices)
        cat = category_map.get(item, 'general')
        table += "{:<20} | {:<8} | {:<15} | {:<10}\n".format(item.title(), count, avg_str, cat)
    table += "```"
    await ctx.send(header + table)

@bot.command(name='removeitem')
async def remove_item(ctx, *, name: str):
    global last_grill_message_id, leaderboard_message_id, ath_message_id
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
            grill_emoji = "🗒️"
            header = f"{grill_emoji}  **The Market List**  {grill_emoji}"
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
                    price_vals = extract_prices(prices)
                    listing_count = len(price_vals)
                    avg = sum(price_vals) / len(price_vals) if price_vals else 0
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


@bot.command(name='leaderboard')
async def leaderboard_command(ctx):
    leaderboard = load_leaderboard()
    if not leaderboard:
        await ctx.send('No leaderboard data yet.')
        return
    sorted_lb = sorted(leaderboard.items(), key=lambda x: x[1]['count'], reverse=True)
    msg = '**🏆 Leaderboard: Most Items Added 🏆**\n'
    msg += '```\n{:<4} {:<25} {:<10}\n'.format('Rank', 'User', 'Listings')
    msg += '-'*45 + '\n'
    for idx, (user_id, entry) in enumerate(sorted_lb[:10], 1):
        msg += '{:<4} {:<25} {:<10}\n'.format(idx, entry['name'], entry['count'])
    msg += '```'
    await ctx.send(msg)

@bot.command(name='search')
async def search_item(ctx, *, query: str):
    # Search for items containing the query (case-insensitive)
    results = []
    for item, prices in item_prices.items():
        if query.lower() in item.lower():
            cat = category_map.get(item, 'general')
            price_vals = extract_prices(prices)
            avg = sum(price_vals) / len(price_vals) if price_vals else 0
            avg_str = f"{int(avg):,}".replace(",", " ") + " Archons"
            results.append((item, len(price_vals), avg_str, cat))
    try:
        if results:
            grill_emoji = "🗒️"
            header = f"{grill_emoji}  **Search Results for '{query}'**  {grill_emoji}\n"
            table = "```\n{:<20} | {:<8} | {:<15} | {:<10}\n".format('Item', 'Listings', 'Avg Price', 'Category')
            table += "-"*65 + "\n"
            for item, count, avg_str, cat in results:
                table += "{:<20} | {:<8} | {:<15} | {:<10}\n".format(item.title(), count, avg_str, cat)
            table += "```"
            await ctx.author.send(header + table)
        else:
            await ctx.author.send(f"No items found matching '{query}'.")
    except discord.Forbidden:
        await ctx.send(f"{ctx.author.mention}, I couldn't DM you. Please check your privacy settings.")
    finally:
        try:
            await ctx.message.delete()
        except Exception:
            pass

def purge_old_prices(item_name):
    if item_name not in item_prices or item_name not in dates:
        return
    today = datetime.now()
    new_prices = []
    new_dates = []
    for price, date_str in zip(item_prices[item_name], dates[item_name]):
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        except Exception:
            continue
        if (today - date_obj).days <= 30:
            new_prices.append(price)
            new_dates.append(date_str)
    item_prices[item_name] = new_prices
    dates[item_name] = new_dates
    save_data()
    save_dates()

bot.run(TOKEN)
