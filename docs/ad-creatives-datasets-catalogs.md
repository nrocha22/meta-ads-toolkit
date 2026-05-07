# Ad Creatives, Datasets y Catalogs — Referencia

**Fuente**: Documentación oficial de Meta for Developers (verificada)

---

## 1. Ad Creatives

### Instagram Placements

```bash
meta ads creative create --name "Insta Ad" \
  --page-id <PAGE_ID> \
  --instagram-actor-id <INSTAGRAM_ACCOUNT_ID> \
  --image ./banner.jpg \
  --body "Shop our collection" \
  --link-url https://example.com
```

### Dynamic Creative Optimization (DCO)

DCO permite proveer múltiples variaciones de imágenes, headlines, body text, descripciones y CTAs. Meta automáticamente testea combinaciones y optimiza la entrega hacia las variantes de mejor rendimiento.

#### Requisitos

- `--link-url` para la URL de destino
- Al menos un `--images` o `--videos`
- Flags en **plural** (`--images`, `--titles`, `--bodies`) en vez de singular (`--image`, `--video`, `--body`, `--title`)

#### Crear DCO

```bash
meta ads creative create --name "DCO Test" \
  --page-id <PAGE_ID> \
  --link-url https://example.com \
  --images ./img1.jpg --images ./img2.jpg --images ./img3.jpg \
  --titles "Shop Now" --titles "Learn More" \
  --bodies "50% off everything!" --bodies "Free shipping today!" \
  --descriptions "Limited time offer" --descriptions "While supplies last" \
  --call-to-actions SHOP_NOW --call-to-actions LEARN_MORE
```

#### DCO con Videos

```bash
meta ads creative create --name "Video DCO" \
  --page-id <PAGE_ID> \
  --link-url https://example.com \
  --videos ./vid1.mp4 --videos ./vid2.mp4 \
  --titles "New Arrivals" --titles "Watch Now" \
  --bodies "Check out our new collection" --bodies "See what's trending"
```

#### Límites de DCO

| Tipo de Asset | Máximo |
|---|---|
| Images | 10 |
| Videos | 10 |
| Titles | 5 |
| Bodies | 5 |
| Descriptions | 5 |
| Call-to-actions | 5 |

### Actualizar Creatives

```bash
# Actualizar texto
meta ads creative update <CREATIVE_ID> --body "New ad copy" --title "New Headline"

# Reemplazar imagen
meta ads creative update <CREATIVE_ID> --image ./new-banner.jpg

# Reemplazar video
meta ads creative update <CREATIVE_ID> --video ./new-video.mp4

# Cambiar estado
meta ads creative update <CREATIVE_ID> --status PAUSED
```

Opciones de update disponibles: `--name`, `--body`, `--title`, `--link-url`, `--description`, `--call-to-action`, `--image`, `--video`, `--instagram-actor-id`, `--status`

> **Nota:** La API previene actualizar algunos campos después de la creación. Si un update falla, crear un nuevo ad creative en su lugar.

### Eliminar Creatives

> **Nota:** No se pueden eliminar ad creatives que estén siendo usados por ads activos. Pausar o eliminar los ads asociados primero.

```bash
meta ads creative delete <CREATIVE_ID>
meta ads creative delete <CREATIVE_ID> --force    # Sin confirmación
```

### Workflow Completo de Creatives

```bash
# 1. Encontrar el Business Page ID
meta ads page list

# 2. Crear un ad creative
meta ads creative create --name "Launch Ad" \
  --page-id <PAGE_ID> \
  --image ./launch-banner.jpg \
  --body "Our new product is here!" \
  --title "Just Launched" \
  --link-url https://example.com/launch \
  --call-to-action SHOP_NOW

# 3. Crear un ad con el creative ID retornado
meta ads ad create <AD_SET_ID> --name "Launch Ad - US" --creative-id <CREATIVE_ID>

# 4. Activar el ad con el ad ID retornado
meta ads ad update <AD_ID> --status ACTIVE
```

