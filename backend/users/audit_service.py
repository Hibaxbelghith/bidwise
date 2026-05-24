import logging

from .models import AuditLog

logger = logging.getLogger(__name__)


# ── Internal helper ─────────────────────────────────────────────────────────

def _record(*, actor, target, action: AuditLog.Action, metadata: dict) -> None:
    """
    Persist one AuditLog row.
    Swallows any exception so a logging failure never surfaces to the user.
    """
    try:
        AuditLog.objects.create(
            actor=actor,
            target=target,
            action=action,
            metadata=metadata,
        )
        logger.info(
            "audit | action=%s actor=%s target=%s",
            action,
            actor.email if actor else "?",
            target.email if target else "?",
        )
    except Exception:
        logger.exception(
            "audit | FAILED to write log | action=%s actor=%s target=%s",
            action,
            actor.email if actor else "?",
            target.email if target else "?",
        )


# ── Public API — one function per action ─────────────────────────────────────

def log_suspend(*, actor, target, reason: str, detail: str = "") -> None:
    """
    Called after a user has been successfully suspended.

    Args:
        actor:  Admin Utilisateur performing the action.
        target: Utilisateur being suspended.
        reason: Canonical reason key (spam / abuse / fraud / other).
        detail: Optional free-text detail from the admin.
    """
    metadata = {"reason": reason}
    if detail:
        metadata["detail"] = detail
    _record(
        actor=actor,
        target=target,
        action=AuditLog.Action.SUSPEND,
        metadata=metadata,
    )


def log_reactivate(*, actor, target) -> None:
    """
    Called after a suspended user has been successfully reactivated.
    """
    _record(
        actor=actor,
        target=target,
        action=AuditLog.Action.REACTIVATE,
        metadata={},
    )


def log_toggle_admin(*, actor, target, granted: bool) -> None:
    """
    Called after admin privilege has been granted or revoked.

    Args:
        granted: True if admin was granted, False if revoked.
    """
    _record(
        actor=actor,
        target=target,
        action=AuditLog.Action.TOGGLE_ADMIN,
        metadata={"granted": granted},
    )


def log_toggle_active(*, actor, target, activated: bool) -> None:
    """
    Called after account active status has been toggled.

    Args:
        activated: True if account was activated, False if deactivated.
    """
    _record(
        actor=actor,
        target=target,
        action=AuditLog.Action.TOGGLE_ACTIVE,
        metadata={"activated": activated},
    )