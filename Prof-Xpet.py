import discord
from discord.ext import tasks
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands
import aiohttp
import json
from datetime import datetime
import asyncio
import os

TOKEN = 'tokendidi'  # Assurez-vous de stocker votre token de manière sécurisée
FILE_PATH = 'tokens_info.json'  # Assurez-vous que le chemin est correct
ALERTS_FILE_PATH = 'alerts_info.json'
UPDATE_JSON_INTERVAL = 10 * 60  # 10 minutes en secondes
STATUS_UPDATE_INTERVAL = 30  #  secondes

# Initialisation du bot
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
            status_message = f"{token_info['emoji']} {token_name.upper()}: {token_info['priceUsd']}$💵"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)
            
            # Définir le statut pour la variation 1h et 24h
            status_message = f"{token_info['emoji']} {token_name.upper()}: 1h: {token_info['priceChange1h']}, 24h: {token_info['priceChange24h']}"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)
            
            # Définir le statut pour le FDV
            status_message = f"{token_info['emoji']} {token_name.upper()}: FDV🔮:{token_info['fdv']}$💸"
            await bot.change_presence(activity=discord.Game(name=status_message))
            await asyncio.sleep(STATUS_UPDATE_INTERVAL)
            
            

@bot.slash_command(name="info", description="Obtenez les informations détaillées pour un crypto-token spécifié.")
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
        embed.add_field(name="Changement de prix (1h)", value=f"{token_info['priceChange1h']}", inline=True)
        embed.add_field(name="Changement de prix (24h)", value=f"{token_info['priceChange24h']}", inline=True)
        embed.add_field(name="Liquidité USD", value=f"${token_info['liquidityUsd']}", inline=True)
        embed.add_field(name="Valeur FDV", value=f"${token_info['fdv']}", inline=True)
        embed.add_field(name="Dernière mise à jour", value=f"{token_info['last_updated']}", inline=False)
        embed.add_field(name="Adresse du contrat", value=f"`{token_info['address']}`", inline=False)  # Ajoutez cette ligne
        # Envoyer l'embed à l'utilisateur
        await interaction.response.edit_message(content="", embed=embed, view=None)

    # Ajouter le callback au menu de sélection
    select_menu.callback = select_callback

    # Envoyer un message à l'utilisateur avec le menu de sélection
    await interaction.response.send_message("Sélectionnez un token pour obtenir des informations:", view=view)



@bot.slash_command(name="alert", description="Définir une alerte de prix pour un token spécifié.")
async def alert(interaction: discord.Interaction):
    token_data = read_token_data()  # Assurez-vous d'attraper les erreurs de lecture du fichier ici

    # Vérifiez que token_data contient bien les données attendues
    if not token_data.get('tokens'):
        await interaction.response.send_message("Erreur lors de la récupération des tokens. Veuillez réessayer plus tard.", ephemeral=True)
        return

    # Créez un menu déroulant pour la sélection des tokens
    select_menu = discord.ui.Select(placeholder="Choisissez un token",
                                    options=[discord.SelectOption(label=token['symbol'], description=token['address'], value=token['symbol'])
                                             for token in token_data['tokens'].values()],
                                    row=0)

    # Définissez le callback pour la sélection du token
    async def select_callback(interaction: discord.Interaction, select: discord.ui.Select):
        # Demandez à l'utilisateur d'entrer le prix cible
        await interaction.response.send_modal(PriceTargetModal(select.values[0]))  # Utilisez un modal pour l'entrée du prix

    select_menu.callback = select_callback

    # Ajoutez le menu de sélection à une vue et envoyez-le
    view = discord.ui.View()
    view.add_item(select_menu)
    await interaction.response.send_message("Veuillez sélectionner un token pour définir une alerte :", view=view, ephemeral=True)

class PriceTargetModal(discord.ui.Modal):
    def __init__(self, token_symbol: str, *args, **kwargs):
        super().__init__(*args, title="Définir le Prix Cible", **kwargs)
        self.token_symbol = token_symbol
        self.add_item(discord.ui.InputText(label="Prix Cible", style=discord.InputTextStyle.short))

    async def callback(self, interaction: discord.Interaction):
        try:
            target_price = float(self.children[0].value)  # Convertissez le prix cible en float
            if target_price <= 0:
                raise ValueError("Le prix cible doit être un nombre positif.")
        except ValueError as e:
            await interaction.response.send_message(f"Erreur: {str(e)}", ephemeral=True)
            return

        # Récupérez les alertes existantes et ajoutez la nouvelle alerte
        alerts = read_alerts_data()  # Assurez-vous d'attraper les erreurs de lecture du fichier ici
        user_id = str(interaction.user.id)
        alerts.setdefault(user_id, []).append({"token": self.token_symbol, "target_price": target_price})
        save_alerts_data(alerts)  # Attrapez les erreurs potentielles d'écriture de fichier

        await interaction.response.send_message(f"Alerte définie pour {self.token_symbol} à ${target_price}.", ephemeral=True)


