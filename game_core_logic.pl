% EXPERT SYSTEM PROJECT 2020/2021
% Faculty of Electrical Engineering and Computing
% FILIP MILIC

% This file contains the knowledge base used by the text adventure.
% We use Prolog for three purposes:
% First, the chain of logic the detective will be using in trying to figure out the culprit's identity.
% Secondly, the behavior of the characters.
% Third, general information on the game state.

% Since the Expert System course focuses on the 'basic' capabilties of Prolog,
% as an additional requirement, we will TRY to avoid using the more 'advanced' features
% of the SWI-Prolog, in spite of the module we are using to interact with our
% Python codebase being just that.

% (That said, in some cases, we WILL use it for convenience, such as simple
% arithmetic!)


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%                                                        %
% SECTION 0: SETUP                                       %
%                                                        %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%                                                        %
% Before outlining the knowledge database, we need       %
% to write out all of the cluases as dynamic for         %
% the closed world assumption to work out smoothly.      %
% IE, if a rule reliess on facts that                    %
% haven't been set yet, Prolog would raise an error.     %
% And we want to use some of these facts as flags,       %
% so them not not being defined at time of checking      %
% is intended behavior.                                  %
%                                                        %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


:- dynamic alerted/2.
:- dynamic alibi/3.
:- dynamic allow_move/4.
:- dynamic cause_correlated/2.
:- dynamic cause_of_death/1.
:- dynamic culprit/1.
:- dynamic current_time/1.
:- dynamic damning_action/3.
:- dynamic dead/1.
:- dynamic deadline/1.
:- dynamic death_delay/1.
:- dynamic distance/3.
:- dynamic dropped/3.  % Used for determining if the object is still in a person's posession.
:- dynamic enterer/5.
:- dynamic fingerprints/2.
:- dynamic follower/5.
:- dynamic impossible_alibi/1.
:- dynamic inventory/2.
:- dynamic incriminating/1.
:- dynamic item/1.
:- dynamic last_known_alibi/4.
:- dynamic leaver/5.
:- dynamic locked/2.
:- dynamic gunshot/1.
:- dynamic incriminating_item_posess/1.
:- dynamic item_type/2.
:- dynamic kill_moment/1.
:- dynamic knows_secret_passage/3.
:- dynamic manhattan/3.
:- dynamic manhattan_secret/3.
:- dynamic means/1.
:- dynamic murder_weapon/1.
:- dynamic opportunity/1.
:- dynamic passer/5.
:- dynamic person/1.
:- dynamic picked_up/3.  % These will have to be manually set every time an object is picked up and dropped, evidently.
:- dynamic player/1.
:- dynamic police/1.
:- dynamic possible_murder_weapon_posess/1.
:- dynamic present/3.
:- dynamic reachable/4.
:- dynamic secret_passage/3.
:- dynamic small/1.  % Used for objects that could potentially be planted on someone else's person?
:- dynamic time/1.
:- dynamic time_of_crime/1.
:- dynamic time_of_act/1.
:- dynamic valid_move/2.
:- dynamic victim/1.
:- dynamic weapon_fingerprints/1.
:- dynamic witness/2.


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%                                                        %
% SECTION 1: DETECTIVE                                   %
%                                                        %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%                                                        %
% The detective need only answer a single, fundanemtal   %
% question: 'Who is the culprit?' This section is thus   %
% about defining the rules in figuring that out.         %
%                                                        %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% Generally speaking, a culprit is someone who has means, motive and opportunity.
% However, in crime fiction (and in real life), motive itself does not necessarily
% carry much weight in the deductiono process.
% Therefore, we define the culprit with someone who has the means at the opportunity.
culprit(X) :- person(X), opportunity(X), means(X).

% Alternatively, a person is immediately caught if there exists a witness to their crime.
% But since we directly only check witness(X, T) in the code, there's no need to
% include it in the ruleset here.
% culprit(X) :- person(X), person(Y), time(T), witness(Y, T), not(X = Y).

% Someone has opportunity if, at the time of the crime, AND if they can reasonably reach
% the place of murder.
opportunity(X) :- person(X), time_possibility(X), place_possibility(X).

