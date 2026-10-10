# What changed

## 1.0.8
Briefs carry Token Saver's helper block when that skill is on, and the report shows each helper's token count when the host reports one.

## 1.0.7
Any prompt or brief written to start a new chat goes in the handoff conductor block, however you asked for it, so Astrolabe shows the Start button for it; a paste fence or a bare code block no longer slips through.

## 1.0.6
The model check reads the model list your environment already gives the chat, so it no longer calls Opus the strongest when Fable is offered, and still names no model itself.

## 1.0.5
Helpers now always come with a card saying who is starting, long ones run in the background so your chat stays free, and a chat started from a handoff still says which model it is on.

## 1.0.4
Dropped the hardcoded model name from the model check; it now says the strongest tier you have access to, so it does not go stale.

## 1.0.3
Renamed plugin and commands to conductor (/conductor, /conductor report, /conductor handoff). Same planning and helper model routing. If you installed `orchestrator`, uninstall it and install `conductor`: an update does not carry you over.
