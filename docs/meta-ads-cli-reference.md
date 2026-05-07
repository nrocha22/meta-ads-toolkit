# Meta Ads CLI — Referencia Interna (Verificada)

**Fecha**: 1 de mayo de 2026
**Fuente**: Documentación oficial de Meta for Developers (extraída manualmente del DOM)
**Status**: ✅ Verificado contra documentación oficial

---

## 1. Qué es

Ads CLI es una herramienta de línea de comandos de Meta para gestionar publicidad desde la terminal. Provee una interfaz developer-friendly sobre el Meta Marketing API.

**Diseñado para:**
- Desarrolladores que prototipan y testean workflows del Marketing API antes de escribir código
- Equipos de operaciones que automatizan creación, monitoreo y limpieza de campañas via scripts y CI/CD
- Agentes AI que interactúan con Meta advertising via CLI estructurado

---

## 2. Instalación

### Requisitos
- Python 3.12+
- pip y uv
- System user access token de Meta con los scopes apropiados
- Ad account con los assets a gestionar

### Pasos

```bash
# Paso 1: Instalar el paquete
pip install meta-ads

# Paso 2: Sincronizar dependencias y virtual environment
uv sync

# Paso 3: Ejecutar el CLI
uv run meta
```

---

## 3. Autenticación

> **Importante**: Ads CLI requiere un **system user access token** para autenticación programática.

### Paso 1: Crear un admin system user

1. Ir a **Meta Business Suite > Settings > Users > System Users**
2. Click **Add** para crear nuevo system user
3. Rol: **Admin**
4. Nombre descriptivo (ej: "Ads CLI")

### Paso 2: Asignar assets al system user

Click en el system user > **Assign Assets**. Dar acceso a:
- Datasets (Meta Pixels) para conversion tracking
- Ad account(s) a gestionar
- Business Page(s) para ad creatives
- Product catalog(s) si usan catalog ads

### Paso 3: Agregar el system user como app admin

1. Ir a la app en **Meta for Developers > App Settings > Roles > Roles**
2. Agregar el system user como **App Admin**

### Paso 4: Generar access token

1. En **Meta Business Suite > Settings > Users > System Users**, seleccionar el system user
2. Click **Generate New Token**
3. Seleccionar la app
4. Otorgar los siguientes scopes:
   - `business_management`
   - `ads_management`
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_ads`
   - `catalog_management`
   - `read_insights`
5. Click **Generate Token** y copiar

### Guardar el token

```bash
# Opción A: En archivo .env (recomendado para desarrollo local)
ACCESS_TOKEN=<TU_ACCESS_TOKEN>

# Opción B: Variable de entorno (CI/scripts)
export ACCESS_TOKEN=<TU_ACCESS_TOKEN>
```

### Verificar autenticación

```bash
meta auth status
```

### Configurar Ad Account ID

```bash
# Opción A: En .env (recomendado)
AD_ACCOUNT_ID=<TU_AD_ACCOUNT_ID>

# Opción B: Variable de entorno
export AD_ACCOUNT_ID=<TU_AD_ACCOUNT_ID>

# Opción C: Flag por comando
meta ads --ad-account-id <AD_ACCOUNT_ID> campaign list
```

### Encontrar tu Ad Account ID

```bash
meta ads adaccount list
```

---

## 4. Variables de Entorno

| Variable | Descripción |
|----------|-------------|
| `ACCESS_TOKEN` | System user access token de Meta |
| `AD_ACCOUNT_ID` | ID de la cuenta publicitaria |
| `BUSINESS_ID` | ID del negocio en Meta Business Suite |

---

## 5. Sintaxis General

```bash
meta ads <resource> <action> [options]
meta auth <action>
```

Convenciones:
- `<lowercase>` = keyword fijo (escribir tal cual)
- `<UPPER_CASE>` = placeholder (reemplazar con tu valor)
- `[lowercase]` = keyword u opción opcional
- `--flag` = opción nombrada

---

## 6. Opciones Globales

```bash
meta [global options] ads <command> <subcommand> [options]
```

| Opción | Corto | Descripción |
|--------|-------|-------------|
| `--output <format>` | `-o` | Formato: `table` (default), `json`, `plain` |
| `--no-color` | | Desactivar colores |
| `--no-input` | | Desactivar prompts interactivos |
| `--debug` | | Activar output de debug |
| `--help` | `-h` | Mostrar ayuda |
| `--version` | `-v` | Mostrar versión |

### Formatos de Salida

- **`table`** (default) — Tabla legible con headers. Para uso interactivo.
- **`json`** — Array JSON estructurado. Para `jq` y otras herramientas.
- **`plain`** — Tab-separated, un registro por línea. Para `cut`, `awk`, `sort`.

```bash
# JSON → jq
meta --output json ads campaign list | jq '.[].name'

