# Scripts Operacionales

## Flujo principal

```
evaluate → decidir → pause / create
```

`--account <name>` es el nombre de la entrada en `accounts.yaml`. Si no se pasa, se usa la primera cuenta declarada.

---

## 1. Evaluar ads activos

```bash
python3 scripts/evaluate.py --account mibrand
python3 scripts/evaluate.py --account mibrand last_7d    # período custom
python3 scripts/evaluate.py --account mibrand --no-cache  # forzar refresh
python3 scripts/evaluate.py --account mibrand --cache-ttl 60  # TTL custom (segundos)
```

Muestra ranking por campaña con scoring de eficiencia + volumen. Output:
- Tabla visual (stderr) para lectura rápida
- JSON (stdout) para pipe a otros scripts o agentes

**Cache**: TTL default 15 minutos. Banner explícito en stderr cuando hay cache hit.

**Scores:**
- `TOP` (***) — alta eficiencia + alto volumen
- `OK` (**) — rendimiento promedio
- `WATCH` (*) — bajo rendimiento, monitorear
- `PAUSE?` (---) — spend sin conversiones, candidato a pausa
- `FATIGUE?` — CTR muy bajo vs promedio (creativos agotados)
- `SOLO` — único ad en la campaña, sin referencia para comparar

---

## 2. Pausar ads

```bash
# Por ID directo
python3 scripts/pause_ads.py --account mibrand <AD_ID> [AD_ID...]

# Desde evaluate (pausa los marcados PAUSE?/FATIGUE?)
python3 scripts/evaluate.py --account mibrand | python3 scripts/pause_ads.py --account mibrand

# Sin confirmación (para agentes)
python3 scripts/pause_ads.py --account mibrand --yes <AD_ID>
```

Muestra preview con métricas antes de confirmar. Log en `logs/paused.log`. Nunca usa cache.

---

## 3. Subir video

```bash
python3 scripts/upload_video.py --account mibrand ./videos/mi-video.mp4 "Nombre del video"
```

Sube via Graph API, espera procesamiento (~10-30s), devuelve JSON con `video_id`.

---

## 4. Crear ad set (con targeting completo)

```bash
# Dry-run primero (preview del payload sin POST)
python3 scripts/create_adset.py --account mibrand \
  --campaign-id <CAMPAIGN_ID> \
  --template templates/leads.example.yaml \
  --name "Web Leads — Bogota" \
  --daily-budget 5000 \
  --dry-run

# Crear de verdad (queda en PAUSED)
python3 scripts/create_adset.py --account mibrand \
  --campaign-id <CAMPAIGN_ID> \
  --template templates/leads.example.yaml \
  --name "Web Leads — Bogota" \
  --daily-budget 5000
```

Soporta targeting completo vía Graph API directa (no posible con `meta ads ad-set create`):
- `geo_locations`: countries + custom_locations (lat/lng + radio en millas)
- `excluded_geo_locations`
- `age_min`, `age_max`, género, locales
- `custom_audiences`, `excluded_custom_audiences`, `flexible_spec`
- `targeting_optimization` (Advantage audience)
- `promoted_object` (pixel + custom_event_type, o page_id para WhatsApp)
- `destination_type` (WEBSITE, WHATSAPP, MESSENGER, ON_AD)
- `attribution_spec` parseable de strings tipo `"click_7d_view_1d"`
- `is_dynamic_creative`

Budget en **minor units** de la moneda de la cuenta (USD/EUR/PEN cents, COP/JPY raw). Log en `logs/created_adsets.log`.

`page_id`, `pixel_id`, `instagram_user_id` se toman de `accounts.yaml` — el template no los duplica.

---

## 5. Crear ad

```bash
# Single creative simple
python3 scripts/create_ad.py --account mibrand \
  --adset-id <ADSET_ID> \
  --video-id <VIDEO_ID> \
  --body "Texto del anuncio" \
  --title "Título" \
  --cta CONTACT_US \
  --link-url "https://..." \
  --name "Nombre del ad"

# DCO con múltiples variaciones (asset_feed_spec sin reglas)
python3 scripts/create_ad.py --account mibrand \
  --adset-id <ADSET_ID> \
  --video-id <VIDEO_ID_1> --video-id <VIDEO_ID_2> \
  --body "Variación 1" --body "Variación 2" \
  --title "Título A" --title "Título B" \
  --cta CONTACT_US \
  --name "Ad DCO"

# Patrón Andromeda (placement asset customization)
# 1 video usa el mismo en ambos placements; 2 videos = primero feed-square, segundo catch-all vertical
python3 scripts/create_ad.py --account mibrand \
  --adset-id <ADSET_ID> \
  --video-id <FEED_VIDEO> --video-id <REELS_VIDEO> \
  --body "..." --body "..." \
  --title "..." --title "..." \
  --description "Primer descriptor" \
  --description "Segundo descriptor" \
  --cta CONTACT_US \
  --link-url "https://..." \
  --whatsapp-addon \
  --placement-customization \
  --name "Ad - N"
```

### Flags de creative avanzados

| Flag | Efecto | Cuándo usarlo |
|---|---|---|
| `--description` (repetible) | `asset_feed_spec.descriptions[]` | Texto secundario debajo del title; complementa el body |
| `--whatsapp-addon` | `asset_feed_spec.message_extensions: [{type: whatsapp}]` | Botón "Enviar a WhatsApp" en placements de browser. **Falla si el app no tiene capability `whatsapp_business_management`** — ver `docs/whatsapp-browser-addon.md` |
| `--placement-customization` | `asset_feed_spec.asset_customization_rules` con 2 reglas | Replica patrón Andromeda. Soporta 1 o 2 video-ids. Requiere `--video-id` |
| `--welcome-template <path>` | `additional_data.page_welcome_message` (asset_feed) o `video_data.page_welcome_message` (single) | WhatsApp welcome message template (CTWA ads). Path a JSON con la estructura del Visual Editor |

**Restricción**: `--description`, `--whatsapp-addon` y `--placement-customization` solo funcionan vía Graph API directa, es decir requieren `--video-id` (no se aplican con `--video-file` o `--video-url` que pasan por el CLI).

Siempre crea en **PAUSED**. Activar manualmente:
```bash
meta ads ad update <AD_ID> --status ACTIVE
```

---

## Notas

- **Rate limiting**: ~30 calls en ráfaga = bloqueo de ~10 min. `evaluate.py` incluye delays + cache local.
- **Adset ID**: para targeting completo al crear adsets, usar `create_adset.py` (Graph API directa). El CLI oficial solo soporta `--targeting-countries`.
- **`--account`**: nombre declarado en `accounts.yaml`. Default: primera entrada.
- **Convención**: tabla a stderr, JSON a stdout. Exit code 0=OK, 1=error, 2=sin datos.
