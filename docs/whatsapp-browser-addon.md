# WhatsApp Browser Add-on (`message_extensions`)

## Qué es

Es un botón **"Send to WhatsApp"** que aparece en ads servidos a navegadores (placements como Facebook desktop feed, Instagram web). Cuando el usuario hace click, se abre WhatsApp Web/Desktop con la conversación ya iniciada hacia el número de WhatsApp Business linkeado a la Page.

A diferencia de Click-to-WhatsApp (CTWA) tradicional que es solo para mobile, el browser add-on lleva la conversación a WhatsApp también desde desktop — útil para mercados donde mucho del tráfico es desde escritorio.

---

## Cómo se construye en el payload

`create_ad.py --whatsapp-addon` agrega el siguiente bloque al `asset_feed_spec` del creative:

```json
{
  "asset_feed_spec": {
    "message_extensions": [
      {"type": "whatsapp"}
    ],
    ...
  }
}
```

Ver `scripts/create_ad.py` para el código exacto.

---

## Por qué falla con la mayoría de apps

La capacidad para inyectar `message_extensions` requiere:

1. **App capability**: `whatsapp_business_management` aprobada en App Review
2. **Business verification** completada para el Business Manager dueño del app
3. La Page del ad debe tener un **WhatsApp Business** account linkeado

Si falta cualquiera, Meta rechaza la creación del creative con:
```
(#3) Application does not have the capability to make this API call.
```

---

## Cómo solicitar la capability

1. [Meta for Developers](https://developers.facebook.com/apps/) → tu app
2. **App Review** → **Permissions and Features**
3. Buscar **`whatsapp_business_management`** → **Request Advanced Access**
4. Completar el formulario:
   - Caso de uso: "Programmatic ad creation with WhatsApp browser add-on"
   - Pasos para reproducir: link al script o documentación
   - Screencast (~1 min) mostrando cómo se usa en tu flujo
5. Esperar aprobación (típicamente 1-3 días hábiles)

Requisitos paralelos:
- **Business Verification**: Settings → Security Center → completar verificación con documentos legales del negocio
- **App en Live mode** (no Development mode)

---

## Workaround manual mientras tanto

Si la capability no está aprobada, el flujo es:

1. Crear el ad con `create_ad.py` **sin** `--whatsapp-addon` (queda en PAUSED como siempre)
2. Abrir el ad en [Meta Ads Manager](https://www.facebook.com/adsmanager) → editar
3. En la sección **Add-ons** del creative, activar **"Allow people to message your business via WhatsApp"**
4. Guardar y activar el ad

Tiene que hacerse uno por uno desde la UI. Tedioso si rotas muchos ads, pero funciona.

---

## Referencias

- [Meta App Review Process](https://developers.facebook.com/docs/app-review)
- [Business Verification](https://www.facebook.com/business/help/2058515294227817)
- [WhatsApp Business Platform Overview](https://developers.facebook.com/docs/whatsapp/cloud-api)
- `scripts/create_ad.py` — implementación del flag `--whatsapp-addon`
