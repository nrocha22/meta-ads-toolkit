# Meta Marketing API — Gotchas operativos

Sorpresas y restricciones del Graph API descubiertas en producción que **no son obvias del [reference oficial](meta-ads-cli-reference.md) ni del [graph capabilities](graph-api-capabilities.md)**. Documentadas el 2026-05-08 al refrescar una campaña que llevaba 14 meses corriendo.

Si construyes campañas/adsets/ads via API directa (no UI Ads Manager), léelo antes para evitar 5-6 idas y vueltas con errores 400.

---

## 1. Custom locations con solapamiento → rechazado en adsets nuevos

**Síntoma**: API responde `error_subcode: 1487756`, mensaje "Algunos de tus lugares se superponen. Elimina un lugar."

**Causa**: Meta cambió la validación. Múltiples `custom_locations` con radios que se solapan (ej. 5 zonas de 5 km en una misma área metropolitana) ya no se aceptan en nuevos adsets. Adsets existentes con esa config quedan grandfathered (siguen corriendo) pero no se pueden replicar.

**Workaround**:
- **1 zona grande** que cubra todo el área metropolitana: típicamente más eficiente que 5 micro-zonas porque Meta optimiza con un pool de audiencia más grande.
- O usar el campo `cities` con `key` (primary_city_id de Meta) en lugar de lat/lng. Las city boundaries no se solapan por construcción.
- Si quieres mantener varias zonas pequeñas, asegurar que la distancia entre centros sea **> 2 × radio** de cada una.

## 2. `countries: [CO]` + `custom_locations` = "overlap"

**Síntoma**: mismo error de overlap (subcode 1487756) incluso con UNA sola custom_location. Confunde porque "una zona no puede solaparse consigo misma".

**Causa**: si en `geo_locations` pasas `countries` Y `custom_locations`, Meta lo interpreta como "todo el país + una zona dentro" → eso solapa.

**Workaround**: cuando uses `custom_locations`, **omitir `countries` del nivel superior**. Cada custom_location ya tiene su propio campo `country` (string corta tipo "CO") que es suficiente.

```python
# MAL
geo_locations = {
    "countries": ["CO"],
    "custom_locations": [{"latitude": ..., "longitude": ..., "radius": ..., "country": "CO"}],
}

# BIEN
geo_locations = {
    "custom_locations": [{"latitude": ..., "longitude": ..., "radius": ..., "country": "CO"}],
}
```

## 3. `bid_strategy` a nivel campaña requiere campaign budget (CBO)

**Síntoma**: al crear/actualizar una campaña sin daily/lifetime budget, intentar setear `bid_strategy` falla con `error_user_title: "Campaña sin presupuesto"`.

**Causa**: `bid_strategy` a nivel campaña aplica solo a Campaign Budget Optimization (CBO). Si vas con Adset Budget Optimization (ABO, que es cuando seteas `is_adset_budget_sharing_enabled: false`), el bid_strategy va en el **adset**, no en la campaña.

**Workaround**:
- ABO: bid_strategy en el adset.
- CBO: bid_strategy en la campaña + daily/lifetime_budget en la campaña.

## 4. `is_dynamic_creative` no se puede cambiar post-creación

**Síntoma**: `POST /{adset_id}` con `is_dynamic_creative: true` devuelve `success: True`, pero el GET subsiguiente muestra que sigue en `false`.

**Causa**: campo immutable post-creación. La API silenciosamente lo ignora en updates en vez de devolver error.

**Workaround**: decidir el valor al crear el adset. Para cambiarlo: borrar y recrear (perdiendo learning).

## 5. `is_dynamic_creative=true` solo permite **1 ad** por adset

**Síntoma**: el primer ad attach OK, el segundo falla con `error_subcode: 1885553` "No puede haber más de un anuncio en el conjunto de anuncios con contenido dinámico".

**Causa**: cuando un adset es dynamic, Meta espera 1 sola creative DCO que se encarga de todas las variantes. Múltiples ads no aplican.

