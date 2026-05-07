# Insights — Referencia

**Fuente**: Documentación oficial de Meta for Developers (verificada)
**URL**: `https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/insights`

---

## Uso Básico

```bash
# Métricas a nivel de cuenta, últimos 30 días (default)
meta ads insights get

# Métricas específicas
meta ads insights get --adset-id <AD_SET_ID> --fields spend,impressions,ctr,cpc
```

---

## Date Ranges

### Presets

```bash
meta ads insights get --date-preset last_30d
meta ads insights get --date-preset yesterday
```

Presets disponibles: `today`, `yesterday`, `last_3d`, `last_7d`, `last_14d`, `last_30d`, `last_90d`, `this_month`, `last_month`

### Rango personalizado

```bash
meta ads insights get --since 2024-01-01 --until 2024-01-31
```

> `--since` y `--until` deben usarse juntos y sobreescriben `--date-preset`.

---

## Time Granularity

Control de cómo se desglosan los resultados en el tiempo con `--time-increment`:

| Valor | Descripción |
|---|---|
| `all_days` (default) | Agregado en todo el rango |
| `daily` | Una fila por día |
| `weekly` | Una fila por semana |
| `monthly` | Una fila por mes |

```bash
# Gasto diario últimos 30 días
meta ads insights get --date-preset last_30d --time-increment daily --fields spend

# Rendimiento semanal de campaña
meta ads insights get --campaign-id <CAMPAIGN_ID> --time-increment weekly
```

---

## Breakdowns

Dimensiones demográficas o de placement con `--breakdown` (repetible):

| Breakdown | Descripción |
|---|---|
| `age` | Rangos de edad |
| `gender` | Género |
| `country` | País |
| `publisher_platform` | Facebook, Instagram, Audience Network |
| `device_platform` | Mobile, desktop |
| `platform_position` | Feed, Stories, Reels |
| `impression_device` | Tipo de dispositivo |

```bash
# Rendimiento por edad y género
meta ads insights get --breakdown age --breakdown gender

# Comparación por plataforma
meta ads insights get --breakdown publisher_platform --fields spend,impressions,ctr
```

---

## Filtering

Filtrar por campaña, ad set, o ad específico:

```bash
meta ads insights get --campaign-id <CAMPAIGN_ID>
meta ads insights get --adset-id <AD_SET_ID>
meta ads insights get --ad-id <AD_ID>
```

---

## Sorting

```bash
meta ads insights get --adset-id <AD_SET_ID> --sort spend_descending
meta ads insights get --adset-id <AD_SET_ID> --sort impressions_ascending

# Últimos 30 días, nivel campaña, ordenado por gasto
meta ads insights get --campaign-id <CAMPAIGN_ID> --date-preset last_30d --sort spend_descending
```

Formato: `<metric>_ascending` o `<metric>_descending`

---

## Custom Fields

Especificar métricas con `--fields` (separadas por coma):

```bash
meta ads insights get --fields spend,impressions,clicks,ctr,cpc,reach
meta ads insights get --fields spend,conversions,cost_per_conversion,purchase_roas
```

**Fields por defecto:** `spend`, `impressions`, `clicks`, `ctr`, `cpc`, `reach`

Cualquier campo válido del Meta Insights API puede usarse. Campos comunes:

| Field | Descripción |
|---|---|
| `spend` | Monto total gastado |
| `impressions` | Veces que se mostraron los ads |
| `reach` | Usuarios únicos que vieron el ad |
| `clicks` | Clicks totales |
| `ctr` | Click-through rate |
| `cpc` | Costo por click |
| `cpm` | Costo por 1,000 impresiones |
| `frequency` | Promedio de veces que cada persona vio el ad |
| `conversions` | Número de conversiones |
| `cost_per_conversion` | Costo por conversión |
| `purchase_roas` | Return on ad spend |

---

## Result Limit

```bash
meta ads insights get --campaign-id <CAMPAIGN_ID> --limit 100    # Default: 50
```

---

## Referencia Completa de Opciones

| Opción | Default | Descripción |
|---|---|---|
| `--date-preset` | `last_30d` | Rango de fechas predefinido |
| `--since` | | Fecha inicio (YYYY-MM-DD). Requiere `--until` |
| `--until` | | Fecha fin (YYYY-MM-DD). Requiere `--since` |
| `--time-increment` | `all_days` | Granularidad: `all_days`, `daily`, `weekly`, `monthly` |
| `--breakdown` | | Dimensión de desglose (repetible) |
| `--fields` | `spend,impressions,...` | Lista de métricas separadas por coma |
| `--campaign-id` | | Filtrar por campaña |
| `--adset-id` | | Filtrar por ad set |
| `--ad-id` | | Filtrar por ad |
| `--sort` | | Orden (ej: `spend_descending`) |
| `--limit` / `-l` | 50 | Máximo de filas a retornar |
