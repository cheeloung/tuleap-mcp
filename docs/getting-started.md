# Getting Started with Tuleap MCP (Windows + Claude Desktop)

This guide walks you through connecting Claude Desktop to your team's Tuleap projects, so you can ask Claude things like "what are my open tasks?" or "create a bug in the Tasks tracker" directly in a chat — no need to open Tuleap in a browser for common actions.

No programming experience needed. You'll be copying and pasting a few commands into a black text window (called Command Prompt) and editing one settings file. It takes about 15 minutes.

---

## What you'll need before starting

- A Windows PC
- A Tuleap account (the same one you use to log into your Tuleap projects)
- Claude Desktop installed ([download here](https://claude.ai/download) if you don't have it yet)
- About 15 minutes

---

## Step 1 — Install Python

Python is the programming language this tool is written in. You need it installed once.

1. Go to [python.org/downloads](https://www.python.org/downloads/) and click the big yellow **"Download Python"** button.
2. Run the installer you downloaded.
3. **Important:** On the very first install screen, tick the checkbox at the bottom that says **"Add python.exe to PATH"**. This is the single most common thing people forget — if you skip it, nothing later in this guide will work.
4. Click **"Install Now"** and let it finish.

**Check it worked:** Open the **Start Menu**, type `cmd`, and press Enter to open Command Prompt. Type:
```
python --version
```
and press Enter. You should see something like `Python 3.12.4`. If instead you see an error, Python isn't installed correctly — reinstall it and make sure you tick the PATH checkbox.

---

## Step 2 — Download the Tuleap MCP program

1. Go to **https://github.com/cheeloung/tuleap-mcp**
2. Click the green **"Code"** button, then click **"Download ZIP"**.
3. Once downloaded, find the ZIP file (usually in your **Downloads** folder), right-click it, and choose **"Extract All..."**.
4. Extract it somewhere easy to find, e.g. `Documents\tuleap-mcp`. Remember this location — you'll need it in a moment.

---

## Step 3 — Set it up

1. Open **File Explorer** and navigate into the folder you just extracted (it should contain a file named `pyproject.toml`).
2. Click into the address bar at the top of the File Explorer window, type `cmd`, and press Enter. This opens Command Prompt already pointed at the right folder.
3. Copy and paste each of these lines one at a time, pressing Enter after each:

```
python -m venv .venv
```
```
.venv\Scripts\activate
```
```
pip install -e .
```

The last command takes a minute or two and will print a lot of text — that's normal. When it's done and you see the prompt again, setup is complete.

4. **Find the program's exact location on your PC** (you'll need this in Step 5):
   - In File Explorer, open the `.venv\Scripts` folder inside your extracted folder.
   - Find the file named `tuleap-mcp.exe`.
   - Hold **Shift**, right-click it, and choose **"Copy as path"**.
   - Paste it somewhere temporary (like a Notepad window) — it'll look something like:
     `"C:\Users\yourname\Documents\tuleap-mcp\.venv\Scripts\tuleap-mcp.exe"`
   - Keep this Notepad window open, you'll need it shortly.

---

## Step 4 — Get your Tuleap access token

This is like a password that lets Claude read/write your Tuleap data on your behalf. Treat it exactly like a password — never share it with anyone or paste it anywhere public.

1. Log into your Tuleap site in a web browser.
2. Click your **avatar/username** in the top-right corner, then find **"Personal Access Tokens"** (usually under Account Settings).
3. Click **"Generate new token"**, give it a name like `Claude Desktop`, and create it.
4. **Copy the token immediately** — Tuleap only shows it once. Paste it into the same Notepad window from Step 3 so you don't lose it.
5. Also note down your Tuleap site's web address (e.g. `https://tuleap.yourcompany.com`) — you'll need that too.

---

## Step 5 — Connect it to Claude Desktop

1. Fully quit Claude Desktop if it's open (right-click its icon in the system tray near the clock, and choose **Quit** — just closing the window isn't enough).
2. Open **File Explorer**, click the address bar, type exactly:
   ```
   %APPDATA%\Claude
   ```
   and press Enter.
3. Look for a file called `claude_desktop_config.json`.
   - If it exists, open it with **Notepad** (right-click → Open with → Notepad).
   - If it doesn't exist, create a new text file in that folder, name it exactly `claude_desktop_config.json` (make sure it doesn't end up `claude_desktop_config.json.txt` — in File Explorer, turn on "File name extensions" under the View tab to check).
4. Paste in the following, replacing the three placeholder values using what you saved in your Notepad window:

```json
{
  "mcpServers": {
    "tuleap": {
      "command": "C:\\Users\\yourname\\Documents\\tuleap-mcp\\.venv\\Scripts\\tuleap-mcp.exe",
      "env": {
        "TULEAP_URL": "https://tuleap.yourcompany.com",
        "TULEAP_API_KEY": "paste-your-token-here"
      }
    }
  }
}
```

**Important Windows detail:** the path must use **double** backslashes (`\\`), not single ones. If you copied a path in Step 3 that looks like `C:\Users\yourname\...`, you need to change every `\` to `\\` before pasting it in. The easiest way: paste the path into Notepad, press `Ctrl+H` (Find & Replace), search for `\` and replace with `\\`, click "Replace All".

If the file already had other content in it (e.g. other MCP servers already configured), just add the `"tuleap": { ... }` block inside the existing `"mcpServers": { ... }` section instead of replacing the whole file.

5. Save the file (**Ctrl+S**) and close Notepad.
6. Reopen Claude Desktop.

---

## Step 6 — Test it

Start a new chat in Claude Desktop and ask something like:

> Can you list the Tuleap projects I'm a member of?

If it works, Claude will show you a list of your projects. If Claude says it doesn't have access to any Tuleap tools, see Troubleshooting below.

---

## Troubleshooting

**Claude says it has no Tuleap tools available**
- Make sure you fully quit and reopened Claude Desktop (system tray → Quit, not just closing the window).
- Double-check `claude_desktop_config.json` is valid — an extra or missing comma will break it. Easiest fix: delete everything and paste the example again carefully.
- Confirm the path to `tuleap-mcp.exe` is correct and uses double backslashes (`\\`).

**"python is not recognized as an internal or external command"**
- Python isn't on your PATH. Reinstall Python from python.org and make sure to tick "Add python.exe to PATH" on the first screen.

**Claude says it can't connect to Tuleap / authentication errors**
- Double-check `TULEAP_URL` doesn't have a trailing slash and starts with `https://`.
- Double-check your access token was copied correctly with no extra spaces, and hasn't expired or been revoked in Tuleap.

**Still stuck?** Ask whoever shared this guide with you for help, or share the exact error message Claude shows you.

---

## Keeping it up to date

This tool is actively being improved. To get the latest version later:

1. Download a fresh ZIP from https://github.com/cheeloung/tuleap-mcp (Step 2 above) and extract it over the same folder (or a new one).
2. Repeat Step 3 (the `python -m venv .venv` / `pip install -e .` commands) inside that folder.
3. If you used a new folder, update the `command` path in `claude_desktop_config.json` (Step 5) to point at the new location.

## A note on your access token

Your Tuleap access token acts like a password. Anyone with it can read and modify your Tuleap projects as you. Don't paste it into chat messages, emails, or share the `claude_desktop_config.json` file with anyone.