**Workaround para múltiples ads**:
- Adset `is_dynamic_creative: false` + creatives **simples** (`object_story_spec.video_data` o `link_data` con 1 body + 1 title cada uno). Cada ad tiene su propia creative no-DCO. Meta optimiza entre los ads naturalmente.
- O: adset `false` + creatives con `asset_customization_rules` (placement customization, estilo "Andromeda" — diferentes assets por placement). Permite asset_feed_spec en adsets no dinámicos.

## 6. `advantage_audience` requiere 0 o 1 explícito (no acepta default)

**Síntoma**: `error_subcode: 1870227` "Se requiere la marca de público Advantage. Configura advantage_audience como 1 o 0 en targeting_automation".

**Causa**: validación nueva. Meta obliga a tomar postura sobre Advantage+ Audience explícitamente al crear adsets.

**Workaround**: pasar siempre:
```python
targeting["targeting_automation"] = {"advantage_audience": 0}  # o 1
```

## 7. `locale 6` es **English (US)**, NO Spanish

**Síntoma**: targeting parece restrictivo, ads no llegan a hispanohablantes.

**Causa**: confusión común. Meta locale IDs:
- `6`: English (US)
- `23`: Spanish (Spain)
- `24`: Spanish (Mexico) — variantes regionales por país
- Lista completa: `GET /search?type=adlocale`

**Workaround**: para audiencias hispanohablantes en LATAM, **típicamente no hace falta filtrar por idioma** (el geo lo hace). Si querés ser explícito, usar 23 o 24 según mercado, no 6.

## 8. Reusar imágenes existentes con `image_hash`

**Útil cuando**: querés crear un ad nuevo con el mismo asset visual que uno viejo. Re-subir la imagen genera un hash distinto y Meta la trata como nueva (pierde history).

**Cómo**:
- Pull el `image_hash` del creative original: `GET /{creative_id}?fields=object_story_spec{link_data{image_hash}}` o `image_hash` directo.
- Crear creative nuevo con `object_story_spec.link_data.image_hash` (no re-upload).

```python
oss = {
    "page_id": page_id,
    "link_data": {
        "image_hash": "<HASH_DEL_CREATIVE_VIEJO>",  # 32 hex chars, scoped al ad account
        "message": body,
        "name": title,
        "link": landing_url,
        "call_to_action": {"type": "CONTACT_US", "value": {"link": landing_url}},
    },
}
```

Para videos es análogo con `video_id` (más conocido).

## 9. URL parameters (UTMs) no se inyectan automáticamente

**Síntoma**: leads aterrizan en el sitio sin UTMs → no podés atribuir downstream qué campaña los generó.

**Causa**: el `link` del creative es la URL pelada. Para UTMs hay que pasar `url_tags` aparte (campo separado del creative).

**Workaround**: en el creative spec, agregar `url_tags`:
```python
creative["url_tags"] = "utm_source=fb&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{ad.name}}"
```

Las macros `{{campaign.name}}` / `{{ad.name}}` / `{{adset.name}}` Meta las expande automáticamente al servir. **Hacerlo siempre** en campañas web-leads para cerrar el loop con el CRM/CSV.

## 10. Eliminar campaña requiere `is_adset_budget_sharing_enabled` explícito al crear

**Síntoma**: crear campaña con objective `OUTCOME_LEADS` o `OUTCOME_ENGAGEMENT` falla con "Debes indicar True o False en is_adset_budget_sharing_enabled".

**Causa**: Meta forzó esta declaración para clarificar CBO vs ABO desde la creación.

**Workaround**: pasar `is_adset_budget_sharing_enabled: false` (ABO, presupuesto por adset) o `true` (CBO con budget compartido).

---

## Detección de drift en campañas viejas

Aprendizaje colateral: las cuentas paid degradan en silencio. Una campaña con CPL lifetime $4 puede deslizar a $7 en 90d sin que nadie lo note si las decisiones se toman con `last_14d`.

Ver `scripts/check_drift.py` para detección automática. Threshold default: ratio CPL `last_90d / lifetime > 1.5×` → flag para refresh.

---

## Ver también

- [meta-ads-cli-reference.md](meta-ads-cli-reference.md) — referencia del CLI oficial.
- [graph-api-capabilities.md](graph-api-capabilities.md) — qué cubre cada API.
- [tutorials-and-recipes.md](tutorials-and-recipes.md) — recetas comunes.
