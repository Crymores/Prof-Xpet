import discord
from discord.ext import tasks
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands
import aiohttp
import json
from datetime import datetime
import asyncio
import os


TOKEN = 'Token_discord'  # Assurez-vous de stocker votre token de manière sécurisée
FILE_PATH = 'tokens_info.json'  # Assurez-vous que le chemin est correct
ALERTS_FILE_PATH = 'alerts_info.json'
UPDATE_JSON_INTERVAL = 10 * 60  # 10 minutes en secondes
STATUS_UPDATE_INTERVAL = 30  #  secondes

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
@tasks.loop(seconds=UPDATE_JSON_INTERVAL)
async def fetch_token_info():
    url = "https://api.dexscreener.com/latest/dex/tokens/"
    async with aiohttp.ClientSession() as session:
        data = read_token_data()  # Assurez-vous que cette fonction lit correctement le fichier
        for token, info in data.get('tokens', {}).items():
            try:
                response = await session.get(f"{url}{info['address']}")
                if response.status == 200:
                    dex_data = await response.json()
                    pair_data = dex_data['pairs'][0]
                    # Formatage des variations de prix avec signe
                    price_change_1h = pair_data['priceChange']['h1']
                    price_change_24h = pair_data['priceChange']['h24']
                    price_change_1h_str = f"+{price_change_1h}%" if price_change_1h > 0 else f"{price_change_1h}%"
                    price_change_24h_str = f"+{price_change_24h}%" if price_change_24h > 0 else f"{price_change_24h}%"
                    
                    # Formatage de la date
                    last_updated = datetime.now().strftime('%d/%m/%Y %Hh%M')
                    
                    info.update({
                        "priceUsd": pair_data['priceUsd'],
                        "priceChange1h": price_change_1h_str,
                        "priceChange24h": price_change_24h_str,
                        "liquidityUsd": pair_data['liquidity']['usd'],
                        "fdv": pair_data['fdv'],
                        "last_updated": last_updated
                    })
                    data['apiCallCount'] = data.get('apiCallCount', 0) + 1
                else:
                    print(f"Erreur {response.status} lors de la récupération des données pour le token {token}")
            except Exception as e:
                print(f"Erreur lors de la récupération des données pour le token {token}: {e}")
        # Mise à jour du fichier JSON avec les nouvelles données
        with open(FILE_PATH, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, indent=4)

# Assurez-vous que la fonction read_token_data est bien définie et capable de lire le fichier correctement
# Exemple de fonction read_token_data ici pour la cohérence
def read_token_data():
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH, 'r', encoding='utf-8') as json_file:
            return json.load(json_file)
    else:
        print(f"Le fichier {FILE_PATH} n'existe pas.")
        return {"tokens": {}, "apiCallCount": 0}  # Initialiser avec une structure de base si le fichier n'existe pas

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
            status_message = f"{token_info['emoji']} {token_name.upper()}: 1h: {token_info['priceChange1h']}, 24h: {token_info['priceChange24h']}"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)
            
            # Définir le statut pour le FDV
            status_message = f"{token_info['emoji']} {token_name.upper()}: FDV:{token_info['fdv']}$"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)
            
            
# Créez un groupe de commandes slash
crypto = SlashCommandGroup("crypto", "Commandes relatives aux crypto-monnaies")

@crypto.command(name="info", description="Obtenez les informations détaillées pour un crypto-token spécifié.")
async def info(interaction: discord.Interaction):
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
async def alert(interaction: discord.Interaction, 
                token: Option(str, "Entrez le symbole du token", required=True),
                target_price: Option(float, "Entrez le prix cible", required=True)):
    user_id = str(interaction.user.id)  # Ensure the user ID is a string for JSON compatibility
    alerts = read_alerts_data()  # Read existing alerts

    # If the user already has alerts, append to them; otherwise, create a new list
    if user_id in alerts:
        alerts[user_id].append({"token": token, "target_price": target_price})
    else:
        alerts[user_id] = [{"token": token, "target_price": target_price}]

    save_alerts_data(alerts)  # Save updated alerts

    await interaction.response.send_message(f"Alerte définie pour {token} à ${target_price}.")

