"""
Core deduplication engine with blocking and fuzzy matching.

This is the heart of the duplicate detection system.
"""
from collections import defaultdict
from typing import Optional
from rapidfuzz import fuzz
from datetime import datetime

from app.models.contact import Contact, DuplicateSet


class DuplicateDetector:
    """
    Detects duplicate contacts using blocking and fuzzy matching.

    Blocking reduces O(n²) comparisons to manageable chunks by grouping
    records that could potentially be duplicates.
    """

    def __init__(self, confidence_threshold: float = 0.90):
        """
        Initialize detector.

        Args:
            confidence_threshold: Minimum similarity (0-1) to consider a match
        """
        self.confidence_threshold = confidence_threshold

    def create_blocks(self, contacts: list[Contact]) -> dict[str, list[Contact]]:
        """
        Group contacts into blocks for efficient comparison.

        Each contact may appear in multiple blocks to ensure recall.
        Blocking keys:
        - Email domain (@acme.com)
        - Name prefix (first 3 chars)
        - Exact email (if present)

        Args:
            contacts: List of all contacts

        Returns:
            Dict mapping block keys to lists of contacts
        """
        blocks: dict[str, list[Contact]] = defaultdict(list)

        for contact in contacts:
            # Block by email domain
            if contact.email_domain:
                blocks[f"domain:{contact.email_domain}"].append(contact)

            # Block by name prefix
            if contact.name_prefix:
                blocks[f"name:{contact.name_prefix}"].append(contact)

            # Block by exact email (for exact matches)
            if contact.normalized_email:
                blocks[f"email:{contact.normalized_email}"].append(contact)

        return blocks

    def find_duplicates(self, contacts: list[Contact]) -> list[DuplicateSet]:
        """
        Find all duplicate sets in the contact list.

        Algorithm:
        1. Create blocking groups
        2. Compare contacts within each block
        3. Merge overlapping duplicate sets
        4. Return unique duplicate sets

        Args:
            contacts: List of all contacts

        Returns:
            List of DuplicateSet objects
        """
        # Create blocks
        blocks = self.create_blocks(contacts)

        # Track which contact IDs we've already grouped
        grouped_ids: set[str] = set()

        # Track duplicate pairs with their confidence
        duplicate_pairs: dict[tuple[str, str], float] = {}

        # Compare within each block
        for block_key, block_contacts in blocks.items():
            # Skip small blocks (no duplicates possible)
            if len(block_contacts) < 2:
                continue

            # Compare all pairs within block
            for i, contact_a in enumerate(block_contacts):
                for contact_b in block_contacts[i + 1:]:
                    # Skip if already compared
                    pair_key = tuple(sorted([contact_a.id, contact_b.id]))
                    if pair_key in duplicate_pairs:
                        continue

                    # Calculate similarity
                    confidence = self._calculate_similarity(contact_a, contact_b)

                    if confidence >= self.confidence_threshold:
                        duplicate_pairs[pair_key] = confidence

        # Build duplicate sets from pairs using Union-Find
        duplicate_sets = self._build_duplicate_sets(contacts, duplicate_pairs)

        return duplicate_sets

    def _calculate_similarity(self, a: Contact, b: Contact) -> float:
        """
        Calculate overall similarity between two contacts.

        Weights:
        - Email: 60% (most reliable identifier)
        - Name: 40% (can have variations)

        Args:
            a: First contact
            b: Second contact

        Returns:
            Similarity score 0-1
        """
        scores = []
        weights = []

        # Email similarity (if both have emails)
        if a.normalized_email and b.normalized_email:
            if a.normalized_email == b.normalized_email:
                email_sim = 1.0
            else:
                # Fuzzy match for typos
                email_sim = fuzz.ratio(a.normalized_email, b.normalized_email) / 100
            scores.append(email_sim)
            weights.append(0.6)

        # Name similarity (if both have names)
        if a.normalized_name and b.normalized_name:
            # token_sort handles reordering (John Smith vs Smith John)
            name_sim = fuzz.token_sort_ratio(a.normalized_name, b.normalized_name) / 100
            scores.append(name_sim)
            weights.append(0.4)

        if not scores:
            return 0.0

        # Weighted average
        total_weight = sum(weights)
        weighted_sum = sum(s * w for s, w in zip(scores, weights))
        return weighted_sum / total_weight

    def _build_duplicate_sets(
        self,
        contacts: list[Contact],
        pairs: dict[tuple[str, str], float]
    ) -> list[DuplicateSet]:
        """
        Build duplicate sets from pairs using Union-Find algorithm.

        This groups all connected duplicates together, handling cases like:
        A matches B, B matches C → {A, B, C} are all duplicates

        Args:
            contacts: All contacts (for lookup)
            pairs: Dict of (id1, id2) -> confidence

        Returns:
            List of DuplicateSet objects
        """
        if not pairs:
            return []

        # Create contact lookup
        contact_map = {c.id: c for c in contacts}

        # Union-Find data structures
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])  # Path compression
            return parent[x]

        def union(x: str, y: str):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Union all duplicate pairs
        for (id1, id2) in pairs.keys():
            union(id1, id2)

        # Group by root
        groups: dict[str, list[str]] = defaultdict(list)
        for contact_id in parent.keys():
            root = find(contact_id)
            groups[root].append(contact_id)

        # Build DuplicateSet for each group with 2+ members
        duplicate_sets = []
        for group_ids in groups.values():
            if len(group_ids) < 2:
                continue

            # Get contacts
            group_contacts = [contact_map[cid] for cid in group_ids if cid in contact_map]
            if len(group_contacts) < 2:
                continue

            # Calculate average confidence for the group
            group_confidences = [
                conf for (id1, id2), conf in pairs.items()
                if id1 in group_ids or id2 in group_ids
            ]
            avg_confidence = sum(group_confidences) / len(group_confidences) if group_confidences else 0

            # Winner will be selected later by WinnerSelector
            # For now, just pick the first contact as placeholder winner
            duplicate_sets.append(DuplicateSet(
                confidence=avg_confidence * 100,  # Convert to 0-100
                winner=group_contacts[0],
                losers=group_contacts[1:],
                merged_preview={},  # Will be filled by FieldBlender
            ))

        return duplicate_sets


