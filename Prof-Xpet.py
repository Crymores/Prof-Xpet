import discord
from discord.ext import tasks, commands
import aiohttp
import json
import asyncio
from datetime import datetime
import os

TOKEN = 'votre_token_de_bot_discord'  # Stockez votre token de manière sécurisée
FILE_PATH = 'tokens_info.json'  # Assurez-vous que le chemin est correct
UPDATE_INTERVAL = 15 * 60  # 15 minutes en secondes
STATUS_UPDATE_INTERVAL = 10  # 10 secondes entre les mises à jour de statut

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = discord.app_commands.CommandTree(bot)

# Fonction de lecture du fichier JSON
def read_token_data():
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r') as json_file:
            return json.load(json_file)
    else:
        print(f"Le fichier {FILE_PATH} n'existe pas.")
        return {"tokens": {}}

# Fonction pour récupérer les informations des tokens
async def fetch_token_info():
    url = "https://api.dexscreener.com/latest/dex/tokens/"
    async with aiohttp.ClientSession() as session:
        data = read_token_data()
        for token, info in data['tokens'].items():
            try:
                response = await session.get(f"{url}{info['address']}")
                if response.status == 200:
                    dex_data = await response.json()
                    pair_data = dex_data['pairs'][0]
                    info.update({
                        "priceUsd": pair_data['priceUsd'],
                        "priceChange1h": pair_data['priceChange']['h1'],
                        "priceChange24h": pair_data['priceChange']['h24'],
                        "liquidityUsd": pair_data['liquidity']['usd'],
                        "fdv": pair_data['fdv'],
                        "last_updated": datetime.now().isoformat()
                    })
                    data['apiCallCount'] += 1
            except Exception as e:
                print(f"Erreur lors de la récupération des données pour le token {token}: {e}")
        with open(FILE_PATH, 'w') as json_file:
            json.dump(data, json_file, indent=4)

@tasks.loop(seconds=UPDATE_INTERVAL)
async def update_token_data_and_status():
    await fetch_token_info()
    await rotate_status()

async def rotate_status():
    token_data = read_token_data()
    tokens = token_data['tokens']
    for token_name, token_info in tokens.items():
        if token_info.get('priceUsd'):  # Vérifiez si le prix est non null
            status_message = f"{token_info['emoji']} {token_name.upper()}: ${token_info['priceUsd']} USD (1h: {token_info['priceChange1h']}%, 24h: {token_info['priceChange24h']}%), FDV: {token_info['fdv']}"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)

@tree.command(name="info", description="Obtenez les informations détaillées pour un crypto-token spécifié.")
async def crypto_info(interaction: discord.Interaction, token: str):
    token_data = read_token_data()
    token_info = token_data['tokens'].get(token.lower())
    if token_info:
        embed = discord.Embed(title=f"{token.upper()} Info", color=discord.Color.blue())
        embed.add_field(name="Prix USD", value=f"{token_info['priceUsd']} $", inline=True)
        embed.add_field(name="Prix EUR", value="Non disponible", inline=True)
        embed.add_field(name="Total Supply", value=token_info['liquidityToken'], inline=True)
        embed.add_field(name="Max Supply", value=token_info['fdv'], inline=True)
        embed.set_thumbnail(url=token_info['imageUrl'])  # Utilisez l'URL de l'image du token
        embed.set_footer(text=f"Dernière mise à jour: {token_info['lastUpdated'] or 'Non disponible'}")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("Informations non trouvées pour le token spécifié.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    update_token_data_and_status.start()

bot.run(TOKEN)
