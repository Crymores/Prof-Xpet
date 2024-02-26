import discord
from discord.ext import tasks
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands
import aiohttp
import json
from datetime import datetime
import asyncio
import os

TOKEN = 'Token'  # Assurez-vous de stocker votre token de manière sécurisée
FILE_PATH = 'tokens_info.json'  # Assurez-vous que le chemin est correct
ALERTS_FILE_PATH = 'alerts_info.json'
UPDATE_JSON_INTERVAL = 15 * 60  # 15 minutes en secondes
STATUS_UPDATE_INTERVAL = 30  # 1 minute en secondes

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)

# Fonction de lecture du fichier JSON
def read_token_data():
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r', encoding='utf-8') as json_file:  # Spécifiez l'encodage ici
            return json.load(json_file)
    else:
        print(f"Le fichier {FILE_PATH} n'existe pas.")
        return {"tokens": {}}

def read_alerts_data():
    if os.path.exists('alerts_data.json'):
        with open('alerts_data.json', 'r', encoding='utf-8') as file:
            return json.load(file)
    else:
        return {}  # Retourne un dictionnaire vide si le fichier n'existe pas

def save_alerts_data(alerts):
    with open('alerts_data.json', 'w', encoding='utf-8') as file:
        json.dump(alerts, file, indent=4)
        
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

@tasks.loop(seconds=STATUS_UPDATE_INTERVAL)
async def update_token_data_and_status():
    token_data = read_token_data()  # Lire les données depuis le fichier JSON
    tokens = token_data['tokens']
    
    for token_name, token_info in tokens.items():
        if token_info.get('priceUsd'):
            # Définir le statut pour le prix
            status_message = f"{token_info['emoji']} {token_name.upper()}: ${token_info['priceUsd']} USD"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)
            
            # Définir le statut pour la variation 1h et 24h
            status_message = f"{token_info['emoji']} {token_name.upper()}: 1h: {token_info['priceChange1h']}%, 24h: {token_info['priceChange24h']}%"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)
            
            # Définir le statut pour le FDV
            status_message = f"{token_info['emoji']} {token_name.upper()}: FDV:{token_info['fdv']}$"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)
            
            
# Créez un groupe de commandes slash
crypto = SlashCommandGroup("crypto", "Commandes relatives aux crypto-monnaies")

@crypto.command(name="info", description="Obtenez les informations détaillées pour un crypto-token spécifié.")
async def crypto_info(interaction: discord.Interaction):
    # Lire les données des tokens
    token_data = read_token_data()

    # Créer un menu de sélection
    select_menu = discord.ui.Select(placeholder="Choisissez une crypto-monnaie",
                                    options=[discord.SelectOption(label=token_data['tokens'][key]['symbol'],
                                                                  description=token_data['tokens'][key]['address'],
                                                                  value=key) for key in token_data['tokens']])

    # Créer une vue qui contient le menu de sélection
    view = discord.ui.View()
    view.add_item(select_menu)

    # Attendre que l'utilisateur fasse un choix
    async def select_callback(interaction):
        token_key = select_menu.values[0]  # Récupérer la valeur sélectionnée
        token_info = token_data['tokens'][token_key]

        # Créer un embed avec les informations du token
        embed = discord.Embed(title=f"{token_info['symbol']} Info", color=discord.Color.blue())
        embed.set_thumbnail(url=token_info['imageUrl'])
        embed.add_field(name="Prix USD", value=f"{token_info['priceUsd']} $", inline=True)
        embed.add_field(name="Changement de prix (1h)", value=f"{token_info['priceChange1h']}%", inline=True)
        embed.add_field(name="Changement de prix (24h)", value=f"{token_info['priceChange24h']}%", inline=True)
        embed.add_field(name="Liquidité USD", value=f"${token_info['liquidityUsd']}", inline=True)
        embed.add_field(name="Valeur FDV", value=f"${token_info['fdv']}", inline=True)
        embed.add_field(name="Dernière mise à jour", value=f"{token_info['last_updated']}", inline=False)

        # Envoyer l'embed à l'utilisateur
        await interaction.response.edit_message(content="", embed=embed, view=None)

    # Ajouter le callback au menu de sélection
    select_menu.callback = select_callback

    # Envoyer un message à l'utilisateur avec le menu de sélection
    await interaction.response.send_message("Sélectionnez un token pour obtenir des informations:", view=view)



@crypto.command(name="alert", description="Définir une alerte de prix pour un token spécifié.")
async def crypto_alert(interaction: discord.Interaction, 
                       token: Option(str, "Entrez le symbole du token", required=True),
                       target_price: Option(float, "Entrez le prix cible", required=True)):
    user_id = interaction.user.id
    alerts = read_alerts_data()  # Vous devez créer cette fonction pour lire les données d'alerte d'un fichier ou d'une base de données
    
    # Ajouter ou mettre à jour l'alerte pour l'utilisateur
    alerts[user_id] = {
        "token": token,
        "target_price": target_price
    }
    save_alerts_data(alerts)  # Vous devez créer cette fonction pour sauvegarder les données d'alerte

    await interaction.response.send_message(f"Alerte définie pour {token} à ${target_price}.")

@tasks.loop(seconds=60)
async def check_price_alerts():
    alerts = read_alerts_data()
    token_data = read_token_data()
    
    for user_id, alert in alerts.items():
        user = await bot.fetch_user(user_id)
        token_info = token_data['tokens'].get(alert['token'])
        if token_info:
            current_price = float(token_info['priceUsd'])
            if current_price >= alert['target_price']:
                # Créer un embed pour la notification d'alerte
                embed = discord.Embed(title=f"🚨 Alerte: {alert['token']} Alerte de Prix", color=discord.Color.red())
                embed.add_field(name="Prix Actuel", value=f"${current_price}", inline=False)
                embed.add_field(name="Prix Cible", value=f"${alert['target_price']}", inline=False)
                embed.set_thumbnail(url='https://github.com/Crymores/Prof-Xpet/blob/main/img-xpet/alerte.jpg?raw=true')  # Utilisez l'URL de l'image depuis les données du token
                await user.send(embed=embed)
                # Supprimer l'alerte après notification
                del alerts[user_id]
    
    save_alerts_data(alerts)  # Sauvegarder les modifications des alertes
    await asyncio.sleep(60)  # Vérifier les prix toutes les 60 secondes


# Ajoutez le groupe de commandes au bot
bot.add_application_command(crypto)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    update_token_data_and_status.start()
    check_price_alerts.start()  # Démarrer la tâche de vérification des alertes
bot.run(TOKEN)
