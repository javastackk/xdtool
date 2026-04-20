import os
import sys
import subprocess
from pathlib import Path
import urllib.request
import json
import time
import argparse
from colorama import init, Fore, Style

# Inicializa colorama para colores en Windows y otros
init(autoreset=True)

from pathlib import Path

# CONSTANCIAS Y RUTAS
VERSION = "40"

BASE_DIR = Path(__file__).resolve().parents[1]

JUICEYUM_DIR = BASE_DIR / "storage" / "juiceyum"
DEFAULT_DOWNLOADS_DIR = BASE_DIR / "downloads"

REPOS = "https://raw.githubusercontent.com/javastackk/xdtool-host/main/yumrepos.json"

APPS_CACHE_FILE = JUICEYUM_DIR / "appscache.json"
INSTALLED_APPS_FILE = JUICEYUM_DIR / "installed_apps.json"

# --- FUNCIONES BÁSICAS ---

def ensure_dirs(path=DEFAULT_DOWNLOADS_DIR):
    JUICEYUM_DIR.mkdir(exist_ok=True)
    path.mkdir(parents=True, exist_ok=True)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_json(path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_installed_apps():
    data = load_json(INSTALLED_APPS_FILE)
    return data or {}

def save_installed_apps(data):
    save_json(INSTALLED_APPS_FILE, data)

# --- REPOSITORIOS ---

def load_repos():
    repos = load_json(REPOS)
    if repos is None:
        repos = {
            "juiceyum-apps": "https://raw.githubusercontent.com/is226wuis6/juiceyum/main/juiceyum-apps.json"
        }
        save_json(REPOS, repos)
    return repos

def add_repo(url):
    repos = load_repos()
    if url in repos.values():
        print(Fore.YELLOW + "[!] Este repositorio ya está agregado.")
        return
    name = url.split("/")[-1].replace(".json", "").replace(".", "-")
    repos[name] = url
    save_json(REPOS, repos)
    print(Fore.GREEN + f"[+] Repositorio '{name}' agregado.")

def remove_repo(name):
    repos = load_repos()
    if name in repos:
        del repos[name]
        save_json(REPOS, repos)
        print(Fore.GREEN + f"[+] Repositorio '{name}' eliminado.")
    else:
        print(Fore.RED + f"[!] No existe repositorio con nombre '{name}'.")

def list_repos():
    repos = load_repos()
    print(Fore.CYAN + "Repositorios agregados:")
    for name, url in repos.items():
        print(f"- {name}: {url}")

# --- APPS ---

def fetch_json(url):
    try:
        with urllib.request.urlopen(url) as resp:
            return json.load(resp)
    except Exception as e:
        print(Fore.RED + f"[!] Error descargando repositorio {url}: {e}")
        return None

def update_apps_cache():
    repos = load_repos()
    all_apps = {}
    print("[*] Actualizando apps desde repositorios...")
    total_apps = 0
    for name, url in repos.items():
        print(f"    ↓ Cargando repo '{name}' ...", end="")
        data = fetch_json(url)
        if data:
            all_apps.update(data)
            count = len(data)
            total_apps += count
            print(f" ✓ {count} apps cargadas")
        else:
            print(" ✗ ERROR al cargar")
    save_json(APPS_CACHE_FILE, all_apps)
    print(f"[*] Actualización completada. Total: {total_apps} apps disponibles.\n")
    return all_apps


def load_apps_cache():
    apps = load_json(APPS_CACHE_FILE)
    if apps is None:
        apps = update_apps_cache()
    return apps

def list_apps(apps):
    print(Fore.CYAN + "Apps disponibles:\n")
    for name, app in apps.items():
        ver = app.get("version", "N/A")
        desc = app.get("description", "Sin descripción")
        print(f"- {name} (v{ver}): {desc}")

def search_apps(term, apps):
    term = term.lower()
    found = False
    for name, app in apps.items():
        if term in name.lower() or term in app.get("description", "").lower():
            ver = app.get("version", "N/A")
            desc = app.get("description", "Sin descripción")
            location = app.get("location", "Ubicación no especificada")
            print(f"- {name} (v{ver}): {desc} - Ubicación: {location}")
            found = True
    if not found:
        print(Fore.YELLOW + f"No se encontraron apps que coincidan con '{term}'.")

def info_app(app_name, apps):
    if app_name not in apps:
        print(Fore.RED + f"[!] La app '{app_name}' no está en los repositorios.")
        return
    app = apps[app_name]
    print(Fore.CYAN + f"Info de '{app_name}':")
    print(f"  Versión: {app.get('version', 'N/A')}")
    print(f"  Descripción: {app.get('description', 'Sin descripción')}")
    print(f"  URL: {app.get('url', 'No especificada')}")
    print(f"  Args instalación silenciosa: {app.get('silent_install_args', 'No especificados')}")
    print(f"  Ruta ejecutable post-instalación: {app.get('exec_path', 'No especificada')}")
    print(f"  Comando para desinstalar: {app.get('uninstall_command', 'No especificado')}")
    if "install_script" in app:
        print("  Instalación vía script PowerShell disponible.")

def uninstall_app(app_name, apps):
    if app_name not in apps:
        print(Fore.RED + f"[!] La app '{app_name}' no está en los repositorios.")
        return

    app = apps[app_name]
    uninstall_cmd = app.get("uninstall_command")
    if not uninstall_cmd:
        print(Fore.YELLOW + f"[!] No hay comando de desinstalación configurado para '{app_name}'.")
        return

    print(Fore.CYAN + f"[*] Ejecutando desinstalación de '{app_name}'...")
    try:
        completed = subprocess.run(uninstall_cmd, shell=True)
        if completed.returncode == 0:
            print(Fore.GREEN + f"[+] Desinstalación de '{app_name}' completada.")
            # Actualiza el archivo de apps instaladas removiendo esta app
            installed = load_installed_apps()
            if app_name in installed:
                del installed[app_name]
                save_installed_apps(installed)
        else:
            print(Fore.RED + f"[!] Error al desinstalar '{app_name}', código: {completed.returncode}")
    except Exception as e:
        print(Fore.RED + f"[!] Error ejecutando el comando de desinstalación: {e}")


# --- BARRA DE DESCARGA ---

def download_file(url, dest, retries=3, delay=3):
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url) as response:
                total_length = response.getheader('content-length')
                if total_length is None:
                    with open(dest, 'wb') as f:
                        f.write(response.read())
                else:
                    total_length = int(total_length)
                    downloaded = 0
                    block_size = 8192
                    start_time = time.time()
                    with open(dest, 'wb') as f:
                        while True:
                            buffer = response.read(block_size)
                            if not buffer:
                                break
                            f.write(buffer)
                            downloaded += len(buffer)
                            done = int(50 * downloaded / total_length)
                            elapsed = time.time() - start_time
                            speed = downloaded / 1024 / elapsed if elapsed > 0 else 0
                            percent = 100 * downloaded / total_length
                            bar = '=' * done + ' ' * (50 - done)
                            sys.stdout.write(f"\r[{bar}] {percent:5.1f}%  {speed:7.2f} KB/s")
                            sys.stdout.flush()
                    print()
            print(Fore.GREEN + f"[+] Descargado a {dest}")
            return True
        except Exception as e:
            print(Fore.RED + f"[!] Error descargando archivo (intento {attempt}): {e}")
            if attempt < retries:
                print(f"    Reintentando en {delay} segundos...")
                time.sleep(delay)
            else:
                print(Fore.RED + "[!] Falló la descarga tras varios intentos.")
                return False

