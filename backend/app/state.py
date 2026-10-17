"""Process-wide stores shared by the routers (single-process hackathon deployment)."""
from .approval_store import ApprovalStore

# Immutable solve snapshots, stored replays and atomic approval (issue #8). The solve router writes it.
approvals = ApprovalStore()
