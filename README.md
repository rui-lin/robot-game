Robot AI Challenge
==================
Using ideas from hybrid automata theory.

Alpha Robot
-----------
Major Improvements

- Initial model with 3 states, gather (near center), attack (while remaining mobile), defend (your current location) [~600 elo, 09/01/2014]
- Change gather behaviour (switch to attack behaviour if unable to move, instead of guarding) [~1000 elo, 09/02/2014]
- Change attack behaviour (suicide only if robot may die next turn and target(s) cannot be killed by one attack)
- Fix "is-in-danger" and "is-safe-from-attacks" logic, so robots avoid getting hit better [~1100 elo, 09/02/2014]
- Enhance attack/defend behaviour (can attack predicted spots, 2 blocks away) [~1500 elo, 09/04/2014]
- Allow two move directions towards target, whichever safer [~1600 elo, 09/05/2014]

-----------
Built for the AI robotics competition at https://robotgame.net