class WinnerSelector:
    """
    Selects the winning record from a duplicate set based on configured rules.
    """

    def __init__(self, rules: list[dict]):
        """
        Initialize with priority-ordered rules.

        Args:
            rules: List of {rule_type: str, field_name: str?, field_value: str?}
        """
        self.rules = rules

    def select_winner(self, contacts: list[Contact]) -> tuple[Contact, list[Contact]]:
        """
        Select the winning contact from a list of duplicates.

        Rules are applied in priority order until a single winner emerges.

        Args:
            contacts: List of duplicate contacts

        Returns:
            Tuple of (winner, losers)
        """
        candidates = contacts.copy()

        for rule in self.rules:
            if len(candidates) == 1:
                break

            rule_type = rule.get("rule_type")

            if rule_type == "oldest_created":
                candidates = self._filter_oldest_created(candidates)

            elif rule_type == "most_recent":
                candidates = self._filter_most_recent(candidates)

            elif rule_type == "most_associations":
                candidates = self._filter_most_associations(candidates)

            elif rule_type == "custom_field":
                field_name = rule.get("field_name")
                field_value = rule.get("field_value")
                if field_name and field_value:
                    candidates = self._filter_custom_field(candidates, field_name, field_value)

        # If still tied, use oldest created as final tiebreaker
        if len(candidates) > 1:
            candidates = self._filter_oldest_created(candidates)

        winner = candidates[0]
        losers = [c for c in contacts if c.id != winner.id]

        return winner, losers

    def _filter_oldest_created(self, contacts: list[Contact]) -> list[Contact]:
        """Keep contacts with the oldest created_at date."""
        dated = [(c, c.created_at or datetime.max) for c in contacts]
        min_date = min(d for _, d in dated)
        return [c for c, d in dated if d == min_date]

    def _filter_most_recent(self, contacts: list[Contact]) -> list[Contact]:
        """Keep contacts with the most recent updated_at date."""
        dated = [(c, c.updated_at or datetime.min) for c in contacts]
        max_date = max(d for _, d in dated)
        return [c for c, d in dated if d == max_date]

    def _filter_most_associations(self, contacts: list[Contact]) -> list[Contact]:
        """Keep contacts with the most associated records."""
        max_assoc = max(c.association_count for c in contacts)
        return [c for c in contacts if c.association_count == max_assoc]

    def _filter_custom_field(
        self,
        contacts: list[Contact],
        field_name: str,
        field_value: str
    ) -> list[Contact]:
        """Keep contacts where the custom field matches the specified value."""
        matching = [
            c for c in contacts
            if str(c.raw_properties.get(field_name, "")).lower() == field_value.lower()
        ]
        return matching if matching else contacts  # Fall through if no matches


class FieldBlender:
    """
    Blends fields from winner and losers to create the merged record.
    """

    # Fields that can be filled from losers if winner's is blank
    FILLABLE_FIELDS = [
        "phone", "company", "job_title",
        # Add more as needed
    ]

    def blend(self, winner: Contact, losers: list[Contact]) -> dict:
        """
        Create merged record preview.

        Strategy:
        - Winner's fields take precedence
        - Fill blank fields from losers (in order)

        Args:
            winner: The winning contact
            losers: List of losing contacts

        Returns:
            Dict representing the merged record
        """
        merged = winner.raw_properties.copy()

        # Fill gaps from losers
        for field in self.FILLABLE_FIELDS:
            if not merged.get(field):
                for loser in losers:
                    value = loser.raw_properties.get(field)
                    if value:
                        merged[field] = value
                        break

        return merged