% Someone also has opportunity if they were in the room with the victim at the time of death,
% and the murder method is poison. The idea is that the culprit could have theoretically administered
% the poison in the same room as a crowd without anyone noticing.
opportunity(X) :- cause_of_death(poison), time_of_crime(T), place_of_crime(P), person(X), alibi(X, P, T).

% Let us continue with the first definition, with the lack of an alibi.
% The 'closed world assumption' is entirely sufficient for our purposes.
time_possibility(X) :- person(X), time_of_crime(T), not(alibi(X, _, T)).

% Reaching the place of murder is a bit more tricky.
% We have to determine if it's possible for the culprit to have reached not only
% the position from their actual last known alibi BEFORE the murder, but from the one
% AFTER it (if one is possible to determine.)
% This idea, however, assumes there was nobody in the room with the victim when
% they died. If there WAS, then the culprit should've been seen anyway, and this
% whole line of reasoning becomes meaningless.
place_possibility(X) :-
                        person(X),
                        (place_distances(X, before); not(last_known_alibi(before, X, _, _))),
                        (place_distances(X, after); not(last_known_alibi(after, X, _, _))),
                        time_of_crime(T),
                        place_of_crime(P),
                        not(alibi(_, P, T)).

% We should also keep in mind of flat-out impossible movements to begin with.
% If it's impossible for a person to be in a place before and after the crime, it's
% automatically suspicious and implies the existence of secret passages.
place_possibility(X) :- impossible_alibi(X).

% We must always keep track of a person's last known alibi.
% Knowing the time of crime and the location of the crime and the last known alibi,
% we can determine if it's feasable for the culprit to have made it to the murder
% location.
% A bit frustratingly, last_known_alibi will have to be asserted manually by the
% controller module instead of established through the ruleset at the very end
% of the process...
place_distances(X, L) :-
                            person(X),
                            room(P),
                            room(Q),
                            last_known_alibi(L, X, P, T),
                            place_of_crime(Q),
                            time_of_crime(K),
                            reachable(P, Q, T, K).

% An alibi is considered impossible if it's simply not reachable in the allocated amount of time.
impossible_alibi(X) :-
                        last_known_alibi(before, X, P, T),
                        last_known_alibi(after, X, Q, K),
                        not(reachable(P, Q, T, K)).

% Determining if the location is reachable comes down to:
reachable(P, Q, T, K) :- room(P), room(Q), distance(P, Q, D), D =< abs(T - K).

% There may be secret passages. If there are, we define a distance calculated by taking into account
% the shortened paths allowed by the secret passages. We assume that if someone other than the
% player knows the existence of secret passage, the police would inevitably find the rest.
distance(P, Q, T) :- room(P), room(Q), not(player(X)), knows_secret_passage(X, _, _), (manhattan_secret(P, Q, T); manhattan_secret(Q, P, T)).

% Otherwise, we define distance between rooms through manhattan distance.
distance(P, Q, T) :- room(P), room(Q), (manhattan(P, Q, T); manhattan(Q, P, T)).

% A person knows a secret passage if they see someone going into it, or leaving
% out of it.
knows_secret_passage(X, P, Q) :-
                                time(T),
                                (K is T+1; K is T-1),
                                room(P),
                                room(Q),
                                person(X),
                                person(Y),
                                present(X, P, T),
                                present(Y, P, T),
                                present(Y, Q, K),
                                secret_passage(P, Q, _),
                                not(X = Y).

% When a person witnesses one person going in, it should make sensse that they implicitly
% know the connection works both ways.
knows_secret_passage(X, Q, P) :-
                                time(T),
                                (K is T+1; K is T-1),
                                time(K),
                                room(P),
                                room(Q),
                                person(X),
                                person(Y),
                                present(X, P, T),
                                present(Y, P, T),
                                present(Y, Q, K),
                                secret_passage(P, Q, _),
                                not(X = Y).

% A witness is defined as someone who is present in the room at the moment of the crime and has
% seen someone perform what is considered a damning action.
% A damning action is, for instance, always set at the time of the crime by the culprit, if they are in the same room
% as the victim.
witness(X, T) :-
                person(Y),
                person(X),
                alibi(X, P, T),
                alibi(Y, P, T),
                damning_action(Y, P, T).

