#!/usr/bin/env python3
"""
Gera um novo refresh_token para a Google Ads API.
Lê client_id e client_secret do google-ads.yaml existente.
Execute quando o refresh_token expirar.

Uso: python generate_refresh_token.py
"""
import os
import re
import sys

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
YAML_PATH = os.path.join(BASE_DIR, "google-ads.yaml")

SCOPES = ["https://www.googleapis.com/auth/adwords"]


def _read_yaml_field(field: str) -> str:
    with open(YAML_PATH) as f:
        for line in f:
            m = re.match(rf"^{field}:\s*(.+)$", line.strip())
            if m:
                return m.group(1).strip()
    raise ValueError(f"Campo '{field}' nao encontrado em {YAML_PATH}")


def main():
    if not os.path.exists(YAML_PATH):
        print(f"Arquivo nao encontrado: {YAML_PATH}")
        print("Crie o google-ads.yaml a partir do google-ads.yaml.example primeiro.")
        sys.exit(1)

    client_id     = _read_yaml_field("client_id")
    client_secret = _read_yaml_field("client_secret")

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        os.system(f"{sys.executable} -m pip install -q google-auth-oauthlib")
        from google_auth_oauthlib.flow import InstalledAppFlow

    print("\n=== Gerando novo Refresh Token para Google Ads API ===\n")
    print("1. Um navegador vai abrir")
    print("2. Faca login com a conta que tem acesso ao Google Ads")
    print("3. Autorize o acesso\n")

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

    # Tenta abrir servidor local em portas alternativas
    creds = None
    for port in [8080, 8888, 9090, 9999]:
        try:
            creds = flow.run_local_server(
                port=port, prompt="consent", access_type="offline",
                open_browser=True,
            )
            break
        except OSError:
            print(f"  Porta {port} ocupada, tentando proxima...")
            continue

    # Fallback: fluxo manual via URL + codigo
    if creds is None:
        import webbrowser
        auth_url, _ = flow.authorization_url(
            prompt="consent", access_type="offline"
        )
        print("\n--- AUTORIZACAO MANUAL ---")
        print("Nao foi possivel abrir servidor local.")
        print("Abra o link abaixo no navegador:\n")
        print(auth_url)
        webbrowser.open(auth_url)
        print("\nApos autorizar, cole o codigo de autorizacao aqui:")
        code = input("Codigo: ").strip()
        flow.fetch_token(code=code)
        creds = flow.credentials

    new_token = creds.refresh_token
    print(f"\nRefresh Token: {new_token}\n")

    # Atualiza google-ads.yaml
    with open(YAML_PATH) as f:
        content = f.read()
    content = re.sub(r"^refresh_token:.*$", f"refresh_token: {new_token}",
                     content, flags=re.MULTILINE)
    with open(YAML_PATH, "w") as f:
        f.write(content)

    print(f"google-ads.yaml atualizado: {YAML_PATH}")


if __name__ == "__main__":
    main()
