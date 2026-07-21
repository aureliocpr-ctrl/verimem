"""Legitimate business/vertical facts that TRIP the L1.x anti-confabulation
detectors — the corpus that measures whether those detectors, built for an
AGENT narrating its own code work, misfire on a MEMORY PRODUCT storing a
customer's ordinary domain facts.

Every line here is a TRUE, ordinary fact a lawyer / engineer / HR / clinician /
PM would store. None is a status claim about software the writer built. If the
write-gate quarantines it, that is a false positive on legitimate knowledge —
the same keyword-blind class as the telemetry-routing default.

Grouped by the detector each is expected to trip, so the measurement names the
culprit, not just a rate.
"""
from __future__ import annotations

#: (fact, vertical, detector_expected_to_trip)
BUSINESS_FACTS: list[tuple[str, str, str]] = [
    # --- L1.10 works/confirmed ---
    ("Sofia works for the logistics division.", "hr", "works"),
    ("The new arbitration clause works in favour of the tenant.", "legal", "works"),
    ("Dr. Rossi confirmed the biopsy results on 12 March.", "clinical", "works"),
    ("The settlement resolved all outstanding claims between the parties.",
     "legal", "works"),
    ("The load-balancing valve works at pressures up to 12 bar.",
     "engineering", "works"),
    ("The mediation succeeded and both parties signed the accord.",
     "legal", "works"),

    # --- L1.0/L1 deployed/shipped ---
    ("The bridge expansion joint was deployed along the north span in 2021.",
     "engineering", "deployed"),
    ("The vaccine was shipped to 40 regional clinics in the first week.",
     "clinical", "shipped"),
    ("The client shipped the disputed goods before the embargo date.",
     "legal", "shipped"),

    # --- L1.12 security/hardened ---
    ("The vault door is rated secure against a 60-minute forced attack.",
     "engineering", "security"),
    ("The witness was moved to a secure location before the trial.",
     "legal", "security"),
    ("The hardened concrete bunker meets the ballistic protection standard.",
     "engineering", "security"),

    # --- L1.15 tested/verified ---
    ("The steel cable was tested to a breaking load of 400 kilonewtons.",
     "engineering", "tested"),
    ("The patient was tested for the antibody on admission.", "clinical",
     "tested"),
    ("The signature on the will was verified by a handwriting expert.",
     "legal", "tested"),

    # --- L1.11 production-ready / stable / robust ---
    ("The foundation design is robust against a magnitude-7 earthquake.",
     "engineering", "prod_ready"),
    ("The company reached a stable market position after the merger.",
     "business", "prod_ready"),

    # --- L1.13 completion (done/complete/finished) ---
    ("The due-diligence review was completed before the acquisition closed.",
     "legal", "completion"),
    ("The surgical procedure was completed without complications.",
     "clinical", "completion"),
    ("The building inspection is finished and the certificate was issued.",
     "engineering", "completion"),

    # --- L1.14 documentation ---
    ("The easement is documented in the 1998 deed at the land registry.",
     "legal", "documentation"),
    ("The failure mode is documented in the maintenance logbook.",
     "engineering", "documentation"),

    # --- L1.17 monitored ---
    ("The patient's blood pressure is monitored every four hours.",
     "clinical", "monitored"),
    ("The dam's water level is monitored by three independent sensors.",
     "engineering", "monitored"),

    # --- L1.9/L1.19 performance / quantitative ---
    ("The new turbine is 15 percent more efficient than the 2019 model.",
     "engineering", "performance"),
    ("Q3 sales grew 22 percent over the same quarter last year.",
     "business", "quantitative"),

    # --- L1 automated/scheduled ---
    ("The court hearing is scheduled for 14 October at 9 a.m.", "legal",
     "automated"),
    ("The MRI scan is scheduled for next Tuesday morning.", "clinical",
     "automated"),

    # --- L1 approval ---
    ("The zoning variance was approved by the municipal board.", "legal",
     "approval"),
    ("The drug was approved by the regulator for paediatric use.", "clinical",
     "approval"),
]


#: control set — facts with NO trigger word, to confirm the gate admits plain
#: business knowledge cleanly (a floor that quarantines everything is useless).
BUSINESS_CONTROLS: list[tuple[str, str]] = [
    ("The office in Milan has 40 desks.", "business"),
    ("The contract term ends on 31 January 2027.", "legal"),
    ("The beam spans 24 metres between supports.", "engineering"),
    ("The patient is 54 years old.", "clinical"),
    ("Giulia is the head of the security team.", "hr"),
    ("The invoice total is 12,450 euros.", "business"),
]