@tasks.loop(seconds=60)
async def check_price_alerts():
    alerts = read_alerts_data()
    token_data = read_token_data()  # Lire les données des tokens une fois pour toutes les alertes

    for user_id_str, user_alerts in alerts.items():
        try:
            user_id = int(user_id_str)  # Assurez-vous que c'est un entier valide
            user = await bot.fetch_user(user_id)
            # Votre logique d'alerte ici
        except ValueError:
            print(f"L'ID d'utilisateur {user_id_str} n'est pas un entier valide.")
            continue  # Passe au prochain ID si celui-ci est invalide
        except discord.NotFound:
            print(f"Utilisateur avec l'ID {user_id} non trouvé.")
            continue
        except Exception as e:
            print(f"Erreur lors de la récupération de l'utilisateur {user_id}: {e}")
            continue
        
        for alert in user_alerts[:]:  # Itérer sur une copie pour pouvoir modifier la liste originale
            token_symbol = alert['token'].upper()
            token_info = token_data['tokens'].get(token_symbol)

            if not token_info:
                print(f"Token {token_symbol} introuvable dans les données des tokens.")
                continue  # Passez à l'alerte suivante si les informations sur le token ne sont pas trouvées

            try:
                if float(token_info['priceUsd']) >= alert['target_price']:
                    embed = discord.Embed(title=f"🚨 Alerte: {token_symbol} Alerte de Prix", color=discord.Color.red())
                    embed.add_field(name="Prix Actuel", value=f"${token_info['priceUsd']}", inline=False)
                    embed.add_field(name="Prix Cible", value=f"${alert['target_price']}", inline=False)
                    embed.set_thumbnail(url='https://github.com/Crymores/Prof-Xpet/blob/main/img-xpet/alerte3.jpeg?raw=true')  
                    await user.send(embed=embed)
                    user_alerts.remove(alert)  # Supprimez l'alerte après notification
            except Exception as e:
                print(f"Erreur lors de la vérification/envoi de l'alerte pour {user_id} et le token {token_symbol}: {e}")
                continue  # Passez à l'alerte suivante en cas d'erreur

    save_alerts_data(alerts)  # Sauvegarder les modifications apportées aux alertes



with open('help_commands.json', 'r', encoding='utf-8') as f:
    commands_help_data = json.load(f)

class HelpMenu(discord.ui.View):
    def __init__(self):
        super().__init__()
        # Extraire les commandes disponibles
        commands_help = commands_help_data.get("help", {}).get("commands", {}).get("items", [])
        options = [
            discord.SelectOption(label=command["command"], description=command.get("description", "No description available")[:100], value=command["command"])
            for command in commands_help
        ]
        # Création du menu de sélection
        self.select_menu = discord.ui.Select(placeholder='Choisissez une commande pour obtenir de l aide', options=options)
        self.select_menu.callback = self.handle_menu
        self.add_item(self.select_menu)

    async def handle_menu(self, interaction: discord.Interaction, select: discord.ui.Select):
        command_info = next((item for item in commands_help_data.get("help", {}).get("commands", {}).get("items", []) if item["command"] == select.values[0]), None)

        if command_info:
            embed = discord.Embed(title=command_info["command"], description=command_info["description"])
            if command_info.get("image") and command_info["image"] != "null":
                embed.set_image(url=command_info["image"])
            await interaction.response.edit_message(content="", embed=embed, view=None)
        else:
            await interaction.response.send_message("Commande non trouvée.", ephemeral=True)

class HelpBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        @self.command(name="help", description="Affiche les informations daide pour les commandes disponibles.")
        async def help_command(ctx):
            view = HelpMenu()
            await ctx.send("Sélectionnez une commande pour obtenir de l'aide:", view=view)

intents = discord.Intents.default()
bot = HelpBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await fetch_token_info()  # Utilisez await ici pour exécuter la fonction asynchrone
    update_token_data_and_status.start()
    check_price_alerts.start()  # Démarrer la tâche de vérification des alertes
bot.run(TOKEN)
