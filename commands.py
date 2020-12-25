"""
EXPERT SYSTEM PROJECT 2020/2021
Faculty of Electrical Engineering and Computing
FILIP MILIC

Module for processing the player input.
"""

import random
from termcolor import colored

from Levenshtein import distance

MOVE_CHECK_MIN_DIST = 1
ITEM_CHECK_MIN_DIST = 2
CHARACTER_CHECK_MIN_DIST = 2


def move_actor(prolog, T, arg_given, loc, assets, output=True, actor="player"):
    """
    Moves the actor from the room they're in, depending on the connections
    the room has.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param loc: The actor's current location.
    :param assets: The game assets.
    :param output: Whether or not to print out the information about the command' results.
    :param actor: The actor using the command (player or other characterss.)
    :return: Boolean signifying success or failure.
    """

    if not arg_given:
        print("Go where?")
        return False

    direction = arg_given[0]
    valid_loc_found = False

    secret_aware_before = set([p["X"] for p in list(prolog.query(f"knows_secret_passage(X, {loc}, Y), present(X, {loc}, {T})"))])
    for dirs in prolog.query(f"allow_move({actor}, {loc}, X, Y)"):
        if distance(dirs["Y"], direction) <= MOVE_CHECK_MIN_DIST:
            valid_loc_found = True
            next_room = dirs["X"]

    if not valid_loc_found:
        if output:
            print("You hit a wall. You can't go that way.")
        if actor == "player":
            return False
        else:
            return wait(prolog, T, None, loc, None, output, actor)

    prolog.assertz(f"present({actor}, {next_room}, {T+1})")

    if len(list(prolog.query(f"secret_passage({loc}, {next_room}, {direction})"))) > 0:
        secret_aware_after = set([p["X"] for p in list(prolog.query(f"knows_secret_passage(X, {loc}, Y), present(X, {loc}, {T})"))])
        secret_aware_diff = secret_aware_after - secret_aware_before

        if not secret_aware_diff:
            return True

        for aware in secret_aware_diff:
            if output:
                print(colored(f"{assets.characters[aware].character_info['name']} sees you go down the secret passage!", "red"))

    return True


def move_character(prolog, T, arg_given, loc, assets, output, actor):
    """
    Moves a character by selecting a random direction for them, if one exists.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param loc: The actor's current location.
    :param assets: The game assets.
    :param output: Whether or not to print out the information about the command' results.
    :param actor: The actor using the command (player or other characterss.)
    :return: Boolean signifying success or failure.
    """

    dirs = list(prolog.query(f"allow_move({actor}, {loc}, X, Y)"))
    if len(dirs) > 0:
        random.shuffle(dirs)
        move_actor(prolog, T, [dirs[0]["Y"]], loc, None, output=False, actor=actor)
    else:
        return wait(prolog, T, None, loc, None, output, actor)


def wait(prolog, T, arg_given, loc, assets, output=True, actor="player"):
    """
    An actor waits for a minute to pass.
    This method is used in general when we want to ensure a command
    that doesn't have the character change rooms still advances time.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param loc: The actor's current location.
    :param assets: The game assets.
    :param output: Whether or not to print out the information about the command' results.
    :param actor: The actor using the command (player or other characterss.)
    :return: Boolean signifying success or failure.
    """

    if output:
        print("Time passes...")
    prolog.assertz(f"present({actor}, {loc}, {T + 1})")
    return True


def get_time(prolog, T, arg_given, player_loc, assets, output=True):
    """
    Gets the current time.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param player_loc: The actor's current location.
    :param assets: The game assets.
    :param output: Whether or not to print out the information about the command' results.
    :return: Always returns False (doesn't advance time).
    """

    print(f"You check your watch. The time is {time_convert(T)}.")
    return False


def time_convert(T):
    """
    Converts the counter to an actual time (starting from 8 PM).

    :param T: Current time in-game.
    :return: String containing the converted time.
    """

    mins = str(T % 60)
    hour = T // 60 + 20
    return "%d:%s" % (hour, mins.zfill(2))


