#!/usr/bin/env python3
"""Crea un ad con creativo dentro de un adset existente. Siempre en PAUSED."""

import json
import sys
import time
import os
import argparse
import subprocess
import requests
from pathlib import Path
from helpers import get_account, get_access_token, ACCOUNTS, PROJECT_DIR, API_BASE_URL

BASE_URL = API_BASE_URL


def load_template(account_key, template_name=None):
    """Carga template YAML para obtener page_id y link_url defaults."""
    # Si no se especifica template, buscar el de leads por default (por convención: <account>_leads.yaml)
    if template_name is None:
        template_name = f"{account_key}_leads" if account_key else "leads"

    template_path = PROJECT_DIR / "templates" / f"{template_name}.yaml"
    if not template_path.exists():
        return None

    # Parse simple YAML (solo campos top-level, evitar dependencia de pyyaml)
    data = {}
    with open(template_path) as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            # Solo campos sin indentación (top-level)
            if line[0] == " " or line[0] == "\t":
                continue
            key, _, value = stripped.partition(":")
            # Re-join con ":" en caso de URLs (https://...)
            value = value.strip().strip('"').strip("'")
            if value:
                data[key.strip()] = value
    return data


def create_creative(page_id, video_files=None, video_urls=None, image_files=None, image_urls=None,
                    bodies=None, titles=None, cta="CONTACT_US", link_url="", name=""):
    """Crea creative via CLI y retorna el ID. Soporta single y DCO (múltiples assets)."""
    videos = (video_files or []) + (video_urls or [])
    images = (image_files or []) + (image_urls or [])
    bodies = bodies or []
    titles = titles or []

    is_dco = len(videos) > 1 or len(images) > 1 or len(bodies) > 1 or len(titles) > 1

    args = ["creative", "create", "--name", name or "Creative", "--page-id", page_id]

    if link_url:
        args.extend(["--link-url", link_url])
    if cta:
        args.extend(["--call-to-action", cta])

    if is_dco:
        # DCO: usa flags plurales (--videos, --bodies, --titles)
        for v in videos:
            args.extend(["--videos", v])
        for img in images:
            args.extend(["--images", img])
        for b in bodies:
            args.extend(["--bodies", b])
        for t in titles:
            args.extend(["--titles", t])
    else:
        # Single creative: usa flags singulares
        # Nota: --link-url no es compatible con --video en single mode
        if videos:
            args.extend(["--video", videos[0]])
            # Remover --link-url si se agregó (incompatible con video_data)
            if "--link-url" in args:
                idx = args.index("--link-url")
                args.pop(idx)  # --link-url
                args.pop(idx)  # value
        elif images:
            args.extend(["--image", images[0]])
        if bodies:
            args.extend(["--body", bodies[0]])
        if titles:
            args.extend(["--title", titles[0]])

    result = run_meta_with_retry(*args)
    if isinstance(result, dict) and "id" in result:
        return result["id"]
    elif isinstance(result, list) and result and "id" in result[0]:
        return result[0]["id"]
    return result


def get_video_thumbnail(video_id, access_token):
    """Obtiene la URL del thumbnail generado por Meta para un video."""
    url = f"{BASE_URL}/{video_id}/thumbnails"
    params = {"access_token": access_token}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json().get("data", [])
        if data:
            return data[0].get("uri") or data[0].get("url")
    return None