# Plain → sort por columna
meta --output plain ads campaign list | sort -t$'\t' -k5 -rn
```

---

## 7. Referencia de Comandos

### 7.1 Autenticación

```bash
# Verificar estado de auth
meta auth status
```

Token se configura via `.env` o variable de entorno `ACCESS_TOKEN`.

---

### 7.2 Ad Accounts

```bash
# Listar cuentas
meta ads adaccount list
meta ads adaccount list --limit 50
meta --output json ads adaccount list

# Cuenta actual
meta ads adaccount current
```

| Opción | Corto | Default | Descripción |
|--------|-------|---------|-------------|
| `--limit` | `-l` | 25 | Máximo de cuentas a retornar |

---

### 7.3 Facebook Business Pages

```bash
meta ads page list
meta ads page list --limit 50
meta --output json ads page list
```

| Opción | Corto | Default | Descripción |
|--------|-------|---------|-------------|
| `--limit` | `-l` | 25 | Máximo de páginas a retornar |

---

### 7.4 Campañas

#### Listar

```bash
meta ads campaign list
meta ads campaign list --limit 25
meta --output json ads campaign list
```

| Opción | Corto | Default | Descripción |
|--------|-------|---------|-------------|
| `--limit` | `-l` | 10 | Máximo de campañas |

#### Crear

```bash
meta ads campaign create --name "My Campaign" --objective OUTCOME_TRAFFIC
meta ads campaign create --name "Sales Campaign" --objective OUTCOME_SALES \
  --daily-budget 5000
```

| Opción | Requerido | Default | Descripción |
|--------|-----------|---------|-------------|
| `--name` | Sí | | Nombre de la campaña |
| `--objective` | Sí | | Objetivo de la campaña |
| `--daily-budget` | No | | Budget diario en **centavos** (5000 = $50.00) |
| `--lifetime-budget` | No | | Budget de vida en centavos |
| `--status` | No | `PAUSED` | Estado inicial: `ACTIVE` o `PAUSED` |

#### Obtener

```bash
meta ads campaign get <CAMPAIGN_ID>
```

#### Actualizar

```bash
meta ads campaign update <CAMPAIGN_ID> --name "New Name"
meta ads campaign update <CAMPAIGN_ID> --status ACTIVE
meta ads campaign update <CAMPAIGN_ID> --daily-budget 10000
```

| Opción | Descripción |
|--------|-------------|
| `--name` | Nuevo nombre |
| `--status` | Nuevo estado: `ACTIVE`, `PAUSED`, `ARCHIVED` |
| `--daily-budget` | Nuevo budget diario en centavos |
| `--lifetime-budget` | Nuevo budget de vida en centavos |

#### Eliminar

```bash
meta ads campaign delete <CAMPAIGN_ID>
meta ads campaign delete <CAMPAIGN_ID> --force    # Sin confirmación
```

---

### 7.5 Ad Sets

#### Listar

```bash
meta ads adset list                    # Todos los ad sets de la cuenta
meta ads adset list <CAMPAIGN_ID>      # Ad sets de una campaña específica
meta ads adset list --limit 25
```

| Argumento | Requerido | Descripción |
|-----------|-----------|-------------|
| `<CAMPAIGN_ID>` | No | Filtrar por campaña |

| Opción | Corto | Default | Descripción |
|--------|-------|---------|-------------|
| `--limit` | `-l` | 10 | Máximo de ad sets |

#### Crear

```bash
# Ad set estándar
meta ads adset create <CAMPAIGN_ID> --name "My Ad Set" \
  --optimization-goal LINK_CLICKS --billing-event IMPRESSIONS \
  --bid-amount 500 --targeting-countries US

# Ad set de conversiones
meta ads adset create <CAMPAIGN_ID> --name "Conversions Set" \
  --optimization-goal OFFSITE_CONVERSIONS \
  --billing-event IMPRESSIONS --pixel-id <PIXEL_ID> \
  --custom-event-type PURCHASE --targeting-countries US