def think(prolog, T, arg_given, loc, assets, output=True, actor="player"):
    """
    Gives the player a hint by giving them the current position of the victim.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param loc: The actor's current location.
    :param assets: The game assets.
    :param output: Whether or not to print out the information about the command' results.
    :param actor: The actor using the command (player or other characterss.)
    :return: Always returns False.
    """

    print("You stop and think.")
    print("You were never much a genius, but you always figured you could see through most human behavior.")
    print("Given everything, you're fairly certain...")
    victim_info = list(prolog.query(f"present(X, Y, {T}), victim(X)"))[0]
    print(colored(f"{assets.characters[victim_info['X']].character_info['name']} is currently in the {assets.rooms[victim_info['Y']].room_info['name'].lower()}.", "cyan"))
    return False


def examine(prolog, T, arg_given, player_loc, assets):
    """
    Used to give a description of the current room, or a character, or an item.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param player_loc: The actor's current location.
    :param assets: The game assets.
    :return: Boolean signifying success or failure.
    """

    if not arg_given:
        assets.rooms[player_loc].show_description(prolog, assets, T)
        return False
    if arg_given[0] == "at":
        arg_given = arg_given[1:]

    look_at = " ".join(arg_given)
    if not look_at:
        assets.rooms[player_loc].show_description(prolog, assets, T)
        return False

    all_items = assets.items
    all_people = assets.characters

    # Looking at inventory item?
    items_in_inventory = get_inventory_item_list(prolog)
    for item in items_in_inventory:
        for alias in all_items[item].item_info["aliases"]:
            if distance(alias, look_at) <= ITEM_CHECK_MIN_DIST:
                all_items[item].show_description()
                return False

    # Look at a person in the room?
    people_in_room = get_people_list(prolog, player_loc, T)
    for p in people_in_room:
        if distance(all_people[p].character_info["name"].lower(), look_at) <= CHARACTER_CHECK_MIN_DIST:
            all_people[p].show_description()
            return False

    # If neither of these is the case, then it comes down to examining an object in the room itself.
    room_items = get_item_list(prolog, player_loc)
    for item in room_items:
        for alias in all_items[item].item_info["aliases"]:
            if distance(alias, look_at) <= ITEM_CHECK_MIN_DIST:
                all_items[item].show_description()
                return False

    # If all of these fail, it must mean that the item is simply not present, either in the room or inventory.
    print("Nothing like that seems to be here.")
    return False


def take(prolog, T, arg_given, loc, assets, output=True, actor="player"):
    """
    Takes an object and adds it to an inventory.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param loc: The actor's current location.
    :param assets: The game assets.
    :param output: Whether or not to print out the information about the command' results.
    :param actor: The actor using the command (player or other characterss.)
    :return: Boolean signifying success or failure.
    """

    if not arg_given:
        if output:
            print("Take what?")
        return False

    if arg_given[0] == "up":
        arg_given = arg_given[1:]
    arg_item = " ".join(arg_given)
    takeable_objects = list(prolog.query(f"item_in_room({loc}, X), item_type(X, carryable)"))
    if len(takeable_objects) == 0:
        if output:
            print("There's nothing here to take.")
        return False

    for item in takeable_objects:
        item_to_check = assets.items[item["X"]]
        for alias in item_to_check.item_info["aliases"]:
            if distance(alias, arg_item) <= ITEM_CHECK_MIN_DIST:

                # Pick up and remove item from the room.
                prolog.assertz(f"picked_up({actor}, {item['X']}, {T})")
                prolog.retract(f"item_in_room({loc}, {item['X']})")

                # If the actor has no gloves, put fingerprints on the object.
                # Since we pick up the object first, we avoid the issue of leaving fingerprints on
                # gloves if that's the first thing the player picks up.
                if len(list(prolog.query(f"inventory({actor}, X), item_type(X, gloves)"))) == 0:
                    prolog.assertz(f"fingerprints({actor}, {item['X']})")

                # Replace description inside its room with the 'other' description from here on out
                if item_to_check.item_info["description_in_start_room"]:
                    item_to_check.item_info["description_in_start_room"] = None

                if output:
                    print(f"You take the {item_to_check.item_info['name'].lower()}.")
                return wait(prolog, T, None, loc, None, output=False, actor=actor)

    # If we go through the entire loop, conclude the item is simply not in the room!
    if output:
        print("You can't pick that up.")
    return False


