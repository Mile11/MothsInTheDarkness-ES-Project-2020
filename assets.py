"""
EXPERT SYSTEM PROJECT 2020/2021
Faculty of Electrical Engineering and Computing
FILIP MILIC

Module used for the game assets.
"""

import random

from commands import command_list_others


class GameAssets:
    """
    Contains all of the game assets.
    """

    def __init__(self):

        self.rooms = {}
        self.items = {}
        self.characters = {}
        self.setup = {}


class Room:
    """
    Contains the information of a room.
    """

    def __init__(self, room_info):

        self.room_info = room_info

    def show_description(self, prolog, all_assets, T):
        """
        Shows a room's general description, the objects in it at the time
        and the characters in it.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param all_assets: All of the game assets.
        :param T: Current time in-game.
        :return:
        """

        # Print the name of the room.
        print("="*5, self.room_info["name"].upper(), "="*5)
        print()

        # Print the general description of the room.
        print(self.room_info["description"])
        print()

        id = self.room_info["id"]

        # Print the items in the room.
        item_str = ""
        for item in prolog.query(f"item_in_room({id}, X)"):
            desc_to_use = "description_in_start_room"
            if not all_assets.items[item["X"]].item_info[desc_to_use]:
                desc_to_use = "description_outside_start_room"
            item_str += all_assets.items[item["X"]].item_info[desc_to_use] + " "

        if item_str:
            print(item_str)
            print()

        # Print the information on the other people in the room.
        people = list(prolog.query(f"present(X, {id}, {T})"))
        people.remove({"X": "player"})
        if len(people) > 0:
            if len(people) == 1:
                per = people[0]["X"]
                per_name = all_assets.characters[per].character_info["name"]
                if len(list(prolog.query(f"dead({per})"))) > 0:
                    print(f"{per_name}'s lifeless body is sprawled on the ground.")
                else:
                    print(f"{per_name} is here.")
            else:
                per_str = ""
                per_add = ", "
                i = 1
                for person in people:
                    per = person["X"]
                    per_name = all_assets.characters[per].character_info["name"]
                    i += 1
                    if i == len(people):
                        per_add = " and "
                    elif i == len(people) + 1:
                        per_add = " "
                    per_str += per_name + per_add
                per_str += "are here."
                print(per_str)
            print()

        # Print the exits.
        # We could get these from the room info, but...
        # We've got a running database for active state of the house, we may as well
        # apply it to the house.
        conn_str = ""
        for e in prolog.query(f"room_conn({id}, X, Y)"):
            conn_str += "To the " + e["Y"] + " is the " + all_assets.rooms[e["X"]].room_info["name"] + ". "
        print(conn_str)


class Character:
    """
    A game character.
    """

    def __init__(self, character_info):

        self.character_info = character_info

    def get_current_status(self, prolog, T):
        """
        Gets the position of the character.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param T: Current time in-game.
        :return:
        """

        # Get the current location of a character.
        loc = list(prolog.query(f"present({self.character_info['id']}, X, {T})"))
        return loc[0]["X"]

    def move(self, prolog, T):
        """
        Randomly decides whether the character should wait or move,
        and calls the appropriate command.

        :param prolog: An instantiated version of the SWI-Prolog Python interface.
        :param T: Current time in-game.
        :return:
        """

        mov_flag = 1

        # The probability distribution used to weigh the importance of the decisions on
        # what move to perform next, given the number of possible ones at any given time.
        weights = {
            1: (100,),
            2: (20*mov_flag, 100 + (mov_flag-1)*20),
        }

        # Get the current location of the character.
        loc = self.get_current_status(prolog, T)

        # Get the valid moves for the character.
        valid_moves = list(prolog.query(f"valid_move({self.character_info['id']}, M)"))
        if len(valid_moves) > 0:
            valid_moves.sort(key=lambda x: x["M"])
            comm_picked = random.choices(valid_moves, weights=weights[len(valid_moves)], k=1)[0]["M"]
            command_list_others[comm_picked](prolog, T, None, loc, None, False, self.character_info["id"])

    def show_description(self):
        """
        Shows the character description.

        :return:
        """

        print(self.character_info["description"])


class Item:
    """
    A game item.
    """

    def __init__(self, item_info):

        self.item_info = item_info

    def show_description(self):
        """
        Shows the item description.

        :return:
        """

        print(self.item_info["description"])

    def get_murder_method(self):
        """
        Shows the action of using the object for murderous purposes.

        :return:
        """

        if "murder_method" in self.item_info:
            return self.item_info["murder_method"]

        return " "