```

| Opción | Requerido | Default | Descripción |
|--------|-----------|---------|-------------|
| `--name` | Sí | | Nombre del ad set |
| `--optimization-goal` | Sí | | Meta de optimización |
| `--billing-event` | Sí | | Evento de facturación |
| `--daily-budget` | No | | Budget diario en centavos (omitir si la campaña usa CBO) |
| `--lifetime-budget` | No | | Budget de vida. Requiere `--end-time` |
| `--bid-amount` | No | | Monto de puja en centavos |
| `--start-time` | No | | Inicio (ISO 8601) |
| `--end-time` | No | | Fin (ISO 8601). Requerido con `--lifetime-budget` |
| `--status` | No | `PAUSED` | Estado inicial |
| `--targeting-countries` | No | | Códigos de país separados por coma (ej: `US,CA,GB`) |
| `--pixel-id` | No | | Dataset (Pixel) ID para conversion tracking |
| `--custom-event-type` | No | `PURCHASE` | Tipo de evento de conversión. Usado con `--pixel-id` |

#### Obtener, Actualizar, Eliminar

```bash
meta ads adset get <AD_SET_ID>

meta ads adset update <AD_SET_ID> --name "New Name"
meta ads adset update <AD_SET_ID> --status ACTIVE
meta ads adset update <AD_SET_ID> --daily-budget 10000

meta ads adset delete <AD_SET_ID>
meta ads adset delete <AD_SET_ID> --force
```

| Opción (update) | Descripción |
|--------|-------------|
| `--name` | Nuevo nombre |
| `--status` | `ACTIVE`, `PAUSED`, `ARCHIVED` |
| `--daily-budget` | Nuevo budget diario en centavos |
| `--lifetime-budget` | Nuevo budget de vida en centavos |
| `--bid-amount` | Nuevo monto de puja en centavos |
| `--end-time` | Nuevo fin (ISO 8601) |

---

### 7.6 Ads

#### Listar

```bash
meta ads ad list                  # Todos los ads de la cuenta
meta ads ad list <AD_SET_ID>      # Ads de un ad set específico
meta ads ad list --limit 25
```

#### Crear

```bash
meta ads ad create <AD_SET_ID> --name "My Ad" --creative-id <CREATIVE_ID>
meta ads ad create <AD_SET_ID> --name "Conversion Ad" --creative-id <CREATIVE_ID> \
  --pixel-id <PIXEL_ID>
```

| Opción | Requerido | Default | Descripción |
|--------|-----------|---------|-------------|
| `--name` | Sí | | Nombre del ad |
| `--creative-id` | Sí | | ID del creativo a usar |
| `--status` | No | `PAUSED` | Estado inicial |
| `--pixel-id` | No | | Dataset (Pixel) ID para tracking |
| `--tracking-specs` | No | | Tracking specs como JSON raw (mutuamente excluyente con `--pixel-id`) |

#### Obtener, Actualizar, Eliminar

```bash
meta ads ad get <AD_ID>
meta --output json ads ad get <AD_ID>

meta ads ad update <AD_ID> --name "New Name"
meta ads ad update <AD_ID> --creative-id <CREATIVE_ID>
meta ads ad update <AD_ID> --status ACTIVE

meta ads ad delete <AD_ID>
meta ads ad delete <AD_ID> --force
```

---

### 7.7 Ad Creatives

#### Listar

```bash
meta ads creative list
meta ads creative list --limit 25
```

#### Crear — Estándar

```bash
meta ads creative create --name "Summer Sale" --image ./banner.jpg \
  --page-id <PAGE_ID> --body "50% off everything!" \
  --link-url https://example.com --title "Shop Now" \
  --call-to-action SHOP_NOW
```

| Opción | Requerido | Descripción |
|--------|-----------|-------------|
| `--name` | Sí | Nombre del creativo |
| `--page-id` | Sí | Facebook Business Page ID (identidad del ad) |
| `--image` | No | Ruta a archivo de imagen |
| `--video` | No | Ruta a archivo de video |
| `--body` | No | Texto principal / copy del ad |
| `--title` | No | Headline debajo de la imagen |
| `--link-url` | No | URL de destino al hacer click |
| `--description` | No | Descripción del link debajo del headline |
| `--call-to-action` | No | Tipo de botón CTA |
| `--instagram-actor-id` | No | Instagram account ID para placements de Instagram |

#### Crear — Dynamic Creative Optimization (DCO)

```bash
meta ads creative create --name "DCO Creative" --page-id <PAGE_ID> \
  --link-url https://example.com \
  --images ./img1.jpg --images ./img2.jpg --images ./img3.jpg \
  --titles "Title A" --titles "Title B" \
  --bodies "Body 1" --bodies "Body 2" \
  --call-to-actions SHOP_NOW --call-to-actions LEARN_MORE
