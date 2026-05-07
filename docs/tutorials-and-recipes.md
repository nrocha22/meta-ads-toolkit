# Tutorials and Recipes — Referencia

**Fuente**: Documentación oficial de Meta for Developers (verificada)
**URL**: `https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/tutorials-and-recipes`

---

## 1. Encontrar tus IDs

### Ad Account ID

```bash
meta ads adaccount list
```

Buscar la columna `id`. Configurar con:

```bash
export AD_ACCOUNT_ID=<AD_ACCOUNT_ID>
```

### Facebook Business Page ID

Necesario para crear ad creatives con el flag `--page-id`. Solo pueden ser Pages asociadas a un business al que el system user tenga acceso.

```bash
meta ads page list
```

### Business ID

Ads CLI normalmente resuelve el business ID automáticamente desde el ad account. Si es necesario, configurar explícitamente:

```bash
export BUSINESS_ID=<BUSINESS_ID>
```

---

## 2. Tu Primera Campaña (End-to-End)

Crea un setup completo: campaign → ad set → ad creative → ad.

### Paso 1: Autenticar y configurar

```bash
# Configurar access token
export ACCESS_TOKEN=<ACCESS_TOKEN>

# Encontrar tu ad account
meta ads adaccount list

# Configurar para la sesión
export AD_ACCOUNT_ID=<AD_ACCOUNT_ID>
```

### Paso 2: Encontrar tu Business Page ID

Cada ad creative necesita una Business Page como identidad:

```bash
meta ads page list
```

### Paso 3: Crear campaña

```bash
meta ads campaign create \
  --name "My First Campaign" \
  --objective OUTCOME_TRAFFIC \
  --daily-budget 5000
```

Guardar el campaign ID retornado.

### Paso 4: Crear ad set

```bash
meta ads adset create <CAMPAIGN_ID> \
  --name "US Audience" \
  --optimization-goal LINK_CLICKS \
  --billing-event IMPRESSIONS \
  --targeting-countries US
```

> Se puede omitir el budget aquí porque la campaña ya tiene daily budget (campaign budget optimization).

### Paso 5: Crear ad creative

```bash
meta ads creative create \
  --name "Hero Banner" \
  --image ./banner.jpg \
  --page-id <PAGE_ID> \
  --body "Check out our latest deals!" \
  --title "Shop Now" \
  --link-url https://example.com/sale \
  --call-to-action SHOP_NOW
```

### Paso 6: Crear ad

```bash
meta ads ad create <AD_SET_ID> \
  --name "Hero Banner Ad" \
  --creative-id <CREATIVE_ID>
```

### Paso 7: Activar

Todo se crea en PAUSED por defecto. Cuando esté listo:

```bash
meta ads campaign update <CAMPAIGN_ID> --status ACTIVE
meta ads adset update <AD_SET_ID> --status ACTIVE
meta ads ad update <AD_ID> --status ACTIVE
```

---

## 3. Scripts y Automatización

### Configuración por variables de entorno

```bash
# Ejemplo CI/CD pipeline
export ACCESS_TOKEN="$META_SYSTEM_USER_TOKEN"
export AD_ACCOUNT_ID=<AD_ACCOUNT_ID>
export BUSINESS_ID=<BUSINESS_ID>  # Se infiere del ad account si no se configura

meta --output json ads campaign list
```

### Modo no interactivo

Usar `--no-input` y `--force` para suprimir todos los prompts:

```bash
meta --no-input ads campaign delete <CAMPAIGN_ID> --force
```

### JSON output para scripts

```bash
# Obtener campaign IDs
CAMPAIGN_IDS=$(meta --output json ads campaign list | jq -r '.[].id')

# Iterar sobre campañas
for id in $CAMPAIGN_IDS; do
  echo "Processing ad campaign $id"
  meta ads insights get --campaign-id "$id" --fields conversions,purchase_roas
done
```

### Exit codes

```bash
meta ads campaign list
if [ $? -eq 3 ]; then
  echo "Not authenticated -- add token to .env"
fi
```

| Exit Code | Significado |
|---|---|
| `0` | Éxito |
| `1` | Error general |
| `2` | Error de uso / argumentos |
| `3` | Error de autenticación |
| `4` | Error de API |
| `5` | Recurso no encontrado |

---

## 4. Cleanup: Eliminar Recursos

### Cascada de eliminación

- Eliminar una **campaña** → elimina automáticamente sus ad sets e ads hijos
- Eliminar un **ad set** → elimina automáticamente sus ads hijos
- Se puede eliminar recursos individuales directamente

```bash
# Eliminar un ad
meta ads ad delete <AD_ID> --force

# Eliminar un ad set (y sus ads)
meta ads adset delete <AD_SET_ID> --force

# Eliminar una campaña (y todos sus ad sets y ads)
meta ads campaign delete <CAMPAIGN_ID> --force

# Eliminar un ad creative
meta ads creative delete <CREATIVE_ID> --force
```

### Desconectar dataset de ad account

```bash
meta ads dataset disconnect <PIXEL_ID> --ad-account-id <AD_ACCOUNT_ID> --force
```

### Eliminar catálogo

```bash
meta ads catalog delete <CATALOG_ID> --force
```
