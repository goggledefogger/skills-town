# What changed

## 1.0.5
Helpers now always come with a card saying who is starting, long ones run in the background so your chat stays free, and a chat started from a handoff still says which model it is on.

## 1.0.4
Dropped the hardcoded model name from the model check; it now says the strongest tier you have access to, so it does not go stale.

## 1.0.3
Renamed plugin and commands to conductor (/conductor, /conductor report, /conductor handoff). Same planning and helper model routing. If you installed `orchestrator`, uninstall it and install `conductor`: an update does not carry you over.
