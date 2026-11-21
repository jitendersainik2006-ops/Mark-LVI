"""
actions/manage_instagram.py — J.A.R.V.I.S. Instagram AI Trading Reels Action Tool

Allows the AI assistant and user to:
- Connect and designate Instagram accounts.
- Autonomously research and generate educational AI trading Reels.
- Preview prepared Reels (video file, caption, hashtags, scheduled time).
- Enforce mandatory human approval prior to publication.
- Publish approved Reels via official Meta Graph API or supported assisted workflow.
"""

from typing import Optional
from core.instagram_manager import instagram_manager


def manage_instagram(parameters: dict, player=None, **_) -> str:
    action = str(parameters.get("action", "list_reels")).strip().lower()
    reel_id = str(parameters.get("reel_id", "")).strip()
    username = str(parameters.get("username", "")).strip()

    if action == "connect_account":
        if not username:
            return "Please provide a 'username' for the Instagram account."
        account_type = str(parameters.get("account_type", "creator")).strip().lower()
        designated = bool(parameters.get("designated_reels", False))
        token = str(parameters.get("access_token", "")).strip()
        ig_user_id = str(parameters.get("instagram_user_id", "")).strip()
        page_id = str(parameters.get("facebook_page_id", "")).strip()

        acc = instagram_manager.connect_account(
            username=username,
            account_type=account_type,
            designated_reels=designated,
            access_token=token,
            instagram_user_id=ig_user_id,
            facebook_page_id=page_id,
        )
        if player:
            player.write_log(f"[Instagram] Connected @{acc.username} (Reels: {acc.designated_reels})")
        return f"Instagram account @{acc.username} connected successfully (Type: {acc.account_type}, Designated Reels: {acc.designated_reels})."

    if action == "set_reels_account":
        if not username:
            return "Please provide the 'username' to designate for Reels."
        ok = instagram_manager.set_reels_account(username)
        if ok:
            if player:
                player.write_log(f"[Instagram] Designated Reels account: @{username}")
            return f"Instagram account @{username} is now the designated account for AI Trading Reels."
        return f"Account @{username} not found. Please connect it first with action='connect_account'."

    if action == "list_accounts":
        accs = instagram_manager.list_accounts()
        if not accs:
            return "No Instagram accounts currently connected. Use action='connect_account' to add one."
        lines = [f"Found {len(accs)} connected Instagram account(s):"]
        for a in accs:
            star = " ⭐ [DESIGNATED REELS]" if a.get("designated_reels") else ""
            lines.append(f"- @{a['username']} ({a.get('account_type')}){star}")
        return "\n".join(lines)

    if action == "generate_idea":
        niche = str(parameters.get("niche", "trading_and_discipline")).strip()
        custom = parameters.get("custom_prompt")
        idea = instagram_manager.generate_reel_idea(niche=niche, custom_prompt=custom)
        scenes_fmt = "\n".join([f"  Scene {s['scene_idx']} ({s['name']}) [{s['time_range']}]: {s['voiceover']}" for s in idea.get("scenes", [])])
        return (
            f"💡 Reel Concept & Script Generated:\n"
            f"Title: {idea.get('title')}\n"
            f"Niche: {idea.get('niche')}\n"
            f"Hook: {idea.get('hook')}\n"
            f"Points:\n" + "\n".join([f"  • {p}" for p in idea.get("points", [])]) + "\n"
            f"CTA: {idea.get('cta')}\n"
            f"Hashtags: {' '.join(idea.get('hashtags', []))}\n\n"
            f"Scene Breakdown:\n{scenes_fmt}"
        )

    if action == "create_reel":
        topic_id = parameters.get("topic_id")
        account_name = parameters.get("username")
        delay_hours = int(parameters.get("delay_hours", 2))
        audio_track = str(parameters.get("audio_track", "ambient_cyber"))
        voice_id = str(parameters.get("voice_id", "female"))
        subtitles_enabled = bool(parameters.get("subtitles_enabled", True))
        transition_type = str(parameters.get("transition_type", "crossfade"))
        custom_prompt = parameters.get("custom_prompt")

        post = instagram_manager.generate_trading_reel(
            topic_id=str(topic_id) if topic_id else None,
            account_username=str(account_name) if account_name else None,
            scheduled_delay_hours=delay_hours,
            audio_track=audio_track,
            voice_id=voice_id,
            subtitles_enabled=subtitles_enabled,
            transition_type=transition_type,
            custom_prompt=str(custom_prompt) if custom_prompt else None,
        )
        if player:
            player.write_log(f"[Reel] 🎬 Generated: '{post.title}' [waiting_for_approval]")

        return (
            f"🎬 AI Trading Reel prepared and awaiting your review!\n"
            f"Reel ID: {post.id}\n"
            f"Title: {post.title}\n"
            f"Designated Account: @{post.account_username}\n"
            f"Status: {post.status.upper()} (Explicit user approval required before publishing)\n"
            f"Video Preview: {post.video_path}\n"
            f"Audio Track: {post.audio_track} (Voice: {post.voice_id})\n"
            f"Subtitles: {'Enabled' if post.subtitles_enabled else 'Disabled'} | Transition: {post.transition_type}\n"
            f"Scenes: {len(post.scenes)} scene breakdown\n"
            f"Proposed Publication Time: {post.scheduled_time}\n"
            f"Full Caption & Hashtags:\n{post.caption}\n\n"
            f"Say 'approve reel {post.id}' or tap Approve on the dashboard to authorize publication."
        )

    if action == "preview_reel":
        if not reel_id:
            return "Please specify the 'reel_id' to preview."
        reel = instagram_manager.get_reel(reel_id)
        if not reel:
            return f"Reel '{reel_id}' not found."
        scenes_str = ""
        if reel.scenes:
            scenes_str = "\nScene Breakdown:\n" + "\n".join([f"  Scene {s.get('scene_idx', i+1)}: {s.get('voiceover', '')}" for i, s in enumerate(reel.scenes)])
        return (
            f"🎬 Reel Preview: '{reel.title}' (ID: {reel.id})\n"
            f"Status: {reel.status.upper()}\n"
            f"Account: @{reel.account_username}\n"
            f"Video Path: {reel.video_path}\n"
            f"Audio Track: {getattr(reel, 'audio_track', 'ambient_cyber')} | Subtitles: {getattr(reel, 'subtitles_enabled', True)}\n"
            f"Scheduled: {reel.scheduled_time}\n"
            f"{scenes_str}\n\n"
            f"Caption:\n{reel.caption}"
        )

    if action == "list_reels":
        filter_status = str(parameters.get("filter", "all")).strip().lower()
        reels = instagram_manager.list_reels(filter_status=filter_status, limit=10)
        if not reels:
            return f"No {filter_status} Reels found in ledger."
        lines = [f"Found {len(reels)} {filter_status} Reel(s):"]
        for r in reels:
            lines.append(f"- [{r['status'].upper()}] {r['title']} (ID: {r['id']}, Account: @{r['account_username']})")
        return "\n".join(lines)

    if action == "approve_reel":
        if not reel_id:
            return "Please specify the 'reel_id' to approve."
        ok = instagram_manager.approve_reel(reel_id)
        if ok:
            if player:
                player.write_log(f"[Reel] ✅ Approved {reel_id}")
            return f"Reel '{reel_id}' approved! You can now publish it with action='publish_reel'."
        return f"Could not approve Reel '{reel_id}'. It may not exist or is already published/cancelled."

    if action == "publish_reel":
        if not reel_id:
            return "Please specify the 'reel_id' to publish."
        result = instagram_manager.publish_reel(reel_id)
        if result.get("ok"):
            if player:
                player.write_log(f"[Reel] 🚀 Published {reel_id} ({result.get('method')})")
            return result.get("message", "Reel published successfully.")
        return f"Publish failed: {result.get('error', 'Unknown error')}"

    if action == "disconnect_account":
        if not username:
            return "Please provide the 'username' of the account to disconnect."
        ok = instagram_manager.disconnect_account(username)
        if ok:
            if player:
                player.write_log(f"[Instagram] Disconnected @{username}")
            return f"Instagram account @{username} disconnected successfully."
        return f"Account @{username} not found."

    if action == "save_draft":
        if not reel_id:
            return "Please specify the 'reel_id' to save as draft."
        ok = instagram_manager.save_draft(reel_id)
        if ok:
            return f"Reel '{reel_id}' saved as draft."
        return f"Could not find Reel '{reel_id}'."

    if action == "edit_reel":
        if not reel_id:
            return "Please specify the 'reel_id' to edit."
        title = parameters.get("title")
        caption = parameters.get("caption")
        tags = parameters.get("hashtags")
        sched = parameters.get("scheduled_time")
        res = instagram_manager.edit_reel(reel_id, title=title, caption=caption, hashtags=tags, scheduled_time=sched)
        if res:
            return f"Reel '{reel_id}' updated successfully."
        return f"Could not find Reel '{reel_id}'."

    if action == "delete_reel":
        if not reel_id:
            return "Please specify the 'reel_id' to delete."
        ok = instagram_manager.delete_reel(reel_id)
        if ok:
            return f"Reel '{reel_id}' deleted."
        return f"Could not find Reel '{reel_id}'."

    if action == "setup_guide":
        guide = instagram_manager.get_setup_guide()
        lines = [f"📖 {guide['title']}\n"]
        lines.append("Prerequisites:")
        for p in guide["prerequisites"]:
            lines.append(f"- {p}")
        lines.append("\nSteps:")
        for s in guide["steps"]:
            lines.append(f"{s['step']}. {s['title']}: {s['instruction']}")
        lines.append(f"\nℹ️ {guide['assisted_mode']}")
        return "\n".join(lines)

    if action == "posting_times":
        times = instagram_manager.get_recommended_posting_times(username)
        lines = [
            f"⏰ Recommended Posting Times for {times['account']} ({times['timezone']}):",
            f"Mode: {times['mode']} | Current Time: {times['current_time_ist']}\n"
        ]
        for w in times["recommended_windows"]:
            lines.append(f"• [{w['confidence']}% Confidence] {w['name']} — {w['time_range']}")
            lines.append(f"  Target: {w['target_audience']}")
            lines.append(f"  Why: {w['rationale']}")
            lines.append(f"  Status: {w['status']}\n")
        lines.append(f"Note: {times['note']}")
        return "\n".join(lines)

    if action == "content_calendar":
        days = int(parameters.get("days", 7))
        cal = instagram_manager.get_content_calendar(username, days=days)
        lines = [f"📅 7-Day Educational Trading Reels Calendar ({cal[0]['target_account']}):\n"]
        for item in cal:
            lines.append(f"• {item['day']} ({item['scheduled_time']}): '{item['title']}' [{item['approval_gate']}]")
            lines.append(f"  Slot: {item['slot_name']} ({item['confidence']}% confidence)")
            lines.append(f"  Hook: \"{item['hook']}\"")
            if item.get("reel_id"):
                lines.append(f"  Reel ID: {item['reel_id']} (Status: {item['status']})")
            lines.append("")
        return "\n".join(lines)

    if action == "view_analytics":
        an = instagram_manager.get_account_analytics(username)
        lines = [
            f"📊 Instagram Performance & Growth Analytics ({an['account']}):",
            f"Status: {an['status']} (Official Insights Active: {an['official_insights_active']})\n",
            f"Message: {an['message']}\n"
        ]
        if "production_summary" in an:
            ps = an["production_summary"]
            lines.append("Local Production Ledger:")
            lines.append(f"- Total Reels Created: {ps['total_reels_created']}")
            lines.append(f"- Reels Awaiting Approval: {ps['reels_awaiting_approval']}")
            lines.append(f"- Published via Assisted Workflow: {ps['reels_published_assisted']}")
        lines.append(f"\nSnapshots Tracked: {', '.join(an['snapshots_tracked'])}")
        return "\n".join(lines)

    if action == "weekly_report":
        rep = instagram_manager.generate_weekly_report(username)
        lines = [
            f"📈 Weekly Instagram Reels Performance Report ({rep['account']}):",
            f"Period: {rep['period']} | Generated: {rep['generated_at']}\n",
            "Metrics Breakdown:",
            f"- Total Reels Prepared: {rep['metrics']['total_reels_prepared']}",
            f"- Reels Published: {rep['metrics']['reels_published']}",
            f"- Awaiting User Review: {rep['metrics']['reels_waiting_review']}",
            f"- Official Insights Status: {rep['metrics']['insights_status']}\n",
            f"Strongest Observed Timing: {rep['strongest_observed_posting_window']}\n",
            "Top Educational Topics:",
        ]
        for t in rep["best_performing_educational_topics"]:
            lines.append(f"- {t}")
        lines.append("\nActionable Recommendations:")
        for r in rep["actionable_recommendations"]:
            lines.append(f"- {r}")
        return "\n".join(lines)

    if action == "regenerate_reel":
        if not reel_id:
            return "Please provide 'reel_id' to regenerate."
        custom = parameters.get("custom_prompt")
        audio_track = parameters.get("audio_track")
        trans = parameters.get("transition_type")
        res = instagram_manager.regenerate_reel(
            reel_id=reel_id,
            custom_prompt=str(custom) if custom else None,
            audio_track=str(audio_track) if audio_track else None,
            transition_type=str(trans) if trans else None,
        )
        if not res:
            return f"Reel '{reel_id}' not found."
        if player:
            player.write_log(f"[Reel] 🔄 Regenerated: {reel_id}")
        return (
            f"🔄 Reel '{reel_id}' successfully regenerated!\n"
            f"Title: {res.get('title')}\n"
            f"Status: WAITING_FOR_APPROVAL\n"
            f"Video Preview: {res.get('video_path')}\n"
            f"Cover Image: {res.get('cover_image_path')}\n"
            f"Audio Track: {res.get('audio_track')} | Transition: {res.get('transition_type')}\n"
            f"Say 'approve reel {reel_id}' or tap Approve on the dashboard to authorize publication."
        )

    if action == "validate_video":
        target_path = None
        if reel_id:
            r = instagram_manager.get_reel(reel_id)
            if r:
                target_path = r.video_path
        if not target_path:
            target_path = parameters.get("video_path")
        if not target_path:
            return "Please provide 'reel_id' or 'video_path' to validate."
        rep = instagram_manager.validate_reel_video(target_path)
        lines = [f"📋 Reel MP4 Technical Validation Report ({target_path}):\n"]
        lines.append(f"• Overall Status: {'✅ PASSED (Instagram-Ready)' if rep['is_valid'] else '⚠️ VALIDATION NOTICE'}")
        lines.append(f"• Resolution: {rep.get('width', 0)}x{rep.get('height', 0)} (Aspect Ratio: {rep.get('aspect_ratio', 0)} {'[9:16 Vertical]' if rep.get('is_9_16_vertical') else '[Non-Standard]'})")
        lines.append(f"• Duration: {rep.get('duration_seconds', 0)}s (Instagram Limit: 3s - 900s)")
        lines.append(f"• File Size: {rep.get('file_size', 0):,} bytes")
        lines.append(f"• Video Codec: {rep.get('video_codec', 'unknown')} @ {rep.get('fps', 0)} fps")
        lines.append(f"• Audio Stream: {'Present' if rep.get('has_audio') else 'None'} ({rep.get('audio_codec')}, {rep.get('audio_sample_rate')}Hz)")
        if rep.get("checks_passed"):
            lines.append("\nChecks Passed:")
            for c in rep["checks_passed"]:
                lines.append(f"  ✓ {c}")
        if rep.get("warnings"):
            lines.append("\nWarnings:")
            for w in rep["warnings"]:
                lines.append(f"  ⚠️ {w}")
        return "\n".join(lines)

    if action == "generate_caption":
        niche = str(parameters.get("niche", "trading_and_discipline")).strip()
        custom = parameters.get("custom_prompt")
        lang = str(parameters.get("language", "all")).strip().lower()
        idea = instagram_manager.generate_reel_idea(niche=niche, custom_prompt=custom)
        multi = instagram_manager.generate_multilingual_captions(idea)
        if lang == "hindi":
            return f"📝 Hindi Caption (Devanagari):\n\n{multi['hindi']}"
        elif lang in ("hinglish", "roman"):
            return f"📝 Hinglish Caption (Roman Hindi):\n\n{multi['hinglish']}"
        elif lang == "english":
            return f"📝 English Caption:\n\n{multi['english']}"
        else:
            return (
                f"📝 Multilingual Reel Captions for '{idea['title']}':\n\n"
                f"--- [1. ENGLISH] ---\n{multi['english']}\n\n"
                f"--- [2. HINDI / देवनागरी] ---\n{multi['hindi']}\n\n"
                f"--- [3. HINGLISH] ---\n{multi['hinglish']}"
            )

    if action == "ready_for_upload":
        if not reel_id:
            return "Please provide 'reel_id' to prepare for upload."
        reel = instagram_manager.get_reel(reel_id)
        if not reel:
            return f"Reel '{reel_id}' not found."
        if reel.status != "approved":
            return f"Security check: Reel '{reel_id}' has status '{reel.status}'. Please approve it first ('approve_reel')."
        return (
            f"🚀 Reel '{reel_id}' is APPROVED and 100% READY FOR UPLOAD!\n"
            f"Target Account: @{reel.account_username}\n"
            f"Video MP4 File: {reel.video_path}\n"
            f"Cover Image: {getattr(reel, 'cover_image_path', 'Auto-generated')}\n"
            f"Caption & Hashtags:\n{reel.caption}\n\n"
            f"Trigger direct upload with action='publish_reel' (Meta Graph API) or tap Assisted Download on the dashboard."
        )

    return f"Unknown Instagram action: '{action}'. Use connect_account, disconnect_account, set_reels_account, list_accounts, create_reel, preview_reel, list_reels, approve_reel, publish_reel, cancel_reel, save_draft, edit_reel, delete_reel, regenerate_reel, validate_video, generate_caption, ready_for_upload, posting_times, content_calendar, view_analytics, weekly_report, or setup_guide."


