import discord
from discord.ext import tasks
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands
import aiohttp
import json
from datetime import datetime
import asyncio
import os

TOKEN = ''  # Assurez-vous de stocker votre token de manière sécurisée
FILE_PATH = 'tokens_info.json'  # Assurez-vous que le chemin est correct
ALERTS_FILE_PATH = 'alerts_info.json'
UPDATE_JSON_INTERVAL = 10 * 60  # 10 minutes en secondes
STATUS_UPDATE_INTERVAL = 30  #  secondes

intents = discord.Intents.default()  # Ou `discord.Intents.all()` pour tous les intents
intents.messages = True  # Assurez-vous d'activer les intents dont vous avez besoin
bot = commands.Bot(command_prefix="!", intents=intents)

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
async def info(ctx):  # Suppression du paramètre `token` inutilisé dans cet exemple
    # Lire les données des tokens
    token_data = read_token_data()

    # Créer un menu de sélection
    select_menu = discord.ui.Select(placeholder="Choisissez une crypto-monnaie",
                                    options=[discord.SelectOption(label=token_data['tokens'][key]['symbol'],
                                                                  description=token_data['tokens'][key]['address'],
                                                                  value=key) for key in token_data['tokens']])

    # Définir la fonction callback pour le menu de sélection
    async def select_callback(interaction: discord.Interaction):
        # Logique de callback identique, assurez-vous juste qu'elle est définie dans la portée appropriée

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
        embed.add_field(name="Adresse du contrat", value=f"`{token_info['address']}`", inline=False)
        
        await interaction.response.edit_message(content="", embed=embed, view=None)

    select_menu.callback = select_callback  # Assignez le callback au menu de sélection

    # Créer une vue qui contient le menu de sélection
    view = discord.ui.View()
    view.add_item(select_menu)

    # Envoyer un message à l'utilisateur avec le menu de sélection
    # Notez l'utilisation de `ctx.respond()` pour répondre à une commande slash
    await ctx.respond("Sélectionnez un token pour obtenir des informations:", view=view)



@bot.slash_command(name="alert", description="Définir une alerte de prix pour un token spécifié.")
async def alert(interaction: discord.Interaction):
    token_data = read_token_data()  # Assurez-vous d'attraper les erreurs de lecture du fichier ici

    if not token_data.get('tokens'):
        await interaction.response.send_message("Erreur lors de la récupération des tokens. Veuillez réessayer plus tard.", ephemeral=True)
        return

    select_menu = discord.ui.Select(placeholder="Choisissez un token",
                                    options=[discord.SelectOption(label=token['symbol'], description=token['address'], value=token['symbol'])
                                             for token in token_data['tokens'].values()],
                                    row=0)

    async def select_callback(interaction: discord.Interaction):
        # Cette ligne a été modifiée pour accéder directement aux valeurs sélectionnées
        selected_token = interaction.data['values'][0]
        # Utilisez un modal pour demander le prix cible
        await interaction.response.send_modal(PriceTargetModal(selected_token))

    select_menu.callback = select_callback

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
                    embed.set_thumbnail(url='https://github.com/Crymores/Prof-Xpet/blob/main/img-xpet/alertxpet/alert8.jpeg?raw=true')  
                    await user.send(embed=embed)
                    user_alerts.remove(alert)  # Supprimez l'alerte après notification
            except Exception as e:
                print(f"Erreur lors de la vérification/envoi de l'alerte pour {user_id} et le token {token_symbol}: {e}")
                continue  # Passez à l'alerte suivante en cas d'erreur

    save_alerts_data(alerts)  # Sauvegarder les modifications apportées aux alertes



@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    fetch_token_info.start()  # Avec py-cord, vous n'avez plus besoin d'utiliser `await` ici
    update_token_data_and_status.start()
    check_price_alerts.start()

bot.run(TOKEN)
