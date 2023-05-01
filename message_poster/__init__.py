from json import dumps, loads
from os import listdir
from os.path import isdir, isfile

from mcdreforged.api.command import CommandContext, SimpleCommandBuilder, Text
from mcdreforged.api.types import (CommandSource, ConsoleCommandSource, Info,
                                   PlayerCommandSource, PluginServerInterface)
from mcdreforged.minecraft.rtext.style import RColor
from mcdreforged.plugin.server_interface import (PluginServerInterface,
                                                 ServerInterface)
from python_nbt.nbt import read_from_nbt_file
from requests import post

from message_poster.utils import load_properties

webhook_url: str = ""
uuids: dict[str, str] = {}
lang: str = "ENUS"
nicknames: dict[str, str] = {}

ZHTW = {
    "help": "幫助",
    "set_webhook_url": "設定 Discord webhook url",
    "join": "加入了遊戲",
    "left": "離開了遊戲",
    "invalid_language": "無效的語言! (ZHTW, ENUS)",
    "done": "完成!",
    "permission_denied": "權限不足!",
    "nickname_update": "暱稱已更新為",
    "nickname_remove": "已清除暱稱",
    "nickname_used": "已使用暱稱",
    "set_language": "設定語言",
    "error": "錯誤",
}

ENUS = {
    "help": "help",
    "set_webhook_url": "Set Discord webhook url",
    "join": "joined the game",
    "left": "left the game",
    "invalid_language": "Invalid language! (ZHTW, ENUS)",
    "done": "Done!",
    "permission_denied": "Permission denied!",
    "nickname_update": "Nickname updated to",
    "nickname_remove": "Nickname removed",
    "nickname_used": "Nickname used",
    "set_language": "Set language",
    "error": "ERROR",
}

LANGS = {"ZHTW": ZHTW, "ENUS": ENUS}

essential_commands_installed: bool = False
world_name: str


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
        f'    {RColor.red.mc_code}!!mp lang <language (ZHTW/ENUS)>{RColor.white.mc_code} {LANGS[lang]["set_webhook_url"]}'
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
    if server is None:
        src.reply(
            f'[{RColor.aqua.mc_code}Message Poster{RColor.white.mc_code}] {RColor.red.mc_code}{LANGS[lang]["error"]} {RColor.yellow.mc_code}server is None{RColor.red.mc_code}!'
        )
        return

    configpath = server.get_data_folder()
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
    if server is None:
        src.reply(
            f'[{RColor.aqua.mc_code}Message Poster{RColor.white.mc_code}] {RColor.red.mc_code}{LANGS[lang]["error"]} {RColor.yellow.mc_code}server is None{RColor.red.mc_code}!'
        )
        return

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


def on_load(server: ServerInterface, _):
    server.logger.info("Message Poster loaded!")

    server_root = server.get_mcdr_config()["working_directory"]
    if isdir(f"{server_root}/mods/"):
        for mod in listdir(f"{server_root}/mods/"):
            if "essential_commands" in mod:
                global essential_commands_installed
                essential_commands_installed = True
                break

    server_properties = load_properties("./server.properties")
    global world_name
    world_name = server_properties["level-name"]

    # command
    builder = SimpleCommandBuilder()

    builder.command("!!mp", get_help)
    builder.command("!!mp url <webhook>", set_webhook_url)
    builder.command("!!mp lang <lang>", set_language)

    builder.arg("webhook", Text)
    builder.arg("lang", Text)

    builder.register(server)


def on_user_info(_: PluginServerInterface, info: Info):
    if (
        not webhook_url
        or not info.content
        or not info.player
        or info.content.startswith("!!")
    ):
        return
    uuid = uuids.get(info.player)

    playload = {
        "content": info.content,
        "avatar_url": f"https://crafatar.com/avatars/{uuid}" if uuid else None,
        "username": info.player,
    }
    post(webhook_url, json=playload)


def on_info(server: PluginServerInterface, info: Info):
    if not webhook_url or not info.content or info.content.startswith("!!"):
        return

    if "User Authenticator" in info.raw_content and info.content.startswith(
        "UUID of player"
    ):
        spilted = info.content.split(" is ")
        uuid = spilted[1]
        nickname = original_name = spilted[0].split(" player ")[1]
        if essential_commands_installed:
            server_root = server.get_mcdr_config()["working_directory"]
            try:
                rawtext = read_from_nbt_file(
                    f"{server_root}/{world_name}/modplayerdata/{uuid}.dat"
                )._value_json_obj()["data"]["value"]["nickname"]["value"]
            except:
                rawtext = "null"
            if rawtext != "null":
                nickname = loads(rawtext)["text"]
                nicknames[original_name] = nickname
        uuids[nickname] = uuid

        playload = {
            "embeds": [
                {
                    "author": {
                        "name": f"{nickname} {LANGS[lang]['join']}",
                        "icon_url": f"https://crafatar.com/avatars/{uuid}",
                    },
                    "color": 65280,
                }
            ],
        }
        post(webhook_url, json=playload)
    elif "'s nickname to 'literal" in info.content:
        server.logger.info(uuids)
        server.logger.info(nicknames)
        spilted = info.content.split("'s nickname to 'literal{")
        original_name = spilted[0].removeprefix("Set ")
        nickname = spilted[1].removesuffix("}'.")
        if original_name in nicknames.keys():
            uuids[nickname] = uuids[nicknames[original_name]]
            del uuids[nicknames[original_name]]
        else:
            uuids[nickname] = uuids[original_name]
            del uuids[original_name]
        nicknames[original_name] = nickname
        server.tell(
            original_name,
            f'[{RColor.aqua.mc_code}Message Poster{RColor.white.mc_code}] {RColor.green.mc_code}{LANGS[lang]["nickname_update"]} {nickname}',
        )
    elif info.content.startswith("Cleared ") and "'s nickname" in info.content:
        original_name = info.content.removeprefix("Cleared ").removesuffix(
            "'s nickname"
        )
        uuids[original_name] = uuids[nicknames[original_name]]
        del uuids[nicknames[original_name]]
        del nicknames[original_name]
        server.tell(
            original_name,
            f'[{RColor.aqua.mc_code}Message Poster{RColor.white.mc_code}] {RColor.green.mc_code}{LANGS[lang]["nickname_remove"]}',
        )


def on_player_left(_: PluginServerInterface, player: str):
    if webhook_url == "":
        return
    uuid = uuids.get(player)

    playload = {
        "embeds": [
            {
                "author": {
                    "name": f"{player} {LANGS[lang]['left']}",
                    "icon_url": f"https://crafatar.com/avatars/{uuid}" if uuid else "",
                },
                "color": 16711680,
            }
        ],
    }
    post(webhook_url, json=playload)
    uuids.pop(player, None)


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
