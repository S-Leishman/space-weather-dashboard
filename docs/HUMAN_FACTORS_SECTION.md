# Human Factors Foundation

Aevion SpaceOps is informed by prior academic work in air traffic control human factors and unmanned-aircraft risk assessment. The design reflects a familiar aviation-safety principle: consequential decisions should be evaluated in the context of the human operator, the software and procedures they use, the hardware involved, and the operating environment.

ICAO's SHELL human-factors model formalizes those interactions across Software, Hardware, Environment, and Liveware, with emphasis on mismatches between the human operator and surrounding system components. The project also draws on system-safety risk-management concepts used in MIL-STD-882, including explicit hazard identification, risk assessment, mitigation, and defined authority for accepting residual risk.

Those ideas influence three design choices in this prototype:

- **Evidence sufficiency** — a successful decision state requires supporting evidence rather than absence of an error.
- **Uncertainty preservation** — `UNKNOWN` and `HOLD` remain explicit outcomes when evidence is incomplete or authority is unavailable.
- **Human authority** — the system provides decision support and evidence; consequential action remains with the human operator.

The resulting evidence package is intended to support a later question central to operational review: what information was available, what supported the system's result, what remained uncertain, and who retained authority to act.

**Author:** Scott Leishman, Arizona State University student.
**Project:** Aevion SpaceOps.
**Affiliation:** Aevion LLC.
