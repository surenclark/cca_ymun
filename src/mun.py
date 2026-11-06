import random
from itertools import groupby

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from dataclasses import dataclass, field, fields
from enum import Enum
from collections import defaultdict


class Organ(Enum):
    GA = "General Assembly"
    ECOSOC = "Economic and Social Council"
    RB = "Regional Bodies"
    SPECIALIZED = "Specialized Committees"
    CRISIS = "Crisis Committees"
    ADVANCED = "Advanced Committees"
    SPANISH = "Spanish Language Committees"
    PORTUGUES = "Portugues Committees"
    PORTSPEC = "Portugues Specialized"

    def __str__(self):
        return self.value


@dataclass(frozen=True)
class Committee:
    """Immutable committee data - just identity"""
    name: str
    organ: Organ

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name if isinstance(other, Committee) else False

    def __repr__(self):
        return f"{self.name} ({self.organ.name})"


@dataclass
class Delegation:
    """Represents a delegation with their preferences"""
    delegation_name: str
    number_delegates: int
    primary_advisor: str = ""
    primary_advisor_email: str = ""
    is_independent: bool = False

    # Spots per organ
    port_spec_spots: int = 0
    ga_ecosoc_spots: int = 0
    regional_body_spots: int = 0
    spanish_spots: int = 0
    specialized_spots: int = 0
    crisis_spots: int = 0
    crisis_specialized_spots: int = 0
    advanced_spots: int = 0
    portugues_spots: int = 0

    # Committee preferences
    ga_ecosoc_preferences: List[str] = field(default_factory=list)
    regional_body_preferences: List[str] = field(default_factory=list)
    spanish_preferences: List[str] = field(default_factory=list)
    specialized_preferences: List[str] = field(default_factory=list)
    crisis_specialized_preferences: List[str] = field(default_factory=list)
    portugues_preferences: List[str] = field(default_factory=list)
    advanced_preferences: List[str] = field(default_factory=list)

    # Country preferences
    country_preferences: List[str] = field(default_factory=list)

    # Track assignments - (committee, position) tuples
    assignments: List[Tuple[str, str]] = field(default_factory=list)

    # Track per-committee counts
    committee_counts: Dict[str, int] = field(default_factory=dict)

    def count_in_committee(self, committee: str) -> int:
        """How many delegates from this delegation in a specific committee"""
        return self.committee_counts.get(committee, 0)

    def remaining_in_organ(self, organ: Organ, committees_dict: Dict[str, Committee]) -> int:
        """Calculate how many spots a delegation has left in a given organ"""
        # Get total spots for this organ
        if organ == Organ.GA or organ == Organ.ECOSOC:
            total_spots = self.ga_ecosoc_spots
        elif organ == Organ.RB:
            total_spots = self.regional_body_spots
        elif organ == Organ.SPANISH:
            total_spots = self.spanish_spots
        elif organ == Organ.CRISIS or organ == Organ.SPECIALIZED:
            total_spots = self.crisis_specialized_spots
        elif organ == Organ.ADVANCED:
            total_spots = self.advanced_spots
        elif organ == Organ.PORTUGUES:
            total_spots = self.portugues_spots
        elif organ == Organ.PORTSPEC:
            total_spots = self.port_spec_spots
        else:
            return 0

        # Subtract already assigned in this organ using your existing method
        assigned_in_organ = self.count_in_organ(organ, committees_dict)

        return total_spots - assigned_in_organ

    def __hash__(self):
        return hash(self.delegation_name)  # or hash some unique identifier

    def __eq__(self, other):
        if not isinstance(other, Delegation):
            return False
        return self.delegation_name == other.delegation_name  # compare based on unique identifier

    def get_preferences_by_organ(self, organ: Organ) -> List[str]:
        """Get preference list for a specific organ"""
        if organ == Organ.GA or organ == Organ.ECOSOC:
            return self.ga_ecosoc_preferences
        elif organ == Organ.RB:
            return self.regional_body_preferences
        elif organ == Organ.SPANISH:
            return self.spanish_preferences
        elif organ == Organ.CRISIS or organ == Organ.SPECIALIZED:
            return self.crisis_specialized_preferences
        elif organ == Organ.ADVANCED:
            return self.advanced_preferences
        elif organ == Organ.PORTUGUES:
            return self.portugues_preferences
        return []

    def count_in_organ(self, organ: Organ, committees_dict: Dict[str, Committee]) -> int:
        """
        Count how many assignments this delegation has in a specific organ

        Args:
            organ: The organ to count assignments for
            committees_dict: Dictionary mapping committee names to Committee objects

        Returns:
            Number of assignments in that organ
        """
        count = 0
        for committee_name, _ in self.assignments:
            if committee_name in committees_dict:
                if committees_dict[committee_name].organ == organ:
                    count += 1
        return count

    def summary(self) -> str:
        """Get a summary string"""
        return (f"{self.delegation_name}: {self.number_delegates} delegates, "
                f"Advisor: {self.primary_advisor}")

    def __repr__(self):
        return self.summary()

    def add_assignment(self, committee: str, position: str):
        """Add an assignment to this delegation"""
        # CRITICAL: Check if this delegation has reached its delegate count
        if len(self.assignments) >= self.number_delegates:
            print(f"  ⚠️  Cannot assign more to {self.delegation_name} - already at {self.number_delegates} delegates")
            return False

        self.assignments.append((committee, position))
        self.committee_counts[committee] = self.committee_counts.get(committee, 0) + 1
        return True

    @property
    def assigned_count(self) -> int:
        return len(self.assignments)

    @property
    def remaining_delegates(self) -> int:
        """How many more delegates need assignments"""
        return self.number_delegates - self.assigned_count

    @property
    def is_fully_assigned(self) -> bool:
        return self.assigned_count >= self.number_delegates

    def rebalance(self):
        num = self.number_delegates

        fields = [
            "crisis_specialized_spots",
            "port_spec_spots",
            "portugues_spots",
        ]

        for f in fields:
            value = getattr(self, f)
            if value > num:
                setattr(self, f, num)
                num = 0
            else:
                num -= value

        self.ga_ecosoc_spots = num

