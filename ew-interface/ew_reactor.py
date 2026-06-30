from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import threading
import time
from pathlib import Path

import serial

from mavlink_connection import (
	_empty_gauges,
	_fold_frame_into_gauges,
	_sanitize_gauges,
	create_mavlink_connection,
	set_parameter,
)


DEFAULT_LOG_PATH = Path("telemetry.txt")
UPDATE_INTERVAL = 2.0  # seconds
mavlink_lock = threading.RLock()

# Formato de telemetría en JSON
def _format_snapshot(message_type: str, gauges: dict) -> str:
	payload = {
		"timestamp": time.time(),
		"message_type": message_type,
		"gauges": gauges,
	}
	return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _write_line(handle, text: str) -> None:
	handle.write(text + "\n")
	handle.flush()

# Terminal intercativa
def _read_interactive_line(prompt: str) -> str:
	if not sys.stdin.isatty() or not sys.stdout.isatty():
		return input(prompt)

	print(prompt, end="", flush=True)
	buffer: list[str] = []

	if os.name == "nt":
		import msvcrt

		while True:
			ch = msvcrt.getwch()
			if ch in {"\r", "\n"}:
				print()
				return "".join(buffer)
			if ch == "\x03":
				raise KeyboardInterrupt
			if ch in {"\b", "\x7f"}:
				if buffer:
					buffer.pop()
					print("\b \b", end="", flush=True)
				continue
			if ch in {"\x00", "\xe0"}:
				msvcrt.getwch()
				continue
			buffer.append(ch)
			print(ch, end="", flush=True)

	import termios
	import tty

	fd = sys.stdin.fileno()
	old_settings = termios.tcgetattr(fd)
	try:
		tty.setcbreak(fd)
		while True:
			ch = sys.stdin.read(1)
			if ch in {"\r", "\n"}:
				print()
				return "".join(buffer)
			if ch == "\x03":
				raise KeyboardInterrupt
			if ch in {"\b", "\x7f"}:
				if buffer:
					buffer.pop()
					print("\b \b", end="", flush=True)
				continue
			if ch == "\x1b":
				continue
			buffer.append(ch)
			print(ch, end="", flush=True)
	finally:
		termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

# Registra la telemetría cada 'UPDATE_INTERVAL' segundos en un fichero
def stream_telemetry(log_path: Path = DEFAULT_LOG_PATH) -> int:
	print("Conectando a MAVLink en udp:0.0.0.0:14570")
	conn = create_mavlink_connection()
	gauges = _empty_gauges()

	log_path = Path(log_path)
	log_path.parent.mkdir(parents=True, exist_ok=True)

	with log_path.open("a", encoding="utf-8", buffering=1) as log_file:
		_write_line(log_file, _format_snapshot("START", _sanitize_gauges(gauges)))
		print(f"Registrando telemetría en {log_path}")

		last_write = 0.0
		snapshot = None

		while True:
			try:
				with mavlink_lock:
					msg = conn.recv_match(blocking=True, timeout=1.0)
			except serial.serialutil.PortNotOpenError:
				print("El puerto MAVLink se ha cerrado.")
				return 1
			except KeyboardInterrupt:
				print("Interrumpido por el usuario.")
				return 0
			except Exception as exc:
				print(f"Error leyendo MAVLink: {exc}")
				continue

			if msg is None:
				continue

			try:
				_fold_frame_into_gauges(gauges, msg)
			except Exception as exc:
				print(f"No se pudo procesar {msg.get_type()}: {exc}")
				continue

			# Prepare snapshot but only write to disk at most once per second
			safe_gauges = _sanitize_gauges(gauges)
			snapshot = _format_snapshot(msg.get_type(), safe_gauges)

			now = time.time()
			if (now - last_write) >= UPDATE_INTERVAL and snapshot is not None:
				_write_line(log_file, snapshot)
				last_write = now
				snapshot = None

# Envía un cambio de parámetro por MAVLink y muestra la respuesta
def send_parameter_change(param_id: str, param_value: float) -> int:
	with mavlink_lock:
		print(f"Enviando modificación de parámetro: {param_id} = {param_value}")
		result = set_parameter(param_id, param_value)

	if result is None:
		print("Se envió el mensaje, pero no se recibió respuesta PARAM_VALUE.")
		return 1

	print(f"Respuesta recibida: {param_id} = {result}")
	return 0

# Bucle interactivo para cambiar parámetros
def interactive_parameter_loop(stop_event: threading.Event) -> int:
	print("Comandos disponibles: set <PARAM_ID> <VALOR>, quit, exit")
	while not stop_event.is_set():
		try:
			line = _read_interactive_line("> ").strip()
		except EOFError:
			return 0
		except KeyboardInterrupt:
			print()
			return 0

		if not line:
			continue

		try:
			parts = shlex.split(line)
		except ValueError as exc:
			print(f"Comando no válido: {exc}")
			continue

		command = parts[0].lower()
		if command in {"quit", "exit"}:
			stop_event.set()
			return 0

		if command in {"set", "param", "set_parameter"}:
			if len(parts) != 3:
				print("Uso: set <PARAM_ID> <VALOR>")
				continue
			param_id = parts[1]
			try:
				param_value = float(parts[2])
			except ValueError:
				print(f"El valor del parámetro debe ser numérico: {parts[2]}")
				continue
			send_parameter_change(param_id, param_value)
			continue

		print("Comando no reconocido. Usa: set <PARAM_ID> <VALOR>, quit, exit")

# Ejecuta el procesamiento de telemetría y la termininal interactiva
def run_reactor(log_path: Path = DEFAULT_LOG_PATH) -> int:
	stop_event = threading.Event()
	create_mavlink_connection()
	telemetry_thread = threading.Thread(
		target=stream_telemetry,
		args=(log_path,),
		daemon=True,
	)
	telemetry_thread.start()
	try:
		return interactive_parameter_loop(stop_event)
	finally:
		stop_event.set()


def parse_args(argv: list[str]) -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Reactor MAVLink para telemetría y cambio de parámetros."
	)
	parser.add_argument(
		"--log-file",
		default=str(DEFAULT_LOG_PATH),
		help="Fichero donde se escribe la telemetría en tiempo real.",
	)
	parser.add_argument(
		"--set-parameter",
		nargs=2,
		metavar=("PARAM_ID", "PARAM_VALUE"),
		help="Envía un cambio de parámetro por MAVLink y muestra la respuesta.",
	)
	return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
	args = parse_args(sys.argv[1:])

	if args.set_parameter:
		param_id, raw_value = args.set_parameter
		try:
			param_value = float(raw_value)
		except ValueError:
			print(f"El valor del parámetro debe ser numérico: {raw_value}")
			return 2
		return send_parameter_change(param_id, param_value)

	return run_reactor(Path(args.log_file))


if __name__ == "__main__":
	raise SystemExit(main())
