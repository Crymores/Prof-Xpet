import discord
from discord.ext import tasks, commands
import aiohttp
import json
from datetime import datetime, timedelta
import asyncio
import os
import aiofiles
import matplotlib.pyplot as plt

TOKEN = 'YOUR_DISCORD_BOT_TOKEN'  # Assurez-vous de stocker votre token de manière sécurisée
FILE_PATH = 'tokens_info.json'
ALERTS_FILE_PATH = 'alerts_info.json'
UPDATE_JSON_INTERVAL = 10 * 60  # 10 minutes en secondes
STATUS_UPDATE_INTERVAL = 30  # secondes
WEEKLY_SUMMARY_CHANNEL_ID = 123456789  # Remplacez par l'ID du canal de résumé hebdomadaire

intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Création automatique des fichiers JSON s'ils n'existent pas
async def create_files():
    if not os.path.exists(FILE_PATH):
        async with aiofiles.open(FILE_PATH, 'w', encoding='utf-8') as file:
            default_data = {
                "tokens": {
                    "xpet": {
                        "address": "0x00CBcF7B3d37844e44b888Bc747bDd75FCf4E555",
                        "symbol": "XPET",
                        "emoji": "🐼",
                        "priceUsd": 0,
                        "priceChange1h": "0%",
                        "priceChange24h": "0%",
                        "priceChange7d": "0%",
                        "liquidityUsd": 0,
                        "volume24h": 0,
                        "holders": 0,
                        "pairCreated": "01/01/2020 00h00",
                        "fdv": 0,
                        "last_updated": "01/01/2020 00h00",
                        "imageUrl": "https://github.com/Crymores/Prof-Xpet/blob/main/img-xpet/xpetv2.jpeg?raw=true"
                    },
                    "bpet": {
                        "address": "0x6dAF586B7370B14163171544fca24AbcC0862ac5",
                        "symbol": "BPET",
                        "emoji": "🦜",
                        "priceUsd": 0,
                        "priceChange1h": "0%",
                        "priceChange24h": "0%",
                        "priceChange7d": "0%",
                        "liquidityUsd": 0,
                        "volume24h": 0,
                        "holders": 0,
                        "pairCreated": "01/01/2020 00h00",
                        "fdv": 0,
                        "last_updated": "01/01/2020 00h00",
                        "imageUrl": "https://github.com/Crymores/Prof-Xpet/blob/main/img-xpet/Bpet.jpg?raw=true"
                    },
                    "x404": {
                        "address": "0x7D5203E74a2aFe3f474e21Fef3e6CE04757652B9",
                        "symbol": "X404",
                        "emoji": "🏹",
                        "priceUsd": 0,
                        "priceChange1h": "0%",
                        "priceChange24h": "0%",
                        "priceChange7d": "0%",
                        "liquidityUsd": 0,
                        "volume24h": 0,
                        "holders": 0,
                        "pairCreated": "01/01/2020 00h00",
                        "fdv": 0,
                        "last_updated": "01/01/2020 00h00",
                        "imageUrl": "https://github.com/Crymores/Prof-Xpet/blob/main/img-xpet/x404r.jpg?raw=true"
                    }
                },
                "apiCallCount": 0
            }
            await file.write(json.dumps(default_data, indent=4))
    if not os.path.exists(ALERTS_FILE_PATH):
        async with aiofiles.open(ALERTS_FILE_PATH, 'w', encoding='utf-8') as file:
            default_data = {}
            await file.write(json.dumps(default_data, indent=4))

async def read_token_data_async():
    await create_files()
    async with aiofiles.open(FILE_PATH, 'r', encoding='utf-8') as json_file:
        return json.loads(await json_file.read())

async def read_alerts_data_async():
    await create_files()
    async with aiofiles.open(ALERTS_FILE_PATH, 'r', encoding='utf-8') as file:
        return json.loads(await file.read())

async def save_alerts_data_async(alerts):
    async with aiofiles.open(ALERTS_FILE_PATH, 'w', encoding='utf-8') as file:
        await file.write(json.dumps(alerts, indent=4))

async def save_token_data_async(data):
    async with aiofiles.open(FILE_PATH, 'w', encoding='utf-8') as file:
        await file.write(json.dumps(data, indent=4))

