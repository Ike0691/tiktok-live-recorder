# tools/run_from_config.py
#!/usr/bin/env python3
import os
import sys
import subprocess
import shlex

# On utilise ta validation existante pour garder les règles 100% identiques
from utils.config_loader import load_config_and_validate

def _repo_root():
    # tools/ -> racine du repo
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _args_to_cli(args):
    """
    Convertit l'object args (issu de load_config_and_validate)
    en liste d'arguments CLI attendus par l'upstream main.py.
    """
    cli = []

    # -mode
    if args.mode:
        cli += ["-mode", args.mode]

    # -user (str "u" ou "u1,u2")
    if args.user:
        if isinstance(args.user, list):
            user_str = ",".join(args.user)
        else:
            user_str = args.user
        cli += ["-user", user_str]

    # -url / -room_id (exclusifs si présents)
    if args.url:
        cli += ["-url", args.url]
    if args.room_id:
        cli += ["-room_id", str(args.room_id)]

    # -automatic_interval
    if args.automatic_interval is not None:
        cli += ["-automatic_interval", str(args.automatic_interval)]

    # -proxy
    if args.proxy:
        cli += ["-proxy", args.proxy]

    # -output
    if args.output:
        cli += ["-output", args.output]

    # -duration
    if args.duration is not None:
        cli += ["-duration", str(args.duration)]

    # -telegram (flag)
    if args.telegram:
        cli += ["-telegram"]

    # -no-update-check (flag inverse)
    if args.update_check is False:
        cli += ["-no-update-check"]

    return cli

def main():
    root = _repo_root()

    # Valide ton config.json avec EXACTEMENT les mêmes règles
    args, _mode_enum = load_config_and_validate("config.json")

    # Construit la ligne de commande pour le main ORIGINAL (upstream)
    cmd = [sys.executable, os.path.join(root, "main.py")]
    cmd += _args_to_cli(args)

    print("→ Running:", " ".join(shlex.quote(c) for c in cmd))
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()
