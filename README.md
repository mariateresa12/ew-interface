# EW Interface

Interfaz para visualizar telemetría MAVLink y enviar cambios de parámetros al simulador desde el contenedor companion computer.

Los ficheros principales son:
- `ew-interface/mavlink-connection.py`
- `ew-interface/ew-reactor.py`

## Ejecución

1. Abrir una terminal dentro del contenedor:

     ```bash
     docker exec -it companion-computer-lite bash
     ```

2. Ejecutar el reactor:

     ```bash
     python3 ew_reactor.py
     ```

## Funcionalidades

- Registra en `telemetry.txt` los datos de telemetría recibidos en formato JSON.
- Permite modificar parámetros con el comando:

    ```text
    set <PARAM_ID> <VALOR>
    ```

   - Si el parámetro no existe, el simulador no devuelve respuesta.
   - Si el parámetro existe, se recibe su valor actualizado. Si coincide con el valor enviado, la modificación se ha aplicado correctamente.

## Cambios realizados en companion-computer

- `interface/app.py`: se añadió `db.session.add(UdpDestination(ip="127.0.0.1", port=14570))` en `initialize_udp_destinations` para recibir telemetría del dron.
- `lite/Dockerfile`: se añadió la sección `EW reactor` para copiar los nuevos ficheros al contenedor.

## Rebuild

Cada vez que se modifique o añada un fichero del contenedor, se debe volver a construir la imagen:

```bash
docker compose -f docker-compose-lite.yaml build
```

Para construir un contenedor en especifico se debe colocar

```bash
docker compose -f docker-compose-lite.yaml build <nombre_del_contenedor>
```

## Parámetros del simulador

### GPS

x $\in {\  ,2}$

- **SIM_GPSx_BYTELOSS:** Pérdida de datos GPS (simula paquetes perdidos)
    - Valores: `0–100` (proporción de pérdida)
- **SIM_GPSx_DISABLE:** Desactiva el GPS
    - Valores: `0 = activo`, `1 = apagado`
- **SIM_GPSx_GLITCH_X / Y / Z:** Error artificial en posición (inyección de fallo)
    - Valores: metros (positivo / negativo)
- **SIM_GPSx_JAM:** Habilitar la simulación de jamming GPS
    - Valores: `0 = desactivado`, `1 = activado`
- **SIM_GPSx_LAG_MS:** Retardo en la medición GPS
    - Valores: `0+` (milisegundos)
- **SIM_GPSx_NOISE:** Error en la medición GPS
    - Valores: `0+` (metros)
- **SIM_GPSx_NUMSATS:** Número de satélites que el GPS tiene a la vista

### Acelerómetro

x $\in {1,2,3}$

- **SIM_ACCx_RND:** Factor de escala para el ruido del acelerómetro
    - Valores: `0+`
- **SIM_ACCELx_FAIL:** Fallo del acelerómetro
    - Valores: `0 = normal`, `1 = fallo`
- **SIM_ACC_FAIL_MSK:** Máscara de fallo del acelerómetro**.** Determina si se detienen las actualizaciones de lectura del acelerómetro cuando se produce un fallo simulado de la IMU mediante los parámetros ACCELx_FAIL.
    - Valores: `0 = desactivado`, `1 = lecturas detenidas`

### Giroscopio

x $\in {1,2,3}$

- **SIM_GYRx_RND:** Factor de escala para el ruido del giroscopio
    - Valores: `0+`
- **SIM_GYR_FAIL_MSK:** Determina si las actualizaciones de lectura del giroscopio se detienen cuando se produce un fallo simulado de la IMU mediante los parámetros ACCELx_FAIL
    - Valores: `0 = desactivado`, `1 = lecturas detenidas`

### Magnetómetro

x $\in {1,2,3}$

- **SIM_MAG_RND:** Factor de ruido del magnetómetro
    - Valores: `0+`
- **SIM_MAGx_FAIL:** Fallo del magnetómetro
    - Valores: `0 = normal`, `1 = fallo`

### Barómetro

x $\in {O,2,3,}$

- **SIM_BARx_DELAY:** Retardo en la lectura
    - Valores: `0+` (milisegundos)
- **SIM_BARx_DISABLE:** Desactiva el barómetro
    - Valores: `0 = desactivado`, `1 = activado`
- **SIM_BARx_DRIFT:** Ratio al que varía la altitud del barómetro
    - Valores: `0+` (metros/segundo)
- **SIM_BARx_FREEZE:** Congela la lectura del sensor al último registrado
    - Valores: `0 = normal`, `1 = congelado`
- **SIM_BARx_GLITCH:** Error puntual (salto brusco) en la medida
    - Valores: `0+` (metros)
- **SIM_BARx_RND:** Ruido de presión/altitud
    - Valores: `0+`  (metros)

### Optical flow

- **SIM_FLOW_ENABLE:** Activa el sensor de flujo óptico
    - Valores: `0 = desactivado`, `1 = activado`
- **SIM_FLOW_RND:** Ruido en el flujo óptico
    - Valores: `0+` (radianes/segundo)

### Sonar (rangefinder)

- **SIM_SONAR_RND:** Factor de escala para el ruido de sonar simulado
    - Valores: `0+`
- **SIM_SONAR_GLITCH:** Probabilidad de que ocurra un fallo en el sonar
    - Valores: `0-1`

### VICON (motion capture)

- **SIM_VICON_ENABLE:** Activa sistema VICON
    - Valores: `0 / 1`
- **SIM_VICON_FAIL:** Simula fallo del sistema
    - Valores: `0 = normal`, `1 = fallo`
- **SIM_VICON_GLIT_X/Y/Z:** Error en posición (glitch)
    - Valores: metros
- **SIM_VICON_VGLI_X/Y/Z:** Error en velocidad
    - Valores: metros/segundo

## Control y RC

### Control del piloto

- **SIM_RC_FAIL:** Simula pérdida de control RC
    - Valores:
        - `0 = normal`
        - `1 = no RC pulses`
        - `2 = todos los canales neutros excepto Throttle con 950 µs`

### Motor / potencia

- **SIM_ENGINE_FAIL:** Fallo del motor. Define la máscara de motores a los que se aplicará `SIM_ENGINE_MUL`.
    - Valores: `0 = normal`, `1 = fallo`.
- **SIM_ENGINE_MUL:** Multiplicador de potencia del motor.
    - Valores:
        - `1 = normal`
        - `<1 = menos potencia`
        - `>1 = más potencia`

### Otros

- **SIM_UART_LOSS:** Pérdida de datos en comunicaciones seriales
    - Valores: `0–100` (porcentaje)
- **SIM_TIME_JITTER:** Límite superior de fluctuación aleatoria en el tiempo del bucle
    - Valores: `0+` (microsegundos)