class Conference:
    def __init__(self, name):
        self.name = name
        self.committees: Dict[str, Committee] = {}  # name -> Committee
        self.committee_positions: Dict[str, List[str]] = {}  # committee_name -> list of positions
        self.delegations: Dict[str, Delegation] = {}  # delegation_name -> Delegation

        # For quick lookups
        self.countries: Dict[str, Dict] = {}  # country_name -> {region, sub_category}
        self.regions: Dict[str, List[str]] = defaultdict(list)
        self.organs: Dict[Organ, List[str]] = defaultdict(list)  # organ -> list of committee names

    def load_committees_from_csv(self, organs_csv: str):
        """Load committees and their organs from CSV"""
        df = pd.read_csv(organs_csv)

        # Map organ strings to Organ enum
        organ_map = {
            'GA': Organ.GA,
            'ECOSOC': Organ.ECOSOC,
            'SPECIALIZED': Organ.SPECIALIZED,
            'ADVANCED': Organ.ADVANCED,
            'CRISIS': Organ.CRISIS,
            'RB': Organ.RB,
            'SPANISH': Organ.SPANISH,
            'PORTUGUES': Organ.PORTUGUES,
            'PORTSPEC': Organ.PORTSPEC,
        }

        for _, row in df.iterrows():
            committee_name = row['Committee']
            organ_str = str(row['Organ']).strip().upper()

            try:
                organ = organ_map[organ_str]
            except KeyError:
                valid = ", ".join(organ_map.keys())
                raise ValueError(
                    f"Invalid organ '{row['Organ']}' in CSV for committee '{committee_name}'. "
                    f"Must be one of: {valid}"
                )

            committee = Committee(name=committee_name, organ=organ)
            self.committees[committee_name] = committee
            self.organs[organ].append(committee_name)

        for d in self.delegations.values():
            if 'Brasilian Constitutional Convention' in d.crisis_specialized_preferences:
                print(f"{d.delegation_name} requests BCC")

        return self

    def load_positions_from_csv(self, positions_csv: str):
        """Load positions for each committee from CSV"""
        df = pd.read_csv(positions_csv)

        for column in df.columns:
            if column in self.committees:
                positions = df[column].dropna().astype(str).tolist()
                self.committee_positions[column] = positions

        return self

    def load_country_regions(self, csv_path: str):
        """Load country regions data"""
        df = pd.read_csv(csv_path)

        for _, row in df.iterrows():
            country = row['Country'].strip()
            region = row['Region']
            sub_category = row['Sub_Category']

            self.countries[country] = {
                'region': region,
                'sub_category': sub_category
            }
            self.regions[region].append(country)

        return self

    def _parse_committee_preferences(self, row, delegation_name, pref_cols, organ_type, unknown_tracker):
        """Parse committee preferences consistently for any organ type"""
        prefs = []
        for pref_col in pref_cols:
            if pref_col in row.index and pd.notna(row.get(pref_col)):
                raw = str(row[pref_col]).strip()
                if raw:
                    mapped = self._map_committee_name(raw)
                    if mapped not in self.committees:
                        unknown_tracker[raw].append(f"{delegation_name} ({organ_type})")
                    prefs.append(mapped)
        return prefs

    def _parse_spots_value(self, value, delegation_name, organ_type):
        """Parse spots value, handling floats and weird inputs"""
        if pd.isna(value):
            return 0

        # Convert to string first
        spots_str = str(value).strip()

        # Try converting to int directly
        try:
            return int(spots_str)
        except ValueError:
            pass

        # Try converting to float first (handles '10.0', '9.0', etc.)
        try:
            float_val = float(spots_str)
            # Check if it's a whole number
            if float_val.is_integer():
                spots = int(float_val)
                return spots
            else:
                print(f"⚠️  {delegation_name}: Decimal '{spots_str}' for {organ_type}, rounding to {int(float_val)}")
                return int(float_val)
        except ValueError:
            pass

        # Handle ranges like '0-2'
        if '-' in spots_str:
            parts = spots_str.split('-')
            try:
                spots = int(parts[0].strip())
                print(f"⚠️  {delegation_name}: Range '{spots_str}' for {organ_type}, using first number: {spots}")
                return spots
            except:
                pass

        # Last resort
        print(f"⚠️  {delegation_name}: Invalid spots '{spots_str}' for {organ_type}, defaulting to 1")
        return 1

    def _parse_organ_requests(self, row, delegation_name, spots_col, pref_cols, organ_type, unknown_tracker):
        """Parse an organ section that has Yes/No + spots + preferences"""
        spots = 0
        prefs = []

        # Use _parse_spots_value for validation!
        spots = self._parse_spots_value(
            row.get(spots_col),
            delegation_name,
            organ_type
        )

        # Get preferences
        prefs = self._parse_committee_preferences(
            row, delegation_name,
            pref_cols, organ_type, unknown_tracker
        )

        return spots, prefs

    def load_delegations_from_preference_form(self, csv_path: str):
        """Load delegations and their preferences"""
        df = pd.read_csv(csv_path)

        unknown_committees = defaultdict(list)
        unknown_countries = defaultdict(list)
        independent_counter = 1

        for idx, row in df.iterrows():
            # Parse number of delegates
            try:
                num_delegates = int(row['How many delegates are in your delegation?']) if pd.notna(row['How many delegates are in your delegation?']) else 1
            except:
                num_delegates = 1

            # Get delegation name
            delegation_name = row['Delegation Name']
            if pd.isna(delegation_name) or not str(delegation_name).strip() or num_delegates == 1:
                delegation_name = f"Independent Delegate #{independent_counter}"
                independent_counter += 1

            # GA/ECOSOC - Use _parse_spots_value here too!
            ga_ecosoc_spots = self._parse_spots_value(
                row.get('How many positions in English-speaking GAs and ECOSOCs would you like to request?'),
                delegation_name,
                "GA/ECOSOC"
            )

            ga_ecosoc_prefs = self._parse_committee_preferences(
                row, delegation_name,
                ['Most Preferred', 'Second-most Preferred', 'Third-most Preferred'],
                "GA/ECOSOC", unknown_committees
            )

            # cs
            cs_spots, cs_prefs = self._parse_organ_requests(
                row, delegation_name,
                'How many positions in the English-speaking Crisis and Specialized Committees would you like to request?',
                ['Most Preferred.1', 'Second-Most Preferred', 'Third-Most Preferred', 'Least Preferred'],
                "CS", unknown_committees
            )

            port_spots, port_prefs = self._parse_organ_requests(
                row, delegation_name,
                'How many positions in Portuguese-speaking GAs and ECOSOCs (UNEA and UNCTAD) would you like to request?',
                ['Which Portuguese-speaking GA/ECOSOC do you prefer more?'],
                "Port", unknown_committees
            )

            portspec_spots = self._parse_spots_value(
                row.get('How many positions in the Portuguese-speaking Specialized Committee (Brasilian Constitutional Convention) would you like to request?'),
                delegation_name,
                "PORTSPEC"
            )

            # Parse country preferences
            country_prefs = []
            for pref_col in ['What is your top choice for your country assignment?', 'What is your second-best choice for your country assignment?', 'What is your third-best choice for your country assignment?', 'What is your fourth-best choice for your country assignment?']:
                if pref_col in df.columns and pd.notna(row.get(pref_col)):
                    country = str(row[pref_col]).strip()
                    if country:
                        if country not in self.countries:
                            unknown_countries[country].append(f"{delegation_name} ({pref_col})")
                        country_prefs.append(country)

            # Create delegation
            delegation = Delegation(
                delegation_name=delegation_name,
                number_delegates=num_delegates,
                primary_advisor=row['Primary Advisor Name'] if pd.notna(row.get('Primary Advisor Name')) else "",
                primary_advisor_email=row['Primary Advisor Email'] if pd.notna(
                    row.get('Primary Advisor Email')) else "",

                # Spots per organ
                ga_ecosoc_spots=ga_ecosoc_spots,
                portugues_spots=port_spots,
                port_spec_spots=portspec_spots,
                crisis_specialized_spots=cs_spots,
                # Committee preferences
                ga_ecosoc_preferences=ga_ecosoc_prefs,
                portugues_preferences=port_prefs,
                crisis_specialized_preferences=cs_prefs,
                # Country preferences
                country_preferences=country_prefs,
                assignments= [],
                is_independent=delegation_name.startswith("Independent Delegate")
            )

            self.delegations[delegation_name] = delegation

        # Print warnings
        if unknown_committees:
            print(f"\n⚠️  Unknown committees: {len(unknown_committees)}")
            for committee, names in list(unknown_committees.items())[:10]:
                print(f"  • '{committee}': {', '.join(names[:3])}")

        if unknown_countries:
            print(f"\n⚠️  Unknown countries: {len(unknown_countries)}")
            for country, names in list(unknown_countries.items())[:10]:
                print(f"  • '{country}': {', '.join(names[:3])}")

        return self

    def validate_country_preferences(self) -> Dict:
        """Analyze country preferences by region"""
        region_counts = defaultdict(int)
        country_counts = defaultdict(int)

        for delegation in self.delegations.values():
            for country in delegation.country_preferences:
                if country in self.countries:
                    region = self.countries[country]['region']
                    region_counts[region] += 1
                    country_counts[country] += 1

        return {
            'by_region': dict(region_counts),
            'by_country': dict(country_counts)
        }

    def _map_committee_name(self, raw_name: str) -> str:
        """Map preference form committee name to actual committee name"""
        mappings = {
            'UNEA (GA)': 'UNEA',
            'UNCTAD (ECOSOC)': 'UNCTAD',
        }
        # Check if we have a direct mapping
        if raw_name in mappings:
            mapped = mappings[raw_name]
            return mapped

        # Try stripping extra spaces
        stripped = raw_name.strip()
        if stripped != raw_name and stripped in mappings:
            mapped = mappings[stripped]
            return mapped

        # If no mapping, return original
        return raw_name

    def get_committees_by_organ(self, organ: Organ) -> List[str]:
        """Get all committee names in a specific organ"""
        return self.organs.get(organ, [])

    def print_summary(self):
        """Print a summary of the conference data"""
        print(f"\n{'=' * 60}")
        print(f"{self.name} - Summary")
        print(f"{'=' * 60}")

        # Overall stats
        print(f"\n📊 OVERALL STATISTICS:")
        print(f"  Committees: {len(self.committees)}")
        print(f"  Total Positions: {sum(len(p) for p in self.committee_positions.values())}")
        print(f"  Delegations: {len(self.delegations)}")
        print(f"  Total Delegates: {sum(d.number_delegates for d in self.delegations.values())}")

        # By organ
        print(f"\n📋 COMMITTEES BY ORGAN:")
        for organ in Organ:
            committee_names = self.organs.get(organ, [])
            if committee_names:
                total_positions = sum(len(self.committee_positions.get(c, [])) for c in committee_names)
                print(f"\n  {organ.name} ({organ.value}):")
                print(f"    {len(committee_names)} committees, {total_positions} total positions")

                # List committees
                for committee in sorted(committee_names)[:5]:  # Show first 5
                    positions = len(self.committee_positions.get(committee, []))
                    print(f"      • {committee}: {positions} positions")

                if len(committee_names) > 5:
                    print(f"      • ... and {len(committee_names) - 5} more")

        # Delegation summary
        print(f"\n👥 DELEGATIONS SUMMARY:")
        for delegation in sorted(self.delegations.values(), key=lambda d: d.delegation_name)[:10]:
            print(f"  • {delegation.summary()}")

        if len(self.delegations) > 10:
            print(f"  • ... and {len(self.delegations) - 10} more")

    def optimize_assignments(self):
        """
        Optimize committee and country assignments with a multi-pass algorithm
        """
        self._init_assignment_tracking()

        self.assign_independent_delegates()
        result = self._fill_all_prefs()
        while result != 0:
            result = self._fill_all_prefs()

        self._assign_remaining_random()

        self._assign_countries_fair_iterative()

        self._force_assign_remaining()

        self._print_optimization_summary()

        self.export_assignments_to_excel(filename="mun_assignments.xlsx")

        return self

    def _force_assign_remaining(self):
        """
        Final fallback: assign remaining delegates to the committee with the
        lowest current fill rate (based on actual assignments and total seats),
        ignoring organ caps. Uses committee_positions for total seats.
        """
        unassigned = [d for d in self.delegations.values() if not d.is_fully_assigned]
        if not unassigned:
            return 0

        # Build a mapping: committee -> assigned count (from all delegations)
        assigned_counts = defaultdict(int)
        for d in self.delegations.values():
            for committee, _ in d.assignments:
                assigned_counts[committee] += 1

        # Ensure all committees from committee_positions are in the mapping
        for committee in self.committee_positions:
            if committee not in assigned_counts:
                assigned_counts[committee] = 0

        # Also ensure any committee that appears in assignments but not in positions? (unlikely)
        total_seats = {committee: len(positions) for committee, positions in self.committee_positions.items()}

        assignments_made = 0
        ga_ecosoc_committees = self.organs.get(Organ.GA, []) + self.organs.get(Organ.ECOSOC, [])

        while unassigned:
            # Find the committee with the lowest fill rate that has free seats
            best_committee = None
            best_fill_rate = float('inf')

            for committee in self.committee_positions:
                total = total_seats[committee]
                assigned = assigned_counts.get(committee, 0)
                if assigned >= total:
                    continue  # already full
                fill_rate = assigned / total if total > 0 else 0
                if fill_rate < best_fill_rate:
                    best_fill_rate = fill_rate
                    best_committee = committee

            if best_committee is None:
                print("⚠️  No committees with remaining capacity – breaking.")
                break

            # Assign one delegate from the first unassigned delegation
            delegation = unassigned[0]
            committee = best_committee

            # Perform the assignment (ignore organ caps)
            if committee in ga_ecosoc_committees:
                delegation.add_assignment(committee, None)
            else:
                # For non‑GA/ECOSOC, we still need a position string.
                # If we have positions available, use the next one; otherwise, use a placeholder.
                # But since this is a fallback, we can assign a generic position.
                # We'll use the next available position from committee_positions
                # but we don't have a "used positions" list here. Simpler: assign a placeholder.
                position = "Delegate"  # or we can keep None for all; but some export expects a string.
                delegation.add_assignment(committee, position)

            # Update counts
            assigned_counts[committee] += 1
            assignments_made += 1

            # If delegation is now fully assigned, remove it
            if delegation.is_fully_assigned:
                unassigned.remove(delegation)

        if unassigned:
            print(f"⚠️  Still {len(unassigned)} delegations with unassigned delegates after fallback:")
            for d in unassigned:
                print(f"    {d.delegation_name}: {d.remaining_delegates} left")

        return assignments_made

    def _assign_countries_fair_iterative(self):
        """
        Fair iterative approach to assign countries to GA/ECOSOC spots.
        """
        ga_committees = self.organs.get(Organ.GA, []) + self.organs.get(Organ.ECOSOC, [])
        total_assignments = 0

        committee_available = {}
        for committee in ga_committees:
            if committee in self.committee_positions:
                committee_available[committee] = self.committee_positions[committee].copy()

        all_spots = []
        for delegation in self.delegations.values():
            for i, (committee, country) in enumerate(delegation.assignments):
                if committee in ga_committees and country is None:
                    all_spots.append((delegation, committee, i))

        for pref_level in [1, 2, 3, 4, 5]:
            level_assignments = 0

            eligible_spots = []
            for spot in all_spots:
                delegation, committee, idx = spot
                if len(delegation.country_preferences) >= pref_level:
                    eligible_spots.append(spot)

            if not eligible_spots:
                continue

            random.shuffle(eligible_spots)

            for delegation, committee, idx in eligible_spots:
                preferred = delegation.country_preferences[pref_level - 1]

                if preferred in committee_available.get(committee, []):
                    committee_available[committee].remove(preferred)
                    delegation.assignments[idx] = (committee, preferred)
                    level_assignments += 1
                    total_assignments += 1

                    all_spots.remove((delegation, committee, idx))


        if all_spots:
            region_assignments = self._assign_countries_by_region_iterative(all_spots, committee_available,
                                                                            ga_committees)
            total_assignments += region_assignments

        if all_spots:
            random_assignments = self._assign_countries_random_fix(all_spots, committee_available)
            total_assignments += random_assignments

        return total_assignments

    def _assign_countries_by_region_iterative(self, all_spots, committee_available, ga_committees):
        """
        Assign by region following preference order:
        First try region of #1 choice, then #2, then #3, etc.
        """
        assignments_made = 0

        spots_by_delegation = defaultdict(list)
        for spot in all_spots:
            delegation, committee, idx = spot
            spots_by_delegation[delegation].append(spot)

        for pref_level in [1, 2, 3, 4, 5]:
            level_assignments = 0

            random.shuffle(all_spots)

            for delegation, committee, idx in all_spots[:]:
                if len(delegation.country_preferences) < pref_level:
                    continue

                target_country = delegation.country_preferences[pref_level - 1]

                if target_country not in self.countries:
                    continue

                target_region = self.countries[target_country]['region']

                if committee not in committee_available:
                    continue

                region_countries = [
                    c for c in committee_available[committee]
                    if c in self.countries and self.countries[c]['region'] == target_region
                ]

                if region_countries:
                    chosen = random.choice(region_countries)
                    committee_available[committee].remove(chosen)
                    delegation.assignments[idx] = (committee, chosen)
                    all_spots.remove((delegation, committee, idx))
                    level_assignments += 1
                    assignments_made += 1

        return assignments_made

    def _assign_countries_random_fix(self, all_spots, committee_available):
        """
        Truly random fill for remaining spots - no alphabetical bias
        """
        assignments_made = 0

        from collections import defaultdict
        country_counter = defaultdict(int)

        random.shuffle(all_spots)

        for i, (delegation, committee, idx) in enumerate(all_spots[:]):
            if committee not in committee_available:
                continue

            available = committee_available[committee]
            if not available:
                continue

            chosen = random.choice(available)

            if chosen in available:
                available.remove(chosen)
                delegation.assignments[idx] = (committee, chosen)
                all_spots.remove((delegation, committee, idx))
                assignments_made += 1
                country_counter[chosen] += 1

        return assignments_made

    def _assign_remaining_random(self):
        """
        Final pass: Guarantee all delegates get assigned.
        Prioritizes emptiest committees but ensures everyone gets a spot.
        """
        assignments_made = 0

        ga_ecosoc_committees = self.organs.get(Organ.GA, []) + self.organs.get(Organ.ECOSOC, [])

        unassigned = [d for d in self.delegations.values() if not d.is_fully_assigned]
        if not unassigned:
            return 0

        total_remaining = sum(d.remaining_delegates for d in unassigned)

        max_attempts = total_remaining * 5
        attempts = 0

        while unassigned and attempts < max_attempts:
            attempts += 1
            made_progress = False

            available_committees = []
            for committee, cap in self.committee_capacity.items():
                if cap['filled'] < cap['total_positions']:
                    fill_rate = cap['filled'] / cap['total_positions']
                    available_committees.append((committee, cap, fill_rate))

            if not available_committees:
                break

            available_committees.sort(key=lambda x: x[2])

            assigned_this_round = False

            for committee, cap, _ in available_committees:
                if cap['filled'] >= cap['total_positions']:
                    continue

                eligible = []
                for delegation in unassigned:
                    if self._can_assign_to_organ(delegation, committee):
                        eligible.append(delegation)

                if not eligible:
                    continue

                delegation = random.choice(eligible)

                if committee in ga_ecosoc_committees:
                    delegation.add_assignment(committee, None)
                else:
                    if cap['positions_available']:
                        position = cap['positions_available'].pop(0)
                        delegation.add_assignment(committee, position)
                    else:
                        continue

                cap['filled'] += 1
                assignments_made += 1
                made_progress = True
                assigned_this_round = True

                if delegation.is_fully_assigned:
                    unassigned.remove(delegation)

                break

            if not assigned_this_round:
                for delegation in unassigned[:]:
                    for committee, cap in self.committee_capacity.items():
                        if cap['filled'] >= cap['total_positions']:
                            continue

                        if self._can_assign_to_organ(delegation, committee):
                            if committee in ga_ecosoc_committees:
                                delegation.add_assignment(committee, None)
                            else:
                                if cap['positions_available']:
                                    position = cap['positions_available'].pop(0)
                                    delegation.add_assignment(committee, position)
                                else:
                                    continue

                            cap['filled'] += 1
                            assignments_made += 1
                            made_progress = True

                            if delegation.is_fully_assigned:
                                unassigned.remove(delegation)
                            break

                    if made_progress:
                        break

                if not made_progress:
                    break

        unassigned = [d for d in self.delegations.values() if not d.is_fully_assigned]
        if unassigned:
            for delegation in unassigned[:]:
                for committee, cap in self.committee_capacity.items():
                    if cap['filled'] >= cap['total_positions']:
                        continue

                    if committee in ga_ecosoc_committees:
                        delegation.add_assignment(committee, None)
                    else:
                        if cap['positions_available']:
                            position = cap['positions_available'].pop(0)
                            delegation.add_assignment(committee, position)

                    cap['filled'] += 1
                    assignments_made += 1

                    if delegation.is_fully_assigned:
                        break

                if delegation.is_fully_assigned:
                    unassigned.remove(delegation)

        return assignments_made

    def count_in_ga_ecosoc(self, delegation) -> int:
        """Count total assignments across BOTH GA and ECOSOC"""
        return (delegation.count_in_organ(Organ.GA, self.committees) +
                delegation.count_in_organ(Organ.ECOSOC, self.committees))

    def _can_assign_to_organ(self, delegation, committee) -> bool:
        committee_obj = self.committees.get(committee)
        if not committee_obj:
            return False
        organ = committee_obj.organ

        if organ in [Organ.GA, Organ.ECOSOC]:
            current = self.count_in_ga_ecosoc(delegation)
            limit = delegation.ga_ecosoc_spots
        elif organ in [Organ.CRISIS, Organ.SPECIALIZED]:
            current = self.count_in_crisis_specialized(delegation)
            limit = delegation.crisis_specialized_spots
        elif organ == Organ.PORTUGUES:
            current = delegation.count_in_organ(organ, self.committees)
            limit = delegation.portugues_spots
        elif organ == Organ.PORTSPEC:
            current = delegation.count_in_organ(organ, self.committees)
            limit = delegation.port_spec_spots
        else:
            return False  # should not happen for unused organs

        return current < limit

    def _init_assignment_tracking(self):
        """Initialize data structures for tracking assignments"""
        # Committee capacity tracking
        self.committee_capacity = {}
        self.organ_stats = {}

        # List of all preference attributes to check
        preference_attrs = [
            'ga_ecosoc_preferences',
            #'regional_body_preferences',
            #'spanish_preferences',
            #'specialized_preferences',
            #'crisis_preferences',
            #'advanced_preferences',
            'crisis_specialized_preferences',
            'portugues_preferences',
        ]

        for committee, positions in self.committee_positions.items():
            organ = self.committees[committee].organ
            # Determine max_per_delegation (1 for crisis/specialized, etc.)
            if organ in [Organ.GA, Organ.ECOSOC]:
                max_per = 4
            elif organ in [Organ.CRISIS, Organ.SPECIALIZED]:
                max_per = 2
            else:
                max_per = 10  # adjust as needed

            # Build requests and count unique delegations
            requests = []
            unique_delegations = set()
            for delegation in self.delegations.values():
                # Check all relevant preference attributes
                for pref_attr in ['ga_ecosoc_preferences', 'crisis_specialized_preferences', 'portugues_preferences']:
                    prefs = getattr(delegation, pref_attr, [])
                    if committee in prefs:
                        rank = prefs.index(committee) + 1
                        requests.append((delegation, rank))
                        unique_delegations.add(delegation)
                        break  # avoid double‑counting if committee appears in multiple lists

            self.committee_capacity[committee] = {
                'total_positions': len(positions),
                'filled': 0,
                'max_per_delegation': max_per,
                'positions_available': positions.copy(),
                'organ': organ,
                'requested': requests,
                'total_requesting_delegations': len(unique_delegations)  # <-- new field
            }
            if organ not in self.organ_stats:
                self.organ_stats[organ] = {
                    "total_positions": 0,
                    "num_committees": 0,
                }

            self.organ_stats[organ]["total_positions"] += len(positions)
            self.organ_stats[organ]["num_committees"] += 1


        for organ, data in self.organ_stats.items():
            if organ in [Organ.GA, Organ.ECOSOC]:
                max_per_delegation = 4
            elif organ in [Organ.CRISIS, Organ.SPECIALIZED]:
                max_per_delegation = 2
            else:
                max_per_delegation = 10

            data["max_per_delegation"] = max_per_delegation * data["num_committees"]

        # Delegation tracking
        for delegation in self.delegations.values():
            delegation.assignments = []
            delegation.committee_counts = defaultdict(int)
            delegation.country_assignments = []  # For country preferences

        # Country pool for balanced assignment
        self.country_pool = list(self.countries.keys())
        self.country_usage = defaultdict(int)
        self.region_usage = defaultdict(lambda: defaultdict(int))

    def _cleanup_requested_lists(self):
        """Remove delegations that have no spots left in that organ"""
        for committee in self.committees:
            capacity = self.committee_capacity[committee]
            organ = capacity['organ']

            # Use your existing remaining_in_organ method
            capacity['requested'] = [
                (d, rank) for d, rank in capacity['requested']
                if d.remaining_in_organ(organ, self.committees) > 0
            ]

    def print_distribution(self):
        """Print distribution of committee and country assignments"""
        print("\n" + "=" * 70)
        print("<UNK> DISTRIBUTION")
        print("=" * 70)

        fields = [
            "spanish_spots",
            "regional_body_spots",
            "advanced_spots",
            "crisis_spots",
            "specialized_spots",
            "ga_ecosoc_spots",
        ]

        totals = {field: 0 for field in fields}


        for dels in self.delegations.values():
            dels.rebalance()
            for field in fields:
                totals[field] += getattr(dels, field)

        for field, total in totals.items():
            print(f"{field}: {total}")

    def _get_organ_group(self, organ):
        if organ in [Organ.GA, Organ.ECOSOC]:
            return "GA_ECOSOC"
        if organ in [Organ.CRISIS, Organ.SPECIALIZED]:
            return "CRISIS_SPECIALIZED"
        return organ  # for other organs (if any)

    def count_in_crisis_specialized(self, delegation) -> int:
        return (delegation.count_in_organ(Organ.CRISIS, self.committees) +
                delegation.count_in_organ(Organ.SPECIALIZED, self.committees))

    def _fill_all_prefs(self):
        """
        Main filling algorithm:
        1. First, fill committees where requests <= spots (guaranteed assignments)
        2. Then, for remaining committees with competition, fill by preference level
        """

        total_assignments = 0

        guaranteed = self._fill_guaranteed_committees()
        total_assignments += guaranteed

        if self._get_remaining_spots() > 0:
            competitive = self._fill_competitive_by_preference()
            total_assignments += competitive

        return total_assignments

    def _get_remaining_spots(self) -> int:
        """Get total number of unfilled positions across all committees"""
        total = 0
        for cap in self.committee_capacity.values():
            total += cap['total_positions'] - cap['filled']
        return total

    def _fill_guaranteed_committees(self):
        assignments_made = 0
        ga_ecosoc_committees = self.organs.get(Organ.GA, []) + self.organs.get(Organ.ECOSOC, [])

        # Get fillable committees and sort by original unique request count (descending)
        fillable = self._get_fillable_committees()
        if not fillable:
            return 0

        fillable.sort(key=lambda c: self.committee_capacity[c]['total_requesting_delegations'], reverse=True)
        print("\n--- Guaranteed phase: fillable committees (sorted by total requests) ---")
        for comm in fillable:
            cap = self.committee_capacity[comm]
            print(
                f"  {comm}: total_req={cap['total_requesting_delegations']}, spots_left={cap['total_positions'] - cap['filled']}")

        for committee in fillable:
            capacity = self.committee_capacity[committee]
            organ = capacity['organ']
            group = self._get_organ_group(organ)

            remaining_spots = capacity['total_positions'] - capacity['filled']
            active_for_this = self._get_active_requests(committee)  # still needed for per‑delegation logic
            if not active_for_this or remaining_spots <= 0:
                continue

            delegation_requests = {}
            for delegation, rank in active_for_this:
                delegation_requests.setdefault(delegation, []).append(rank)

            sorted_delegations = sorted(
                delegation_requests.items(),
                key=lambda x: min(x[1])
            )

            delegations_that_hit_zero = set()
            for delegation, ranks in sorted_delegations:
                if remaining_spots <= 0:
                    break
                if self._spots_left_in_group(delegation, group) <= 0:
                    continue
                if delegation.count_in_committee(committee) >= capacity['max_per_delegation']:
                    continue

                # Assign
                if committee in ga_ecosoc_committees:
                    delegation.add_assignment(committee, None)
                else:
                    if capacity['positions_available']:
                        position = capacity['positions_available'].pop(0)
                        delegation.add_assignment(committee, position)
                    else:
                        continue

                capacity['filled'] += 1
                remaining_spots -= 1
                assignments_made += 1

                if self._spots_left_in_group(delegation, group) <= 0:
                    delegations_that_hit_zero.add(delegation)

            if delegations_that_hit_zero:
                self._remove_from_group_requests(delegations_that_hit_zero, group)

        return assignments_made

    def _fill_competitive_by_preference(self):
        assignments_made = 0
        ga_ecosoc_committees = self.organs.get(Organ.GA, []) + self.organs.get(Organ.ECOSOC, [])

        for pref_level in [1, 2, 3]:
            committees_with_need = [
                c for c, cap in self.committee_capacity.items()
                if cap['filled'] < cap['total_positions']
            ]
            if not committees_with_need:
                break

            # Sort by total_requesting_delegations descending
            sorted_committees = sorted(
                committees_with_need,
                key=lambda c: self.committee_capacity[c]['total_requesting_delegations'],
                reverse=True
            )

            assigned_this_level = set()
            for committee in sorted_committees:
                capacity = self.committee_capacity[committee]
                if capacity['filled'] >= capacity['total_positions']:
                    continue

                remaining_spots = capacity['total_positions'] - capacity['filled']
                if remaining_spots <= 0:
                    continue

                organ = capacity['organ']
                group = self._get_organ_group(organ)

                # Build candidate list for this committee at this preference level
                candidates = []
                for delegation in self.delegations.values():
                    if delegation.is_fully_assigned or delegation.delegation_name in assigned_this_level:
                        continue
                    prefs = delegation.get_preferences_by_organ(organ)
                    if len(prefs) >= pref_level and prefs[pref_level - 1] == committee:
                        if self._spots_left_in_group(delegation, group) > 0:
                            if delegation.count_in_committee(committee) < capacity['max_per_delegation']:
                                candidates.append(delegation)

                if not candidates:
                    continue

                random.shuffle(candidates)
                assigned = 0
                for delegation in candidates:
                    if assigned >= remaining_spots:
                        break

                    if committee in ga_ecosoc_committees:
                        delegation.add_assignment(committee, None)
                    else:
                        if capacity['positions_available']:
                            position = capacity['positions_available'].pop(0)
                            delegation.add_assignment(committee, position)
                        else:
                            continue

                    capacity['filled'] += 1
                    assigned += 1
                    assignments_made += 1
                    assigned_this_level.add(delegation.delegation_name)

        return assignments_made

    def _get_active_requests(self, committee):
        """Get requests for a committee from delegations that still have spots in that organ group"""
        capacity = self.committee_capacity[committee]
        organ = capacity['organ']
        group = self._get_organ_group(organ)

        active = []
        for delegation, rank in capacity['requested']:  # Use ORIGINAL requested list
            if self._spots_left_in_group(delegation, group) > 0:
                active.append((delegation, rank))

        return active

    def _get_fillable_committees(self):
        """Find committees where unique active delegations <= remaining spots"""
        fillable = []

        for committee in self.committees:
            capacity = self.committee_capacity[committee]

            # Skip if already full
            if capacity['filled'] >= capacity['total_positions']:
                continue

            remaining_spots = capacity['total_positions'] - capacity['filled']

            # Get ACTIVE delegations (still have spots in this organ group)
            active_requests = self._get_active_requests(committee)

            # Count UNIQUE delegations
            unique_delegations = set(d for d, _ in active_requests)

            if unique_delegations and len(unique_delegations) <= remaining_spots:
                fillable.append(committee)

        return fillable

    def _spots_left_in_group(self, delegation, group):
        if group == "GA_ECOSOC":
            total_spots = delegation.ga_ecosoc_spots
            assigned = self.count_in_ga_ecosoc(delegation)
            return total_spots - assigned
        if group == "CRISIS_SPECIALIZED":
            total_spots = delegation.crisis_specialized_spots
            assigned = self.count_in_crisis_specialized(delegation)
            return total_spots - assigned
        # For other organs (e.g., PORTUGUES, PORTSPEC) we use the existing per‑organ method
        return delegation.remaining_in_organ(group, self.committees)

    def _remove_from_group_requests(self, delegations, group):
        """
        Remove specific delegations from ALL committee requested lists in this group
        ONLY because they have ZERO spots left
        """
        committees_in_group = []
        for committee in self.committees:
            capacity = self.committee_capacity[committee]
            if self._get_organ_group(capacity['organ']) == group:
                committees_in_group.append(committee)

        for committee in committees_in_group:
            capacity = self.committee_capacity[committee]

            capacity['requested'] = [
                (d, rank) for d, rank in capacity['requested']
                if d not in delegations
            ]

    def assign_independent_delegates(self):
        """
        Assign independent delegates (exactly 1 spot in one organ) to their highest preferences
        """
        assignments_made = 0

        ga_ecosoc_committees = self.organs.get(Organ.GA, []) + self.organs.get(Organ.ECOSOC, [])

        organ_config = {
            Organ.GA: {'pref': 'ga_ecosoc_preferences', 'spot': 'ga_ecosoc_spots'},
            Organ.ECOSOC: {'pref': 'ga_ecosoc_preferences', 'spot': 'ga_ecosoc_spots'},
            Organ.PORTUGUES: {'pref': 'portugues_preferences', 'spot': 'portugues_spots'},
            Organ.SPECIALIZED: {'pref': 'crisis_specialized_preferences', 'spot': 'crisis_specialized_spots'},
            Organ.CRISIS: {'pref': 'crisis_specialized_preferences', 'spot': 'crisis_specialized_spots'},
            Organ.PORTSPEC: {'pref': 'advanced_preferences', 'spot': 'port_spec_spots'},
        }

        spot_type_groups = {}
        for organ, config in organ_config.items():
            key = (config['pref'], config['spot'])
            if key not in spot_type_groups:
                spot_type_groups[key] = {
                    'organs': [],
                    'delegates': [],
                    'pref_attr': config['pref'],
                    'spot_attr': config['spot']
                }
            spot_type_groups[key]['organs'].append(organ)

        for delegation in self.delegations.values():
            if not delegation.is_independent:
                continue

            for (pref_attr, spot_attr), group in spot_type_groups.items():
                if getattr(delegation, spot_attr, 0) == 1:
                    group['delegates'].append(delegation)
                    break

        for (pref_attr, spot_attr), group in spot_type_groups.items():
            delegates = group['delegates']
            if not delegates:
                continue

            organs = group['organs']

            available_committees = [
                (name, cap) for name, cap in self.committee_capacity.items()
                if cap['organ'] in organs
                   and cap['filled'] < cap['total_positions']
            ]

            if not available_committees:
                continue

            available_committees.sort(key=lambda x: (x[1]['organ'].value, x[1]['total_positions']))

            for delegation in delegates:
                preferences = getattr(delegation, pref_attr, [])
                assigned = False

                for rank, committee_name in enumerate(preferences, 1):
                    if committee_name not in self.committee_capacity:
                        continue

                    capacity = self.committee_capacity[committee_name]

                    if capacity['organ'] in organs and capacity['filled'] < capacity['total_positions']:

                        if committee_name in ga_ecosoc_committees:
                            delegation.add_assignment(committee_name, None)
                        else:
                            if capacity['positions_available']:
                                position = capacity['positions_available'].pop(0)
                                delegation.add_assignment(committee_name, position)
                            else:
                                continue

                        capacity['filled'] += 1
                        assignments_made += 1
                        assigned = True

                        break

                if not assigned:
                    available = [
                        (name, cap) for name, cap in available_committees
                        if cap['filled'] < cap['total_positions']
                    ]

                    if available:
                        committee_name, capacity = random.choice(available)

                        if committee_name in ga_ecosoc_committees:
                            delegation.add_assignment(committee_name, None)
                        else:
                            if capacity['positions_available']:
                                position = capacity['positions_available'].pop(0)
                                delegation.add_assignment(committee_name, position)
                            else:
                                continue

                        capacity['filled'] += 1
                        assignments_made += 1

        self._cleanup_requested_lists()
        return assignments_made

    def _print_optimization_summary(self):
        """Print a detailed summary based on actual assignments, not cached capacity."""
        print(f"\n{'=' * 70}")
        print("📊 OPTIMIZATION RESULTS")
        print(f"{'=' * 70}")

        # 1. Overall delegate statistics
        total_delegates = sum(d.number_delegates for d in self.delegations.values())
        total_assigned = sum(d.assigned_count for d in self.delegations.values())

        print(f"\n✅ Total Delegates: {total_delegates}")
        print(f"✅ Positions Assigned: {total_assigned}")
        if total_assigned < total_delegates:
            print(f"⚠️  Unassigned delegates: {total_delegates - total_assigned}")
        elif total_assigned == total_delegates:
            print("✅ All delegates successfully assigned.")

        # 2. Per‑organ fill rates (use assignments from delegations)
        # Initialize organ stats with total seats from committee_positions
        organ_stats = {organ: {"total_spots": 0, "filled": 0} for organ in Organ}
        committee_stats = {}  # committee name -> {'total': int, 'filled': int}

        # First, count total seats per committee from committee_positions
        for committee, positions in self.committee_positions.items():
            if committee not in self.committees:
                continue
            organ = self.committees[committee].organ
            total = len(positions)
            organ_stats[organ]["total_spots"] += total
            committee_stats[committee] = {"total": total, "filled": 0}

        # Now count filled seats from assignments
        for delegation in self.delegations.values():
            for committee, position in delegation.assignments:
                if committee in committee_stats:
                    committee_stats[committee]["filled"] += 1
                    if committee in self.committees:
                        organ = self.committees[committee].organ
                        organ_stats[organ]["filled"] += 1

        # Print organ fill rates
        print("\n📋 Per‑Organ Fill Rates:")
        for organ in Organ:
            stats = organ_stats[organ]
            if stats["total_spots"] > 0:
                fill_pct = (stats["filled"] / stats["total_spots"]) * 100
                bar = '█' * int(fill_pct // 10) + '░' * (10 - int(fill_pct // 10))
                print(f"  {organ.name:15} [{bar}] {stats['filled']:3}/{stats['total_spots']:3} ({fill_pct:.0f}%)")

        # 3. Preference satisfaction – based on assignments
        # Map each organ to its preference attribute (only organs that have preferences)
        organ_pref_attr = {
            Organ.GA: 'ga_ecosoc_preferences',
            Organ.ECOSOC: 'ga_ecosoc_preferences',
            Organ.CRISIS: 'crisis_specialized_preferences',
            Organ.SPECIALIZED: 'crisis_specialized_preferences',
            Organ.PORTUGUES: 'portugues_preferences',
            # PORTSPEC has no preference attribute (set to None)
            Organ.PORTSPEC: None,
            Organ.RB: None,
            Organ.SPANISH: None,
            Organ.ADVANCED: None,
        }

        rank_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        not_preferred = 0
        total_pref_check = 0

        for delegation in self.delegations.values():
            for committee, position in delegation.assignments:
                if committee not in self.committees:
                    continue
                organ = self.committees[committee].organ
                pref_attr = organ_pref_attr.get(organ)
                if pref_attr is None:
                    continue  # no preference data for this organ
                prefs = getattr(delegation, pref_attr, [])
                if committee in prefs:
                    rank = prefs.index(committee) + 1
                    if rank <= 5:
                        rank_counts[rank] += 1
                    total_pref_check += 1
                else:
                    not_preferred += 1
                    total_pref_check += 1

        total_matched = total_pref_check - not_preferred

        print("\n📋 Preference Satisfaction (based on assignments with preference data):")
        if total_pref_check > 0:
            print(
                f"  • Assignments matching a preference: {total_matched} ({total_matched / total_pref_check * 100:.1f}%)")
            print(
                f"  • Assignments not in preference list: {not_preferred} ({not_preferred / total_pref_check * 100:.1f}%)")
            if total_matched > 0:
                print("\n  Rank Distribution (among matched preferences):")
                for rank in sorted(rank_counts.keys()):
                    if rank_counts[rank]:
                        pct = rank_counts[rank] / total_matched * 100
                        print(f"    Rank {rank}: {rank_counts[rank]} ({pct:.1f}%)")
        else:
            print("  No assignments with preference data found.")

        # 4. Unassigned delegations (if any)
        unassigned = [d for d in self.delegations.values() if not d.is_fully_assigned]
        if unassigned:
            print(f"\n⚠️  Delegations with remaining spots:")
            for d in unassigned:
                print(f"  {d.delegation_name}: {d.remaining_delegates} left")

        # 5. Committee‑level fill rates
        print(f"\n📋 Committee Fill Rates:")
        for committee, stats in committee_stats.items():
            total = stats["total"]
            filled = stats["filled"]
            fill_pct = (filled / total) * 100 if total > 0 else 0
            bar = '█' * int(fill_pct // 10) + '░' * (10 - int(fill_pct // 10))
            print(f"  {committee:30} [{bar}] {filled:2}/{total:2} ({fill_pct:.0f}%)")

    def export_assignments_to_excel(self, filename="mun_assignments.xlsx"):
        """
        Export assignments to Excel with delegation name and their assignments in a clean format
        """
        print(f"\n📤 Exporting assignments to {filename}...")

        # Prepare data for export
        export_data = []

        for delegation in self.delegations.values():
            row = {
                'Delegation': delegation.delegation_name,
                'Delegates': delegation.number_delegates,
            }

            # Add up to 10 assignments (or however many they have)
            for i, (committee, position) in enumerate(delegation.assignments, 1):
                row[f'Assignment {i}'] = f"{committee} — {position}"

            export_data.append(row)

        # Create DataFrame
        df = pd.DataFrame(export_data)

        # Fill NaN with empty strings for cleaner output
        df = df.fillna('')

        # Export to Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Assignments', index=False)

            # Auto-adjust column widths
            worksheet = writer.sheets['Assignments']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        print(f"✅ Exported {len(export_data)} delegations to {filename}")

        # Show preview
        print("\n📋 Preview:")
        print(df.head(10).to_string(index=False))

        return df

def group_shuffle(delegations):
    items = [(name, delegation) for name, delegation in delegations
             if delegation.ga_ecosoc_spots > 0 and delegation.ga_ecosoc_preferences]

    # Sort by number_delegates first
    items.sort(key=lambda x: x[1].number_delegates)

    # Group by the number_delegates value
    grouped = []
    for _, group in groupby(items, key=lambda x: x[1].number_delegates):
        group_list = list(group)
        random.shuffle(group_list)
        grouped.extend(group_list)

    return grouped