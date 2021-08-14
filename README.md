# nozomi-cb-bot

A discord bot made to help managing clan battles in Princess Connect! Re: Dive.

## Installation and Setup

1. After cloning the repository use pip to install the required packages.
```bash
pip install -r requirements.txt
```

2. Create a `discord_token.txt` file containing your bot's Discord API token.

3. Create a `clans_config.json` file containing the clan battle settings.
You can also overwrite the default settings in this file or in `config.py`.

	Example:
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