def _build_placement_customization(video_ids, bodies, titles, descriptions, link_url, cta):
    """Construye asset_feed_spec con placement asset customization (estilo Andromeda).

    1 video  → mismo video en ambas reglas (feed-square + catch-all vertical).
    2 videos → primero a feed/instream/stream, segundo a catch-all.
    """
    if len(video_ids) > 2:
        sys.stderr.write("Error: --placement-customization soporta máximo 2 video-ids (1=ambos placements, 2=feed+catch-all).\n")
        sys.exit(1)

    L_VID_FEED, L_VID_OTHER = "ph_vid_feed", "ph_vid_other"
    L_BODY_FEED, L_BODY_OTHER = "ph_body_feed", "ph_body_other"
    L_TITLE_FEED, L_TITLE_OTHER = "ph_title_feed", "ph_title_other"
    L_LINK_FEED, L_LINK_OTHER = "ph_link_feed", "ph_link_other"
    L_DESC_FEED, L_DESC_OTHER = "ph_desc_feed", "ph_desc_other"

    if len(video_ids) == 1:
        videos_spec = [{"video_id": video_ids[0],
                        "adlabels": [{"name": L_VID_FEED}, {"name": L_VID_OTHER}]}]
    else:
        videos_spec = [
            {"video_id": video_ids[0], "adlabels": [{"name": L_VID_FEED}]},
            {"video_id": video_ids[1], "adlabels": [{"name": L_VID_OTHER}]},
        ]

    both_body = [{"name": L_BODY_FEED}, {"name": L_BODY_OTHER}]
    both_title = [{"name": L_TITLE_FEED}, {"name": L_TITLE_OTHER}]
    both_link = [{"name": L_LINK_FEED}, {"name": L_LINK_OTHER}]
    both_desc = [{"name": L_DESC_FEED}, {"name": L_DESC_OTHER}]

    rule1 = {
        "customization_spec": {
            "age_min": 13, "age_max": 65,
            "publisher_platforms": ["facebook", "instagram"],
            "facebook_positions": ["feed", "instream_video"],
            "instagram_positions": ["stream"],
        },
        "video_label": {"name": L_VID_FEED},
        "body_label": {"name": L_BODY_FEED},
        "link_url_label": {"name": L_LINK_FEED},
        "priority": 1,
    }
    rule2 = {
        "customization_spec": {"age_min": 13, "age_max": 65},
        "video_label": {"name": L_VID_OTHER},
        "body_label": {"name": L_BODY_OTHER},
        "link_url_label": {"name": L_LINK_OTHER},
        "priority": 2,
    }
    if titles:
        rule1["title_label"] = {"name": L_TITLE_FEED}
        rule2["title_label"] = {"name": L_TITLE_OTHER}
    if descriptions:
        rule1["description_label"] = {"name": L_DESC_FEED}
        rule2["description_label"] = {"name": L_DESC_OTHER}

    afs = {
        "videos": videos_spec,
        "bodies": [{"text": b, "adlabels": both_body} for b in bodies],
        "call_to_action_types": [cta.upper()],
        "ad_formats": ["AUTOMATIC_FORMAT"],
        "optimization_type": "PLACEMENT",
        "asset_customization_rules": [rule1, rule2],
    }
    if titles:
        afs["titles"] = [{"text": t, "adlabels": both_title} for t in titles]
    if descriptions:
        # Meta no permite múltiples descriptions por regla. Si hay >1, usamos solo
        # la primera y emitimos warning para que el usuario lo sepa.
        if len(descriptions) > 1:
            sys.stderr.write(f"  WARN: placement_customization solo acepta 1 description por regla. Usando solo: '{descriptions[0]}'\n")
        afs["descriptions"] = [{"text": descriptions[0], "adlabels": both_desc}]
    if link_url:
        afs["link_urls"] = [{"website_url": link_url, "adlabels": both_link}]
    return afs


def _build_basic_asset_feed(video_ids, bodies, titles, descriptions, link_url, cta):
    """Construye asset_feed_spec sin placement customization (DCO simple)."""
    afs = {
        "videos": [{"video_id": vid} for vid in video_ids],
        "bodies": [{"text": b} for b in bodies],
        "call_to_action_types": [cta.upper()],
        "ad_formats": ["AUTOMATIC_FORMAT"],
    }
    if titles:
        afs["titles"] = [{"text": t} for t in titles]
    if descriptions:
        afs["descriptions"] = [{"text": d} for d in descriptions]
    if link_url:
        afs["link_urls"] = [{"website_url": link_url}]
    return afs


