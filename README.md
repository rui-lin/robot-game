Robot AI Challenge
==================
Using ideas from hybrid automata theory.

Alpha Robot
-----------
Major Improvements

- Initial model with 3 states, gather (near center), attack (while remaining mobile), defend (your current location) [~600 elo, 09/01/2014]
- Change gather behaviour (switch to attack behaviour if unable to move, instead of guarding) [~1000 elo, 09/02/2014]
- Change attack behaviour (suicide only if robot may die next turn and target(s) cannot be killed by one attack)
- Fix "is-in-danger" and "is-safe-from-attacks" logic, so robots avoid getting hit better [~1500 elo, 09/02/2014]
- Enhance attack/defend behaviour (can attack predicted spots, 2 blocks away)
- Enhance gather behaviour (allow two move directions towards target, whichever safer) [~1600 elo, 09/05/2014]
- Enhance attack/defend behaviour (add extra prediction - towards robot) [~1800 elo, 09/05/2014]
- Add intelligence gathering unit (ability to reconstruct enemy moves, make predictions, evaluate and adjust)
  Currently features predicting enemy explosions, and avoiding self-collisions [~1900 elo, 09/08/2014]
- Enhance combat behaviour with parrying at low hp [~2000 elo, 09/08/2014]
- Add escape from spawn point routine [~2100 elo, 09/10/2014]

-----------
Built for the AI robotics competition at https://robotgame.net
