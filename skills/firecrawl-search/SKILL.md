---
name: firecrawl-search
allowed-tools: [Bash, WebSearch, mcp__firecrawl__firecrawl_search, mcp__firecrawl__firecrawl_scrape, mcp__firecrawl__firecrawl_credit_usage]
description: Make Firecrawl the default web search for the rest of this chat, and set Firecrawl up if it is not connected yet. Use when the user presses a Firecrawl button, runs /firecrawl-search, says "use Firecrawl", "search with Firecrawl", "turn on Firecrawl", asks how many Firecrawl credits are left, or asks how to set up, pay for, or connect Firecrawl.
---

# Firecrawl search

Turning this on does not search anything. It switches this chat over: from
now on, whenever the user asks you to look something up, find, research, or
read a page on the web, you use Firecrawl instead of the built-in web search.
Then you say, in one line, that it is on and what to try.

Firecrawl is a web search and page reader built for AI. Its results come back
as clean text with the useful parts highlighted, it can read whole pages
(including ones that need a real browser), and it is free up to a monthly
allowance.

## 1. Is it connected?

Look at the tools you have. If you have `firecrawl_search` (any tool whose name
ends in `firecrawl_search`, for example `mcp__firecrawl__firecrawl_search`), it
is connected. Skip to section 3.

If it is connected through an account, call `firecrawl_credit_usage` right
away (it costs nothing). If credits are at or below zero, go straight to
section 5 instead of announcing that Firecrawl is on.

If not, go to section 2. Do not search with the built-in tool and pretend it
was Firecrawl.

## 2. Setting it up (first time)

Pick ONE path for this person and offer only that one, with one line on why.
Mention the others only if they ask or the first one does not fit.

| Their situation | Best path |
|---|---|
| Just wants to try it, no account | **Keyless** |
| Wants it for real, or keyless ran out | **Free account + API key** |
| Uses Claude Code in a terminal and likes signing in with a browser | **Sign-in (OAuth)** |
| Also uses Codex, OpenCode, Antigravity, or an agent without MCP | **Firecrawl CLI** |
| Building their own app or script | **REST API / SDKs** (point at docs.firecrawl.dev, nothing to set up here) |

When the chat runs without a terminal in front of the user (an app or
dashboard driving Claude Code), default to **Keyless** the first time, and to
**Free account + API key** once they want to keep using it. Such a chat cannot
click through a browser sign-in on its own, so the key path is the reliable
one there.

Every MCP path adds a server Claude Code loads when a chat STARTS. After adding
it, tell them: open a new chat and turn Firecrawl on again there. It
will not appear in the chat where it was added.

Before adding, run `claude mcp list` and look for an existing `firecrawl`
entry. If one is there but failing, ask before removing it.

### Keyless (no account, no key)

```
claude mcp add --scope user --transport http firecrawl https://mcp.firecrawl.dev/v2/mcp
```

Gives search, page reading (scrape) and file parsing only. Limits are per day
and per internet connection (IP address), so anyone else on the same wifi or
office network shares the allowance. Good for a taste, not for daily use.

### Free account + API key (recommended for ongoing use)

1. They sign up at https://www.firecrawl.dev (Google or GitHub sign-in is fine).
   No card needed for the free plan.
2. They copy their API key from the dashboard at https://www.firecrawl.dev/app
   (it starts with `fc-`).
3. The key must never be typed into this chat: the chat is saved. On a Mac,
   have them run this in Terminal; it asks for the key without showing it:

   ```
   security add-generic-password -a "$USER" -s firecrawl-api-key -w
   ```

   Then you run (the key stays out of the transcript):

   ```
   claude mcp add --scope user --transport http firecrawl https://mcp.firecrawl.dev/v2/mcp --header "Authorization: Bearer $(security find-generic-password -s firecrawl-api-key -w)"
   ```

   Not on a Mac: give them the `claude mcp add` line with `fc-YOUR-KEY` as a
   placeholder in a fenced block and let them run it in their own terminal.
   Never print, echo, or read back the key to check it.

