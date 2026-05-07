# Getting Started — Datos que necesitas

El toolkit asume que ya tienes acceso a un Business Manager y un ad account en Meta Ads Manager. Esta guía cubre cómo obtener cada uno de los IDs y credenciales que el toolkit necesita.

---

## Resumen

Para correr cualquier script necesitas:

1. **`ACCESS_TOKEN`** (en `.env`) — System User token con permisos sobre el ad account y la Page
2. **`ad_account_id`** (en `accounts.yaml`) — formato `act_XXXXXXXXXXXXXXX`
3. **`page_id`** (en `accounts.yaml`) — Page de Facebook que publica los ads
4. **`instagram_user_id`** (opcional) — Instagram Business actor para placements de IG
5. **`pixel_id`** (en `accounts.yaml`) — Pixel/dataset ID para optimización por conversión

---

## 1. ACCESS_TOKEN — System User Token

**Por qué System User**: los tokens de usuario regular caducan a las pocas horas. Los System User tokens, una vez emitidos, no expiran (a menos que cambies la contraseña del business o revoques el acceso).

### Pasos

1. Entrar a [Meta Business Suite](https://business.facebook.com/) → tu Business Manager
2. **Settings** (menú lateral) → **Users** → **System Users**
3. **Add** → crear un System User (sugerencia: nombre descriptivo como `cli-manager`)
4. Una vez creado, **Add Assets** → asignar:
   - **Ad Accounts**: agregar tu ad account con permiso "Manage campaigns"
   - **Pages**: agregar la Page con permiso "Create content"
5. **Generate New Token** → seleccionar la app del Business Manager (si no tienes app, crea una en [Meta for Developers](https://developers.facebook.com/apps/))
6. Permisos a marcar:
   - `ads_management`
   - `ads_read`
   - `pages_show_list`
   - `pages_read_engagement`
   - `business_management`
   - `instagram_basic` (si vas a usar placements de Instagram)
7. **Generate Token** → copiar el token a `.env`:
   ```
   ACCESS_TOKEN=EAAXXXXXXX...
   ```

### Verificación

```bash
meta ads adaccount list
```

Si lista tus ad accounts, el token funciona.

---

## 2. Ad Account ID

Formato: `act_XXXXXXXXXXXXXXX` (16 dígitos).

### Cómo obtenerlo

```bash
meta ads adaccount list
```

Output esperado (JSON):
```json
[
  {"id": "act_1234567890", "name": "Mi Brand", "currency": "USD"},
  ...
]
```

Alternativa visual: en Ads Manager, mirar la URL — `act=XXXXXX` después del nombre del ad account.

---

## 3. Page ID

Formato: solo dígitos (15-16 dígitos típicamente).

### Cómo obtenerlo

- En [Meta Business Suite](https://business.facebook.com/) → **Settings** → **Pages** → click en tu Page → ID visible
- O desde la URL pública de la Page: `facebook.com/<page_id>` o vía `facebook.com/<vanity-name>` y consultar "About"

**Importante**: la Page debe estar:
- Asignada al mismo Business Manager que el ad account
- Asignada al mismo System User con permiso "Create content"

### Discovery automático (recomendado)

Si tienes el `ad_account_id`, lista todas las Pages que pueden promocionar desde esa cuenta y rankéalas por fans + presencia de Instagram para identificar la principal:

```bash
curl -sG "https://graph.facebook.com/v21.0/<AD_ACCOUNT_ID>/promote_pages" \
  -d "fields=id,name,fan_count,instagram_business_account{username,followers_count}" \
  -d "access_token=$ACCESS_TOKEN" | python3 -m json.tool
```

Cuando una marca tiene múltiples Pages con el mismo nombre (común tras varios años de operación), la correcta suele ser la que tiene **más fans + Instagram linkeado**. Ejemplo real: una cuenta arrojó 6 Pages "Brand X" pero solo una tenía 65k+ fans y `@brand` en IG — esa era la activa.

---

## 4. Instagram Business User ID (opcional)

Necesario solo si usas placements de Instagram (Reels, Stories, Feed IG).

### Pasos previos

1. Tu cuenta de Instagram debe ser **Profesional** (Business o Creator)
2. Debe estar **vinculada** a la Page de Facebook (desde la app de IG → Settings → Account → Connected Accounts)

### Cómo obtenerlo

```bash
curl -G "https://graph.facebook.com/v21.0/<PAGE_ID>" \
  -d "fields=instagram_business_account" \
  -d "access_token=$ACCESS_TOKEN"
```

Output:
```json
{"instagram_business_account": {"id": "17841XXXXXXXXX"}}
```

Ese `id` es tu `instagram_user_id`.

---

## 5. Pixel / Dataset ID

Formato: solo dígitos (15-16 dígitos).

### Cómo obtenerlo

[Events Manager](https://business.facebook.com/events_manager) → seleccionar tu dataset → ID visible en la parte superior, o en la URL.

### Discovery automático

Lista los pixels asignados al ad account y su última actividad:

```bash
curl -sG "https://graph.facebook.com/v21.0/<AD_ACCOUNT_ID>/adspixels" \
  -d "fields=id,name,last_fired_time" \
  -d "access_token=$ACCESS_TOKEN" | python3 -m json.tool
```

El `last_fired_time` reciente confirma que el Pixel está activo y enviando eventos.

Si no tienes Pixel:
1. Events Manager → **Connect Data Sources** → **Web** → **Meta Pixel**
2. Seguir el setup, instalar el Pixel en tu landing
3. Verificar eventos con la [Pixel Helper](https://chrome.google.com/webstore/detail/meta-pixel-helper/) extension

---

## 6. BUSINESS_ID (opcional)

Algunas operaciones avanzadas (catálogos, audiencias compartidas) requieren el `business_id`.

### Cómo obtenerlo

Meta Business Suite → **Settings** → **Business Info** → **Business ID** visible.

Agregar a `.env` si lo necesitas:
```
BUSINESS_ID=1234567890123456
```

---

## 7. WhatsApp Business (avanzado)

Si planeas usar el flag `--whatsapp-addon` de `create_ad.py` (botón "Send to WhatsApp" en placements de browser), necesitas:

- Capability `whatsapp_business_management` aprobada para tu app
- Business verification

Ver [whatsapp-browser-addon.md](whatsapp-browser-addon.md) para el proceso completo. Sin esto, el flag funcionará a nivel código pero Meta rechazará la creación con `(#3) Application does not have the capability to make this API call`.

---

## Resumen del setup

```bash
# 1. Clonar
git clone https://github.com/<usuario>/meta-ads-toolkit.git
cd meta-ads-toolkit

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar credenciales
cp .env.example .env
# editar .env y poner ACCESS_TOKEN

cp accounts.example.yaml accounts.yaml
# editar accounts.yaml con tus IDs

# 4. Verificar
python3 scripts/status.py --account mibrand
```

Si el último comando lista tus campañas, todo está bien configurado.
