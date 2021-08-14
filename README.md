# nozomi-cb-bot

Here is the source code for Nozomi.
A discord bot made to help managing clan battles in Princess Connect! Re: Dive JP.

You have to create your own discord bot and run the code yourself for it to work while it's still under development.

## Features

* Hit tracking
* Damage tracking
* Overflow tracking
* Queueing system
* [Discord Embed display](https://cdn.discordapp.com/attachments/796797906706497536/876172860090105876/unknown.png) 
* Google Drive display (disabled)

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
		"GUILD_ID": 796792048882548756,
        	"CHANNEL_ID": 798368120913788969,
        	"CLAN_ROLE_ID": 797601335839031337,
        	"CLAN_MOD_ROLE_ID": 797601335839031337
	}
}
```

4. Run `nozomi.py`

*In config.py, ENV=0 is for production, anything above is for development.*

## Usage

Commands are not case sensitive but the arguments are.

### List of commands: (examples with B1)
* `!q b1` : Add yourself to B1's queue.
* `!dq b1` : Remove yourself from B1's queue.
* `!h b1` : Claim a hit on B1 (Means you're going to hit now)
* `!s b1 @member` : Claim a B1 hit with someone else. (sync)
* `!c` : Cancel a claimed hit.
* `!d 1m` : Register 1 million damages to the boss you claimed.
* `!dead` : Kill the boss you claimed (register damages equal to the boss' remaining health).
* `!of` : Gives you the OF status
* `!rmof` : Removes your OF status

Mods only:
* `!fdq b1 @member` : Dequeue the mentioned member from B1's queue. 
* `!fc @member` : Cancel the hit of the mentioned member

### OF status:
When you are about to do a OF hit you need to tell the bot beforehand.
When the bot knows you are using OF it means you have the OF status.
The OF status will remain until you perform a hit or use the !rmof command.
You can also be granted the OF status by typing 'of' anywhere during any of the !q, !h, !s, !d or !dead commands (eg. !h b1 of)

## Notes
* For now, most of the clan battle specific data has to be edited in the config.py file every month.
* This bot is still under development, contact me on discord (SkySet#3043) if you have any questions or suggestions.
* I will make a proper documentation and tutorials when everything is mostly done