def create_creative_with_video_id(
    video_ids, page_id, bodies, titles, cta, link_url, name, ad_account_id,
    descriptions=None, message_extensions=None, placement_customization=False,
    instagram_user_id=None, page_welcome_message=None, url_tags=None,
):
    """Crea creative via Graph API directa usando video_id(s) ya procesados.

    Modos:
    - placement_customization=True → asset_feed_spec con asset_customization_rules
      (replica patrón Andromeda: feed-square + catch-all vertical, copy DCO dentro).
    - Multi-asset DCO o feature opcional (descriptions/message_extensions) →
      asset_feed_spec sin reglas.
    - Single video + 1 body + 1 title sin extras → object_story_spec.video_data simple.

    page_welcome_message: dict con la estructura del template de WhatsApp welcome
    (ver templates/whatsapp_welcome.example.json). Para ads CTWA. Se serializa a JSON
    string e inyecta en el lugar correcto según el modo:
    - asset_feed_spec mode: asset_feed_spec.additional_data.page_welcome_message
    - video_data mode: object_story_spec.video_data.page_welcome_message
    """
    access_token = get_access_token()
    url = f"{BASE_URL}/{ad_account_id}/adcreatives"

    thumbnail_url = get_video_thumbnail(video_ids[0], access_token)
    sys.stderr.write(f"  Thumbnail: {'OK' if thumbnail_url else 'no disponible'}\n")

    object_story_spec = {"page_id": page_id}
    if instagram_user_id:
        object_story_spec["instagram_user_id"] = instagram_user_id

    needs_asset_feed = (
        placement_customization
        or descriptions
        or message_extensions
        or len(video_ids) > 1
        or len(bodies) > 1
        or len(titles) > 1
    )

    if not needs_asset_feed:
        # Single creative con video_data — más liviano cuando no hay features extra
        video_data = {
            "video_id": video_ids[0],
            "message": bodies[0] if bodies else "",
            "title": titles[0] if titles else "",
            "call_to_action": {
                "type": cta.upper(),
                "value": {"link": link_url} if link_url else {},
            },
        }
        if thumbnail_url:
            video_data["image_url"] = thumbnail_url
        if page_welcome_message:
            video_data["page_welcome_message"] = json.dumps(page_welcome_message, ensure_ascii=False)
        object_story_spec["video_data"] = video_data
        payload = {
            "name": name,
            "object_story_spec": json.dumps(object_story_spec),
            "access_token": access_token,
        }
    else:
        if placement_customization:
            asset_feed = _build_placement_customization(video_ids, bodies, titles, descriptions, link_url, cta)
        else:
            asset_feed = _build_basic_asset_feed(video_ids, bodies, titles, descriptions, link_url, cta)
        if message_extensions:
            asset_feed["message_extensions"] = list(message_extensions)
        if page_welcome_message:
            asset_feed.setdefault("additional_data", {})["page_welcome_message"] = json.dumps(page_welcome_message, ensure_ascii=False)
        payload = {
            "name": name,
            "object_story_spec": json.dumps(object_story_spec),
            "asset_feed_spec": json.dumps(asset_feed),
            "access_token": access_token,
        }

    if url_tags:
        payload["url_tags"] = url_tags

    response = requests.post(url, data=payload)

    if response.status_code != 200:
        sys.stderr.write(f"  Error API ({response.status_code}): {response.text}\n")
        sys.exit(1)

    return response.json().get("id")


