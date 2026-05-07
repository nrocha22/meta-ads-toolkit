# Meta Graph API / Marketing API — Mapa de Capacidades

**Verificado**: Mayo 2026, API v21.0
**Propósito**: Entender qué es posible con la API directa más allá de lo que cubre el Meta Ads CLI. No es tutorial — para implementación, ver docs oficiales linkeadas en cada sección.

---

## Arquitectura

```
Graph API (infraestructura general de Meta)
  └── Marketing API (subset para ads)
       └── Meta Ads CLI (wrapper con subset de Marketing API)
```

- **Mismo token**: el system user token del CLI funciona para llamadas directas a la API.
- **Versionamiento**: Meta deprecia versiones cada ~2 años, lanza nueva versión cada trimestre. Actual: v21.0.
- **Base URL**: `https://graph.facebook.com/v21.0/`

---

## Mapa de Capacidades

### 1. Campaign Management

| Capacidad | CLI | API | Qué hace |
|-----------|-----|-----|----------|
| CRUD campaigns | ✅ | ✅ | Crear, leer, actualizar, eliminar campañas |
| CRUD ad sets | ✅ | ✅ | Crear, leer, actualizar, eliminar ad sets |
| CRUD ads | ✅ | ✅ | Crear, leer, actualizar, eliminar ads |
| Status management | ✅ | ✅ | ACTIVE, PAUSED, ARCHIVED |
| Campaign Budget Optimization (CBO) | ✅ | ✅ | Budget a nivel campaña distribuido entre ad sets |
| Ad Set Budget (ABO) | ✅ | ✅ | Budget individual por ad set |
| Special Ad Categories | Parcial | ✅ | Housing, credit, employment, politics |
| Campaign spending limits | ❌ | ✅ | Tope de gasto total de campaña |

