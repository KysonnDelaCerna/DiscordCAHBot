import os
from re import S

import discord
from dotenv import load_dotenv
import gspread
import json

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

gameStarted = False
players = []
czar = 0
prompts = []
responses = []

@client.event
async def on_ready():
    global prompts
    global responses

    print(f'{client.user} has connected to Discord!')

    with open("sheets.json", "r") as json_file:
        sheet_details = json.load(json_file)
        service_account = gspread.service_account(filename="service_account.json")

        for [spreadsheet_name, worksheet_name] in sheet_details:
            spreadsheet = service_account.open(spreadsheet_name)
            worksheet = spreadsheet.worksheet(worksheet_name)
            black = [card for card in worksheet.col_values(1) if card]
            white = [card for card in worksheet.col_values(2) if card]
            black.pop(0)
            white.pop(0)

            prompts.extend(black)
            responses.extend(white)
            print(f'Loaded {spreadsheet_name}')
        
        print("Finished loading cards")

@client.event
async def on_message(message):
    global players
    global gameStarted

    if message.author == client.user:
        return

    if len(message.content) > 3 and message.content[:3].lower() == "cah":
        arguments = message.content.split(" ")
        if len(arguments) <= 1:
            return
        
        arguments[1] = arguments[1].lower()

        if arguments[1] == "join":
            index = -1

            for i in range(len(players)):
                if players[i][0] == message.author.id:
                    index = i
                    break
            
            if index == -1:
                players.append((message.author.id, message.author.name, 0))
                await message.add_reaction('\N{THUMBS UP SIGN}')

        elif arguments[1] == "leave":
            index = -1

            for i in range(len(players)):
                if players[i][0] == message.author.id:
                    index = i
                    break
            
            if index != -1:
                players.pop(index)
                await message.add_reaction('\N{THUMBS UP SIGN}')

        elif arguments[1] == "start":
            gameStarted = True
            await message.add_reaction('\N{THUMBS UP SIGN}')

        elif arguments[1] == "end":
            gamestarted = False
            players = []
            await message.add_reaction('\N{THUMBS UP SIGN}')

        elif arguments[1] == "list":
            response = ""
            if not players:
                response = "No players have joined yet"
            else:
                for i in range(len(players)):
                    response += str(i + 1) + ". " + players[i][1]
                    if i != len(players) - 1:
                        response += "\n"
            await message.channel.send(response)
            
client.run(TOKEN)