@tasks.loop(seconds=UPDATE_JSON_INTERVAL)
async def fetch_token_info():
    url = "https://api.dexscreener.com/latest/dex/tokens/"
    async with aiohttp.ClientSession() as session:
        data = await read_token_data_async()
        for token, info in data.get('tokens', {}).items():
            try:
                async with session.get(f"{url}{info['address']}") as response:
                    if response.status == 200:
                        dex_data = await response.json()
                        pair_data = dex_data['pairs'][0]
                        price_change_1h = pair_data['priceChange']['h1']
                        price_change_24h = pair_data['priceChange']['h24']
                        price_change_7d = pair_data['priceChange'].get('d7', 'N/A')
                        volume_24h = pair_data['volume']['h24']
                        holders = pair_data.get('holders', 'N/A')
                        pair_created = datetime.fromtimestamp(pair_data['pairCreatedAt']).strftime('%d/%m/%Y %Hh%M')
                        
                        price_change_1h_str = f"+{price_change_1h}%" if price_change_1h > 0 else f"{price_change_1h}%"
                        price_change_24h_str = f"+{price_change_24h}%" if price_change_24h > 0 else f"{price_change_24h}%"
                        price_change_7d_str = f"+{price_change_7d}%" if price_change_7d != 'N/A' and price_change_7d > 0 else f"{price_change_7d}%"
                        
                        last_updated = datetime.now().strftime('%d/%m/%Y %Hh%M')
                        info.update({
                            "priceUsd": pair_data['priceUsd'],
                            "priceChange1h": price_change_1h_str,
                            "priceChange24h": price_change_24h_str,
                            "priceChange7d": price_change_7d_str,
                            "liquidityUsd": pair_data['liquidity']['usd'],
                            "volume24h": volume_24h,
                            "holders": holders,
                            "pairCreated": pair_created,
                            "fdv": pair_data['fdv'],
                            "last_updated": last_updated
                        })
                        data['apiCallCount'] = data.get('apiCallCount', 0) + 1
                    else:
                        print(f"Erreur {response.status} lors de la récupération des données pour le token {token}")
            except Exception as e:
                print(f"Erreur lors de la récupération des données pour le token {token}: {e}")
        await save_token_data_async(data)

@tasks.loop(seconds=STATUS_UPDATE_INTERVAL)
async def update_token_data_and_status():
    token_data = await read_token_data_async()
    tokens = token_data['tokens']
    for token_name, token_info in tokens.items():
        if token_info.get('priceUsd'):
            status_message = f"{token_info['emoji']} {token_name.upper()}: {token_info['priceUsd']}$💵"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)
            status_message = f"{token_info['emoji']} {token_name.upper()}: 1h: {token_info['priceChange1h']}, 24h: {token_info['priceChange24h']}"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)
            status_message = f"{token_info['emoji']} {token_name.upper()}: FDV🔮:{token_info['fdv']}$💸"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)

@bot.slash_command(name="info", description="Obtenez les informations détaillées pour un crypto-token spécifié.")
async def info(ctx):
    token_data = await read_token_data_async()
    select_menu = discord.ui.Select(placeholder="Choisissez une crypto-monnaie",
                                    options=[discord.SelectOption(label=token_data['tokens'][key]['symbol'],
                                                                  description=token_data['tokens'][key]['address'],
                                                                  value=key) for key in token_data['tokens']])

    async def select_callback(interaction: discord.Interaction):
        token_key = select_menu.values[0]
        token_info = token_data['tokens'][token_key]
        embed = discord.Embed(title=f"{token_info['symbol']} Info", color=discord.Color.blue())
        embed.set_thumbnail(url=token_info.get('imageUrl', ''))
        embed.add_field(name="Prix USD", value=f"{token_info['priceUsd']} $", inline=True)
        embed.add_field(name="Changement de prix (1h)", value=f"{token_info['priceChange1h']}", inline=True)
        embed.add_field(name="Changement de prix (24h)", value=f"{token_info['priceChange24h']}", inline=True)
        embed.add_field(name="Changement de prix (7j)", value=f"{token_info['priceChange7d']}", inline=True)
        embed.add_field(name="Liquidité USD", value=f"${token_info['liquidityUsd']}", inline=True)
        embed.add_field(name="Volume (24h)", value=f"${token_info['volume24h']}", inline=True)
        embed.add_field(name="Nombre de holders", value=f"{token_info['holders']}", inline=True)
        embed.add_field(name="Date de création du pair", value=f"{token_info['pairCreated']}", inline=True)
        embed.add_field(name="Valeur FDV", value=f"${token_info['fdv']}", inline=True)
        embed.add_field(name="Dernière mise à jour", value=f"{token_info['last_updated']}", inline=False)
        embed.add_field(name="Adresse du contrat", value=f"`{token_info['address']}`", inline=False)
        await interaction.response.edit_message(content="", embed=embed, view=None)

    select_menu.callback = select_callback
    view = discord.ui.View()
    view.add_item(select_menu)
    await ctx.respond("Sélectionnez un token pour obtenir des informations:", view=view)

