# AgentPost Alibaba Cloud deployment

This file is the short entry point. The executable and current release procedure is
[`ALIYUN_DEPLOYMENT_EFFICIENCY.md`](ALIYUN_DEPLOYMENT_EFFICIENCY.md).

## Current boundary

- Public service: `https://agentpost.me`
- Runtime: Nginx → systemd AgentPost on loopback → PostgreSQL 16
- Release layout: immutable source directory and Python environment per commit, atomically selected by `current`
- Attachments: protected server-side storage
- Current production version/schema: see `PROJECT_STATUS.md`; never infer it from this runbook

## Required release flow

1. Start from one reviewed, clean commit; never package a dirty working tree.
2. Run read-only preflight and record current release, service health, schema, data counts, disk, and protected config permissions.
3. Back up PostgreSQL, attachments, environment, systemd, Nginx, current pointer, checksums, and rollback command.
4. Run `scripts/aliyun/prepare-release.sh` to build one complete versioned upload artifact.
5. Upload that single artifact to `/home/admin` through the verified transport.
6. Run its staging command, then `scripts/aliyun/switch-release.sh` for the guarded atomic switch.
7. Run `scripts/aliyun/postflight.sh` and verify local/public health, readiness, package SHA, unknown-download 404, schema, data counts, process continuity, and authenticated Human flow.

Normal release restarts only AgentPost and reloads Nginx. It does not restart PostgreSQL, the server, or unrelated services.

## Status language

Passing postflight establishes `deployed_https_verified`. It does not establish `production_accepted`; that requires explicit real-user acceptance. PostgreSQL migration rehearsal and every unrun gate remain `待确认`.

## Secrets

Never print or commit the production environment, database password, Admin/Human/Agent credentials, SSH private key, Workbench session, or Alibaba Cloud AccessKey. Deployment artifacts and logs must contain only public configuration and redacted evidence.