% Obviously, people who pass by someone on their way to a room would also count as witnesses
% if they catch a damning action. This applies to damning actions that have an active effect
% rather than being a one-time event.
witness(X, T) :-
                    V is T-1,
                    person(X),
                    person(Y),
                    room(P),
                    room(D),
                    time(T),
                    time(V),
                    present(X, D, V),
                    present(X, P, T),
                    present(Y, P, V),
                    present(Y, D, T),
                    not(D = P),
                    not(X = Y),
                    damning_action(Y, D, V).

% A damning action is carrying something extremely visible and extremely incriminating.
damning_action(X, P, T) :-
                        person(X),
                        room(P),
                        time(T),
                        time(K),
                        present(X, P, T),
                        item_type(A, incriminating),
                        picked_up(X, A, K),
                        not(dropped(X, A, K)),
                        T >= K.

% A damning action is being present at the scene at the time of death and the move
% immediately after. In this case we have to set the player, if only because innocent
% witnesses will potentially be considered culprits otherwise, in spite of being in
% the clear.
damning_action(X, P, T) :-
                        player(X),
                        room(P),
                        (time_of_act(T); K is T-1, time_of_act(K)).

% A dead person can be considered in a room when carried through rooms.
present(X, P, T) :-
                person(X),
                dead(X),
                person(Y),
                not(dead(Y)),
                room(P),
                time(T),
                present(Y, P, T),
                picked_up(Y, X, K),
                not(dropped(Y, X, K)),
                not(X = Y),
                T >= K.

% Determining means comes down to finding some kind of conclusive piece of evidence
% against the culprit.

% Someone has the means if their fingerprints are found on the murder weapon.
means(X) :- weapon_fingerprints(X).