```

| Opción | Máximo | Descripción |
|--------|--------|-------------|
| `--images` | 10 | Rutas de imagen (repetir para cada una) |
| `--videos` | 10 | Rutas de video (repetir para cada uno) |
| `--titles` | 5 | Variaciones de headline (repetir) |
| `--bodies` | 5 | Variaciones de texto principal (repetir) |
| `--descriptions` | 5 | Variaciones de descripción (repetir) |
| `--call-to-actions` | 5 | Tipos de CTA (repetir) |

#### Obtener, Actualizar, Eliminar

```bash
meta ads creative get <CREATIVE_ID>
meta --output json ads creative get <CREATIVE_ID>

meta ads creative update <CREATIVE_ID> --name "New Name"
meta ads creative update <CREATIVE_ID> --body "Updated copy" --title "New Title"
meta ads creative update <CREATIVE_ID> --image ./new-banner.jpg
meta ads creative update <CREATIVE_ID> --status PAUSED

meta ads creative delete <CREATIVE_ID>
meta ads creative delete <CREATIVE_ID> --force
```

---

### 7.8 Datasets (Meta Pixels)

#### Listar

```bash
meta ads dataset list
meta ads dataset list --business-id <BUSINESS_ID>
meta ads dataset list --limit 50
```

| Opción | Corto | Default | Descripción |
|--------|-------|---------|-------------|
| `--business-id` | | | Listar datasets de este business |
| `--limit` | `-l` | 25 | Máximo de datasets |

#### Obtener

```bash
meta ads dataset get <PIXEL_ID>
```

#### Crear

```bash
meta ads dataset create --name "My Pixel"
meta ads dataset create --name "My Pixel" --business-id <BUSINESS_ID>
```

| Opción | Requerido | Descripción |
|--------|-----------|-------------|
| `--name` | Sí | Nombre del dataset |
| `--business-id` | No | Business donde crear (se resuelve del ad account si se omite) |

#### Conectar

```bash
meta ads dataset connect <PIXEL_ID> --ad-account-id <AD_ACCOUNT_ID>
meta ads dataset connect <PIXEL_ID> --catalog-id <CATALOG_ID>
meta ads dataset connect <PIXEL_ID> --ad-account-id <AD_ACCOUNT_ID> --catalog-id <CATALOG_ID>
```

| Opción | Descripción |
|--------|-------------|
| `--ad-account-id` | Cuenta a conectar |
| `--catalog-id` | Catálogo a conectar |
| `--business-id` | Business dueño del dataset (se resuelve si se omite) |

#### Desconectar

```bash
meta ads dataset disconnect <PIXEL_ID> --ad-account-id <AD_ACCOUNT_ID>
meta ads dataset disconnect <PIXEL_ID> --ad-account-id <AD_ACCOUNT_ID> --force
```

#### Asignar Usuario

```bash
meta ads dataset assign-user <PIXEL_ID>
meta ads dataset assign-user <PIXEL_ID> --user-id <USER_ID>
meta ads dataset assign-user <PIXEL_ID> --tasks ADVERTISE --tasks ANALYZE --tasks EDIT
```

| Opción | Default | Descripción |
|--------|---------|-------------|
| `--user-id` | Usuario autenticado | User ID a asignar |
| `--tasks` | `ADVERTISE`, `ANALYZE` | Permisos a otorgar (repetir para múltiples) |

---

### 7.9 Product Catalogs

Opción a nivel de grupo:

| Opción | Default | Descripción |
|--------|---------|-------------|
| `--business-id` | Se resuelve del ad account | Business ID. También lee env var `BUSINESS_ID` |

#### Listar

```bash
meta ads catalog list
meta ads catalog list --business-id <BUSINESS_ID>
meta ads catalog list --limit 50
```

#### Obtener

```bash
meta ads catalog get <CATALOG_ID>
```

#### Crear

```bash
meta ads catalog create --name "My Catalog"
meta ads catalog create --name "Hotel Catalog" --vertical hotels
```

| Opción | Requerido | Default | Descripción |
|--------|-----------|---------|-------------|
| `--name` | Sí | | Nombre del catálogo |
| `--vertical` | No | `commerce` | Tipo de catálogo |

#### Actualizar, Eliminar

```bash
meta ads catalog update <CATALOG_ID> --name "Renamed Catalog"