TOOL = {
    "name": "manage_instagram",
    "tier": "core",
    "brief": "Manage Instagram accounts, research and create AI Trading Reels, preview, approve, regenerate, and publish.",
    "description": (
        "Automates educational AI Trading Reels on Instagram for @mentos_life_gym. "
        "Understands voice and chat commands in English, Hindi, and Hinglish such as: "
        "'ek nayi Reel banao', 'gym motivation par Reel banao', 'is Reel ke liye caption aur hashtags likho', "
        "'Reel ka preview dikhao', 'is Reel ko regenerate karo', 'approved Reel upload karne ke liye ready karo'. "
        "Actions: "
        "action='create_reel' (creates vertical 9:16 MP4 video, voiceover, cover image, and captions); "
        "action='preview_reel' (shows video, scene plan, captions); "
        "action='approve_reel' (grants mandatory human approval); "
        "action='regenerate_reel' (re-renders video, audio, and cover for draft); "
        "action='validate_video' (checks 9:16 aspect ratio, H.264/AAC codecs, duration); "
        "action='generate_caption' (generates English, Hindi, and Hinglish captions); "
        "action='ready_for_upload' (prepares final video and caption package); "
        "action='publish_reel' (publishes approved Reel via Meta Graph API or assisted mode)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "create_reel | preview_reel | approve_reel | publish_reel | cancel_reel | list_reels | regenerate_reel | validate_video | generate_caption | ready_for_upload | connect_account | set_reels_account | list_accounts"
            },
            "reel_id": {
                "type": "STRING",
                "description": "Unique ID of the Reel for preview, approve, publish, or cancel"
            },
            "username": {
                "type": "STRING",
                "description": "Instagram handle for connect_account or set_reels_account"
            },
            "topic_id": {
                "type": "STRING",
                "description": "Optional specific trading topic ID for create_reel"
            },
            "delay_hours": {
                "type": "INTEGER",
                "description": "Proposed delay hours before publication (default: 2)"
            },
            "filter": {
                "type": "STRING",
                "description": "Filter for list_reels: all | waiting_for_approval | approved | published"
            },
            "account_type": {
                "type": "STRING",
                "description": "creator | business | personal"
            },
            "designated_reels": {
                "type": "BOOLEAN",
                "description": "Whether to designate this account for Reels"
            },
            "access_token": {
                "type": "STRING",
                "description": "Official Meta Graph API access token"
            },
            "instagram_user_id": {
                "type": "STRING",
                "description": "Instagram Business/Creator User ID"
            },
            "facebook_page_id": {
                "type": "STRING",
                "description": "Connected Facebook Page ID"
            }
        },
        "required": ["action"]
    },
    "handler": manage_instagram,
}
