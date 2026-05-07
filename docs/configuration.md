# Configuration — Referencia

**Fuente**: Documentación oficial de Meta for Developers (verificada)
**URL**: `https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/setup/configuration`

---

## Variables de Entorno

| Variable | Requerida | Descripción |
|---|---|---|
| `ACCESS_TOKEN` | Sí | System user access token generado en Meta Business Suite |
| `AD_ACCOUNT_ID` | Sí (para la mayoría de comandos) | ID de la cuenta publicitaria de Meta |
| `BUSINESS_ID` | No | Business ID por defecto (para comandos de catálogo/dataset) |

---

## Precedencia de Configuración

Ads CLI resuelve settings en este orden (prioridad más alta primero):

1. **Command-line flags** (ej: `--ad-account-id`)
2. **Variables de entorno**
3. **Archivo `.env` a nivel de proyecto**
4. **Config a nivel de usuario** (`~/.config/meta/`)

---

## Archivo .env

Para evitar configurar las variables de entorno en cada sesión, se puede crear un `.env` en el directorio donde se ejecuta Ads CLI:

```bash
cat > .env << 'DOTENV'
ACCESS_TOKEN='<ACCESS_TOKEN>'
AD_ACCOUNT_ID='<AD_ACCOUNT_ID>'
BUSINESS_ID='<BUSINESS_ID>'
DOTENV
```

> **Nota:** Las variables de entorno del shell tienen precedencia sobre los valores del `.env`.

---

## Directorio de Configuración

Ads CLI almacena configuración en un directorio compatible con XDG:

```
~/.config/meta/
```

Se puede sobreescribir el directorio base con la variable de entorno `XDG_CONFIG_HOME`.
