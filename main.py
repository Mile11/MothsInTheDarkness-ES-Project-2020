import colorama

from pyswip import Prolog

from interactive_game import InvestigationGame

colorama.init()

if __name__ == '__main__':

    prolog = Prolog()
    prolog.consult("game_core_logic.pl")
    game = InvestigationGame("scenario.json", prolog)
    game.core_loop(prolog)