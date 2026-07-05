"""Admin CLI for local login accounts used by the Streamlit app's username/password
auth (utils/auth.py, streamlit-authenticator). Users can also register themselves
via the "还没有账号？点击注册" expander on the login screen - this CLI is for
out-of-band account management (provisioning ahead of time, or removing accounts),
matching the "local files, no cloud infra" constraint. Edits .streamlit/auth_config.yaml
directly (gitignored - see .streamlit/auth_config.yaml.example for the template).

Usage:
    python scripts/manage_users.py add <username> "<display name>"
    python scripts/manage_users.py remove <username>
    python scripts/manage_users.py list
"""
import argparse
import getpass
import secrets
import sys
from pathlib import Path

import yaml
from yaml.loader import SafeLoader

import streamlit_authenticator as stauth

CONFIG_PATH = Path(".streamlit/auth_config.yaml")


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {
            "credentials": {"usernames": {}},
            "cookie": {
                "name": "ruyuan_auth",
                "key": secrets.token_hex(32),
                "expiry_days": 30,
            },
        }
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.load(f, Loader=SafeLoader)


def _save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def add_user(username: str, name: str) -> None:
    config = _load_config()
    password = getpass.getpass(f"Password for {username}: ")
    confirm = getpass.getpass("Confirm password: ")
    if not password:
        sys.exit("Password cannot be empty.")
    if password != confirm:
        sys.exit("Passwords do not match.")
    config["credentials"]["usernames"][username.lower()] = {
        "name": name,
        "password": stauth.Hasher.hash(password),
    }
    _save_config(config)
    print(f"Saved user '{username}' to {CONFIG_PATH}.")


def remove_user(username: str) -> None:
    config = _load_config()
    if config["credentials"]["usernames"].pop(username.lower(), None) is None:
        sys.exit(f"No such user: {username}")
    _save_config(config)
    print(f"Removed user '{username}'.")


def list_users() -> None:
    config = _load_config()
    usernames = config["credentials"]["usernames"]
    if not usernames:
        print("No users configured yet.")
        return
    for username, info in usernames.items():
        print(f"{username}\t{info.get('name', '')}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Add or update a user (prompts for password).")
    add_p.add_argument("username")
    add_p.add_argument("name", help="Display name shown after login.")

    remove_p = sub.add_parser("remove", help="Remove a user.")
    remove_p.add_argument("username")

    sub.add_parser("list", help="List configured users.")

    args = parser.parse_args()
    if args.command == "add":
        add_user(args.username, args.name)
    elif args.command == "remove":
        remove_user(args.username)
    elif args.command == "list":
        list_users()


if __name__ == "__main__":
    main()