def create_creative_with_image_hash(
    image_hashes, page_id, bodies, titles, cta, link_url, name, ad_account_id,
    descriptions=None, instagram_user_id=None, url_tags=None,
):
    """Crea creative reusando image_hash(es) ya en la library del ad account.

    Single hash + 1 body + 1 title → object_story_spec.link_data (no DCO).
    Multi hash o multi-variante → asset_feed_spec.images (DCO; requiere adset
    is_dynamic_creative=true). Ver docs/api-gotchas.md #5 y #8.
    """
    access_token = get_access_token()
    url = f"{BASE_URL}/{ad_account_id}/adcreatives"

    object_story_spec = {"page_id": page_id}
    if instagram_user_id:
        object_story_spec["instagram_user_id"] = instagram_user_id

    needs_asset_feed = (
        len(image_hashes) > 1
        or len(bodies) > 1
        or len(titles) > 1
        or (descriptions and len(descriptions) > 1)
    )

    if not needs_asset_feed:
        link_data = {
            "image_hash": image_hashes[0],
            "message": bodies[0] if bodies else "",
            "name": titles[0] if titles else "",
            "link": link_url or "",
            "call_to_action": {
                "type": cta.upper(),
                "value": {"link": link_url} if link_url else {},
            },
        }
        if descriptions:
            link_data["description"] = descriptions[0]
        object_story_spec["link_data"] = link_data
        payload = {
            "name": name,
            "object_story_spec": json.dumps(object_story_spec),
            "access_token": access_token,
        }
    else:
        afs = {
            "images": [{"hash": h} for h in image_hashes],
            "bodies": [{"text": b} for b in bodies],
            "call_to_action_types": [cta.upper()],
            "ad_formats": ["AUTOMATIC_FORMAT"],
        }
        if titles:
            afs["titles"] = [{"text": t} for t in titles]
        if descriptions:
            afs["descriptions"] = [{"text": d} for d in descriptions]
        if link_url:
            afs["link_urls"] = [{"website_url": link_url}]
        payload = {
            "name": name,
            "object_story_spec": json.dumps(object_story_spec),
            "asset_feed_spec": json.dumps(afs),
            "access_token": access_token,
        }

    if url_tags:
        payload["url_tags"] = url_tags

    response = requests.post(url, data=payload)
    if response.status_code != 200:
        sys.stderr.write(f"  Error API ({response.status_code}): {response.text}\n")
        sys.exit(1)
    return response.json().get("id")


def run_meta_with_retry(*args, max_retries=4, wait_seconds=30):
    """Ejecuta meta CLI con retry para errores de video processing."""
    acct = get_account()
    cmd = ["meta", "--output", "json", "ads", "--ad-account-id", acct["ad_account_id"], *args]

    for attempt in range(max_retries):
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_DIR)

        if result.returncode == 0:
            return json.loads(result.stdout)

        # Si el error es de video procesando, retry
        if "se está procesando" in result.stderr or "still being processed" in result.stderr:
            if attempt < max_retries - 1:
                sys.stderr.write(f"    Video procesando... reintento en {wait_seconds}s ({attempt+1}/{max_retries})\n")
                time.sleep(wait_seconds)
                continue

        # Otro error: fallar
        sys.stderr.write(f"Error (exit {result.returncode}): {result.stderr.strip()}\n")
        sys.exit(1)

    sys.stderr.write("Error: Video no terminó de procesar después de todos los reintentos.\n")
    sys.exit(1)


def create_ad(adset_id, creative_id, name, status="PAUSED"):
    """Crea ad dentro del adset con el creative."""
    from helpers import run_meta
    result = run_meta(
        "ad", "create", adset_id,
        "--creative-id", creative_id,
        "--name", name,
        "--status", status,
    )
    if isinstance(result, dict) and "id" in result:
        return result["id"]
    elif isinstance(result, list) and result and "id" in result[0]:
        return result[0]["id"]
    return result


