"""Merge INI configs and env overrides without storing secrets in source code."""

from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Iterable


def read_merged_ini(base_dir: Path, *extra_names: str) -> configparser.ConfigParser:
    """
    Read config.ini then secrets.local.ini (if present) from base_dir.
    Later files override earlier keys. Optional extra_names add more overlays.
    """
    parser = configparser.ConfigParser()
    names: Iterable[str] = ("config.ini", "secrets.local.ini", *extra_names)
    for name in names:
        path = base_dir / name
        if path.is_file():
            parser.read(path, encoding="utf-8-sig")
    return parser


def env_or_ini(
    parser: configparser.ConfigParser,
    section: str,
    env_key: str,
    ini_key: str,
    *,
    fallback: str = "",
) -> str:
    """Environment variable wins over INI value."""
    env_val = os.environ.get(env_key, "").strip()
    if env_val:
        return env_val
    if parser.has_section(section):
        return parser.get(section, ini_key, fallback=fallback).strip()
    return fallback


def flex_credentials(
    parser: configparser.ConfigParser,
) -> tuple[str, str]:
    """Env FLEX_TOKEN / FLEX_QUERY_ID override [flex] token and query_id."""
    token = env_or_ini(parser, "flex", "FLEX_TOKEN", "token")
    query_id = env_or_ini(parser, "flex", "FLEX_QUERY_ID", "query_id")
    return token, query_id


def green_api_credentials(
    parser: configparser.ConfigParser,
    section: str = "trading",
) -> tuple[str, str, str]:
    """
    Load Green API id, token, and target phone.
    Env: GREEN_API_ID_INSTANCE, GREEN_API_TOKEN, WHATSAPP_TARGET_PHONE
    INI: whatsapp_id_instance / id_instance, whatsapp_api_token_instance / api_token,
         whatsapp_target_phone / target_phone
    """
    id_inst = env_or_ini(parser, section, "GREEN_API_ID_INSTANCE", "whatsapp_id_instance")
    if not id_inst and parser.has_section(section):
        id_inst = parser.get(section, "id_instance", fallback="").strip()
    token = env_or_ini(parser, section, "GREEN_API_TOKEN", "whatsapp_api_token_instance")
    if not token and parser.has_section(section):
        token = parser.get(section, "api_token", fallback="").strip()
    phone = env_or_ini(parser, section, "WHATSAPP_TARGET_PHONE", "whatsapp_target_phone")
    if not phone and parser.has_section(section):
        phone = parser.get(section, "target_phone", fallback="").strip()
    return id_inst, token, phone
