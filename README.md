# Warning

Due to discord's new rate limit on messages older than one hour the bot is not updating properly.

# nozomi-cb-bot

Here is the source code for Nozomi.
A discord bot made to help managing clan battles in Princess Connect! Re: Dive JP.<br>
You have to create your own discord bot and run the code yourself for it to work while it's still under development.

## Features

* Hit tracking
* Damage tracking
* Overflow tracking
* Queueing system
* [Discord Embed display](https://cdn.discordapp.com/attachments/796797906706497536/876172860090105876/unknown.png) 
* Google Drive database backup (diabled)
* Google Sheet display (disabled)

## Installation and Setup

1. After cloning the repository use pip to install the required packages.
```bash
pip install -r requirements.txt
```

2. Create a `discord_token.txt` file containing your bot's Discord API token.

3. Create a `clans_config.json` file containing the clan battle settings.
You can also overwrite the default settings in this file or in `config.py`.

    `clans_config.json` example:
```json
{
    "test": {
        "ENV": 1,
        "GUILD_ID": 1234567890123456789,
        "CHANNEL_ID": 1234567890123456789,
        "CLAN_ROLE_ID": 1234567890123456789,
        "CLAN_MOD_ROLE_ID": 1234567890123456789
    }
}
```

4. Run `nozomi.py`

### Enviromment
In config.py, `ENV=0` is for production, anything above is for development.<br>
Only the clan battle profiles with the same ENV value as the config variable will be started.

||DEV|PROD|
|-|:-:|:-:|
|CB start date|Now*|Latest cb's date|
|CB end date|Now + 115 hours|Latest cb's date|
|Db name|\<name\>_dev.db|\<name\>.db|
|Error messages|Yes|No**|

 *The time the script is started at<br>
 **Unless unexpected errors

## Usage

### List of commands: (examples with B1)
* `!q b1`  : Add yourself to B1's queue.<br>
args : **boss**, of, [message], wave
* `!dq b1` : Remove yourself from B1's queue.<br>
args : **boss**
* `!h b1` : Claim a hit on B1 (Means you're going to hit now)<br>
args : **boss**, of
* `!s b1 @member` : Claim a B1 hit with someone else. (sync)<br>
args : **boss**,  **@member**, of
* `!c` : Cancel a claimed hit.
* `!d 1m` : Register 1 million damages to the boss you claimed. (dot and coma are counted as decimal separator)<br>
args : **damage**, of
* `!dead` : Same as `!d` but kills the boss you claimed.
* `!undo` : Undo the last hit you made as long as no one hit the boss after you.
* `!of` : Gives you the OF status
* `!rmof` : Removes your OF status

*Argument in bold are required for the command to work.*<br>
*Commands and arguments are not case sensitive.*

### Arguments:
Every argument must be separated by spaces when using multiple of them, they can be used in any order.


* `boss` : Either b1, b2, b3, b4 or b5 depending on the boss you want to target.
* `damage` : The number of damage you dealt. you can add the letter `k` or `m` to multiply by 1 000 (k) or 1 000 000 (m) the number you entered (e.g. `4.2m`, `4200k` or `4200000` are equivalent).
* `of` : Just type `of`, shorthand for using the `!of` command.
* `[message]` : Put some text between `[]` to add a text note.
* `@member` : Mention the user you want to target.
* `wave` : Type the letter `w` followed by the number of the wave you want to target (e.g. `w32`).

### Mods only:
* `!fdq b1 @member` : Dequeue the mentioned member from B1's queue. 
* `!fc @member` : Cancel the hit of the mentioned member.
* `!stop` : Stops the clan battle for the channel the command is used in.
* `!shutdown` : Shutdowns the bot.

### OF status:
When you are about to do a OF hit you need to tell the bot beforehand.
When the bot knows you are using OF it means you have the OF status.
The OF status will remain until you perform a hit or use the !rmof command.
You can also be granted the OF status by typing 'of' anywhere during any of the !q, !h, !s, !d or !dead commands (eg. !h b1 of)

## Notes
* This bot is still under development, contact me on discord (SkySet#3043) if you have any questions or suggestions.
* I'm currently rewriting the bot in javascript since the python library i was using will no longer be updated.

## Setup
```sh
# Install dependencies
pipenv install --dev

# Setup pre-commit and pre-push hooks
pipenv run pre-commit install -t pre-commit
pipenv run pre-commit install -t pre-push
```

## Credits
This package was created with Cookiecutter and the [sourcery-ai/python-best-practices-cookiecutter](https://github.com/sourcery-ai/python-best-practices-cookiecutter) project template.
