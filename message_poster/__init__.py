from json import dumps, loads
from os.path import isfile

from mcdreforged.api.command import CommandContext, SimpleCommandBuilder, Text
from mcdreforged.api.types import (CommandSource, ConsoleCommandSource, Info,
                                   PlayerCommandSource, PluginServerInterface)
from mcdreforged.minecraft.rtext.style import RColor
from mcdreforged.plugin.server_interface import (PluginServerInterface,
                                                 ServerInterface)
from requests import get, post

webhook_url: str = ""
uuids: dict[str, str] = {}
lang: str = "ENUS"

ZHTW = {
    "help": "幫助",
    "set_webhook_url": "設定 Discord webhook url",
    "join": "加入了遊戲",
    "left": "離開了遊戲",
    "invalid_language": "無效的語言! (ZHTW, ENUS)",
    "done": "完成!",
    "permission_denied": "權限不足!",
}

ENUS = {
    "help": "help",
    "set_webhook_url": "Set Discord webhook url",
    "join": "joined the game",
    "left": "left the game",
    "invalid_language": "Invalid language! (ZHTW, ENUS)",
    "done": "Done!",
    "permission_denied": "Permission denied!",
}

LANGS = {"ZHTW": ZHTW, "ENUS": ENUS}


def get_help(src: CommandSource):
    if src.is_player:
        src: PlayerCommandSource = src
    elif src.is_console:
        src: ConsoleCommandSource = src
    else:
        return

    src.reply(
        f'[{RColor.aqua.mc_code}Message Poster{RColor.white.mc_code}] {LANGS[lang]["help"]}:'
    )
    src.reply(
        f'    {RColor.red.mc_code}!!mp url <url>{RColor.white.mc_code} {LANGS[lang]["set_webhook_url"]}'
    )
    src.reply(
        f"{RColor.aqua.mc_code}Message Poster{RColor.white.mc_code} by {RColor.yellow.mc_code}momu54{RColor.red.mc_code}#8218"
    )


def set_webhook_url(src: CommandSource, ctx: CommandContext):
    if not src.has_permission(4):
        src.reply(
            f'[{RColor.aqua.mc_code}Message Poster{RColor.white.mc_code}] {RColor.red.mc_code}{LANGS[lang]["permission_denied"]}'
        )
        return

    server = src.get_server().as_plugin_server_interface()
    configpath = server.get_data_folder()
    server.logger.info(ctx["webhook"])
    config = {"webhook_url": ctx["webhook"], "lang": lang}
    global webhook_url
    webhook_url = ctx["webhook"]
    file = open(f"{configpath}/webhook_url.json", "w")
    file.write(dumps(config, indent=4))
    file.close()
    src.reply(
        f'[{RColor.aqua.mc_code}Message Poster{RColor.white.mc_code}] {RColor.green.mc_code}{LANGS[lang]["done"]}'
    )


def set_language(src: CommandSource, ctx: CommandContext):
    global lang
    if not src.has_permission(4):
        src.reply(
            f'[{RColor.aqua.mc_code}Message Poster{RColor.white.mc_code}] {RColor.red.mc_code}{LANGS[lang]["permission_denied"]}'
        )
        return
    if ctx["lang"] not in LANGS.keys():
        src.reply(
            f'[{RColor.aqua.mc_code}Message Poster{RColor.white.mc_code}] {RColor.red.mc_code}{LANGS[lang]["invalid_language"]}'
        )
        return

    server = src.get_server().as_plugin_server_interface()
    configpath = server.get_data_folder()
    config = {"webhook_url": webhook_url, "lang": ctx["lang"]}
    lang = ctx["lang"]
    file = open(f"{configpath}/webhook_url.json", "w")
    file.write(dumps(config, indent=4))
    file.close()
    src.reply(
        f'[{RColor.aqua.mc_code}Message Poster{RColor.white.mc_code}] {RColor.green.mc_code}{LANGS[lang]["done"]}'
    )


def on_server_startup(server: PluginServerInterface):
    configpath = f"{server.get_data_folder()}/webhook_url.json"
    config = WebhookConfig(configpath)
    global webhook_url, lang
    webhook_url = config.webhook_url
    lang = config.lang


def on_load(server: ServerInterface, prev):
    server.logger.info("Message Poster loaded!")

    # command
    builder = SimpleCommandBuilder()

    builder.command("!!mp", get_help)
    builder.command("!!mp url <webhook>", set_webhook_url)
    builder.command("!!mp lang <lang>", set_language)

    builder.arg("webhook", Text)
    builder.arg("lang", Text)

    builder.register(server)


def on_user_info(server: PluginServerInterface, info: Info):
    if webhook_url == "":
        return
    if info.content.startswith("!!"):
        return
    uuid = uuids.get(info.player)

    payload = {
        "content": info.content,
        "username": info.player,
    }
    if uuid:
        payload["avatar_url"] = f"https://crafatar.com/avatars/{uuid}"
    post(webhook_url, json=payload)

def on_player_joined(server: PluginServerInterface, player: str, info: Info):
    if webhook_url == "":
        return
    uuid = get(f"https://api.mojang.com/users/profiles/minecraft/{player}").json()["id"]
    uuids[player] = uuid

    playload = {
        "embeds": [
            {
                "author": {
                    "name": f"{player} {LANGS[lang]['join']}",
                    "icon_url": f"https://crafatar.com/avatars/{uuid}",
                },
                "color": 65280,
            }
        ],
    }
    post(webhook_url, json=playload)


def on_player_left(server: PluginServerInterface, player: str):
    if webhook_url == "":
        return
    uuid = uuids[player]

    playload = {
        "embeds": [
            {
                "author": {
                    "name": f"{player} {LANGS[lang]['left']}",
                    "icon_url": f"https://crafatar.com/avatars/{uuid}",
                },
                "color": 16711680,
            }
        ],
    }
    post(webhook_url, json=playload)
    del uuids[player]


class WebhookConfig:
    def __init__(self, configpath: str):
        if not isfile(configpath):
            file = open(configpath, "w")
            default_config = {"webhook_url": "", "lang": "ENUS"}
            file.write(dumps(default_config, indent=4))
            file.close()
            self.webhook_url = default_config["webhook_url"]
            self.lang = default_config["lang"]
            return
        file = open(configpath, "r")
        file_content = file.read()
        file.close()
        parsed = loads(file_content)
        self.webhook_url: str = parsed["webhook_url"]
        self.lang: str = parsed["lang"]