# --- INSTALACIÓN ---

def run_powershell(script):
    try:
        completed = subprocess.run(["powershell", "-Command", script], check=True)
        if completed.returncode == 0:
            print(Fore.GREEN + "[+] Script PowerShell ejecutado correctamente.")
        else:
            print(Fore.RED + f"[!] Error en script PowerShell, código: {completed.returncode}")
    except Exception as e:
        print(Fore.RED + f"[!] Error ejecutando script PowerShell: {e}")

def install_app(app_name, apps, download_folder, silent_mode):
    if app_name not in apps:
        print(Fore.RED + f"[!] La app '{app_name}' no está en los repositorios.")
        return
    app = apps[app_name]
    if app.get("install_script"):
        print(Fore.CYAN + f"[*] Ejecutando script de instalación para '{app_name}'...")
        run_powershell(app["install_script"])
        return
    url = app.get("url")
    if not url:
        print(Fore.RED + f"[!] No hay URL para instalar '{app_name}'.")
        return
    silent_args = app.get("silent_install_args", "")
    if silent_mode and silent_args:
        install_args = silent_args
    else:
        install_args = ""
    filename = url.split("/")[-1].split("?")[0]
    dest_path = download_folder / f"{app_name}_{filename}"
    ensure_dirs(download_folder)
    if not download_file(url, dest_path):
        return
    print(Fore.CYAN + f"[*] Ejecutando instalador para '{app_name}'...")
    try:
        cmd = f'"{dest_path}" {install_args}'.strip()
        completed = subprocess.run(cmd, shell=True)
        if completed.returncode == 0:
            print(Fore.GREEN + f"[+] Instalación de '{app_name}' finalizada.")
            # Actualiza registro local de apps instaladas
            installed = load_installed_apps()
            installed[app_name] = app.get("version", "unknown")
            save_installed_apps(installed)
        else:
            print(Fore.RED + f"[!] Error en instalación, código: {completed.returncode}")
    except Exception as e:
        print(Fore.RED + f"[!] Error ejecutando instalador: {e}")
        return
    exec_path = app.get("exec_path")
    if exec_path:
        answer = input(Fore.YELLOW + f"¿Quieres ejecutar '{app_name}' ahora? (y/N): ").lower()
        if answer == "y":
            try:
                subprocess.Popen(exec_path)
                print(Fore.GREEN + f"[+] Ejecutando '{app_name}'...")
            except Exception as e:
                print(Fore.RED + f"[!] No se pudo ejecutar '{app_name}': {e}")
    try:
        os.remove(dest_path)
    except Exception as e:
        print(Fore.YELLOW + f"[!] No se pudo borrar el instalador: {e}")