def drop(prolog, T, arg_given, loc, assets, output=True, actor="player"):
    """
    Drop the item, removing it from the inventory.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param loc: The actor's current location.
    :param assets: The game assets.
    :param output: Whether or not to print out the information about the command' results.
    :param actor: The actor using the command (player or other characterss.)
    :return: Boolean signifying success or failure.
    """

    if not arg_given:
        if output:
            print("Drop what?")
        return False

    arg_item = " ".join(arg_given)
    inventory_items = list(prolog.query(f"inventory({actor}, X), not(item_type(X, undroppable))"))
    if len(inventory_items) == 0:
        if output:
            print("You don't have anything to drop.")
        return False

    for item in inventory_items:
        item_to_check = assets.items[item['X']]
        for alias in item_to_check.item_info["aliases"]:
            if distance(alias, arg_item) <= ITEM_CHECK_MIN_DIST:

                if len(list(prolog.query(f"inventory({actor}, X), item_type(X, gloves)"))) == 0:
                    prolog.assertz(f"fingerprints({actor}, {item['X']})")

                # Get the proper relevant timestamp to drop the object.
                relevant_timestamp = list(prolog.query(
                    f"picked_up({actor}, {item['X']}, T), not(dropped({actor}, {item['X']}, T))")
                )[0]["T"]

                prolog.assertz(f"dropped({actor}, {item['X']}, {relevant_timestamp})")
                prolog.assertz(f"item_in_room({loc}, {item['X']})")

                if output:
                    print(f"You drop the {item_to_check.item_info['name'].lower()}.")
                return wait(prolog, T, None, loc, None, output=False, actor=actor)

    # If we go through the entire loop, conclude the item is simply not in the inventory!
    if output:
        print("You can't drop what you don't have.")
    return False


def inventory(prolog, T, arg_given, player_loc, assets):
    """
    Prints out the player's current inventory.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param player_loc: The actor's current location.
    :param assets: The game assets.
    :return: Boolean signifying success or failure.
    """

    items = get_inventory_item_list(prolog)
    if not items:
        print("You don't seem to have anything at the moment.")
        return False

    print("You're carrying:")
    print()
    for item in items:
        print(f"- {assets.items[item].item_info['name']}")
    return False


def get_inventory_item_list(prolog, actor="player"):
    """
    Get a list of items an actor has in their inventory.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param actor: The actor whose inventory is being retrieved.
    :return:
    """

    return [item["X"] for item in list(prolog.query(f"inventory({actor}, X), not(item_type(X, undroppable))"))]


def get_people_list(prolog, loc, T):
    """
    Get a list of people in the room.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param loc: Room to get the list of people from.
    :param T: Current time in-game.
    :return:
    """

    ret = [p["X"] for p in list(prolog.query(f"present(X, {loc}, {T})"))]
    ret.remove("player")
    return ret


def get_item_list(prolog, loc):
    """
    Get a list of items in a room.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param loc: Room to get the list of people from.
    :return:
    """

    return [item["X"] for item in list(prolog.query(f"item_in_room({loc}, X)"))]


def talk(prolog, T, arg_given, player_loc, assets):
    """
    Talking to characters.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param player_loc: The actor's current location.
    :param assets: The game assets.
    :return: Boolean signifying success or failure.
    """

    if not arg_given:
        print("Talk to who?")
        return False

    if arg_given[0] == "to":
        arg_given = arg_given[1:]

    all_people = assets.characters
    name = " ".join(arg_given)

    # Look at a person in the room?
    people_in_room = get_people_list(prolog, player_loc, T)
    for p in people_in_room:
        check_name = all_people[p].character_info["name"]
        if distance(check_name.lower(), name) <= CHARACTER_CHECK_MIN_DIST:

            print(f"You walk up to {check_name}.\n")

            talk_options = list(all_people[p].character_info["talks"].items())
            i = 1
            for t, _ in talk_options:
                print(str(i) + ".", t)
                i += 1
            print("0.", "Nevermind.")
            print()

            select = input("> ")

            try:
                num = int(select)
                if num < 0 or num > len(talk_options):
                    raise
            except:
                print(f"You stumble your words. {check_name} doesn't seem to understand, and you walk away in confusion and shame.")
                return False

            if num == 0:
                return False

            _, val = talk_options[num-1]
            print(val)
            return wait(prolog, T, None, player_loc, None, output=False, actor="player")

    pass


