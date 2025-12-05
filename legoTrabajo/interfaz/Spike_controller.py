import asyncio
from bleak import BleakScanner, BleakClient

class SpikeController:
    def __init__(self):
        self.client = None
        self.hub_address = None
        self.hub_name = None
        self.connected = False
        self.write_char_uuid = None  # Se descubrirá dinámicamente
        self.notify_char_uuid = None
        # No enviar el prefijo 0x06 por defecto — el hub actual espera comandos ASCII simples
        # Si necesita el prefijo Pybricks, active `self.use_pybricks_prefix = True`.
        self.use_pybricks_prefix = False
        # Flag que indica si la característica soporta escritura con respuesta
        # Por compatibilidad con este hub, usar escritura WITHOUT_RESPONSE por defecto
        # (algunos dispositivos y backends rechazan write-with-response con Protocol Error 0x80)
        self.write_requires_response = False
        
    async def scan_hubs(self):
        """Escanea dispositivos BLE disponibles."""
        print("[DEBUG] Iniciando escaneo BLE...")
        try:
            devices = await BleakScanner.discover(timeout=10.0)
            spike_hubs = []
            
            print(f"[DEBUG] Dispositivos encontrados: {len(devices)}")
            for device in devices:
                name = device.name if device.name else "Sin nombre"
                address = device.address
                print(f"[DEBUG] Dispositivo: {name} | MAC: {address}")
                
                # Retornar con nombre y MAC (sin UUID)
                spike_hubs.append((f"{name} ({address})", address))
            
            print(f"[DEBUG] Total de dispositivos retornados: {len(spike_hubs)}")
            return spike_hubs if spike_hubs else [("No se encontraron dispositivos", None)]
        except Exception as e:
            print(f"[ERROR] Error en escaneo BLE: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def connect(self, address):
        """Conecta al hub por BLE usando MAC address."""
        if not address:
            print("Dirección inválida")
            return False
        try:
            print(f"[DEBUG] Intentando conectar a {address}...")
            self.client = BleakClient(address, timeout=20.0)
            await self.client.connect()
            self.connected = True
            self.hub_address = address
            print(f"[DEBUG] Conectado a {address}")
            
            # Descubrir automáticamente la característica de escritura y notificación
            await self._discover_write_char()
            # Si la característica soporta notificaciones, suscribirse
            if self.notify_char_uuid:
                try:
                    await self.client.start_notify(self.notify_char_uuid, self._notification_handler)
                    print(f"[DEBUG] Suscrito a notificaciones en {self.notify_char_uuid}")
                except Exception as e:
                    print(f"[ERROR] No se pudo suscribir a notificaciones: {e}")
            return True
        except Exception as e:
            print(f"[ERROR] Error conectando a {address}: {e}")
            import traceback
            traceback.print_exc()
            self.connected = False
            return False
    
    async def _discover_write_char(self):
        """Descubre la característica de escritura disponible."""
        try:
            print("[DEBUG] Buscando característica de escritura...")
            
            # Intentar acceder directamente a services (versión más nueva de Bleak)
            services = None
            if hasattr(self.client, 'services'):
                services = self.client.services
            else:
                # Fallback: intentar get_services() para versiones antiguas
                try:
                    services = await self.client.get_services()
                except Exception:
                    pass
            
            if not services:
                print("[ERROR] No se pudieron obtener servicios")
                return
            
            # Iterar sobre servicios (no usar len() que no está soportado)
            service_count = 0
            for service in services:
                service_count += 1
                print(f"[DEBUG] Servicio: {service.uuid}")
                for char in service.characteristics:
                    props = getattr(char, "properties", [])
                    print(f"  └─ Característica: {char.uuid} props={props}")
                    # Registrar soporte de escritura
                    if "write" in props or "write-without-response" in props:
                        # Registrar característica de escritura. Por compatibilidad con el
                        # backend WinRT que falla con "write with response" en este hub,
                        # dejamos `write_requires_response` en False por defecto.
                        self.write_char_uuid = char.uuid
                        # Mostrar qué propiedades están disponibles
                        print(f"[DEBUG] ✓ Característica de escritura detectada: {self.write_char_uuid} (props={props})")
                    # Registrar soporte de notificación
                    if "notify" in props:
                        if not self.notify_char_uuid:
                            self.notify_char_uuid = char.uuid
                            print(f"[DEBUG] ✓ Característica de notificación detectada: {self.notify_char_uuid}")
                    # Si ya tenemos ambas, salir pronto
                    if self.write_char_uuid and self.notify_char_uuid:
                        return
            
            print(f"[DEBUG] Total servicios procesados: {service_count}")
            if not self.write_char_uuid:
                print("[WARNING] No se encontró característica de escritura")
            else:
                print(f"[DEBUG] Escritura detectada en {self.write_char_uuid}; notify={self.notify_char_uuid}")
        except Exception as e:
            print(f"[ERROR] Error descubriendo características: {e}")
            import traceback
            traceback.print_exc()
    
    async def disconnect(self):
        """Desconecta del hub."""
        if self.client and self.connected:
            try:
                # Detener notificaciones si estábamos suscritos
                if self.notify_char_uuid:
                    try:
                        await self.client.stop_notify(self.notify_char_uuid)
                    except Exception:
                        pass
                await self.client.disconnect()
                print("[DEBUG] Desconectado")
            except Exception as e:
                print(f"[ERROR] Error al desconectar: {e}")
        self.connected = False
        self.write_char_uuid = None
        self.notify_char_uuid = None
    
    async def send_command(self, command):
        """Envía un comando al hub vía BLE (sin UUID fijo)."""
        if not self.connected or not self.client:
            print("[ERROR] No conectado al hub")
            return False
        
        if not self.write_char_uuid:
            print("[ERROR] Característica de escritura no descubierta")
            return False
        
        try:
            # Preparar el comando
            if isinstance(command, str):
                b = command.encode('utf-8')
            else:
                b = bytes(command)
            
            if not b.endswith(b"\n"):
                b = b + b"\n"
            
            # No añadir prefijo por defecto. Si el hub necesitara el prefijo
            # Pybricks (0x06), active `self.use_pybricks_prefix = True`.
            if self.use_pybricks_prefix:
                if not b.startswith(b"\x06"):
                    b = b"\x06" + b
            
            print(f"[DEBUG] Enviando a {self.write_char_uuid}: {b} (response={self.write_requires_response})")
            try:
                await self.client.write_gatt_char(self.write_char_uuid, b, response=self.write_requires_response)
            except Exception as e:
                # Intentar una vez con el flag contrario si falla por protocolo
                print(f"[DEBUG] Primer intento falló ({e}), reintentando con response={not self.write_requires_response}...")
                await self.client.write_gatt_char(self.write_char_uuid, b, response=not self.write_requires_response)
            print(f"[DEBUG] Enviado: {b.decode('utf-8', errors='replace').strip()}")
            return True
        except Exception as e:
            print(f"[ERROR] Error enviando comando: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def move_motors(self, motor_a_speed, motor_b_speed, duration=1000):
        """Envía comando de movimiento (compatible con auto.py)."""
        cmd = f"velocidad:{int(motor_a_speed)}"
        await self.send_command(cmd)

    def _notification_handler(self, sender, data: bytearray):
        """Maneja notificaciones entrantes desde el hub y las muestra en consola."""
        # Mostrar información completa de la notificación: handle, longitud, hex, repr y texto
        try:
            text = data.decode('utf-8', errors='replace')
        except Exception:
            text = None
        hexstr = data.hex()
        print(f"[NOTIF] from {sender} (len={len(data)}) hex=0x{hexstr}")
        if text is not None:
            # Mostrar texto tal cual, sin strip para no perder bytes de control
            print(f"[NOTIF] text: {text!r}")
        else:
            print(f"[NOTIF] raw: {repr(data)}")
