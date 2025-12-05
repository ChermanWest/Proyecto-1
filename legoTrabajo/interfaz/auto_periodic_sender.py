#!/usr/bin/env python3

import asyncio
import argparse
import sys
import signal

from Spike_controller import SpikeController


async def run_pattern(controller: SpikeController):
    """Envía un patrón de movimiento repetitivo al hub."""
    # Ajuste inicial de velocidad
    await controller.send_command("velocidad:80")

    try:
        while True:
            # Adelante 2s
            print("[PATTERN] forward")
            await controller.send_command("forward")
            await asyncio.sleep(2)

            # Parar 1s
            print("[PATTERN] stop")
            await controller.send_command("stop")
            await asyncio.sleep(1)

            # Giro a la derecha 1s
            print("[PATTERN] giro:50")
            await controller.send_command("giro:50")
            await asyncio.sleep(1)

            # Reset giro
            print("[PATTERN] giro:0")
            await controller.send_command("giro:0")
            await asyncio.sleep(0.5)

            # Atrás 2s
            print("[PATTERN] backward")
            await controller.send_command("backward")
            await asyncio.sleep(2)

            # Parar 3s antes de repetir
            print("[PATTERN] stop")
            await controller.send_command("stop")
            await asyncio.sleep(3)

    except asyncio.CancelledError:
        # Cancelación limpia del patrón
        pass


async def main(address: str | None):
    controller = SpikeController()

    # Si no se proporciona dirección, escanear y buscar un hub llamado "SP-7"
    if not address:
        print("[MAIN] Escaneando hubs BLE (10s)... buscando 'SP-7'")
        hubs = await controller.scan_hubs()
        if not hubs:
            print("[MAIN] No se encontraron hubs BLE. Asegúrate de que el hub esté emparejado y en rango.")
            return 1

        # Buscar dispositivo cuyo nombre contenga 'SP-7' (case-insensitive)
        target = None
        for display, mac in hubs:
            if not display or mac is None:
                continue
            if 'sp-7' in display.lower() or display.lower().startswith('sp-7'):
                target = mac
                break

        if target:
            address = target
            print(f"[MAIN] Encontrado 'SP-7' en {address}")
        else:
            # Fallback: usar el primer hub encontrado
            address = hubs[0][1]
            print(f"[MAIN] 'SP-7' no encontrado — usando primer hub detectado: {address}")

    print(f"[MAIN] Conectando a {address}...")
    ok = await controller.connect(address)
    if not ok:
        print("[MAIN] Falló la conexión")
        return 2

    # Correr patrón hasta interrupción
    pattern_task = asyncio.create_task(run_pattern(controller))

    # Manejar Ctrl+C limpiamente
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _on_signal(sig, frame):
        print(f"[MAIN] Señal recibida: {sig}. Deteniendo...")
        stop_event.set()

    # Registrar señal en Windows y POSIX
    try:
        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)
    except Exception:
        # algunos entornos no permiten signal.signal (ej. ciertos intérpretes embebidos)
        pass

    await stop_event.wait()
    pattern_task.cancel()
    try:
        await pattern_task
    except asyncio.CancelledError:
        pass

    print("[MAIN] Desconectando...")
    await controller.disconnect()
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Envía comandos periódicos al hub Spike.')
    parser.add_argument('-a', '--address', help='Dirección MAC del hub (opcional)')
    args = parser.parse_args()

    try:
        code = asyncio.run(main(args.address))
        sys.exit(code if code is not None else 0)
    except KeyboardInterrupt:
        print('\n[MAIN] Interrumpido por usuario')
        sys.exit(0)