def kill(prolog, T, arg_given, player_loc, assets):
    """
    Initiates the player killing sequence.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param player_loc: The actor's current location.
    :param assets: The game assets.
    :return: Boolean signifying success or failure.
    """

    # Check if the victim is present in the room
    if len(list(prolog.query(f"kill_moment({T})"))) > 0:

        weapons = [w["X"] for w in list(prolog.query(f"inventory(player, X), item_type(X, weapon)"))]
        if len(weapons) == 0:
            print("As good as the opportunity might be, you don't seem to have anything to do the job...")
            print(colored("(You'll have to find a weapon...)", "magenta"))
            return False

        print("It looks like the time has come.")
        print("You look at what you have on-hand and consider your options...")
        i = 1
        for w in weapons:
            print(str(i) + ".", assets.items[w].item_info["name"])
            i += 1
        print("0.", "Back Out")

        print()
        print(colored("Select the weapon you want to use."))
        print()
        select = input("> ")

        try:
            num = int(select)
            if num < 0 or num > len(weapons):
                raise
        except:
            print("Invalid choice!")
            return False

        if num == 0:
            return False

        weapon = weapons[num-1]
        cause = list(prolog.query(f"cause_correlated(Z, T), item_type({weapon}, T)"))[0]["Z"]
        prolog.assertz(f"cause_of_death({cause})")
        prolog.assertz(f"time_of_act({T})")
        delay = int(list(prolog.query(f"death_delay(X)"))[0]["X"])
        prolog.assertz(f"time_of_crime({T+delay})")

        print()
        print(colored(assets.items[weapon].get_murder_method(), "red"))

        return wait(prolog, T, None, player_loc, None, output=False, actor="player")
    else:
        print("Your victim is not in the room!")
        return False


def lock(prolog, T, arg_given, player_loc, assets):
    """
    Locks the door.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param player_loc: The actor's current location.
    :param assets: The game assets.
    :return: Boolean signifying success or failure.
    """

    if len(list(prolog.query("inventory(player, key)"))) > 0:
        if not arg_given:
            print("Enter the direction of the door you wish to lock.")
            return False

        direction = arg_given[0]
        valid_loc_found = False
        for dirs in prolog.query(f"room_conn({player_loc}, X, Y)"):
            if distance(dirs["Y"], direction) <= MOVE_CHECK_MIN_DIST:
                valid_loc_found = True
                next_room = dirs["X"]

        if not valid_loc_found:
            print("There's no door in that direction to lock.")
            return False

        if len(list(prolog.query(f"locked({player_loc}, {next_room}); locked({next_room}, {player_loc})"))) > 0:
            print("This door is already locked.")
            return False

        prolog.assertz(f"locked({player_loc}, {next_room})")
        print(f"You covertly lock the door to the {assets.rooms[next_room].room_info['name'].lower()}.")
        return wait(prolog, T, None, player_loc, None, output=False, actor="player")
    else:
        print("You need a key to lock doors.")
        return False


def unlock(prolog, T, arg_given, player_loc, assets):
    """
    Unlocks the door.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param player_loc: The actor's current location.
    :param assets: The game assets.
    :return: Boolean signifying success or failure.
    """

    if len(list(prolog.query("inventory(player, key)"))) > 0:
        if not arg_given:
            print("Enter the direction of the door you wish to unlock.")
            return False

        direction = arg_given[0]
        valid_loc_found = False
        for dirs in prolog.query(f"room_conn({player_loc}, X, Y)"):
            if distance(dirs["Y"], direction) <= MOVE_CHECK_MIN_DIST:
                valid_loc_found = True
                next_room = dirs["X"]

        if not valid_loc_found:
            print("There's no door in that direction to unlock.")
            return False

        if len(list(prolog.query(f"not(locked({player_loc}, {next_room})), not(locked({next_room}, {player_loc}))"))) > 0:
            print("This door is already unlocked.")
            return False

        if len(list(prolog.query(f"locked({player_loc}, {next_room})"))) > 0:
            prolog.retract(f"locked({player_loc}, {next_room})")
        else:
            prolog.retract(f"locked({next_room}, {player_loc})")
        print(f"You covertly unlock the door to the {assets.rooms[next_room].room_info['name'].lower()}.")
        return wait(prolog, T, None, player_loc, None, output=False, actor="player")
    else:
        print("You need a key to unlock doors.")
        return False