% Someone has the means if an object that could have caused the murder is found on
% a character's person at the time the police arrive.
% (If an object Y of type W that causes Z is found on the culprit's person, means are confirmed.)
means(X) :- possible_murder_weapon_posess(X).

% ...Or an item that is incriminating by its very nature (bloody clothes and such.)
means(X) :- incriminating_item_posess(X).

% I orginally wanted to have a rule about keeping track of whether or not an object has fingerprints
% on it, but it became an absolute nightmare to implement, and with all the extra rules it would've
% required, asserting that an object has fingerprints by the controller seemed much cleaner in the end.
weapon_fingerprints(X) :- person(X), murder_weapon(Y), fingerprints(X, Y).

possible_murder_weapon_posess(X) :- person(X), item(Y), inventory(X, Y), item_type(Y, W), cause_of_death(Z), cause_correlated(Z, W).

incriminating_item_posess(X) :- person(X), item_type(Y, incriminating), inventory(X, Y).

% A murder weapon has a definition of an object having the potential cause of death not being hidden.
murder_weapon(X) :- item(X), item_type(X, W), cause_of_death(Z), cause_correlated(Z, W), not(item_type(X, hidden)).

% A person has an alibi if at least two DIFFERENT people were present in the same room
% at the same time. This means they can vouch for each other.
% In addition, the victim cannot establish an alibi, nor can a victim have an alibi established for them.
alibi(X, P, T) :-
                person(X),
                person(Y),
                room(P),
                present(X, P, T),
                present(Y, P, T),
                not(X = Y),
                not(victim(Y)),
                not(victim(X)).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%                                                        %
% SECTION 2: CHARACTER BEHAVIOR                          %
%                                                        %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%                                                        %
% This part overview some general characcter behavior,   %
% and some additional rules for the player, along with   %
% the core procedure for calling the police.             %
%                                                        %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% The deduction period begins when the police is called.
% For the police to be called, one of the guests needs to be alerted.
% For a guest to be alerted, they need to find the body. In other words, the first time they are in the
% same room as the body.
alerted(X, P) :-
            person(X),
            person(Y),
            room(P),
            time_of_crime(K),
            present(X, P, T),
            present(Y, P, T),
            not(X = Y),
            victim(Y),
            dead(Y),
            not(player(X)),
            not(victim(X)),
            T >= K.

% Let us define the place of crime as the place where the body is found.
place_of_crime(P) :- alerted(_, P).

% The police are always called the moment the body is found, IE the moment someone finds the body.
police(called) :- alerted(_, _).

% As long as a person is alive, they can always move.
valid_move(X, move) :- person(X), not(dead(X)).

% As long as a person is not panicking, they are allowed to wait.
valid_move(X, wait) :- person(X), not(panicking(X)), not(inventory(_, X)).

% It is possible to move between rooms provided the door between them is not locked.
allow_move(X, P, Q, K) :- person(X), room(P), room(Q), room_conn(P, Q, K), not(locked(P, Q)), not(locked(Q, P)).

% It is also possible to go down secret passages, provided the person knows of their existence.
allow_move(X, P, Q, K) :- person(X), room(P), room(Q), secret_passage(P, Q, K), knows_secret_passage(X, P, Q).

% A person is dead when the time of death is set and that time exists.
dead(X) :- person(X), victim(X), time(T), time_of_crime(T).

% We can define a panicking state as, for example, a standard state where a gunshot is not heard.
% The victim cannot panic, as they are likely dead at that point in time anyway.
% (Also conveniently stops them from running around while being dead.)
panicking(X) :-
            person(X),
            not(victim(X)),
            gunshot(heard).

% A gunshot is always heard when a gun is used for the murder.
gunshot(heard) :- item(X), item_type(X, pistol), cause_of_death(Z), cause_correlated(Z, pistol).

% The conditions in which the player is allowed to kill.
kill_moment(T) :- person(X), person(Y), room(P), present(X, P, T), present(Y, P, T), player(X), victim(Y), not(dead(Y)).


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%                                                        %
% SECTION 3: GAME STATE/LOGIC                            %
%                                                        %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%                                                        %
% This section outlines the rules we need to track       %
% game state, and some additional logic to make certain  %
% mechanics easier to do, implementation-wise.           %
%                                                        %
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

% A leaver is a person leaving the room the player has chosen to stay in for the current move.
leaver(X, P, D, T, K) :-
                    V is T-1,
                    person(X),
                    room(P),
                    room(D),
                    present(X, P, T),
                    present(X, D, V),
                    present(player, D, V),
                    present(player, D, T),
                    not(D = P),
                    not(X = player),
                    (room_conn(D, P, K); secret_passage(D, P, K)).

% An enterer is a person entering a room the player has chosen to stay in for the current move.
enterer(X, D, P, T, K) :-
                    V is T-1,
                    person(X),
                    room(P),
                    room(D),
                    present(X, D, V),
                    present(X, P, T),
                    present(player, P, V),
                    present(player, P, T),
                    not(D = P),
                    not(X = player),
                    (room_conn(P, D, K); secret_passage(P, D, K)).

% A passer is a person that is leaving a room just as the player is entering it.
passer(X, P, D, T, K) :-
                    V is T-1,
                    person(X),
                    room(P),
                    room(D),
                    present(X, D, V),
                    present(X, P, T),
                    present(player, P, V),
                    present(player, D, T),
                    not(D = P),
                    not(X = player),
                    (room_conn(P, D, K); secret_passage(P, D, K)).

% A follower is a person that enters the same room the player does in the same move.
follower(X, D, P, T, K) :-
                    V is T-1,
                    person(X),
                    room(P),
                    room(D),
                    present(X, D, V),
                    present(X, P, T),
                    present(player, D, V),
                    present(player, P, T),
                    not(D = P),
                    not(X = player),
                    (room_conn(P, D, K); secret_passage(P, D, K)).

% A person becomes carryable once it's dead.
item_type(X, carryable) :- person(X), dead(X).

% Carrying a dead body is incriminating.
item_type(X, incriminating) :- person(X), dead(X).

% When the player usess a knife, if they don't happen to have an object to cover
% the bloodstain with, they will be noticeably incriminating themselves, as
% they will be covered with blood.
item_type(X, bloodied) :-
                            cause_of_death(stabwound),
                            person(Y),
                            item(Z),
                            item_type(X, clothing),
                            inventory(Y, X),
                            not(inventory(Y, Z)),
                            item_type(Z, cover).

item_type(X, incriminating) :- item_type(X, bloodied).

% Something is in an inventory when picked up and never dropped.
inventory(X, Y) :- picked_up(X, Y, T), not(dropped(X, Y, T)).

% The amount of delay from the moment of the act to the actual death.
death_delay(8) :- cause_of_death(poison).

death_delay(0) :- not(cause_of_death(poison)).

% Some facts regarding objects and their related causes of death:
cause_correlated(stabwound, knife).
cause_correlated(gunshot, pistol).
cause_correlated(poison, cyanide).
cause_correlated(bluntforce, bat).