📖 [Campaign API Reference](https://developers.facebook.com/docs/marketing-api/reference/ad-campaign-group)

---

### 2. Targeting

| Capacidad | CLI | API | Qué hace |
|-----------|-----|-----|----------|
| Países | ✅ | ✅ | `--targeting-countries US,MX` |
| Ciudades | ❌ | ✅ | Target por ciudad con radio |
| Geo radius | ❌ | ✅ | Radio alrededor de un punto |
| Geo exclusiones | ❌ | ✅ | Excluir zonas geográficas |
| Edad (age_min/age_max) | ❌ | ✅ | Rango de edad |
| Género | ❌ | ✅ | Hombres, mujeres, todos |
| Intereses y comportamientos | ❌ | ✅ | Targeting por intereses |
| Exclusiones de audiencia | ❌ | ✅ | Excluir custom audiences |
| Connections | ❌ | ✅ | Personas conectadas/no conectadas a tu página |
| Advantage+ Targeting | ❌ | ✅ | Meta expande automáticamente con AI |

> **Nota**: el CLI hoy solo soporta `--targeting-countries`. Para edad, género, geo radius, custom audiences y exclusiones se necesita Graph API directa.

📖 [Targeting Spec Reference](https://developers.facebook.com/docs/marketing-api/audiences/reference/basic-targeting)

---

### 3. Audiences

| Capacidad | CLI | API | Qué hace |
|-----------|-----|-----|----------|
| Custom Audience: Customer List | ❌ | ✅ | Subir lista de teléfonos/emails para matching |
| Custom Audience: Website | ❌ | ✅ | Visitantes del sitio web (via Pixel) |
| Custom Audience: Engagement | ❌ | ✅ | Personas que interactuaron con tu página/IG/ads |
| Custom Audience: App Activity | ❌ | ✅ | Usuarios de tu app |
| Lookalike Audiences | ❌ | ✅ | Personas similares a una custom audience |
| Advantage+ Audiences | ❌ | ✅ | Meta usa AI para encontrar la mejor audiencia |
| Saved Audiences | ❌ | ✅ | Reutilizar combinaciones de targeting |

📖 [Custom Audiences](https://developers.facebook.com/docs/marketing-api/reference/custom-audience/) | [Lookalike](https://developers.facebook.com/docs/marketing-api/lookalike-audiences)

---

### 4. Creatives

| Capacidad | CLI | API | Qué hace |
|-----------|-----|-----|----------|
| Imagen/video estándar | ✅ | ✅ | Un creative con un asset |
| Dynamic Creative (DCO) | ✅ | ✅ | Múltiples assets, Meta optimiza combinaciones |
| Asset Customization Rules | ❌ | ✅ | Asignar video específico a placement específico |
| Carousel ads | ❌ | ✅ | Múltiples cards deslizables |
| Collection ads | ❌ | ✅ | Instant Experience con catálogo |
| Dynamic Ads (catalog) | Parcial | ✅ | Productos del catálogo automáticamente |
| Creative enhancements | ❌ | ✅ | Mejoras automáticas (crop, brightness) |
| Instagram-specific formats | Parcial | ✅ | Reels, Stories con stickers, polls |

> **Nota**: `scripts/create_ad.py --placement-customization` ya replica el patrón Andromeda de Asset Customization Rules vía Graph API directa (1 ó 2 video-ids, feed-square + catch-all vertical).

📖 [Ad Creative](https://developers.facebook.com/docs/marketing-api/reference/ad-creative) | [Asset Feed Spec](https://developers.facebook.com/docs/marketing-api/ad-creative/asset-feed-spec/options/)

---

### 5. Measurement & Attribution

| Capacidad | CLI | API | Qué hace |
|-----------|-----|-----|----------|
| Insights (métricas de rendimiento) | ✅ | ✅ | spend, impressions, clicks, CTR, CPC, ROAS |
| Breakdowns | ✅ | ✅ | Por edad, género, placement, dispositivo, país |
| Date ranges y presets | ✅ | ✅ | Períodos custom y presets (last_7d, etc.) |
| Attribution windows | Parcial | ✅ | 1d click, 7d click, 1d view — configurable por ad set |
| Conversions API (CAPI) | ❌ | ✅ | Enviar eventos server-side (no depende del browser) |
| Offline Conversions | ❌ | ✅ | Subir conversiones offline (ej: ventas en local) |
| Attribution models | ❌ | ✅ | Last-touch, multi-touch, modelos custom |
| Custom conversions | ❌ | ✅ | Definir conversión por URL, evento, o regla |

📖 [Insights API](https://developers.facebook.com/docs/marketing-api/insights) | [Conversions API](https://developers.facebook.com/docs/marketing-api/conversions-api)

---

### 6. Optimization & Automated Rules

| Capacidad | CLI | API | Qué hace |
|-----------|-----|-----|----------|
| Bid strategies | Parcial | ✅ | Lowest cost, cost cap, bid cap, ROAS target |
| Delivery estimates | ❌ | ✅ | Estimación de alcance antes de activar |
| Automated Rules | ❌ | ✅ | Pausar/activar ads por reglas (CPA > $X, frequency > Y) |
| Budget scheduling | ❌ | ✅ | Aumentar/disminuir budget por horario |
| Pacing | ❌ | ✅ | Standard vs accelerated delivery |

📖 [Ad Rules](https://developers.facebook.com/docs/marketing-api/ad-rules)

---

### 7. Pixel & Events

| Capacidad | CLI | API | Qué hace |
|-----------|-----|-----|----------|
| Pixel management (CRUD) | ✅ | ✅ | Crear, conectar, asignar usuarios |
| Standard events | ❌ | ✅ | PageView, Lead, Purchase, etc. (configuración) |
| Custom events | ❌ | ✅ | Eventos propios (ej: "Conversation6Plus") |
| Event deduplication | ❌ | ✅ | Pixel + CAPI envían el mismo evento sin contar doble |
| Data Processing Options | ❌ | ✅ | LDU (Limited Data Use) para compliance |
| Server events (CAPI) | ❌ | ✅ | Enviar eventos desde servidor sin JavaScript |

📖 [Datasets (Pixels)](https://developers.facebook.com/docs/marketing-api/reference/ads-pixel) | [Server Events](https://developers.facebook.com/docs/marketing-api/conversions-api/using-the-api)

---

### 8. Catalog & Commerce

| Capacidad | CLI | API | Qué hace |
|-----------|-----|-----|----------|
| Catalog CRUD | ✅ | ✅ | Crear y gestionar catálogos de productos |
| Product items CRUD | ✅ | ✅ | Productos individuales |
| Product sets | ✅ | ✅ | Agrupaciones de productos |
| Product feeds | ✅ | ✅ | Imports automáticos |
| Dynamic product ads | Parcial | ✅ | Ads que muestran productos relevantes automáticamente |

📖 [Product Catalog](https://developers.facebook.com/docs/marketing-api/catalog)

---

### 9. Leads

| Capacidad | CLI | API | Qué hace |
|-----------|-----|-----|----------|
| Lead retrieval | ❌ | ✅ | Descargar leads de instant forms vía API |
| Lead form creation | ❌ | ✅ | Crear formularios programáticamente |
| CRM integration webhooks | ❌ | ✅ | Notificar en tiempo real cuando llega un lead |
| Lead ads filtering | ❌ | ✅ | Filtrar leads por fecha, formulario, ad |

📖 [Lead Ads](https://developers.facebook.com/docs/marketing-api/guides/lead-ads)

---

### 10. Batch & Efficiency

| Capacidad | CLI | API | Qué hace |
|-----------|-----|-----|----------|
| Batch requests | ❌ | ✅ | Múltiples operaciones en un solo HTTP call (hasta 50) |
| Async jobs | ❌ | ✅ | Reports grandes sin timeout |
| Webhooks/Subscriptions | ❌ | ✅ | Notificaciones push cuando algo cambia |
| Rate limits | N/A | ✅ | 200 calls/hour creación, 600 reads por ad account |

📖 [Batch Requests](https://developers.facebook.com/docs/graph-api/making-multiple-requests) | [Rate Limiting](https://developers.facebook.com/docs/marketing-api/overview/authorization#limits)

---

## Resumen: CLI vs API Directa

| Categoría | CLI cubre | Solo API |
|-----------|-----------|----------|
| Campaign/AdSet/Ad CRUD | ✅ | — |
| Insights y reporting | ✅ | Más breakdowns disponibles |
| DCO (multi-asset) | ✅ | — |
| Pixel management | ✅ | — |
| Catalogs | ✅ | — |
| **Targeting demográfico** | ❌ Solo países | **Edad, género, radius, exclusiones** |
| **Asset customization** | ❌ | **Video por placement** (cubierto por `create_ad.py`) |
| **Audiences** | ❌ | **Custom, lookalike, saved** |
| **CAPI** | ❌ | **Server-side events** |
| **Automated rules** | ❌ | **Start/stop por threshold** |
| **Offline conversions** | ❌ | **Subir ventas reales** |

---

## Custom Audiences — patrón general

Para subir una lista de clientes (teléfonos/emails) y crear lookalikes:

**Crear audiencia** (una vez por segmento):
```
POST /v21.0/{ad_account_id}/customaudiences
{
  "name": "Customer List",
  "subtype": "CUSTOM",
  "customer_file_source": "USER_PROVIDED_ONLY"
}
```

**Subir usuarios** (periódicamente):
```
POST /v21.0/{audience_id}/users
{
  "payload": {
    "schema": ["PHONE", "EMAIL", "FN", "LN", "COUNTRY"],
    "data": [
      ["<sha256_phone>", "<sha256_email>", "<sha256_first>", "<sha256_last>", "<country_code>"]
    ]
  }
}
```

Requisitos:
- Identificadores hasheados con **SHA-256** (Meta no acepta datos raw)
- Teléfono normalizado a E.164 antes de hashear (`+15551234567`)
- Email lowercase antes de hashear
- Nombre/apellido lowercase, sin espacios extra, antes de hashear

**Lookalike**:
```
POST /v21.0/{ad_account_id}/customaudiences
{
  "name": "Lookalike 1% - Best Customers",
  "subtype": "LOOKALIKE",
  "origin_audience_id": "{source_audience_id}",
  "lookalike_spec": {"country": "DO", "ratio": 0.01}
}
```

Tamaño mínimo: ~100 personas matched por audiencia. Match rate típico con teléfono+email+nombre: 60-70%.

---

## Notas de Implementación

- **Patrón**: `requests.get/post` con `ACCESS_TOKEN` del `.env` — misma auth que el CLI. Ver `scripts/create_ad.py` y `scripts/upload_video.py` para ejemplos.
- **Versión**: fijar `API_VERSION = "v21.0"` en `helpers.py`, actualizar cuando Meta deprecie.
- **Rate limits**: 200 calls/hora para creación, 600 para reads. `evaluate.py` integra cache local para mitigar.
- **Testing**: usar [Meta API Explorer](https://developers.facebook.com/tools/explorer/) para probar calls antes de scriptear.
- **Estilo**: scripts self-contained, sin abstracciones extra.

---

## Fuentes

- [Marketing API Overview](https://developers.facebook.com/docs/marketing-api/)
- [Graph API Reference](https://developers.facebook.com/docs/graph-api/)
- [API Versioning & Deprecation](https://developers.facebook.com/docs/graph-api/guides/versioning)
- [Targeting Spec](https://developers.facebook.com/docs/marketing-api/audiences/reference/basic-targeting)
- [Custom Audiences](https://developers.facebook.com/docs/marketing-api/reference/custom-audience/)
- [Custom Audience Users](https://developers.facebook.com/docs/marketing-api/reference/custom-audience/users/)
- [Lookalike Audiences](https://developers.facebook.com/docs/marketing-api/lookalike-audiences)
- [Asset Feed Spec](https://developers.facebook.com/docs/marketing-api/ad-creative/asset-feed-spec/options/)
- [Conversions API](https://developers.facebook.com/docs/marketing-api/conversions-api)
- [CAPI for Offline Events](https://developers.facebook.com/docs/marketing-api/conversions-api/offline-events/)
- [Insights API](https://developers.facebook.com/docs/marketing-api/insights)
- [Ad Rules](https://developers.facebook.com/docs/marketing-api/ad-rules)
- [Rate Limiting](https://developers.facebook.com/docs/marketing-api/overview/authorization#limits)
