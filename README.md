<p align="center">
  <img src="https://github.com/Mile11/MothsInTheDarkness-ES-Project-2020/blob/master/logo.png?raw=true" alt="Sublime's custom image"/>
</p>

## Overview

*Moths in the Darkness* is a project for the Expert Systems course at the Faculty of Electrical Engineering and Computing, for the
academic year of 2020/2021.

The idea was to create an interactive text adventure, in which the player's goal is to navigate a mansion filled
with people and commit a murder without getting caught. 

The systems for deducing the player's culpability, the movements of other characters and game state were all implemented 
using Prolog (or, rather, [SWI-Prolog](https://www.swi-prolog.org/), but feature-wise, only the core elements of 'normal' 
Prolog were ultimately been used for this project.)

The game itself was made with Python, with the interface to Prolog being the [pyswip](https://pypi.org/project/pyswip/) module.

## Installation and Usage

Installation steps:

* Install Python: Python (3.6+)
* Install [SWI-Prolog](https://www.swi-prolog.org/)
* Install Python modules: [pyswip](https://pypi.org/project/pyswip/), [python-Levenshtein](https://pypi.org/project/python-Levenshtein/),
either through individual `pip` commands, or by using the provided `requirements.txt`

After cloning this repository, you can run the game with:

```
python main.py
```

## Game Rules

When first starting the game, it is recommended to play the intro and use the `help` command to get a full list of commands.

The overall game flow goes as follows:

* The player moves around the mansion, interacting with objects and characters, gathering weapons to commit the murder with.
* Once in the same room as the victim, the player can commit the murder, provided they have a weapon.
* If the player is caught in the act, the game ends immediately.
* If not, the game continues until one of the other guests comes across the body or the player themselves reports it.
* After this comes the sequence where the detective uses the rules outlined in the Prolog rule base to determine the culprit.
* If the player manages to avoid being on that list, they win!