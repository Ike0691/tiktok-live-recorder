# utils/config_loader.py
import os
import json
import re
from types import SimpleNamespace
from typing import Union, List, Optional

from utils.custom_exceptions import ArgsParseError
from utils.enums import Mode, Regex


# ---------------------------
# Helpers
# ---------------------------

def _project_root() -> str:
    """Retourne la racine du repo (en partant de /utils)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _to_namespace(d: dict) -> SimpleNamespace:
    """Convertit un dict en SimpleNamespace (comme argparse)."""
    return SimpleNamespace(**d)


def _read_json(path: str) -> dict:
    """Lit un JSON avec messages d'erreur explicites."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ArgsParseError(
            f"Fichier de configuration introuvable: {path}\n"
            f"Crée un 'config.json' à la racine du projet."
        )
    except json.JSONDecodeError as e:
        raise ArgsParseError(
            f"Le fichier JSON '{path}' est invalide: {e}\n"
            f"Vérifie les virgules, guillemets et accolades."
        )


def _normalize_user(user: Union[None, str, List[str]]) -> Union[None, str, List[str]]:
    """
    Accepte:
      - None
      - "user" ou "@user"
      - "u1,u2,@u3"
      - ["user", "@u2", " u3 "]
    Reproduit le comportement de validate_and_parse_args:
      - args.user devient liste si >1, sinon str
      - on strip '@' et espaces
    """
    if user is None:
        return None

    if isinstance(user, list):
        users = [u.lstrip("@").strip() for u in user if isinstance(u, str) and u.strip()]
    elif isinstance(user, str):
        users = [u.lstrip("@").strip() for u in user.split(",") if u.strip()]
    else:
        raise ArgsParseError("Le champ 'user' doit être une chaîne, une liste de chaînes, ou null.")

    if not users:
        return None
    return users[0] if len(users) == 1 else users


def _ensure_int(name: str, value: Optional[Union[int, str]], min_value: Optional[int] = None) -> int:
    """Convertit value en int et vérifie une éventuelle borne minimale."""
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        raise ArgsParseError(f"Le champ '{name}' doit être un entier valide (reçu: {value!r}).")

    if min_value is not None and ivalue < min_value:
        raise ArgsParseError(f"Incorrect {name} value. Must be {min_value} or more.")
    return ivalue


def _resolve_output_path(output: Optional[str]) -> Optional[str]:
    """
    Déplie ~ et variables d’environnement.
    Si chemin relatif, le rend absolu par rapport à la racine du repo
    (comportement robuste pour éviter les surprises de cwd).
    """
    if not output:
        return None
    out = os.path.expanduser(os.path.expandvars(output))
    if not os.path.isabs(out):
        out = os.path.join(_project_root(), out)
    return out


# ---------------------------
# Public API
# ---------------------------

def load_config_and_validate(filename: str = "config.json"):
    """
    Charge <racine>/<filename> et applique les mêmes validations que validate_and_parse_args.
    Retourne (args: SimpleNamespace, mode: Mode).
    """
    path = os.path.join(_project_root(), filename)
    raw = _read_json(path)

    # Valeurs par défaut cohérentes avec parse_args()
    mode_str = raw.get("mode", "manual")
    url = raw.get("url")
    user = _normalize_user(raw.get("user"))
    room_id = raw.get("room_id")
    automatic_interval = raw.get("automatic_interval", 5)
    proxy = raw.get("proxy")
    output = raw.get("output")  # respecte le défaut CLI (None si non fourni)
    duration = raw.get("duration", None)
    telegram = bool(raw.get("telegram", False))
    update_check = bool(raw.get("update_check", True))

    # ----------- VALIDATIONS (fidèles à validate_and_parse_args) -----------

    if not mode_str:
        raise ArgsParseError(
            "Missing mode value. Please specify the mode (manual, automatic or followers)."
        )
    if mode_str not in ["manual", "automatic", "followers"]:
        raise ArgsParseError(
            "Incorrect mode value. Choose between 'manual', 'automatic' or 'followers'."
        )

    if mode_str in ["manual", "automatic"]:
        if not user and not room_id and not url:
            raise ArgsParseError(
                "Missing URL, username, or room ID. Please provide one of these parameters."
            )

    # Plusieurs users => ne pas fournir room_id ou url
    if isinstance(user, list) and len(user) > 1 and (room_id or url):
        raise ArgsParseError(
            "When using multiple usernames, do not provide room_id or url."
        )

    if url and not re.match(str(Regex.IS_TIKTOK_LIVE), str(url)):
        raise ArgsParseError(
            "The provided URL does not appear to be a valid TikTok live URL."
        )

    # Exclusivité stricte entre user / room_id / url
    if (
        (isinstance(user, (str, list)) and user and room_id)
        or (isinstance(user, (str, list)) and user and url)
        or (room_id and url)
    ):
        raise ArgsParseError("Please provide only one among username, room ID, or URL.")

    # automatic_interval >= 1 (entier)
    automatic_interval = _ensure_int("automatic_interval", automatic_interval, min_value=1)

    # Mapping string -> enum Mode
    if mode_str == "manual":
        mode = Mode.MANUAL
    elif mode_str == "automatic":
        mode = Mode.AUTOMATIC
    else:  # "followers"
        mode = Mode.FOLLOWERS

    # Normalisation de 'output' (absolu depuis racine du repo)
    output = _resolve_output_path(output)

    # Recomposer args comme argparse le ferait
    args = _to_namespace(
        {
            "url": url,
            "user": user,
            "room_id": room_id,
            "mode": mode_str,                      # string, comme côté CLI
            "automatic_interval": automatic_interval,
            "proxy": proxy,
            "output": output,
            "duration": duration,
            "telegram": telegram,
            "update_check": update_check,
        }
    )

    return args, mode