@tasks.loop(seconds=60)
async def check_price_alerts():
    alerts = read_alerts_data()
    
    for user_id, user_alerts in alerts.items():
        try:
            user_int_id = int(user_id)  # Essayez de convertir en entier
        except ValueError:
            print(f"ID utilisateur invalide : {user_id}")
            continue  # Passez à l'ID utilisateur suivant si la conversion échoue
        
        user = await bot.fetch_user(user_int_id)
        for alert in user_alerts:
            token_info = read_token_data(alert['token'])  # Adjust this to match your token data fetching logic
            if token_info and float(token_info['priceUsd']) >= alert['target_price']:
                embed = discord.Embed(title=f"🚨 Alerte: {alert['token']} Alerte de Prix", color=discord.Color.red())
                embed.add_field(name="Prix Actuel", value=f"${token_info['priceUsd']}", inline=False)
                embed.add_field(name="Prix Cible", value=f"${alert['target_price']}", inline=False)
                # Assuming the image URL is static or you have a way to dynamically fetch it based on the token
                embed.set_thumbnail(url='https://github.com/Crymores/Prof-Xpet/blob/main/img-xpet/alerte3.jpeg?raw=true')  
                await user.send(embed=embed)
                # Instead of deleting, mark for removal or directly remove if your logic permits
                user_alerts.remove(alert)
    
    save_alerts_data(alerts)  # Save any changes to the alerts
    await asyncio.sleep(60)  # Vérifier les prix toutes les 60 secondes


# Ajoutez le groupe de commandes au bot
bot.add_application_command(crypto)


# Charger le fichier JSON contenant les informations d'aide pour les commandes
with open('help_commands.json', 'r') as f:
    commands_help = json.load(f)

class HelpMenu(discord.ui.View):
    def __init__(self, commands_help):
        super().__init__()
        self.commands_help = commands_help
        # Création du menu de sélection avec les noms des commandes disponibles
        options = [
            discord.SelectOption(label=command["name"], description=command["description"][:100])
            for command in self.commands_help["commands_help"]
        ]
        self.select_menu = discord.ui.Select(placeholder='Choisissez une commande pour obtenir de l’aide', options=options)
        self.add_item(self.select_menu)

@discord.ui.select()
async def handle_menu(self, interaction: discord.Interaction, select: discord.ui.Select):
    selected_command_name = select.values[0]
    command_info = next((item for item in self.commands_help["commands_help"] if item["name"] == selected_command_name), None)

    if command_info:
        # Création d'un embed
        embed = discord.Embed(title=command_info["name"])

        # Position de la description
        if command_info["layout"]["description_position"] == "top":
            embed.description = command_info["description"]

        # Ajouter l'image si disponible et ajuster la taille
        if command_info.get("image"):
            embed.set_image(url=command_info["image"])
            # Vous devrez implémenter une logique pour ajuster la taille de l'image.

        # Position de la description (si elle est en bas)
        if command_info["layout"]["description_position"] == "bottom":
            embed.description = command_info["description"]

        # Ajouter les détails supplémentaires
        if command_info.get("details"):
            for key, value in command_info["details"].items():
                embed.add_field(name=key.capitalize(), value=value, inline=False)

        # Envoyer l'embed à l'utilisateur
        await interaction.response.edit_message(embed=embed, view=None)
    else:
        await interaction.response.send_message("Commande non trouvée.", ephemeral=True)

# Chargement du fichier JSON
with open('help_commands.json', 'r') as file:
    data = json.load(file)

commands_help = data['commands_help']


@bot.command(name="help", description="Affiche les informations d'aide pour les commandes disponibles.")
async def help_command(ctx):
    # Créer une instance de la vue contenant le menu de sélection
    view = HelpMenu(commands_help)
    
    # Envoyer le message avec le menu de sélection à l'utilisateur
    await ctx.send("Sélectionnez une commande pour obtenir de l'aide:", view=view)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await fetch_token_info()  # Utilisez await ici pour exécuter la fonction asynchrone
    update_token_data_and_status.start()
    check_price_alerts.start()  # Démarrer la tâche de vérification des alertes
bot.run(TOKEN)