# --- ACTUALIZAR APPS INSTALADAS LOCALMENTE ---

def upgrade_apps_local(apps, download_folder, silent_mode):
    installed = load_installed_apps()
    if not installed:
        print(Fore.YELLOW + "No hay apps instaladas para actualizar.")
        return
    
    updated_any = False
    for app_name, installed_version in installed.items():
        if app_name not in apps:
            print(Fore.YELLOW + f"App '{app_name}' ya no está en la caché local.")
            continue
        
        latest_version = apps[app_name].get("version", "unknown")
        if latest_version != installed_version:
            print(Fore.CYAN + f"Actualizando '{app_name}' de v{installed_version} a v{latest_version}...")
            install_app(app_name, apps, download_folder, silent_mode)
            updated_any = True
        else:
            print(f"'{app_name}' ya está actualizado (v{installed_version}).")
    
    if not updated_any:
        print(Fore.GREEN + "Todas las apps instaladas están actualizadas.")

# --- REFRESH ---

def refresh():
    print(Fore.CYAN + "[*] Reiniciando JuiceYum para aplicar cambios...")
    args = sys.argv
    args = [arg for arg in args if arg != "refresh"]
    os.execv(sys.executable, [sys.executable] + args)

# --- MAIN ---

def main():
    parser = argparse.ArgumentParser(description="Gestor JuiceYum para instalar apps.")
    parser.add_argument(
        "-f", "--path",
        type=Path,
        default=DEFAULT_DOWNLOADS_DIR,
        help="Carpeta donde se descargarán los instaladores (default: juiceyum/downs)"
    )
    parser.add_argument(
        "-s", "--silent",
        action="store_true",
        help="Si está disponible, instala en modo silencioso"
    )
    parser.add_argument(
    "-v", "--version",
    action="version",
    version=f"{VERSION}",
    help="Muestra la versión del programa y sale"
    )


    # Subparsers principales
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Agregamos el comando refresh
    subparsers.add_parser("refresh", help="Reinicia JuiceYum para aplicar cambios")

    # Grupo de comandos para apps
    apps_parser = subparsers.add_parser("apps", help="Comandos para manejar apps")
    apps_subparsers = apps_parser.add_subparsers(dest="apps_cmd", required=True)

    apps_subparsers.add_parser("list", help="Listar apps disponibles")

    search_parser = apps_subparsers.add_parser("search", help="Buscar apps")
    search_parser.add_argument("term", help="Término a buscar")

    info_parser = apps_subparsers.add_parser("info", help="Mostrar información de una app")
    info_parser.add_argument("app_name", help="Nombre de la app")

    install_parser = apps_subparsers.add_parser("install", help="Instalar una o más apps")
    install_parser.add_argument("app_names", nargs="+", help="Nombres de las apps a instalar")

    uninstall_parser = apps_subparsers.add_parser("uninstall", help="Desinstalar una app")
    uninstall_parser.add_argument("app_names", nargs="+", help="Nombre(s) de la(s) app(s) a desinstalar")

    apps_subparsers.add_parser("update", help="Actualizar lista de apps desde repositorios")
    apps_subparsers.add_parser("upgrade", help="Actualizar las apps instaladas si hay versión nueva")

    # Grupo de comandos para repositorios
    repo_parser = subparsers.add_parser("repo", help="Gestionar repositorios")
    repo_subparsers = repo_parser.add_subparsers(dest="repo_cmd", required=True)

    add_parser = repo_subparsers.add_parser("add", help="Agregar repositorio")
    add_parser.add_argument("url", help="URL del repositorio JSON")

    remove_parser = repo_subparsers.add_parser("remove", help="Eliminar repositorio")
    remove_parser.add_argument("name", help="Nombre del repositorio a eliminar")

    list_parser = repo_subparsers.add_parser("list", help="Listar repositorios")

    args = parser.parse_args()

    # Si el comando es refresh, ejecuta la función y termina
    if args.command == "refresh":
        refresh()
        return

    # Carga o actualiza apps según comando
    if args.command == "apps" and args.apps_cmd == "update":
        apps = update_apps_cache()
    else:
        apps = load_apps_cache()

    if args.command == "apps":
        if args.apps_cmd == "list":
            list_apps(apps)
        elif args.apps_cmd == "search":
            search_apps(args.term, apps)
        elif args.apps_cmd == "info":
            info_app(args.app_name, apps)
        elif args.apps_cmd == "install":
            for app_name in args.app_names:
                install_app(app_name, apps, args.path, args.silent)
        elif args.apps_cmd == "uninstall":
            for app_name in args.app_names:
                uninstall_app(app_name, apps)
        elif args.apps_cmd == "update":
            pass  # ya se actualizó arriba
        elif args.apps_cmd == "upgrade":
            upgrade_apps_local(apps, args.path, args.silent)
        else:
            print(Fore.RED + "[!] Comando de apps desconocido.")
    elif args.command == "repo":
        if args.repo_cmd == "add":
            add_repo(args.url)
        elif args.repo_cmd == "remove":
            remove_repo(args.name)
        elif args.repo_cmd == "list":
            list_repos()
        else:
            print(Fore.RED + "[!] Comando de repositorio desconocido.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()