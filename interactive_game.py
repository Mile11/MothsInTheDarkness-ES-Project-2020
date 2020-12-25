"""
EXPERT SYSTEM PROJECT 2020/2021
Faculty of Electrical Engineering and Computing
FILIP MILIC

Contains the main game module and interface with the user.
"""

import json
import random
from termcolor import colored

from pyswip import Prolog

from assets import GameAssets, Character, Item, Room
from commands import command_list, time_convert
from room_distance_calculator import submit_distances


class InvestigationGame:
    """
    The core module containing the main game logic/game flow.
    """

    GAME_TIMEOUT = 150

    def __init__(self, json_data, prolog: Prolog):
        """

        :param json_data: Path to the JSON file containing the information necessary for the game to use.
        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        """

        with open(json_data) as f:
            core_data = json.loads(f.read())

        self.assets = GameAssets()
        self.prolog = prolog
        self.generate_scenario(prolog, core_data)

    def generate_scenario(self, prolog, core_data):
        """
        Loads the data containing characters, rooms and items the game will be using.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param core_data: A loaded version of the JSON file containing the information the game runs on.
        :return:
        """

        # Handle the character generation.
        all_characters = core_data["characters"]
        wanted_character_num = 5
        random.shuffle(all_characters)
        selected_characters = all_characters[:wanted_character_num]
        victims = core_data["victims"]
        random.shuffle(victims)
        victim = victims[0]
        self.generate_characters(prolog, selected_characters, victim)

        # Add the player.
        start_items = core_data["start_items"]
        self.generate_player(prolog, start_items)

        # Handle room generation.
        rooms = core_data["rooms"]
        self.generate_rooms(prolog, rooms)

        # Get the setup
        self.assets.setup = core_data["setup"]
        self.assets.setup["victim"] = victim

    def generate_characters(self, prolog, selected_characters, victim):
        """
        Adds the characters to the game.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param selected_characters: A list of characters to be used for the game instance.
        :param victim: The selected victim character.
        :return:
        """

        # Add the characters to the knowledge base.
        for c in selected_characters:
            prolog.assertz(f"person({c['id']})")
            self.assets.characters[c["id"]] = Character(c)

        # Add the victim.
        prolog.assertz(f"person({victim['id']})")
        prolog.assertz(f"victim({victim['id']})")
        self.assets.characters[victim["id"]] = Character(victim)

    def generate_player(self, prolog, start_items):
        """
        Adds the player to the game.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param start_items: A set of items the player starts with by default.
        :return:
        """

        prolog.assertz(f"person(player)")
        prolog.assertz(f"player(player)")

        for item in start_items:
            prolog.assertz(f"picked_up(player, {item['id']}, 0)")
            for t in item["type"]:
                prolog.assertz(f"item_type({item['id']}, {t})")

    def generate_rooms(self, prolog, selected_rooms):
        """
        Adds all the rooms, their relations, and the objects initially in them.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param selected_rooms: The rooms that the game's environment will be built with.
        :return:
        """

        # Add rooms to the knowledge base.
        for r in selected_rooms:
            r_id = r["id"]
            prolog.assertz(f"room({r_id})")
            self.assets.rooms[r_id] = Room(r)

            # Add the items initially in the room.
            for item in r["items"]:
                item_id = item["id"]
                prolog.assertz(f"item({item_id})")
                prolog.assertz(f"item_in_room({r_id}, {item_id})")
                for types in item["type"]:
                    prolog.assertz(f"item_type({item_id}, {types})")
                self.assets.items[item_id] = Item(item)

            # Add the exits from the room.
            for e in r["exits"]:
                prolog.assertz(f"room_conn({r_id}, {r['exits'][e]}, {e})")
            if "secret_exits" in r:
                for e in r["secret_exits"]:
                    prolog.assertz(f"secret_passage({r_id}, {r['secret_exits'][e]}, {e})")
                    prolog.assertz(f"knows_secret_passage(player, {r_id}, {r['secret_exits'][e]})")

    def core_loop(self, prolog):
        """
        The core of the game. This is the method that is run to start the game proper.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :return:
        """

        # Place all of the characters in necessary rooms.
        self.init_game(prolog)

        # Display the game's introduction.
        self.show_setup()

        # Initial time is set to 0.
        T = 0
        prev_loc = ""
        curr_loc = ""
        prolog.assertz(f"time({T})")

        # The main loop continues until the police are called -- IE, until the body is found.
        while not len(list(prolog.query("police(called)"))):

            # Get the player's current location.
            curr_loc = self.get_player_loc(prolog, T)

            # The player acts first.
            self.player_move(prolog, T, prev_loc, curr_loc)
            # print()

            # Check if the player's action was something suspicious / that can be witnessed by people.
            self.caught_early(prolog, T)

            # Have the other characters move.
            self.cast_move(prolog, T)

            T += 1
            prev_loc = curr_loc
            prolog.assertz(f"time({T})")

        # There is an instance where it's important to say who entered the room
        # at the very move the body is found on and check if the player got caught
        # in the act directly after killing the victim.
        self.get_changers(prolog, T, curr_loc, "enterer", {
            ("before direction", True): " comes in from the ",
            ("before direction", False): " come in from the ",
            "after direction": ", from the ",
            "after room name": "",
        }, "yellow")

        # Check if the player was caught red-handed at the very moment the body was found.
        self.caught_early(prolog, T)

        # Determine last known alibis.
        alibis = self.get_last_known_alibi(prolog)

        # From last known alibis, determine how much time it would've taken between the location
        # of the crime and the places a person was seen directly before and directly after the
        # crime.
        submit_distances(prolog, self.assets, alibis)

        # Begin the deduction process.
        self.deduce(prolog)

    def init_game(self, prolog):
        """
        Place characters in the environment.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :return:
        """

        # Start people in random rooms.
        room_ids = [room for room in self.assets.rooms]
        room_ids.remove("entrance")

        for c in self.assets.characters:
            prolog.assertz(f"present({c.lower()}, {random.choice(room_ids)}, 0)")

        # Place the player at the entrance.
        prolog.assertz(f"present(player, entrance, 0)")

    def show_setup(self):
        """
        Show the title and the introduction.

        :return:
        """

        character_intros = ""
        for c in self.assets.characters.values():
            if c.character_info["id"] != self.assets.setup["victim"]["id"]:
                character_intros += f"{c.character_info['name']}, {c.character_info['intro']}.\n"

        instructions = self.assets.setup["instructions"]

        title_path = self.assets.setup["title"]
        with open(title_path) as title_big:
            title = title_big.read()
        print(title)
        print()

        print("Play opening? [y/n]?")
        use_opening = ""
        while use_opening not in ["y", "n"]:
            use_opening = input("> ")
            use_opening = use_opening.lower()

        print()

        if use_opening == "y":
            opening = self.assets.setup["opening"]
            opening.extend(self.assets.setup["victim"]["opening_section"])
            opening.extend([character_intros])
            opening.extend(self.assets.setup["opening2"])
            opening.extend(self.assets.setup["victim"]["opening_section2"])
            opening.extend(self.assets.setup["final_remarks"])
            for o in opening:
                print(o)
                print()
                input(colored("Press Enter to continue...", "grey"))
                print()
        else:
            print("You arrive at the mansion, murderous thoughts swirling in your head.")
            print(f"Your target is {self.assets.setup['victim']['name']}.")
            print("The guests in the house are:")
            print()
            print(character_intros)
            print(f"{self.assets.setup['victim']['name']} greets you at the entrance before wandering off somewhere. You are left alone in the entrance.")
            print("You check your watch. The time is 8 PM. That gives you just two and a half hours to pull the murder off.")
            print()

        print(colored(instructions[0], "grey"))
        print()
        input(colored("Press Enter to Start.", "grey"))

        print("\n")

    def player_move(self, prolog, T, prev_loc, curr_loc):
        """
        The player's move. First checks for notable changes in the environment,
        then waits until the player gives a valid input that advances time.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param T: Current time in-game.
        :param prev_loc: The player's previous location.
        :param curr_loc: The player's current location.
        :return:
        """

        # If the player has moved to a different room, keep track if some of the characters
        # moved with the player to where they should notice. (Moving with the player or entering
        # the room just as the player is entering it.)
        if prev_loc != curr_loc:
            self.get_changers(prolog, T, curr_loc, "follower", {
                ("before direction", True): " comes ",
                ("before direction", False): " come ",
                "after direction": " with you to the ",
                "after room name": "",
            }, "yellow")

            self.get_changers(prolog, T, curr_loc, "passer", {
                ("before direction", True): " passes you as you head ",
                ("before direction", False): " pass you as you head ",
                "after direction": ", going to the ",
                "after room name": "",
            }, "cyan")

            # Check if the move in the previous move had caused to be caught in the current one.
            self.caught_early(prolog, T)

            # With this, we show the description of the room only if changing rooms.
            self.assets.rooms[curr_loc].show_description(prolog, self.assets, T)
            print()

        # Otherwise, if the player had waited in the room, notice the characters entering and leaving.
        else:
            self.get_changers(prolog, T, curr_loc, "leaver", {
                ("before direction", True): " heads off ",
                ("before direction", False): " head off ",
                "after direction": ", to the ",
                "after room name": "",
            }, "cyan")

            self.get_changers(prolog, T, curr_loc, "enterer", {
                ("before direction", True): " comes in from the ",
                ("before direction", False): " come in from the ",
                "after direction": ", from the ",
                "after room name": "",
            }, "yellow")

            self.caught_early(prolog, T)

        # Keep allowing input until a valid command that advancess time is given.
        while not self.command_prompt(prolog, T, curr_loc):
            print()

        print()

    def get_changers(self, prolog, T, curr_loc, change_atom, formation_strs, color_tag="yellow"):
        """
        Tracks the characters that have changed their positions, and whom the player would
        take notice of, depending on where the player is and what they're doing.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param T: Current time in-game.
        :param curr_loc: The player's current location.
        :param change_atom: The rule which will be using to figure out the change in environment.
        :param formation_strs: A dictionary containing how the information will be parsed and presented as a coherent sentence.
        :param color_tag: The color the information will be printed with.
        :return:
        """

        help = {}
        for c in prolog.query(f"{change_atom}(X, P, {curr_loc}, {T}, K)"):
            direction = c["K"]
            room_name = self.assets.rooms[c["P"]].room_info["name"]
            if (direction, room_name) not in help:
                help[(direction, room_name)] = []

            help[(direction, room_name)].append(self.assets.characters[c["X"]].character_info["name"])

        mov_str = ""
        for k in help:
            if help[k]:
                m = help[k]
                i = 1
                conn_str = ", "
                for c in m:
                    i += 1
                    if i == len(m):
                        conn_str = " and "
                    elif i == len(m) + 1:
                        conn_str = ""
                    mov_str += c + conn_str
                mov_str += formation_strs[("before direction", len(m) == 1)]
                mov_str += k[0]
                mov_str += formation_strs["after direction"]
                mov_str += k[1]
                mov_str += formation_strs["after room name"]
                mov_str += ". "

        if mov_str:
            print(colored(mov_str, color_tag))
            print()

    def get_player_loc(self, prolog, T):
        """
        Get the player's current location.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param T: Current time in-game.
        :return:
        """

        res = list(prolog.query(f"present(player, X, {T})"))
        loc = res[0]["X"]
        return loc

    def command_prompt(self, prolog, T, loc):
        """
        The command prompt. Passes the inputted commands to the proper callback methods.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param T: Current time in-game.
        :param loc: The player's current location.
        :return: True only if a valid command that advances time was given.
        """

        # Command prompot for the player to use.
        comm = input("> ")
        comm = comm.strip().lower()

        if not comm:
            return False

        print()

        # Extract the command and its arguments.
        command_split = comm.split(" ")
        command_to_use = command_split[0]

        if command_to_use not in command_list:
            print("I'm afraid I don't understand.")
            return False

        if len(command_split) == 1:
            rest_of_command = None
        else:
            rest_of_command = command_split[1:]

        # Hand the command over for processing to the appropriate function.
        return command_list[command_to_use](prolog, T, rest_of_command, loc, self.assets)

    def cast_move(self, prolog, T):
        """
        Has all of the characters make a move for the minute.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param T: Current time in-game.
        :return:
        """

        for c in self.assets.characters:
            self.assets.characters[c].move(prolog, T)

    def caught_early(self, prolog, T):
        """
        Check if the player was caught red-handed or they simply ran out of time.

        :param prolog:
        :param T: Current time in-game.
        :return:
        """

        if len(list(prolog.query(f"witness(X, {T})"))) > 0:
            print("You were caught in the act! Game Over!")
            exit(0)

        if T >= self.GAME_TIMEOUT:
            print("Time is up.")
            if len(list(prolog.query("victim(X), dead(X)"))) == 0:
                print("You failed to kill the victim in the required time! Game Over!")
                exit(0)
            else:
                print("You managed to kill the victim and go through the entire night without it being discovered!")
                print("You win!")
                exit(0)

    def get_last_known_alibi(self, prolog):
        """
        Determine everyone's last known alibi from the existing list of alibis,
        relative to the time of the crime.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :return: Last known alibis.
        """

        time_of_crime = list(prolog.query("time_of_crime(T)"))[0]["T"]
        people = {}
        for a in prolog.query("alibi(X, P, T)"):

            if a["X"] not in people:
                people[a["X"]] = {
                    "before": None,
                    "after": None,
                }

            if a["T"] <= time_of_crime:
                if not people[a["X"]]["before"]:
                    people[a["X"]]["before"] = (a["P"], a["T"])
                    continue

                if a["T"] > people[a["X"]]["before"][1]:
                    people[a["X"]]["before"] = (a["P"], a["T"])

            else:
                if not people[a["X"]]["after"]:
                    people[a["X"]]["after"] = (a["P"], a["T"])
                    continue

                if a["T"] < people[a["X"]]["after"][1]:
                    people[a["X"]]["after"] = (a["P"], a["T"])

        for p in people:
            for k in people[p]:
                alibi = people[p][k]
                if alibi:
                    prolog.assertz(f"last_known_alibi({k}, {p}, {alibi[0]}, {alibi[1]})")

        return people

    def deduce(self, prolog):
        """
        Use the Prolog deduction rules to determine who the culprit is.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :return:
        """

        # Show the information about the people who found the body.
        self.assets.characters["player"] = Character({"name": "Player"})

        print("THE BODY HAS BEEN FOUND.")
        print()
        print("The ones who found the body are:")
        alerters = set([p["X"] for p in list(prolog.query("alerted(X, P)"))])
        a_named = [self.assets.characters[c].character_info["name"] for c in alerters]
        print(a_named)

        print()
        print("The police are called...")

        print("The detective arrives at the scene...")
        print("The first thing he needs to establish is OPPORTUNITY. Who had a chance to kill the victim?")
        time_of_crime = list(prolog.query("time_of_crime(X)"))[0]["X"]
        place_of_crime = list(prolog.query("place_of_crime(X)"))[0]["X"]
        print("The coroner has accurately estimated that the time of the murder was:", time_convert(time_of_crime) + ".")
        print("The scene of the crime was at the", self.assets.rooms[place_of_crime].room_info["name"].lower() + ".")
        print()
        print("Let us look at everyone's last known alibis before and after the crime.")

        alibi_locations_before = {}
        alibi_locations_after = {}
        for K, alibi_coll in [("before", alibi_locations_before), ("after", alibi_locations_after)]:
            confirmed_alibis = list(prolog.query(f"last_known_alibi({K}, X, Y, T)"))
            for alibi in confirmed_alibis:
                person = alibi["X"]
                loc = alibi["Y"]
                t = alibi["T"]
                if (loc, t) not in alibi_coll:
                    alibi_coll[(loc, t)] = set()
                alibi_coll[(loc, t)].add(person)

        print("After speaking with the witnesses, it would seem that the timetable would be something like...")
        print()

        reachability = {
            "before":{
                True: ("COULD HAVE MADE IT TO THE CRIME SCENE AFTER", "green"),
                False: ("COULD NOT HAVE MADE IT TO THE CRIME SCENE", "red")
            },
            "after":{
                True: ("COULD HAVE MADE IT FROM THE CRIME SCENE AFTER THE FACT", "green"),
                False: ("COULD NOT HAVE BEEN HERE IF HAD COME FROM THE CRIME SCENE", "red")
            }
        }

        for h, K, alibi_coll in [("before", "LAST TIME SEEN BEFORE, OR AT THE MOMENT OF CRIME", alibi_locations_before), ("after", "FIRST TIME SEEN AFTER THE MURDER", alibi_locations_after)]:
            print(K)
            for a in alibi_coll:
                place, t = a
                reachb = len(list(prolog.query(f"reachable({place}, {place_of_crime}, {t}, {time_of_crime})"))) > 0
                room_name = self.assets.rooms[place].room_info["name"]
                t_conv = time_convert(t)
                chars = [self.assets.characters[c].character_info["name"] for c in alibi_coll[a]]
                print(room_name, t_conv, chars, "[", colored(reachability[h][reachb][0], reachability[h][reachb][1]), "]")
            print()

        print("Based on the time and the locations, we can conclude that the ones with the opportunity are:")
        suspects = set([p["X"] for p in list(prolog.query("opportunity(X)"))])
        s_named = [self.assets.characters[c].character_info["name"] for c in suspects]
        print(s_named)
        print()

        if "player" in suspects:
            print("It seems it's entirely possible for you to have committed the crime...")
            print("Still, that doesn't mean you're necessarily done for. They still need to gather an actual case.")
        else:
            print("Great! You've managed to use a trick to give yourself an alibi for the crime!")

        print("Of course, the victim is always on the list when it comes to opportunity. Even if it seems unlikely, given everything.")

        print()

        print("Next, let us consider the means. Do we possess any hard evidence against anyone? What about the MEANS?")
        print()
        print("Have fingerprints been found on the murder weapon?")
        suspects_2 = set(p["X"] for p in list(prolog.query("weapon_fingerprints(X)")))
        s_named = [self.assets.characters[c].character_info["name"] for c in suspects_2]
        print(s_named)

        print()
        print("Has a potential murder weapon been found on anyone's person?")
        suspects_2 = set(p["X"] for p in list(prolog.query("possible_murder_weapon_posess(X)")))
        s_named = [self.assets.characters[c].character_info["name"] for c in suspects_2]
        print(s_named)

        print()
        print("Has a generally incriminating piece of evidence been found on anyone's person?")
        suspects_2 = set(p["X"] for p in list(prolog.query("incriminating_item_posess(X)")))
        s_named = [self.assets.characters[c].character_info["name"] for c in suspects_2]
        print(s_named)

        print()
        print("Based on this, the people with the MEANS are...")
        suspects_2 = set(p["X"] for p in list(prolog.query("means(X)")))
        s_named = [self.assets.characters[c].character_info["name"] for c in suspects_2]
        print(s_named)
        print()

        if "player" in suspects_2:
            print("Unfortunately, the police have gathered some good evidence against you.")
            print("You've tried to pass it off as being framed, but you're not sure if they're buying the excuses.")
        else:
            print("Great. You've managed to avoid leaving any damning evidence.")

        print()

        print("Based an all this, we can attempt to find the culprit...")
        culprit = set(p["X"] for p in list(prolog.query("culprit(X)")))
        s_named = [self.assets.characters[c].character_info["name"] for c in culprit]
        print(s_named)
        print()

        if "player" not in culprit:
            print("You are not in the culprit list! You managed to escape judgement!")
            print("You Win!")
            exit(0)
        else:
            print("You've been caught! Game Over!")
            exit(0)


if __name__ == '__main__':

    prolog = Prolog()
    prolog.consult("game_core_logic.pl")
    game = InvestigationGame("scenario.json", prolog)
    game.core_loop(prolog)