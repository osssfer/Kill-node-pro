#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import os
from typing import Set, List
from datetime import datetime

# Colores ANSI (PowerShell / CMD)
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"

try:
    import psutil
except ImportError:
    psutil = None

# =============================================
# FUNCIONES UTILITARIAS
# =============================================

def is_admin() -> bool:
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def pid_name(pid: int) -> str:
    try:
        if psutil:
            return psutil.Process(pid).name()
        out = subprocess.check_output(["tasklist"], text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit() and int(parts[1]) == pid:
                return parts[0]
    except Exception:
        pass
    return "unknown"

def find_all_node_pids() -> Set[int]:
    pids = set()
    if psutil:
        for p in psutil.process_iter(["pid", "name"]):
            try:
                if p.info["name"] and "node" in p.info["name"].lower():
                    pids.add(p.info["pid"])
            except Exception:
                continue
        return pids
    try:
        out = subprocess.check_output(["tasklist"], text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for line in out.splitlines():
            if "node.exe" in line.lower():
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    pids.add(int(parts[1]))
    except Exception:
        pass
    return pids

def find_pids_by_port(port: int) -> Set[int]:
    ports = {int(port)}
    pids = set()
    if psutil:
        for kind in ("tcp", "udp"):
            try:
                for c in psutil.net_connections(kind=kind):
                    if c.laddr and hasattr(c.laddr, "port") and c.laddr.port in ports and c.pid:
                        pids.add(c.pid)
            except Exception:
                continue
        if pids:
            return pids
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for line in out.splitlines():
            if any(proto in line for proto in ("TCP", "UDP")):
                parts = line.split()
                if len(parts) >= 4:
                    local = parts[1]
                    try:
                        pid = int(parts[-1])
                        port_local = int(local.rsplit(":", 1)[1])
                        if port_local in ports:
                            pids.add(pid)
                    except Exception:
                        continue
    except Exception:
        pass
    return pids

def kill_pid(pid: int, force: bool = True) -> bool:
    name = pid_name(pid)
    try:
        if psutil:
            proc = psutil.Process(pid)
            proc.kill() if force else proc.terminate()
            print(f"{GREEN}✔ Killed PID {pid} ({name}){RESET}")
            return True
        subprocess.run(["taskkill", "/PID", str(pid), "/F" if force else ""],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{GREEN}✔ taskkill PID {pid} ({name}){RESET}")
        return True
    except Exception as e:
        print(f"{RED}✖ Error al matar PID {pid}: {e}{RESET}")
        return False

def input_int(prompt: str) -> int:
    while True:
        val = input(prompt).strip()
        if val.isdigit():
            return int(val)
        print(f"{YELLOW}⚠ Ingresa un número válido.{RESET}")

# =============================================
# MENÚS DE ACCIÓN
# =============================================

def menu_header():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{CYAN}{BOLD}╔══════════════════════════════════════════════╗")
    print(f"║  KillNode PRO  v2.1   (Fernando’s Dev Tool) ║")
    print(f"╚══════════════════════════════════════════════╝{RESET}")
    print(f"{MAGENTA}🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    if is_admin():
        print(f"{GREEN}🛡 Ejecutando como Administrador{RESET}\n")
    else:
        print(f"{YELLOW}⚠ Ejecuta PowerShell o CMD como Administrador para permisos totales{RESET}\n")

def confirm(msg: str) -> bool:
    return input(f"{YELLOW}{msg} [y/N]: {RESET}").strip().lower() in ("y","yes","s","si","sí")

def menu_kill_all():
    menu_header()
    pids = find_all_node_pids()
    if not pids:
        print(f"{RED}No hay procesos Node.js en ejecución.{RESET}")
        input("\nPresiona Enter para volver al menú...")
        return
    print(f"{CYAN}Procesos detectados:{RESET}")
    for pid in sorted(pids):
        print(f"  {pid:<6} {pid_name(pid)}")
    if confirm("¿Cerrar todos los procesos Node?"):
        for pid in sorted(pids):
            kill_pid(pid)
    input("\nPresiona Enter para volver al menú...")

def menu_kill_port(port: int, confirm_required=True):
    menu_header()
    pids = find_pids_by_port(port)
    if not pids:
        print(f"{RED}No se encontraron procesos en el puerto {port}.{RESET}")
        input("\nPresiona Enter para volver al menú...")
        return
    print(f"{CYAN}Procesos en el puerto {port}:{RESET}")
    for pid in sorted(pids):
        print(f"  {pid:<6} {pid_name(pid)}")
    if confirm_required:
        if not confirm(f"¿Cerrar todos los procesos del puerto {port}?"):
            print(f"{YELLOW}Cancelado por el usuario.{RESET}")
            input("\nPresiona Enter para volver al menú...")
            return
    for pid in sorted(pids):
        kill_pid(pid)
    input("\nPresiona Enter para volver al menú...")

def menu_kill_port_duo():
    menu_header()
    ports = [5173, 4000]
    print(f"{CYAN}Buscando procesos en los puertos {ports}...{RESET}")
    pids = set()
    for p in ports:
        pids.update(find_pids_by_port(p))
    if not pids:
        print(f"{RED}No hay procesos en los puertos 5173 ni 4000.{RESET}")
        input("\nPresiona Enter para volver al menú...")
        return
    for pid in sorted(pids):
        print(f"  {pid:<6} {pid_name(pid)}")
    if confirm("¿Cerrar todos los procesos en 5173 y 4000?"):
        for pid in sorted(pids):
            kill_pid(pid)
    input("\nPresiona Enter para volver al menú...")

def menu_kill_by_id():
    menu_header()
    port = input_int("Puerto a inspeccionar: ")
    pids = sorted(find_pids_by_port(port))
    if not pids:
        print(f"{RED}No hay procesos en el puerto {port}.{RESET}")
        input("\nPresiona Enter para volver al menú...")
        return
    print(f"{CYAN}PIDs activos en el puerto {port}:{RESET}")
    for pid in pids:
        print(f"  {pid:<6} {pid_name(pid)}")
    pid_sel = input_int("PID a cerrar (0 para cancelar): ")
    if pid_sel == 0:
        return
    if pid_sel not in pids:
        print(f"{YELLOW}PID no encontrado en la lista.{RESET}")
    else:
        kill_pid(pid_sel)
    input("\nPresiona Enter para volver al menú...")

# =============================================
# MENÚ PRINCIPAL
# =============================================

def main_menu():
    while True:
        menu_header()
        print(f"{BOLD}1.{RESET} Kill them all! (cerrar todos los Node)")
        print(f"{BOLD}2.{RESET} Kill port (cierra TODOS los procesos del puerto X)")
        print(f"{BOLD}3.{RESET} Kill by ID (lista PIDs y eliges cuál matar)")
        print(f"{BOLD}4.{RESET} Kill ports 5173 y 4000 (juntos)")
        print(f"{BOLD}5.{RESET} Kill port 5173 {YELLOW}(sin confirmación){RESET}")
        print(f"{BOLD}6.{RESET} Kill port 4000 {YELLOW}(sin confirmación){RESET}")
        print(f"{BOLD}0.{RESET} Salir")
        op = input(f"\n{CYAN}Selecciona una opción:{RESET} ").strip()
        if op == "1":
            menu_kill_all()
        elif op == "2":
            menu_kill_port(input_int("Puerto: "))
        elif op == "3":
            menu_kill_by_id()
        elif op == "4":
            menu_kill_port_duo()
        elif op == "5":
            # Modo rápido: sin confirmación
            menu_kill_port(5173, confirm_required=False)
        elif op == "6":
            # Modo rápido: sin confirmación
            menu_kill_port(4000, confirm_required=False)
        elif op == "0":
            print(f"{MAGENTA}👋 Hasta luego, Dev!{RESET}")
            break
        else:
            print(f"{YELLOW}Opción inválida.{RESET}")
            input("\nPresiona Enter para continuar...")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Cancelado por el usuario.{RESET}")