### Sign-in (OAuth)

```
claude mcp add --scope user --transport http firecrawl https://mcp.firecrawl.dev/v2/mcp-oauth
```

Then in a terminal Claude Code session they type `/mcp`, pick firecrawl, and
sign in in the browser. Same account and allowance as the key path, no key to
look after. Needs that interactive step, which is why it is not the default
for a chat with no terminal.

### Firecrawl CLI (works across several AI tools at once)

```
npx -y firecrawl-cli@latest init --all --browser
```

Installs the `firecrawl` command plus Firecrawl's own skills into every AI
coding tool it finds, and opens the browser to sign in. Then search with
`firecrawl search "query"` through Bash. Choose this only when they want
Firecrawl in tools other than Claude Code too.

## 3. Turned on: how to search for the rest of this chat

- Every web lookup goes to `firecrawl_search` first. Pass `sources: ["web"]`
  unless they want news or images, and keep `limit` at 5 to 10: search costs
  2 credits per 10 results.
- When a result's excerpt is not enough, read the page with `firecrawl_scrape`
  (1 credit per page). Read the one or two pages that matter, not all of them.
- For a single known page they hand you, go straight to `firecrawl_scrape`.
- Bigger jobs (`firecrawl_crawl`, `firecrawl_map`, `firecrawl_agent`) cost
  more and need an account. Say roughly what it will cost before starting one.
- Cite what you used as links at the end, as with any search.
- It stays on until the chat ends or they say to switch back.

## 4. Credits and limits

Know these so you can answer plainly when asked. Check the live numbers with
`firecrawl_credit_usage` (account paths only) rather than quoting from memory;
prices change.

- **Free plan:** 1,000 credits a month, reset on the account's billing date,
  no rollover. About 10 searches a minute.
- **What things cost:** search 2 credits per 10 results; read a page 1 credit;
  crawl or map 1 credit per page. A typical "look this up and read the best
  page" is about 3 to 4 credits, so the free plan is a few hundred lookups a
  month.
- **Keyless:** a daily cap per internet connection, shared with anyone on the
  same network.
- **Paid plans** (as of late 2026, billed yearly): Hobby about $16 a month for
  5,000 credits, Standard about $83 for 100,000, then Growth and Scale. Paid
  plans can top up automatically in $5 steps when credits run out (they can
  turn that off). Current prices: https://www.firecrawl.dev/pricing

If they ask whether to pay: compare what they actually use (the
`firecrawl_credit_usage` historical view) against the free 1,000. Most people
searching from a chat never need to. Recommend paying only if they keep running
out before the reset date, and say how strongly.

## 5. When it runs out or fails

- **Out of credits** (an error saying payment required, low credits, or a 402):
  tell them once, in one line, with the reset date from `firecrawl_credit_usage`
  (`billingPeriodEnd`). Then answer this request with the built-in web search
  and say that is what you used. Offer the options once: wait for the reset,
  add the keyless server as a backup, or upgrade.
- **Keyless as a backup** sits beside the account server under its own name,
  so it never replaces it:
  `claude mcp add --scope user --transport http firecrawl-keyless https://mcp.firecrawl.dev/v2/mcp`
  When both are connected, search with the account one first and use the
  `firecrawl-keyless` tools only when the account one is out of credits. Fall
  back to the built-in search only when both are spent.
- **Too many requests** (429): wait a few seconds and retry once, then fall
  back as above.
- **Not authorized** (401/403): the key or sign-in has expired. Point back to
  section 2 for their path.

Never silently switch providers. If an answer did not come from Firecrawl,
say so.

## Asked again, or asked for credits

When it is turned on again in a chat where Firecrawl is already on, or the
request is `credits`, tell them how many credits are left and when they reset,
in one line.
