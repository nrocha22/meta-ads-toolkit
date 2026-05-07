# meta-ads-toolkit

Scripts Python + templates YAML que **complementan** el [Meta Ads CLI oficial](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/ads-cli-overview) (open beta desde abril 2026). No es un wrapper ni un framework: son scripts simples que llaman `meta ads` directamente y rellenan los gaps del CLI con Graph API directa.

Diseñado para multi-cuenta desde el inicio (`accounts.yaml`). Usable con cualquier ad account de Meta Ads, en cualquier mercado.

---

## ¿Qué resuelve este toolkit?

El Meta Ads CLI oficial cubre el CRUD básico (crear/listar/actualizar campañas, ad sets, ads, insights). Pero deja varios gaps importantes para operación real:

| Gap del CLI | Cómo lo cubre el toolkit |
|---|---|
| Evaluar ads activos con scoring | `scripts/evaluate.py` — ranking eficiencia (CPL) + volumen, output JSON pipe-able |
| Pausar ads en lote con preview | `scripts/pause_ads.py` — confirmación + log |
| Subir videos a la library | `scripts/upload_video.py` — Graph API directa con espera de procesamiento |
| Crear ads con Asset Customization Rules | `scripts/create_ad.py --placement-customization` — patrón Andromeda (video por placement) |
| Crear ads con `descriptions[]` | `scripts/create_ad.py --description` (repetible) |
| Rate limiting en evaluación | Cache local con TTL en `evaluate.py` |
| Reporting con breakdowns y comparación | `scripts/report_*.py` |
| Investigación histórica de cuenta | `scripts/research_*.py` |

**Lo que NO cubre (todavía)**:

- Crear ad sets con targeting demográfico completo (edad, género, geo radius, custom audiences). El CLI solo soporta `--targeting-countries`. Para esto hace falta `create_adset.py` vía Graph API directa — está en la roadmap.
- Activar el WhatsApp browser add-on (`message_extensions`) requiere capability `whatsapp_business_management` aprobada en tu app. Ver `docs/whatsapp-browser-addon.md`.

---

## Pre-requisitos

- Python 3.12+
- [`meta-ads`](https://pypi.org/project/meta-ads/) v1.0.1+
- Acceso a un Business Manager con un ad account, una Page, y un System User token

---

## Setup

```bash
git clone https://github.com/<usuario>/meta-ads-toolkit.git
cd meta-ads-toolkit

# Dependencias
pip install -r requirements.txt

# Credenciales
cp .env.example .env             # editar y poner ACCESS_TOKEN
cp accounts.example.yaml accounts.yaml   # editar y poner los IDs de tu cuenta
```

**¿Qué IDs necesitas?** Ver [`docs/getting-started.md`](docs/getting-started.md) para la guía paso a paso de cómo obtener `ACCESS_TOKEN`, `ad_account_id`, `page_id`, `instagram_user_id`, y `pixel_id`.

### `accounts.yaml` mínimo

```yaml
accounts:
  mibrand:
    ad_account_id: "act_XXXXXXXXXXXXXXX"
    page_id: "XXXXXXXXXXXXXXX"
    instagram_user_id: "XXXXXXXXXXXXXXX"
    pixel_id: "XXXXXXXXXXXXXXX"
    label: "Mi Brand"
    currency: "$"
```

Puedes declarar múltiples cuentas (ej. distintos mercados o distintos clientes) y elegir cuál operar con `--account <name>`.

### Verificación

```bash
python3 scripts/status.py --account mibrand
```

Si lista tus campañas, todo está OK.

---

## Tour rápido

### Evaluar ads activos

```bash
python3 scripts/evaluate.py --account mibrand last_14d
```

Muestra ranking por campaña (TOP / OK / WATCH / PAUSE? / FATIGUE?) basado en CPL relativo al promedio + volumen de conversiones. Cache local 15 min por default.

### Crear un ad

```bash
# Subir el video primero
python3 scripts/upload_video.py --account mibrand ./videos/mi-video.mp4 "Mi video"
# → devuelve {"video_id": "..."}

# Crear el ad (queda en PAUSED siempre)
python3 scripts/create_ad.py --account mibrand \
  --adset-id <ADSET_ID> \
  --video-id <VIDEO_ID> \
  --body "Texto del anuncio" \
  --title "Título" \
  --cta CONTACT_US \
  --link-url "https://tu-landing.example.com/oferta" \
  --name "Ad de prueba"
```

Más ejemplos en [`scripts/README.md`](scripts/README.md).

### Reportes

```bash
python3 scripts/report_daily.py --account mibrand last_7d
python3 scripts/report_campaign.py --account mibrand <CAMPAIGN_ID> last_30d
python3 scripts/report_compare.py --account mibrand 7d
```

---

## Estructura del repo

```
meta-ads-toolkit/
├── README.md
├── LICENSE                   # MIT
├── .env.example              # ACCESS_TOKEN
├── accounts.example.yaml     # cuentas + thresholds
├── requirements.txt
├── docs/
│   ├── getting-started.md         # Cómo obtener cada ID
│   ├── meta-ads-cli-reference.md  # Referencia del CLI oficial
│   ├── graph-api-capabilities.md  # Mapa CLI vs Graph API
│   ├── insights.md
│   ├── configuration.md
│   ├── ad-creatives-datasets-catalogs.md
│   ├── tutorials-and-recipes.md
│   └── whatsapp-browser-addon.md  # Workaround capability
├── scripts/
│   ├── helpers.py            # Loader de accounts.yaml
│   ├── _cache.py             # Cache TTL para insights
│   ├── status.py
│   ├── report_daily.py
│   ├── report_campaign.py
│   ├── report_compare.py
│   ├── evaluate.py           # Ranking con cache
│   ├── pause_ads.py
│   ├── upload_video.py
│   ├── create_ad.py          # Graph API: descriptions, placement-customization
│   └── research_*.py
└── templates/
    ├── leads.example.yaml
    └── whatsapp.example.yaml
```

---

## Convenciones

- **PAUSED siempre**: todo lo que crea ads/campañas lo deja en PAUSED. Activar es manual.
- **stdout = JSON, stderr = tabla**: scripts pensados para piping a otros scripts/agentes.
- **Confirmación humana**: scripts que crean o pausan piden confirmación antes de actuar (excepto con `--yes`).
- **Self-contained**: cada script importa solo `helpers.py` (y `_cache.py` cuando aplica). Sin framework.

---

## Roadmap

- [ ] `create_adset.py` — adsets con targeting demográfico completo vía Graph API
- [ ] `cleanup.py` — archivar campañas pausadas hace > N meses
- [ ] Skills de Claude Code para flujos de gestión

PRs y issues bienvenidos.

---

## Licencia

MIT — ver [LICENSE](LICENSE).