@bot.slash_command(name="alert", description="Définir une alerte de prix pour un token spécifié.")
async def alert(ctx):
    token_data = await read_token_data_async()

    if not token_data.get('tokens'):
        await ctx.respond("Erreur lors de la récupération des tokens. Veuillez réessayer plus tard.", ephemeral=True)
        return

    select_menu = discord.ui.Select(placeholder="Choisissez un token",
                                    options=[discord.SelectOption(label=token['symbol'], description=token['address'], value=token['symbol'])
                                             for token in token_data['tokens'].values()],
                                    row=0)

    async def select_callback(interaction: discord.Interaction):
        selected_token = select_menu.values[0]
        await interaction.response.send_modal(PriceTargetModal(selected_token))

    select_menu.callback = select_callback
    view = discord.ui.View()
    view.add_item(select_menu)
    await ctx.respond("Veuillez sélectionner un token pour définir une alerte :", view=view, ephemeral=True)

class PriceTargetModal(discord.ui.Modal):
    def __init__(self, token_symbol: str, *args, **kwargs):
        super().__init__(*args, title="Définir le Prix Cible", **kwargs)
        self.token_symbol = token_symbol
        self.add_item(discord.ui.InputText(label="Prix Cible", style=discord.InputTextStyle.short))

    async def callback(self, interaction: discord.Interaction):
        try:
            target_price = float(self.children[0].value)
            if target_price <= 0:
                raise ValueError("Le prix cible doit être un nombre positif.")
        except ValueError as e:
            await interaction.response.send_message(f"Erreur: {str(e)}", ephemeral=True)
            return

        alerts = await read_alerts_data_async()
        user_id = str(interaction.user.id)
        alerts.setdefault(user_id, []).append({"token": self.token_symbol, "target_price": target_price})
        await save_alerts_data_async(alerts)
        await interaction.response.send_message(f"Alerte définie pour {self.token_symbol} à ${target_price}.", ephemeral=True)

@tasks.loop(seconds=60)
async def check_price_alerts():
    alerts = await read_alerts_data_async()
    token_data = await read_token_data_async()

    for user_id_str, user_alerts in alerts.items():
        try:
            user_id = int(user_id_str)
            user = await bot.fetch_user(user_id)
        except ValueError:
            continue
        except discord.NotFound:
            continue
        except Exception as e:
            print(f"Erreur lors de la récupération de l'utilisateur {user_id}: {e}")
            continue

        alerts_to_remove = []
        for alert in user_alerts:
            token_symbol = alert['token'].upper()
            token_info = token_data['tokens'].get(token_symbol)

            if not token_info:
                continue

            current_price = float(token_info['priceUsd'])
            target_price = float(alert['target_price'])
            if current_price >= target_price or current_price <= target_price:
                embed = discord.Embed(title=f"🚨 Alerte: {token_symbol} Alerte de Prix", color=discord.Color.red())
                embed.add_field(name="Prix Actuel", value=f"${current_price}", inline=False)
                embed.add_field(name="Prix Cible", value=f"${target_price}", inline=False)
                embed.set_thumbnail(url='https://github.com/Crymores/Prof-Xpet/blob/main/img-xpet/alertxpet/alert8.jpeg?raw=true')
                await user.send(embed=embed)
                alerts_to_remove.append(alert)

        for alert in alerts_to_remove:
            user_alerts.remove(alert)

    await save_alerts_data_async(alerts)

@tasks.loop(hours=168)  # 168 heures = 7 jours
async def weekly_summary():
    token_data = await read_token_data_async()
    alerts_data = await read_alerts_data_async()
    channel = bot.get_channel(WEEKLY_SUMMARY_CHANNEL_ID)
    
    if not channel:
        print("Le canal de résumé hebdomadaire est introuvable.")
        return

    embed = discord.Embed(title="Résumé Hebdomadaire des Tokens", color=discord.Color.green())
    price_data = {}

    for token_symbol, token_info in token_data['tokens'].items():
        if token_symbol not in price_data:
            price_data[token_symbol] = {
                "prices": [],
                "dates": [],
            }

        current_price = float(token_info['priceUsd'])
        last_updated = datetime.strptime(token_info['last_updated'], '%d/%m/%Y %Hh%M')
        price_data[token_symbol]['prices'].append(current_price)
        price_data[token_symbol]['dates'].append(last_updated)

        embed.add_field(name=token_symbol, value=f"Prix: {current_price}$\nVolume: {token_info['liquidityUsd']}$", inline=False)

    # Generate plots for each token
    for token_symbol, data in price_data.items():
        plt.figure()
        plt.plot(data['dates'], data['prices'], marker='o')
        plt.title(f"Prix de {token_symbol} sur la semaine")
        plt.xlabel("Date")
        plt.ylabel("Prix USD")
        plt.grid(True)
        plt.tight_layout()
        file_path = f"weekly_summary_{token_symbol}.png"
        plt.savefig(file_path)
        plt.close()
        await channel.send(file=discord.File(file_path))
        os.remove(file_path)

    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Erreur lors de l'envoi du message au canal: {e}")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await create_files()  # Crée les fichiers JSON au démarrage si nécessaire
    fetch_token_info.start()
    update_token_data_and_status.start()
    check_price_alerts.start()
    weekly_summary.start()

bot.run(TOKEN)
