"""Connectivity check for the LMSYS leaderboard endpoint."""
from __future__ import annotations

import json
import os
import socket
import sys
import time
from typing import Any
from urllib.parse import urlparse

try:
    import requests
except Exception as exc:  # pragma: no cover - diagnostics script
    print("❌ Le module 'requests' est introuvable dans cet environnement.")
    print("Installez les dépendances avec: pip install -r requirements.txt")
    raise SystemExit(1) from exc


DEFAULT_URL = "https://chat.lmsys.org/api/leaderboard"
DEFAULT_TIMEOUT = float(os.getenv("LMSYS_TIMEOUT", "6"))


def _print_section(title: str) -> None:
    print("\n" + title)
    print("-" * len(title))


def _pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)


def main() -> None:
    url = os.getenv("LMSYS_API_URL", DEFAULT_URL)
    timeout = DEFAULT_TIMEOUT
    parsed = urlparse(url)

    if not parsed.scheme.startswith("http"):
        print(f"⚠️ URL invalide pour LMSYS_API_URL: {url}")
        raise SystemExit(2)

    host = parsed.hostname
    if not host:
        print(f"⚠️ Impossible d'extraire le nom d'hôte depuis {url}")
        raise SystemExit(2)

    _print_section("Paramètres")
    print(f"URL ciblée : {url}")
    print(f"Timeout    : {timeout}s")

    _print_section("Résolution DNS")
    try:
        start = time.perf_counter()
        infos = socket.getaddrinfo(host, parsed.port or 443, proto=socket.IPPROTO_TCP)
        elapsed = (time.perf_counter() - start) * 1000
        addresses = sorted({addr[4][0] for addr in infos})
        print(f"Résolution OK en {elapsed:.1f} ms ➜ {', '.join(addresses)}")
    except socket.gaierror as exc:
        print(f"❌ Échec DNS pour {host}: {exc}")
        raise SystemExit(3) from exc

    _print_section("Requête HTTPS")
    try:
        response = requests.get(url, timeout=timeout)
        print(f"Réponse HTTP {response.status_code}")
        content_type = response.headers.get("content-type", "?")
        print(f"Content-Type: {content_type}")
        if response.ok:
            data: Any
            try:
                data = response.json()
            except Exception:
                data = response.text[:400]
            preview = data
            if isinstance(data, dict):
                preview = {k: data[k] for k in list(data)[:2]}
            elif isinstance(data, list):
                preview = data[:2]
            print("Aperçu:")
            print(_pretty(preview))
        else:
            print("Corps de réponse (200 premiers caractères):")
            print(response.text[:200])
    except requests.exceptions.SSLError as exc:
        print("❌ Erreur TLS/SSL :", exc)
        print("Vérifiez les certificats racine et les outils de filtrage HTTPS.")
        raise SystemExit(4) from exc
    except requests.exceptions.ConnectTimeout as exc:
        print("❌ Délai dépassé (connexion)")
        print("Pare-feu/proxy ou coupure réseau probable.")
        raise SystemExit(5) from exc
    except requests.exceptions.ProxyError as exc:
        print("❌ Erreur proxy :", exc)
        print("Vérifiez les variables HTTPS_PROXY/HTTP_PROXY.")
        raise SystemExit(6) from exc
    except requests.exceptions.RequestException as exc:
        print("❌ Requête échouée :", exc)
        raise SystemExit(7) from exc

    _print_section("Résultat")
    print("✅ Accès réussi. Lancez le bouton Refresh ou attendez le scheduler.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        if exc.code not in (0, 7):
            print("\nℹ️ Consultez docs/NETWORKING.md pour les actions correctives.")
        raise