---

## 2. Datasets (Meta Pixels)

Un dataset representa un Meta Pixel o endpoint de Conversions API. Se usan para trackear eventos en el sitio web (purchases, add-to-carts, page views). Son esenciales para campañas de conversión y retargeting.

### Resolución de Business ID

Ads CLI resuelve el business ID en este orden:

1. Flag `--business-id`
2. Variable de entorno `BUSINESS_ID`
3. Derivado automáticamente del ad account configurado

### Listar Datasets

```bash
meta ads dataset list
meta ads dataset list --business-id <BUSINESS_ID>
```

### Crear Dataset

```bash
meta ads dataset create --name "My Website Pixel"
meta ads dataset create --name "My Pixel" --business-id <BUSINESS_ID>
```

> Después de la creación, Ads CLI automáticamente asigna al usuario autenticado al dataset con permisos `ADVERTISE`, `ANALYZE` y `EDIT`.

### Ver Detalles del Dataset

```bash
meta ads dataset get <PIXEL_ID>
```

### Conectar Dataset a Ad Account

```bash
meta ads dataset connect <PIXEL_ID> --ad-account-id <AD_ACCOUNT_ID>
```

### Conectar Dataset a Catálogo

```bash
meta ads dataset connect <PIXEL_ID> --catalog-id <CATALOG_ID>
```

### Conectar a Ambos

```bash
meta ads dataset connect <PIXEL_ID> --ad-account-id <AD_ACCOUNT_ID> --catalog-id <CATALOG_ID>
```

### Desconectar Dataset

```bash
meta ads dataset disconnect <PIXEL_ID> --ad-account-id <AD_ACCOUNT_ID>
meta ads dataset disconnect <PIXEL_ID> --ad-account-id <AD_ACCOUNT_ID> --force
```

### Asignar Usuario a Dataset

```bash
meta ads dataset assign-user <PIXEL_ID>
meta ads dataset assign-user <PIXEL_ID> --user-id <USER_ID>
meta ads dataset assign-user <PIXEL_ID> --tasks ADVERTISE --tasks ANALYZE --tasks EDIT
```

| Opción | Default | Descripción |
|--------|---------|-------------|
| `--user-id` | Usuario autenticado | User ID a asignar |
| `--tasks` | `ADVERTISE`, `ANALYZE` | Permisos (repetir para múltiples) |

---

## 3. Product Catalogs

### Listar Catálogos

```bash
meta ads catalog list
meta ads catalog list --business-id <BUSINESS_ID>
meta ads catalog list --limit 50
```

### Crear Catálogo

```bash
meta ads catalog create --name "My Catalog"
meta ads catalog create --name "Hotel Catalog" --vertical hotels
```

| Opción | Requerido | Default | Descripción |
|--------|-----------|---------|-------------|
| `--name` | Sí | | Nombre del catálogo |
| `--vertical` | No | `commerce` | Tipo de catálogo |

### Ver, Actualizar, Eliminar

```bash
meta ads catalog get <CATALOG_ID>
meta ads catalog update <CATALOG_ID> --name "Renamed Catalog"
meta ads catalog delete <CATALOG_ID>
meta ads catalog delete <CATALOG_ID> --force
```

### Product Items

```bash
meta ads product-item list --catalog-id <CATALOG_ID>
meta ads product-item create --catalog-id <CATALOG_ID> ...
meta ads product-item get <PRODUCT_ID>
meta ads product-item update <PRODUCT_ID> ...
meta ads product-item delete <PRODUCT_ID>
```

### Product Sets

```bash
meta ads product-set list --catalog-id <CATALOG_ID>
meta ads product-set create --catalog-id <CATALOG_ID> ...
meta ads product-set get <PRODUCT_SET_ID>
meta ads product-set update <PRODUCT_SET_ID> ...
meta ads product-set delete <PRODUCT_SET_ID>
```
