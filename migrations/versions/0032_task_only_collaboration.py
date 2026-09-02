"""Retire legacy multi-user collaboration storage in favor of Task membership.

Revision ID: 0032_task_only_collaboration
Revises: 0031_connector_upgrade_directives
Create Date: 2026-09-02
"""

from __future__ import annotations

import importlib.util
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

from alembic import op

revision: str = "0032_task_only_collaboration"
down_revision: str | None = "0031_connector_upgrade_directives"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The removed data was explicitly declared disposable. TaskMembership and
    # TaskAgentParticipant are the only multi-Human collaboration scope.
    for table_name in (
        "oidc_login_states",
        "organization_oidc_identities",
        "organization_oidc_providers",
        "organization_domains",
        "organization_invitations",
        "organization_agents",
        "organization_memberships",
        "organizations",
    ):
        op.drop_table(table_name)


def downgrade() -> None:
    # A rollback restores empty compatibility tables only; discarded rows cannot
    # be reconstructed. Reuse the exact historical table definitions so later
    # Alembic downgrades can continue safely to an older release.
    for filename in (
        "0008_organizations.py",
        "0013_organization_self_governance.py",
        "0014_organization_domain_verification.py",
        "0017_enterprise_oidc.py",
    ):
        module = _load_revision(filename)
        module.upgrade()


def _load_revision(filename: str) -> ModuleType:
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"agentpost_rollback_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load rollback schema from {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