def report(prolog, T, arg_given, player_loc, assets):
    """
    If the player runs out of patience waiting for the body to be discoverred
    and believes their plan is good enough, they can report the body themselves.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param player_loc: The actor's current location.
    :param assets: The game assets.
    :return: Boolean signifying success or failure.
    """

    # Check if player is in same room with victim.
    loc_check = list(prolog.query(f"present(player, P, {T}), present(X, P, {T}), dead(X)"))

    if len(loc_check) > 0:
        print("You pretend to discover the body!")
        prolog.assertz(f"alerted(player, {loc_check[0]['P']})")
        return wait(prolog, T, None, player_loc, None, output=False, actor="player")
    else:
        print("There's nothing here to report.")
        return False


def help(prolog, T, arg_given, player_loc, assets):
    """
    Prints out the help for playing the game.

    :param prolog: An instantiated version of the SWI-Prolog Python interface.
    :param T: Current time in-game.
    :param arg_given: The argument given to the command.
    :param player_loc: The actor's current location.
    :param assets: The game assets.
    :return: Boolean signifying success or failure.
    """

    print("Here is a list of acceptable commands:")
    comm_list = list(command_list.keys())
    comm_list.remove("lock")
    comm_list.remove("unlock")
    comm_list.remove("help")
    for c in comm_list:
        print(c)
    print()

    print("Moving, taking items, dropping items and talking to people always takes a minute, unless you back out of a conversation before picking a topic OR by picking an invalid direction.")
    print("'Talk to' and 'Pick up' are valid commands.")
    print("You can also choose to do nothing by waiting, which causes time to pass.")
    print("Time passes in one-minute intervals.")
    print("Thinking will tell you where your victim currently is. It does not cost time.")
    print("You can check the current time with the time command.")
    print("The inventory command will simply give you a list of items in your inventory, without advancing time.")
    print("Look and examine do the same thing. If you type only 'look', you will be given the current description of the room again. 'Look at' is also valid. Looking around does not cost time.")
    print("The report command will allow you to report the body yourself after commiting the crime. This will end the game and call the police, where the evidence against you will be weighted.")
    print("If you do not report the body, the first people that walk onto the crime scene will do so.")
    print("There is one more command not listed here, which will be unlocked if you can find a certain object.")
    print("Initiating the kill command will begin by asking you what weapon you wish to use.",
          "If you have no weapon, you won't be able to commit the crime.")
    print("Keep in mind that the police will consider your last known alibi before and after the time of death.",
          "You will be cleared of suspicion if you can either: \n",
          "-  Have an alibi before the crime, in which you were at a place and a time where you couldn't have made it to the crime scene for the time of the crime to fit.\n",
          "-  Have an alibi after the crime, in which you were at a place and a time where you couldn't have made it if you were at the crime scene at the time of the crime."
          )
    print("If you cannot figure out how to do this, attempt to at least minimize the physical evidence against you.")
    print("The cast is always randomized, as is their movement.")
    print()
    print("Using this command has not cost you any time.")


# Contains the bindings between commands and callback functions that
# process them.
# These are for the player-only.
command_list = {
    "move": move_actor,
    "go": move_actor,
    "wait": wait,
    "time": get_time,
    "kill": kill,
    "examine": examine,
    "look": examine,
    "inventory": inventory,
    "take": take,
    "drop": drop,
    "pick": take,
    "lock": lock,
    "unlock": unlock,
    "think": think,
    "report": report,
    "talk": talk,
    "help": help,
}

# Contains the bindings for non-player characters.
command_list_others = {
    "move": move_character,
    "wait": wait,
}