def main():
    parser = argparse.ArgumentParser(description="Crear ad en adset existente (PAUSED)")
    parser.add_argument("--account", default=None, help="Nombre de cuenta declarado en accounts.yaml")
    parser.add_argument("--adset-id", required=True, help="ID del adset existente (obligatorio)")
    parser.add_argument("--template", default=None, help="Template para defaults (ej: leads)")
    parser.add_argument("--video-id", action="append", default=None, help="Video ID ya subido a Meta (repetir para DCO). Usar upload_video.py primero.")
    parser.add_argument("--video-file", action="append", default=None, help="Path a video local (repetir para DCO con múltiples videos)")
    parser.add_argument("--video-url", action="append", default=None, help="URL de video (repetir para DCO)")
    parser.add_argument("--image-file", action="append", default=None, help="Path a imagen local (repetir para DCO)")
    parser.add_argument("--image-url", action="append", default=None, help="URL de imagen (repetir para DCO)")
    parser.add_argument("--image-hash", action="append", default=None, help="image_hash de imagen ya en la library (repetir para DCO). Ver docs/api-gotchas.md #8.")
    parser.add_argument("--body", action="append", required=True, help="Texto del ad (repetir para variaciones DCO)")
    parser.add_argument("--title", action="append", default=None, help="Título del ad (repetir para variaciones DCO)")
    parser.add_argument("--description", action="append", default=None, help="Description text (repetir para variaciones)")
    parser.add_argument("--cta", default="CONTACT_US", help="Call to action (CONTACT_US, WHATSAPP_MESSAGE, etc)")
    parser.add_argument("--link-url", default=None, help="URL de destino")
    parser.add_argument("--url-tags", default=None, help="UTMs / url_tags. Soporta macros Meta como {{campaign.name}}, {{ad.name}}. Ej: 'utm_source=fb&utm_campaign={{campaign.name}}&utm_content={{ad.name}}'. Ver docs/api-gotchas.md #9.")
    parser.add_argument("--name", required=True, help="Nombre del ad")
    parser.add_argument("--whatsapp-addon", action="store_true", help="Browser CTA add-on de WhatsApp (asset_feed_spec.message_extensions)")
    parser.add_argument("--placement-customization", action="store_true", help="Replicar patrón Andromeda: asset_customization_rules con feed-square + catch-all vertical (requiere --video-id, máx 2)")
    parser.add_argument("--welcome-template", default=None, help="Path a archivo JSON con WhatsApp welcome message template. Para ads CTWA.")
    parser.add_argument("--yes", action="store_true", help="Skip confirmación")

    args = parser.parse_args()

    # Resolver cuenta
    acct = get_account(args.account)
    account_key = args.account
    currency = acct["currency"]

    # Resolver defaults del template
    template = load_template(account_key, args.template)
    page_id = acct["page_id"]
    link_url = args.link_url
    if not link_url and template:
        link_url = template.get("link_url", "")

    # Consolidar assets
    video_ids = args.video_id or []
    video_files = args.video_file or []
    video_urls = args.video_url or []
    image_files = args.image_file or []
    image_urls = args.image_url or []
    image_hashes = args.image_hash or []
    all_videos = video_files + video_urls
    all_images = image_files + image_urls
    bodies = args.body  # ya es lista por action="append"
    titles = args.title or []
    descriptions = args.description or []
    message_extensions = [{"type": "whatsapp"}] if args.whatsapp_addon else []
    welcome_template = None
    if args.welcome_template:
        with open(args.welcome_template) as f:
            welcome_template = json.load(f)
        # strip our local _comment field if present (Meta no lo necesita)
        welcome_template.pop("_comment", None)

    use_api_direct = bool(video_ids or image_hashes)  # Si hay asset pre-existente, usar Graph API directa

    has_creative = bool(video_ids or all_videos or all_images or image_hashes)
    if not has_creative:
        sys.stderr.write("Error: Se requiere al menos uno de --video-id, --video-file, --video-url, --image-file, --image-url, --image-hash\n")
        sys.exit(1)
    if image_hashes and (video_ids or all_videos or all_images):
        sys.stderr.write("Error: --image-hash no se mezcla con otros tipos de asset en el mismo ad.\n")
        sys.exit(1)

    if args.placement_customization and not video_ids:
        sys.stderr.write("Error: --placement-customization requiere --video-id (no funciona con --video-file por ahora).\n")
        sys.exit(1)

    all_video_sources = video_ids + all_videos
    is_dco = len(all_video_sources) > 1 or len(all_images) > 1 or len(bodies) > 1 or len(titles) > 1

    # Preview
    sys.stderr.write(f"\n  CREAR AD (PAUSED):\n")
    sys.stderr.write(f"  {'─'*50}\n")
    sys.stderr.write(f"  Cuenta:    {acct['label']}\n")
    sys.stderr.write(f"  Ad Set:    {args.adset_id} (existente)\n")
    if args.placement_customization:
        modo = f"Placement customization ({len(video_ids)} video{'s' if len(video_ids)>1 else ''})"
    elif is_dco:
        modo = "DCO (múltiples assets)"
    else:
        modo = "Single creative"
    sys.stderr.write(f"  Modo:      {modo}\n")
    if use_api_direct:
        sys.stderr.write(f"  Método:    Graph API directa (video pre-subido)\n")
    for vid in video_ids:
        sys.stderr.write(f"  Video ID:  {vid}\n")
    for v in all_videos:
        sys.stderr.write(f"  Video:     {v}\n")
    for img in all_images:
        sys.stderr.write(f"  Imagen:    {img}\n")
    for b in bodies:
        sys.stderr.write(f"  Body:      {b[:60]}{'...' if len(b) > 60 else ''}\n")
    for t in titles:
        sys.stderr.write(f"  Title:     {t}\n")
    if not titles:
        sys.stderr.write(f"  Title:     (ninguno)\n")
    for d in descriptions:
        sys.stderr.write(f"  Descript.: {d}\n")
    sys.stderr.write(f"  CTA:       {args.cta}\n")
    sys.stderr.write(f"  Link:      {link_url or '(ninguno)'}\n")
    if message_extensions:
        sys.stderr.write(f"  WA addon:  ON (browser CTA)\n")
    if welcome_template:
        tid = welcome_template.get("template_id","?")
        sys.stderr.write(f"  WA welcome template: {args.welcome_template} (template_id={tid})\n")
    sys.stderr.write(f"  Nombre:    {args.name}\n")
    sys.stderr.write(f"  Status:    PAUSED\n")
    sys.stderr.write(f"  {'─'*50}\n\n")

    # Confirmar
    if not args.yes:
        response = input("  Proceder? [y/N]: ").strip().lower()
        if response != "y":
            sys.stderr.write("  Cancelado.\n")
            sys.exit(0)

    # 1. Crear creative
    sys.stderr.write("  Creando creative...\n")
    if image_hashes:
        creative_id = create_creative_with_image_hash(
            image_hashes=image_hashes,
            page_id=page_id,
            bodies=bodies,
            titles=titles,
            cta=args.cta,
            link_url=link_url,
            name=f"Creative - {args.name}",
            ad_account_id=acct["ad_account_id"],
            descriptions=descriptions,
            instagram_user_id=acct.get("instagram_user_id"),
            url_tags=args.url_tags,
        )
    elif use_api_direct:
        creative_id = create_creative_with_video_id(
            video_ids=video_ids,
            page_id=page_id,
            bodies=bodies,
            titles=titles,
            cta=args.cta,
            link_url=link_url,
            name=f"Creative - {args.name}",
            ad_account_id=acct["ad_account_id"],
            descriptions=descriptions,
            message_extensions=message_extensions,
            placement_customization=args.placement_customization,
            instagram_user_id=acct.get("instagram_user_id"),
            page_welcome_message=welcome_template,
            url_tags=args.url_tags,
        )
    else:
        if descriptions or message_extensions or args.placement_customization:
            sys.stderr.write("Error: --description, --whatsapp-addon, --placement-customization requieren --video-id (no soportados con --video-file/--video-url por el CLI path).\n")
            sys.exit(1)
        creative_id = create_creative(
            page_id=page_id,
            video_files=video_files,
            video_urls=video_urls,
            image_files=image_files,
            image_urls=image_urls,
            bodies=bodies,
            titles=titles,
            cta=args.cta,
            link_url=link_url,
            name=f"Creative - {args.name}",
        )
    sys.stderr.write(f"  Creative ID: {creative_id}\n")

    # 2. Crear ad
    sys.stderr.write("  Creando ad...\n")
    ad_id = create_ad(
        adset_id=args.adset_id,
        creative_id=str(creative_id),
        name=args.name,
    )
    sys.stderr.write(f"  Ad ID: {ad_id}\n")
    sys.stderr.write(f"\n  Listo. Ad creado en PAUSED.\n")
    sys.stderr.write(f"  Activar: meta ads ad update {ad_id} --status ACTIVE\n\n")

    # JSON a stdout
    print(json.dumps({
        "ad_id": ad_id,
        "creative_id": creative_id,
        "adset_id": args.adset_id,
        "name": args.name,
        "status": "PAUSED",
    }, indent=2))


if __name__ == "__main__":
    main()