meta ads catalog delete <CATALOG_ID>
meta ads catalog delete <CATALOG_ID> --force
```

---

### 7.10 Product Items

```bash
meta ads product-item list --catalog-id <CATALOG_ID>
meta ads product-item create --catalog-id <CATALOG_ID> ...
meta ads product-item get <PRODUCT_ID>
meta ads product-item update <PRODUCT_ID> ...
meta ads product-item delete <PRODUCT_ID>
```

---

### 7.11 Product Sets

```bash
meta ads product-set list --catalog-id <CATALOG_ID>
meta ads product-set create --catalog-id <CATALOG_ID> ...
meta ads product-set get <PRODUCT_SET_ID>
meta ads product-set update <PRODUCT_SET_ID> ...
meta ads product-set delete <PRODUCT_SET_ID>
```

---

### 7.12 Product Feeds

> Descubierto en verificación real del CLI (no aparece en docs oficiales web).

```bash
meta ads product-feed list --catalog-id <CATALOG_ID>
meta ads product-feed get <FEED_ID>
meta ads product-feed create --catalog-id <CATALOG_ID> --name "Daily Feed"
meta ads product-feed update <FEED_ID> --name "Renamed Feed"
meta ads product-feed delete <FEED_ID>
```

---

### 7.12 Insights

```bash
meta ads insights get
meta ads insights get --fields spend,impressions,ctr
meta ads insights get --since 2024-01-01 --until 2024-01-31
meta ads insights get --breakdown age --breakdown gender
meta ads insights get --campaign-id <CAMPAIGN_ID>
```

> Ver `docs/insights.md` para la referencia completa (fields, breakdowns, date presets, sorting).

---

## 8. Tabla de Recursos Completa

| Recurso | Operaciones |
|---------|-------------|
| Ad Campaigns | list, create, get, update, delete |
| Ad Sets | list, create (con targeting, Pixels, conversion tracking), get, update, delete |
| Ads | list, create (con tracking specs), get, update, delete |
| Ad Creatives | list, create (estándar + DCO), get, update, delete |
| Insights | get (con date ranges, breakdowns, custom fields) |
| Product Catalogs | list, create, get, update, delete |
| Product Items | list, create, get, update, delete |
| Product Sets | list, create, get, update, delete |
| Product Feeds | list, create, get, update, delete |
| Datasets (Pixels) | list, create, get, connect, disconnect, assign-user |
| Ad Accounts | list, get, current |
| Facebook Business Pages | list, get |

---

## 9. Enums de Referencia

### Objetivos de Campaña

| Valor | Descripción |
|-------|-------------|
| `OUTCOME_TRAFFIC` | Tráfico al sitio web |
| `OUTCOME_AWARENESS` | Alcance y reconocimiento de marca |
| `OUTCOME_ENGAGEMENT` | Interacción con publicaciones |
| `OUTCOME_LEADS` | Generación de leads |
| `OUTCOME_SALES` | Conversiones y ventas |
| `OUTCOME_APP_PROMOTION` | Instalación y uso de apps |

### CTAs Disponibles (verificado del CLI real)

| Valor | Texto |
|-------|-------|
| `apply_now` | Aplicar ahora |
| `book_travel` | Reservar viaje |
| `buy_now` | Comprar ahora |
| `contact_us` | Contactar |
| `download` | Descargar |
| `get_offer` | Obtener oferta |
| `get_quote` | Obtener cotización |
| `learn_more` | Más información |
| `no_button` | Sin botón |
| `open_link` | Abrir enlace |
| `shop_now` | Comprar ahora |
| `sign_up` | Registrarse |
| `subscribe` | Suscribirse |
| `watch_more` | Ver más |

> **Nota:** El CLI usa lowercase (`shop_now`) en vez de UPPERCASE (`SHOP_NOW`) como aparece en algunos ejemplos de la documentación.

---

## 10. Primeros Comandos (Quick Start)

```bash
# Verificar autenticación
meta auth status

# Listar campañas
meta ads campaign list

# Rendimiento últimos 30 días
meta ads insights get --fields spend,impressions,ctr,cpc

# Listar Business Pages (necesario para crear creatives)
meta ads page list

# Listar ad accounts
meta ads adaccount list
```

---

## 11. Exit Codes

| Código | Significado |
|--------|-------------|
| `0` | Éxito |
| `1` | Error general |
| `2` | Error de uso / argumentos |
| `3` | Error de autenticación |
| `4` | Error de API |
| `5` | Recurso no encontrado |

---

## 12. Documentación Complementaria (en este proyecto)

| Archivo | Contenido |
|---------|-----------|
| `docs/insights.md` | Referencia completa de Insights: fields, breakdowns, date presets, sorting |
| `docs/configuration.md` | Precedencia de config, .env, directorio XDG |
| `docs/ad-creatives-datasets-catalogs.md` | DCO, Instagram placements, workflows de creatives, datasets, catálogos |
| `docs/tutorials-and-recipes.md` | Tutorial end-to-end, scripts, exit codes, cleanup |
