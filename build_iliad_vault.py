#!/usr/bin/env python3
"""
Generate an Obsidian vault for Homer's *Iliad* designed for the K-Plex plugin.

* Relationships are written as frontmatter properties whose names come from an
  external ontology file (default: iliad_ontology.yaml).
* Every edge is validated against that ontology (known relation, domain, range)
  before anything is written.
* Because the ontology lives outside the script, you can rename fields, change
  K-Plex roles, or add node types without touching Python.

Usage:
    pip install pyyaml
    python build_iliad_vault.py --out "Iliad Vault"
    python build_iliad_vault.py --check          # validate only, write nothing

After generating, open the folder as a vault in Obsidian, install/enable K-Plex,
and map the fields to compass roles (see "00 Ontology Setup.md" in the vault).
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required:  pip install pyyaml")

ROLES = ("parent", "child", "friend", "challenger", "previous", "next")
ILLEGAL_FILENAME = re.compile(r'[\\/:*?"<>|#^\[\]]')

WORK = "The Iliad"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Entity:
    name: str
    type: str
    body: str = ""
    props: dict = field(default_factory=dict)
    aliases: list = field(default_factory=list)
    rels: dict = field(default_factory=lambda: defaultdict(list))  # relation -> [targets]


ENTITIES: "OrderedDict[str, Entity]" = OrderedDict()


def _add(ent: Entity) -> Entity:
    if ent.name in ENTITIES:
        raise ValueError(f"Duplicate entity: {ent.name}")
    if ILLEGAL_FILENAME.search(ent.name):
        raise ValueError(f"Illegal character in note name: {ent.name!r}")
    ENTITIES[ent.name] = ent
    return ent


def _norm_rels(ent: Entity, rels: dict) -> None:
    # kwargs use underscores for spaces: member_of -> "member of"
    for key, targets in rels.items():
        if isinstance(targets, str):
            targets = [targets]
        ent.rels[key.replace("_", " ")].extend(targets)


def char(name, side, kind, summary, aliases=(), **rels):
    e = _add(Entity(name, "Character", summary, {"side": side, "kind": kind}, list(aliases)))
    _norm_rels(e, rels)


def faction(name, summary, **rels):
    e = _add(Entity(name, "Faction", summary))
    _norm_rels(e, rels)


def place(name, summary):
    _add(Entity(name, "Place", summary))


# Plot points are kept in narrative order; ``order`` is assigned automatically.
EVENT_SEQUENCE: list[str] = []


def event(name, book, summary, participants, location, caused_by=()):
    e = _add(Entity(name, "Event", summary, {"book": book}))
    e.rels["participants"] = list(participants)
    e.rels["location"] = [location]
    if caused_by:
        e.rels["caused by"] = list(caused_by)
    EVENT_SEQUENCE.append(name)


# ---------------------------------------------------------------------------
# Content: places and factions
# ---------------------------------------------------------------------------
place("Troy", "Also called Ilion; the walled city of King Priam and the object of the ten-year siege.")
place("Trojan Plain", "The open ground between the city and the Achaean ships where most battles are fought.")
place("Achaean Camp", "The beached ships and fortified camp of the Achaean army, later protected by a wall and ditch.")
place("Mount Olympus", "Home of the gods, where Zeus presides over councils.")
place("Mount Ida", "The mountain above Troy from which Zeus watches the war.")
place("River Scamander", "The river (also Xanthus) that rises against Achilles in Book 21.")

faction("Achaeans", "The Greek coalition besieging Troy, led by Agamemnon (also called Danaans and Argives).")
faction("Trojans", "The defenders of Troy and their allies, led by King Priam and Hector.")
faction("Myrmidons", "Achilles' Thessalian warriors, a contingent of the Achaean army.", member_of="Achaeans")
faction("Immortals", "The Olympian gods and other divinities who intervene on both sides.")

# ---------------------------------------------------------------------------
# Content: characters
# ---------------------------------------------------------------------------
# Elders and parents
char("Atreus", "Achaean", "Mortal", "Late king of Mycenae and father of Agamemnon and Menelaus.")
char("Peleus", "Achaean", "Mortal", "Father of Achilles and husband of the sea-goddess Thetis.", spouse_of="Thetis")
char("Telamon", "Achaean", "Mortal", "King of Salamis and father of Ajax.")
char("Tydeus", "Achaean", "Mortal", "Deceased Aetolian hero, father of Diomedes.")
char("Anchises", "Trojan", "Mortal", "Trojan prince, father of Aeneas by Aphrodite.")

# Achaeans
char("Agamemnon", "Achaean", "King", "King of Mycenae and supreme commander of the Achaeans. His seizure of Briseis from Achilles drives the poem's central wrath.",
     aliases=["Son of Atreus"], father="Atreus", member_of="Achaeans", allied_with="Nestor", enemy_of="Achilles")
char("Menelaus", "Achaean", "King", "King of Sparta and aggrieved husband of Helen; the personal cause of the war.",
     father="Atreus", member_of="Achaeans", spouse_of="Helen", enemy_of="Paris")
char("Achilles", "Achaean", "Hero", "The greatest Achaean warrior, son of Peleus and the goddess Thetis. His wrath and its consequences form the poem's subject.",
     aliases=["Son of Peleus"], father="Peleus", mother="Thetis", member_of="Myrmidons",
     companion_of="Patroclus", kills="Hector")
char("Patroclus", "Achaean", "Hero", "Achilles' dearest companion, who fights in Achilles' armor and is slain by Hector.",
     member_of="Myrmidons", kills="Sarpedon")
char("Odysseus", "Achaean", "Hero", "King of Ithaca, famed for cunning counsel; an envoy in the embassy to Achilles.",
     member_of="Achaeans", allied_with=["Diomedes", "Ajax the Great"])
char("Diomedes", "Achaean", "Hero", "Young king of Argos whose aristeia in Book 5 wounds two gods.",
     father="Tydeus", member_of="Achaeans", kills="Pandarus")
char("Ajax the Great", "Achaean", "Hero", "Towering son of Telamon and the Achaeans' great defensive fighter.",
     aliases=["Telamonian Ajax"], father="Telamon", member_of="Achaeans", enemy_of="Hector")
char("Nestor", "Achaean", "Elder", "Aged king of Pylos, the army's trusted adviser.", member_of="Achaeans")
char("Phoenix", "Achaean", "Elder", "Achilles' old tutor and an envoy to him in Book 9.", member_of="Achaeans")
char("Calchas", "Achaean", "Seer", "The army's seer who reveals why Apollo has sent the plague.", member_of="Achaeans")
char("Briseis", "Achaean", "Captive", "Captive woman awarded to Achilles and taken from him by Agamemnon.", war_prize_of="Achilles")
char("Chryseis", "Trojan", "Captive", "Daughter of Chryses, taken as a prize by Agamemnon.", war_prize_of="Agamemnon", father="Chryses")
char("Chryses", "Trojan", "Priest", "Priest of Apollo whose plea for Chryseis opens the poem.")

# Trojans
char("Priam", "Trojan", "King", "Aged king of Troy, father of Hector and Paris.", member_of="Trojans", spouse_of="Hecuba")
char("Hecuba", "Trojan", "Queen", "Queen of Troy and mother of Hector and Paris.", member_of="Trojans")
char("Hector", "Trojan", "Hero", "Prince of Troy and its greatest defender; killer of Patroclus.",
     father="Priam", mother="Hecuba", member_of="Trojans", spouse_of="Andromache",
     kills="Patroclus", allied_with=["Polydamas", "Aeneas", "Sarpedon"])
char("Paris", "Trojan", "Prince", "Prince whose abduction of Helen caused the war; also called Alexandros.",
     aliases=["Alexandros"], father="Priam", mother="Hecuba", member_of="Trojans", spouse_of="Helen")
char("Helen", "Trojan", "Queen", "Wife of Menelaus, taken to Troy by Paris.", member_of="Trojans")
char("Andromache", "Trojan", "Wife", "Hector's wife, whose farewell scene in Book 6 is one of the poem's most famous.", member_of="Trojans")
char("Astyanax", "Trojan", "Child", "Infant son of Hector and Andromache.", father="Hector", mother="Andromache", member_of="Trojans")
char("Sarpedon", "Trojan", "Hero", "Lycian ally of Troy and son of Zeus, killed by Patroclus.",
     father="Zeus", member_of="Trojans", allied_with="Glaucus")
char("Glaucus", "Trojan", "Hero", "Lycian ally who exchanges armor with Diomedes in Book 6.", member_of="Trojans")
char("Aeneas", "Trojan", "Hero", "Dardanian prince saved from death by gods.", father="Anchises", mother="Aphrodite", member_of="Trojans")
char("Pandarus", "Trojan", "Archer", "Lycian archer who breaks the truce by wounding Menelaus.", member_of="Trojans")
char("Polydamas", "Trojan", "Counsellor", "Trojan commander who repeatedly gives Hector prudent advice.", member_of="Trojans")

# Immortals
char("Zeus", "Immortal", "God", "King of the gods, who honors Thetis' request by letting the Trojans prevail until Achilles returns.",
     aliases=["Cronion"], member_of="Immortals", protects=["Sarpedon", "Hector"])
char("Hera", "Immortal", "Goddess", "Queen of the gods, fierce partisan of the Achaeans.", member_of="Immortals",
     spouse_of="Zeus", protects="Achaeans")
char("Athena", "Immortal", "Goddess", "Goddess of war and wisdom, patron of the Achaeans.", father="Zeus",
     member_of="Immortals", protects=["Diomedes", "Odysseus", "Achaeans"])
char("Apollo", "Immortal", "God", "God who sends the plague on the Achaeans and later strikes Patroclus in battle.",
     father="Zeus", member_of="Immortals", protects=["Hector", "Chryses", "Trojans"])
char("Poseidon", "Immortal", "God", "Sea-god who aids the Achaeans against Zeus' wishes.", member_of="Immortals", protects="Achaeans")
char("Thetis", "Immortal", "Goddess", "Sea-goddess and mother of Achilles who petitions Zeus on his behalf.",
     member_of="Immortals", protects="Achilles")
char("Aphrodite", "Immortal", "Goddess", "Goddess of love; wounded by Diomedes while rescuing Aeneas.",
     father="Zeus", member_of="Immortals", protects=["Paris", "Aeneas"])
char("Ares", "Immortal", "God", "God of war, who supports the Trojans.", father="Zeus", mother="Hera",
     member_of="Immortals", protects="Trojans")
char("Hephaestus", "Immortal", "God", "Divine smith who forges Achilles' new armor.", father="Zeus", mother="Hera", member_of="Immortals")
char("Hermes", "Immortal", "God", "Divine messenger who escorts Priam to Achilles' tent.", father="Zeus", member_of="Immortals", protects="Priam")

# ---------------------------------------------------------------------------
# Content: plot points (narrative order). caused_by creates the causal tree;
# the chronological chain is derived from the order listed here.
# ---------------------------------------------------------------------------
E = {}  # short keys, readability only


def ev(key, name, *a, **k):
    E[key] = name
    event(name, *a, **k)


ev("chryses", "Chryses Pleads for His Daughter", 1,
   "Chryses offers ransom for Chryseis; Agamemnon harshly refuses.",
   ["Chryses", "Agamemnon", "Chryseis", "Apollo"], "Achaean Camp")
ev("plague", "Apollo's Plague", 1,
   "At Chryses' prayer Apollo shoots plague arrows into the Achaean army for nine days.",
   ["Apollo", "Achaeans"], "Achaean Camp", [E["chryses"]])
ev("quarrel", "The Quarrel of Achilles and Agamemnon", 1,
   "Calchas names the cause of the plague; Agamemnon grudgingly returns Chryseis but demands a replacement prize, and Achilles nearly kills him before Athena restrains him.",
   ["Achilles", "Agamemnon", "Calchas", "Athena", "Nestor"], "Achaean Camp", [E["plague"]])
ev("briseis", "Agamemnon Takes Briseis", 1,
   "Heralds remove Briseis from Achilles' hut; he withdraws from battle and prays for Achaean defeat.",
   ["Agamemnon", "Achilles", "Briseis"], "Achaean Camp", [E["quarrel"]])
ev("thetis", "Thetis Petitions Zeus", 1,
   "Thetis asks Zeus to give the Trojans victory until the Achaeans honor Achilles; Zeus agrees despite Hera's anger.",
   ["Thetis", "Zeus", "Hera", "Achilles"], "Mount Olympus", [E["briseis"]])
ev("dream", "Zeus Sends a Deceptive Dream", 2,
   "A false dream urges Agamemnon to attack Troy; he tests the army's morale and nearly causes a rout.",
   ["Zeus", "Agamemnon", "Odysseus", "Nestor"], "Achaean Camp", [E["thetis"]])
ev("catalogue", "The Catalogue of Ships", 2,
   "The Achaean and Trojan contingents are listed as the armies assemble.",
   ["Achaeans", "Trojans"], "Trojan Plain", [E["dream"]])
ev("duel1", "Duel of Paris and Menelaus", 3,
   "Both sides swear oaths for a single combat; Aphrodite rescues the defeated Paris.",
   ["Paris", "Menelaus", "Helen", "Aphrodite", "Priam"], "Trojan Plain", [E["catalogue"]])
ev("truce", "Pandarus Breaks the Truce", 4,
   "Athena, disguised, persuades Pandarus to wound Menelaus; the truce collapses.",
   ["Pandarus", "Menelaus", "Athena", "Agamemnon"], "Trojan Plain", [E["duel1"]])
ev("aristeia", "Diomedes' Aristeia", 5,
   "Empowered by Athena, Diomedes slays Pandarus and wounds Aeneas, Aphrodite and Ares.",
   ["Diomedes", "Athena", "Pandarus", "Aeneas", "Aphrodite", "Ares"], "Trojan Plain", [E["truce"]])
ev("farewell", "Hector Meets Andromache", 6,
   "Hector returns to Troy, rallies Paris, and bids his wife and son farewell.",
   ["Hector", "Andromache", "Astyanax", "Paris", "Helen", "Hecuba", "Glaucus", "Diomedes"], "Troy", [E["aristeia"]])
ev("ajaxduel", "Duel of Hector and Ajax", 7,
   "An inconclusive single combat ends at nightfall with an exchange of gifts.",
   ["Hector", "Ajax the Great", "Nestor"], "Trojan Plain", [E["farewell"]])
ev("tide", "Zeus Turns the Tide", 8,
   "Zeus forbids divine intervention and weighs the fates; the Trojans drive the Achaeans back to their wall.",
   ["Zeus", "Hector", "Hera", "Athena", "Achaeans", "Trojans"], "Mount Ida", [E["thetis"], E["ajaxduel"]])
ev("embassy", "Embassy to Achilles", 9,
   "Odysseus, Phoenix and Ajax offer gifts and Briseis' return; Achilles refuses.",
   ["Odysseus", "Phoenix", "Ajax the Great", "Achilles", "Agamemnon"], "Achaean Camp", [E["tide"]])
ev("nightraid", "Night Raid on the Trojan Camp", 10,
   "Odysseus and Diomedes kill the spy Dolon and slaughter the Thracian king Rhesus in his sleep.",
   ["Odysseus", "Diomedes", "Athena"], "Trojan Plain", [E["embassy"]])
ev("wounded", "The Achaean Leaders Are Wounded", 11,
   "Agamemnon, Diomedes and Odysseus are wounded; Nestor urges Patroclus to lead the Myrmidons or wear Achilles' armor.",
   ["Agamemnon", "Diomedes", "Odysseus", "Nestor", "Patroclus"], "Trojan Plain", [E["tide"]])
ev("breach", "Hector Breaches the Wall", 12,
   "Ignoring Polydamas' warning, Hector smashes the gate of the Achaean wall with a boulder.",
   ["Hector", "Polydamas", "Sarpedon", "Glaucus"], "Achaean Camp", [E["wounded"]])
ev("heraseduce", "Hera Seduces Zeus", 14,
   "Hera borrows Aphrodite's charm to lull Zeus to sleep while Poseidon rallies the Achaeans and Ajax stuns Hector.",
   ["Hera", "Zeus", "Poseidon", "Ajax the Great", "Hector", "Aphrodite"], "Mount Ida", [E["breach"]])
ev("ships", "The Trojans Reach the Ships", 15,
   "Zeus wakes, orders Apollo to revive Hector, and the Trojans fire the Achaean ships.",
   ["Zeus", "Apollo", "Hector", "Poseidon", "Ajax the Great"], "Achaean Camp", [E["heraseduce"]])
ev("armor", "Patroclus Dons Achilles' Armor", 16,
   "Achilles lets Patroclus lead the Myrmidons into battle in his armor, with orders to drive the Trojans from the ships and no further.",
   ["Patroclus", "Achilles", "Myrmidons", "Nestor"], "Achaean Camp", [E["ships"], E["embassy"]])
ev("sarpedon", "Death of Sarpedon", 16,
   "Patroclus kills Sarpedon; Zeus mourns his son but allows fate to proceed.",
   ["Patroclus", "Sarpedon", "Zeus", "Glaucus"], "Trojan Plain", [E["armor"]])
ev("patroclus", "Death of Patroclus", 16,
   "Pursuing the Trojans to the walls, Patroclus is struck by Apollo, wounded by Euphorbus, and killed by Hector.",
   ["Patroclus", "Hector", "Apollo"], "Trojan Plain", [E["sarpedon"]])
ev("body", "Battle over Patroclus' Body", 17,
   "Menelaus and Ajax defend the corpse while Hector takes Achilles' armor from it.",
   ["Menelaus", "Ajax the Great", "Hector", "Aeneas"], "Trojan Plain", [E["patroclus"]])
ev("learns", "Achilles Learns of Patroclus' Death", 18,
   "Achilles' grief ends his withdrawal; Thetis promises new armor.",
   ["Achilles", "Thetis"], "Achaean Camp", [E["body"]])
ev("shield", "Hephaestus Forges the Shield", 18,
   "Hephaestus makes a new panoply, including a shield depicting the whole world.",
   ["Hephaestus", "Thetis", "Achilles"], "Mount Olympus", [E["learns"]])
ev("reconcile", "Achilles and Agamemnon Reconcile", 19,
   "Agamemnon returns Briseis with gifts; Achilles rejoins the war and arms himself.",
   ["Achilles", "Agamemnon", "Odysseus", "Briseis"], "Achaean Camp", [E["learns"]])
ev("gods", "The Gods Join the Battle", 20,
   "Zeus lifts his ban; Achilles faces Aeneas, who is carried away by Poseidon.",
   ["Achilles", "Aeneas", "Poseidon", "Apollo", "Hera", "Athena"], "Trojan Plain", [E["reconcile"]])
ev("scamander", "Achilles at the Scamander", 21,
   "Achilles fills the river with corpses; the river-god attacks him until Hephaestus drives the flood back.",
   ["Achilles", "Hephaestus"], "River Scamander", [E["gods"]])
ev("hector", "Death of Hector", 22,
   "Abandoned by Apollo and tricked by Athena, Hector faces Achilles alone and is killed; his body is dragged behind Achilles' chariot.",
   ["Achilles", "Hector", "Athena", "Apollo", "Priam", "Hecuba"], "Troy", [E["scamander"], E["patroclus"]])
ev("games", "Funeral Games for Patroclus", 23,
   "Patroclus is cremated and honored with athletic contests.",
   ["Achilles", "Diomedes", "Ajax the Great", "Odysseus", "Nestor", "Agamemnon"], "Achaean Camp", [E["hector"]])
ev("ransom", "Priam Ransoms Hector's Body", 24,
   "Guided by Hermes, Priam enters Achilles' hut and kisses the hands that killed his son; the two weep together.",
   ["Priam", "Achilles", "Hermes", "Zeus", "Thetis"], "Achaean Camp", [E["hector"]])
ev("funeral", "Funeral of Hector", 24,
   "Troy mourns; Andromache, Hecuba and Helen lament, and Hector is buried.",
   ["Priam", "Hecuba", "Andromache", "Helen", "Paris"], "Troy", [E["ransom"]])

# ---------------------------------------------------------------------------
# Content: books
# ---------------------------------------------------------------------------
BOOK_SUMMARIES = [
    "Plague, quarrel, and Thetis' appeal to Zeus.",
    "The deceptive dream, the army's test, and the Catalogue of Ships.",
    "Oaths, Helen on the wall, and the duel of Paris and Menelaus.",
    "The truce is broken and fighting resumes.",
    "Diomedes' aristeia; gods are wounded.",
    "Glaucus and Diomedes; Hector in Troy; farewell to Andromache.",
    "Hector and Ajax duel; the truce for the dead; the Achaean wall.",
    "Zeus forbids intervention; the Trojans prevail.",
    "The embassy to Achilles is rejected.",
    "The night raid of Odysseus and Diomedes.",
    "Agamemnon's aristeia; the leaders wounded; Patroclus sent to Nestor.",
    "The Trojans assault the wall and Hector breaks the gate.",
    "Poseidon rallies the Achaeans at the ships.",
    "Hera deceives Zeus; Hector is struck down.",
    "Zeus wakes; Apollo routs the Achaeans; the ships are attacked.",
    "Patroclus in Achilles' armor; the deaths of Sarpedon and Patroclus.",
    "The struggle over Patroclus' body.",
    "Achilles learns of Patroclus' death; the shield of Hephaestus.",
    "Reconciliation; Achilles arms for battle.",
    "The gods join the battle; Achilles and Aeneas.",
    "Achilles at the river; the battle of the gods.",
    "The death of Hector.",
    "The funeral and games for Patroclus.",
    "Priam ransoms Hector; the funeral of Hector.",
]
BOOK_NAMES = {i + 1: f"Book {i + 1:02d}" for i in range(24)}


# ---------------------------------------------------------------------------
# Ontology loading and validation
# ---------------------------------------------------------------------------
class OntologyError(Exception):
    pass


def load_ontology(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        onto = yaml.safe_load(fh)
    errors = []
    types = onto.get("node_types") or {}
    rels = onto.get("relations") or {}
    inv_defs: dict[str, str] = {}

    for rname, r in rels.items():
        if r.get("role") not in ROLES:
            errors.append(f"relation '{rname}': role must be one of {ROLES}")
        for side in ("domain", "range"):
            for t in r.get(side, []):
                if t not in types:
                    errors.append(f"relation '{rname}': unknown node type '{t}' in {side}")
        if r.get("symmetric") and r.get("inverse"):
            errors.append(f"relation '{rname}': symmetric relations take no inverse")
        inv = r.get("inverse")
        if inv:
            if r.get("inverse_role") not in ROLES:
                errors.append(f"relation '{rname}': inverse_role must be one of {ROLES}")
            if inv in rels:
                errors.append(f"relation '{rname}': inverse '{inv}' also declared as a forward relation")
            prev = inv_defs.setdefault(inv, r["inverse_role"])
            if prev != r["inverse_role"]:
                errors.append(f"inverse '{inv}' has conflicting roles")
    for key, rname in (onto.get("generated") or {}).items():
        if rname not in rels:
            errors.append(f"generated.{key}: unknown relation '{rname}'")
    if errors:
        raise OntologyError("Invalid ontology:\n  - " + "\n  - ".join(errors))
    return onto


def add_generated_edges(onto: dict) -> None:
    gen = onto["generated"]
    ENTITIES.setdefault(WORK, Entity(
        WORK, "Work",
        "Homer's epic of the wrath of Achilles in the tenth year of the Trojan War, in 24 books."))
    for n, name in BOOK_NAMES.items():
        b = Entity(name, "Book", BOOK_SUMMARIES[n - 1], {"number": n})
        b.rels[gen["book_to_work"]] = [WORK]
        ENTITIES[name] = b
    for n in range(1, 24):
        ENTITIES[BOOK_NAMES[n]].rels[gen["book_chain"]] = [BOOK_NAMES[n + 1]]
    for i, ename in enumerate(EVENT_SEQUENCE):
        e = ENTITIES[ename]
        e.props["order"] = i + 1
        e.rels[gen["event_to_book"]] = [BOOK_NAMES[e.props["book"]]]
        if i + 1 < len(EVENT_SEQUENCE):
            e.rels[gen["event_chain"]] = [EVENT_SEQUENCE[i + 1]]


def build_edges(onto: dict) -> list[tuple[str, str, str]]:
    """Validate declared edges and expand inverses/symmetry. Returns deduped edges."""
    rels = onto["relations"]
    errors: list[str] = []
    seen: "OrderedDict[tuple, None]" = OrderedDict()

    for ent in ENTITIES.values():
        for rname, targets in ent.rels.items():
            r = rels.get(rname)
            if r is None:
                errors.append(f"{ent.name}: relation '{rname}' is not in the ontology")
                continue
            if ent.type not in r.get("domain", [ent.type]):
                errors.append(f"{ent.name} ({ent.type}) is outside domain of '{rname}'")
            for t in targets:
                tgt = ENTITIES.get(t)
                if tgt is None:
                    errors.append(f"{ent.name} --{rname}--> {t}: target note does not exist")
                    continue
                if tgt.type not in r.get("range", [tgt.type]):
                    errors.append(f"{ent.name} --{rname}--> {t}: target type {tgt.type} outside range")
                    continue
                seen[(ent.name, rname, t)] = None
                if onto["vault"].get("write_inverse", True):
                    if r.get("symmetric"):
                        seen[(t, rname, ent.name)] = None
                    elif r.get("inverse"):
                        seen[(t, r["inverse"], ent.name)] = None
    if errors:
        raise OntologyError("Data violates ontology:\n  - " + "\n  - ".join(errors))
    return list(seen)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def role_of(onto: dict, rname: str) -> str:
    r = onto["relations"].get(rname)
    if r:
        return r["role"]
    for rr in onto["relations"].values():
        if rr.get("inverse") == rname:
            return rr["inverse_role"]
    raise KeyError(rname)


def ordered_relation_names(onto: dict) -> list[str]:
    names: list[str] = []
    for n, r in onto["relations"].items():
        names.append(n)
        if r.get("inverse") and r["inverse"] not in names:
            names.append(r["inverse"])
    return names


def yaml_dump(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=10_000).rstrip()


def write_note(path: Path, front: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{yaml_dump(front)}\n---\n\n{body.rstrip()}\n", encoding="utf-8")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def write_vault(out: Path, onto: dict, edges: list[tuple[str, str, str]]) -> dict:
    vault_cfg = onto["vault"]
    by_src: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for s, rname, t in edges:
        by_src[s][rname].append(t)
    field_order = ordered_relation_names(onto)

    counts: dict[str, int] = defaultdict(int)
    for ent in ENTITIES.values():
        ntype = onto["node_types"][ent.type]
        folder = out / ntype.get("folder", "")
        front: dict = {}
        front[vault_cfg["type_property"]] = ent.type
        front[vault_cfg["tag_property"]] = [slug(ent.type)]
        if ent.aliases:
            front["aliases"] = ent.aliases
        for k, v in ent.props.items():
            front[k] = v
        rels = by_src.get(ent.name, {})
        for fname in field_order:
            if fname in rels:
                front[fname] = [f"[[{t}]]" for t in sorted(rels[fname], key=_sort_key)]
        body = f"# {ent.name}\n\n{ent.body}\n"
        write_note(folder / f"{ent.name}.md", front, body)
        counts[ent.type] += 1
    return counts


def _sort_key(name: str):
    e = ENTITIES[name]
    return (e.props.get("order", 0), e.props.get("number", 0), name)


def write_setup_note(out: Path, onto: dict, edges) -> None:
    fields_by_role: dict[str, list[str]] = {r: [] for r in ROLES}
    for n in ordered_relation_names(onto):
        fields_by_role[role_of(onto, n)].append(n)

    lines = [
        "# Ontology Setup", "",
        "This vault was generated from the ontology file. Relationships live in note",
        "properties (frontmatter) so K-Plex can read them directly.", "",
        "## Map fields to compass roles", "",
        "Open **Settings → K-Plex → Ontology → Manage ontology** and assign each",
        "property below to the matching role. Properties that are inverses of each",
        "other (for example `kills` and `killed by`) can be paired there; this vault",
        "writes both sides so either note shows the link.", "",
        "| Role | Compass | Properties |", "|---|---|---|",
    ]
    compass = {"parent": "North", "child": "South", "friend": "West",
               "challenger": "East", "previous": "West (sequence)", "next": "East (sequence)"}
    for role in ROLES:
        props = ", ".join(f"`{p}`" for p in fields_by_role[role]) or "-"
        lines.append(f"| {role.capitalize()} | {compass[role]} | {props} |")
    lines += [
        "", "## Note types", "",
        f"Each note has a `{onto['vault']['type_property']}` property and a matching tag",
        "(K-Plex Note Types are tag-based). Style them under **Visual styling → Node styling**.", "",
        "| Type | Suggested icon | Suggested color | Meaning |", "|---|---|---|---|",
    ]
    for tname, t in onto["node_types"].items():
        lines.append(f"| {tname} | {t.get('icon', '')} | `{t.get('color', '')}` | {t.get('description', '')} |")
    lines += ["", "## Relationship dictionary", "", "| Field | Role | Domain | Range | Meaning |", "|---|---|---|---|---|"]
    for n, r in onto["relations"].items():
        inv = f" (inverse `{r['inverse']}`)" if r.get("inverse") else (" (symmetric)" if r.get("symmetric") else "")
        lines.append(f"| `{n}`{inv} | {r['role']} | {', '.join(r.get('domain', []))} | "
                     f"{', '.join(r.get('range', []))} | {r.get('description', '')} |")
    lines += ["", "## Where to start", "",
              "Run **K-Plex: Open canvas** and search for `Death of Hector` (a plot point with causes to the north,",
              "participants to the west, and a chronological chain east/west), or for `Achilles` (family, loyalties,",
              "and kills). Try Graph Lenses on a field such as `kills` or `protects`.", "",
              f"Generated: {len(edges)} relationship edges across {len(ENTITIES)} notes."]
    (out / "00 Ontology Setup.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="Generate a K-Plex-ready Iliad vault for Obsidian.")
    ap.add_argument("--ontology", type=Path, default=here / "iliad_ontology.yaml",
                    help="path to the ontology YAML (default: next to this script)")
    ap.add_argument("--out", type=Path, default=Path("Iliad Vault"), help="output vault folder")
    ap.add_argument("--check", action="store_true", help="validate data against the ontology and exit")
    args = ap.parse_args(argv)

    try:
        onto = load_ontology(args.ontology)
        add_generated_edges(onto)
        edges = build_edges(onto)
    except OntologyError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Ontology OK: {len(onto['relations'])} relations, {len(onto['node_types'])} node types.")
    print(f"Data OK: {len(ENTITIES)} notes, {len(edges)} edges (inverses included).")
    if args.check:
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    counts = write_vault(args.out, onto, edges)
    write_setup_note(args.out, onto, edges)
    for t, n in sorted(counts.items()):
        print(f"  {t:<10} {n}")
    print(f"Vault written to: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
