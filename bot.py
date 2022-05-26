from importlib.machinery import WindowsRegistryFinder
import os

import discord
from dotenv import load_dotenv
import gspread
import json
from copy import deepcopy
from random import randint

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
POINTS_TO_WIN = int(os.getenv('POINTS_TO_WIN'))
HAND_SIZE = int(os.getenv('HAND_SIZE'))
MAX_PLAYERS = int(os.getenv('MAX_PLAYERS'))
PROMPTS = []
RESPONSES = []

client = discord.Client()

game_started = False
players = []
czar = 0
current_prompt = None
prompts_copy = []
responses_copy = []
waiting_for = []
answers = []
czar_chosen = 0
channel = None

@client.event
async def on_ready():
    global PROMPTS
    global RESPONSES

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

            PROMPTS.extend(black)
            RESPONSES.extend(white)
            print(f'Loaded {spreadsheet_name}')
        
        print("Finished loading cards")

@client.event
async def on_message(message):
    global players
    global game_started
    global MAX_PLAYERS
    global channel

    if message.author == client.user:
        return

    if str(message.channel.type) == "text" and len(message.content) > 3 and message.content[:3].lower() == "cah":
        arguments = message.content.split(" ")
        if len(arguments) <= 1:
            return
        
        arguments[1] = arguments[1].lower()

        if arguments[1] == "join":
            if len(players) >= MAX_PLAYERS:
                return

            index = -1

            for i in range(len(players)):
                if players[i][0] == message.author.id:
                    index = i
                    break
            
            if index == -1:
                players.append((message.author.id, message.author.name, 0, []))
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
            if len(players) >= 3:
                game_started = True
                channel = message.channel
                await start_game()
                await message.add_reaction('\N{THUMBS UP SIGN}')
            else:
                await message.channel.send("Not enough players to start the game.")

        elif arguments[1] == "end":
            end_game()
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
            
    if str(message.channel.type) == "private":
        # 1. check if we're waiting input from user
        if message.author.id not in waiting_for:
            return
        else:
            # 2. check if input is valid
            indices = message.content.split(", ")
            valid = True

            for i in range(len(indices)):
                if not index[i].isdigit():
                    valid = False
                    break
                index[i] = int(index[i])
                if index[i] < 1 or index[i] > HAND_SIZE:
                    valid = False
                    break
            
            set_indices = set(indices)
            if len(set_indices) != indices:
                valid = False
            
            if len(set_indices) != current_prompt.count("_"):
                valid = False

            # 3. update game state
            if valid:
                waiting_for.remove(message.author.id)

                player_index = -1
                for i in range(len(players)):
                    if players[i][0] == message.author.id:
                        player_index = i

                if player_index != -1:
                    answer = ([], message.author.id)
                    for index in indices:
                        answer[0].append(players[player_index][3][index - 1])
                    indices.sort(reverse=True)
                    for index in indices:
                        players[player_index][3].pop(index - 1)
                    
                    answers.append(answer)
        
        # 1. if czar and everyone already submitted
        if not waiting_for and message.author.id == players[czar][0]:
            if not message.content.isdigit():
                return
            index = int(message.content)
            if index < 1 or index > len(answers):
                return
            czar_chosen = index

async def message_player(id, message):
    try:
        user = await client.fetch_user(id)
        await user.send(message)
    except:
        print("Something went wrong when messaging player")

async def start_game():
    prompts_copy = deepcopy(PROMPTS)
    responses_copy = deepcopy(RESPONSES)

    while game_started:
        # 1. draw
        for player in players:
            while len(player[3]) < HAND_SIZE:
                if len(responses_copy) < 1:
                    responses_copy = deepcopy(RESPONSES)
                index = randint(1, len(responses_copy) - 1)
                player[3].append(responses_copy[index])
                responses_copy.pop(index)

        # 2. pick black card, inform everyone
        if len(prompts_copy) < 1:
            prompts_copy = deepcopy(PROMPTS)
        prompt_index = randint(1, len(prompts_copy) - 1)
        current_prompt = prompts_copy[prompt_index]
        prompts_copy.pop(prompt_index)

        for i in range(len(players)):
            message_player(player[i][0], "The black card is", current_prompt)

            if i == czar:
                message_player(player[i][0], "You are the czar.")
            else:
                waiting_for.append(player[i][0])
                card_text = ""
                for j in range(HAND_SIZE):
                    card_text += str(j + 1) + ". " + player[i][3][j]
                    if j != HAND_SIZE - 1:
                        card_text += "\n"
                message_player(player[i][0], "You're cards are:\n" + card_text)

        # 3. wait until everyone picks
        while waiting_for:
            pass

        # 4. wait until czar chooses winner
        czar_chosen = 0

        answer_text = ""
        for i in range(len(answers)):
            answer_text += str(i + 1) + ". " + answers[0].join("\n")
            if i != len(answers - 1):
                answer_text += "\n"
        message_player(player[i][0], "The players reponses were:\n", answer_text)

        while czar_chosen == 0:
            pass

        winner_index = -1
        for i in range(len(players)):
            if answers[czar_chosen - 1][1] == players[i][0]:
                winner_index = i

        if winner_index != -1:
            if channel:
                await channel.message("The winner is", players[i][1])
                await channel.message("The black card was:", current_prompt)

                await channel.message(players[i][1] + "'s answer was", answers[czar_chosen - 1][0].join("\n"))

        # 5. check if game is over
        czar = (czar + 1) % len(players)
        if winner_index != -1:
            players[winner_index][2] += 1
            if players[winner_index][2] >= POINTS_TO_WIN:
                channel.message(players[winner_index][1], "has won!")
                end_game()

def end_game():
    game_started = False
    players = []
    czar = 0
    prompts_copy = []
    responses_copy = []
    waiting_for = []
    answers = []
    czar_chosen = 0
    channel = None

client.run(TOKEN)