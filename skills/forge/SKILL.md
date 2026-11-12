---
name: forge
description: Turn something the member keeps doing by hand into a skill with its own button. Skims the open Astrolabe chats for repeatable ways of working, offers about 3, looks closer at the one they pick, writes the skill and pins its button to their shelf. Use when the member presses the Forge card, types /forge, or says "forge a skill", "make this a skill", "turn this into a button", or "what in my chats could be a skill".
allowed-tools: [Read, Write, Bash]
---

# Forge

The member has been working something out by hand across their chats. Find the ways of working worth repeating, let them pick one, and end with a finished button on their shelf. One press, one question, one button. Not a draft, not an interview.

A forged skill carries the **method**, never the content. See "What never goes in" before writing anything.

## 1. Skim

Run the reading step, `skim.mjs`, which sits beside this page (under Claude Code, `${CLAUDE_PLUGIN_ROOT}/skim.mjs`). Give its full path; it runs from any folder:

```
node <this skill's folder>/skim.mjs <dashboard address> --skip <this chat's tab id>
```

The dashboard address and this chat's tab id are the ones your session was given. It prints each open chat's title, the member's own messages, and the opening of each reply. Their messages are where the repeated asks and the corrections are, so read those closest.

If the member pointed at something (words after `/forge`, "the deck chat", "the thing we just did"), skip to step 3 with that. If the step fails or this is not Astrolabe, work from this conversation alone and say so in one line.

## 2. Offer about 3

Look for the bigger repeatable ideas, not one-off tasks. Signs of one:

- they walked you through the same kind of steps more than once, in one chat or several
- they corrected how you did it, and the corrected way is now the way
- they described how they like a kind of work to go
- the work will plainly come round again (a weekly thing, every talk, every trip, every client)

One chat can hold several. No fixed list of kinds: judge what is worth repeating for this person. Before offering, list the names and descriptions of the skills they already have (`.agents/skills/` in the brain, and the session's own skill list). When one already does the job, offer to improve that one instead of making a twin.

Name the whole way of working, not one move inside it: several moves in the same chats that serve one purpose (preparing, rehearsing and revising the same piece of work) are one idea. A fix, a lookup or a decision made once is a task, not a way of working; leave it out.

When a chat that looks promising was cut short in the digest, read it with `--tab` before offering.

Show about 3, the one they are likeliest to use again first, each as a name and one plain line that says what the button would do and the chat or chats it came from (chat titles are fine here). Fewer than 3 is fine; never pad the list, and when unsure whether something is a way of working or a one-off, leave it out. Then ask once which to make. They may pick one, name another, or point at a chat.

## 3. Look closer

Read the chat or chats the pick came from in full:

```
node skim.mjs <dashboard address> --tab <tab id>
```

Pull out the method:

- what starts it (what they say or have in hand when they want this)
- what it needs each time (a file, a link, a topic), and where that usually lives
- the steps, in the order that worked
- every correction they made, as a rule ("one line per idea", not the story of the mistake)
- what done looks like, and what they do with the result

Keep it general across the kind of work. A skill forged from one talk should serve the next talk. If something essential is missing and cannot be reasonably assumed, ask one question; otherwise decide and say what you assumed in the closing line.

## 4. Write the skill

If a skill for writing skills is installed here (skill-creator, writing-skills), use it for the wording and keep the rules on this page. Otherwise write this shape:

```markdown
---
name: <kebab-id>
description: <what it does, then "Use when" with the button's phrase and the words they would say>
---

# <Name>

<2 lines: what this is for and what it ends with>

## Steps
<numbered, imperative, in the order that worked>

## How they like it
<their corrections, as rules>

## Done
<what finished looks like>
```

Short beats complete: steps someone could follow, under about 60 lines. Save it to `.agents/skills/<id>/SKILL.md` in the member's brain.

## 5. The button

Add a card to `.dashboard-rituals.json` in the brain folder (create it as `[]` if missing; keep every card already there):

```json
{ "id": "<kebab-id>", "label": "<Name>", "phrase": "<what a press says>",
  "desc": "<one plain line>", "skill": "<kebab-id>", "source": "forged",
  "app": { "bg": "<a colour or gradient>", "mark": "<plain white SVG shapes on a 48 unit grid>" } }
```

The phrase is what a press types into a chat, so the skill's description must name it. Give the card its own icon, fitted to what it does: plain shapes, no scripts, links or images. A card written there pins itself; do not send them anywhere to pin it.

## 6. Say what you made

In 3 lines or fewer: the button's name and what a press does, what you assumed, and that "undo that" removes it. Show the skill itself in a card if it is short, otherwise its path. Do not run the new skill; pressing the button is theirs.

Undo means: remove the card from `.dashboard-rituals.json` and delete `.agents/skills/<id>/`. Nothing else was touched.

## What never goes in

The chats are private. The skill and its card hold how the work is done, and none of what it was done on:

- no names of people, companies or clients, no contact details, no figures, dates or places from the chats
- no text of their documents, slides, messages or notes, even as an example; write a made-up example instead
- no file paths from their machine; say "the deck" or "the outline they name", and let the skill ask or look at run time
- their preferences about the work ("keyword bullets, not sentences") are method, so those go in the skill

Read the finished skill once against this list before saving.

Everything Forge makes stays in the member's brain. Sharing a forged skill with other people is a separate step they ask for, never part of a press.

## Requirements

Astrolabe, for the open chats and the shelf. Node, which Astrolabe already runs on. Without Astrolabe, Forge works from the current conversation and writes the skill wherever this assistant keeps skills; there is no button.
