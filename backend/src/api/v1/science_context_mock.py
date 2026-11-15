from fastapi import APIRouter, status
from src.schemas.astronaut import (
    EvidenceLevelEnum,
    ScienceContextCard,
    ScienceContextResponse,
)

router = APIRouter(prefix="/science-context", tags=["Science Context Mock"])

MOCK_CARDS = [
    ScienceContextCard(
        id="sc-tregs",
        title="Regulatory T-Cell (Treg) Modulation in Spaceflight",
        plain_summary="Observational spaceflight studies report alterations in regulatory T-cell proportions and suppressor activity during orbital missions.",
        why_it_matters="Altered immune cell distribution shifts adaptive immune response context in microgravity. Check with flight surgeon for surveillance context.",
        evidence_level=EvidenceLevelEnum.EMERGING,
        sources=["Crucian et al., J. Leukocyte Biology", "NASA Twins Study (Science, 2019)"],
        linked_signals=["treg_ratio", "immune_activation", "cytokine_profile"],
    ),
    ScienceContextCard(
        id="sc-latent-virus",
        title="Latent Virus Reactivation Surveillance",
        plain_summary="Subclinical shedding of latent herpesviruses (EBV, VZV, CMV) has been documented in astronauts during spaceflight due to physical and microgravity stressors.",
        why_it_matters="Tracking shedding biomarker trends provides objective context for cellular immune status without indicating clinical status. Check with flight surgeon.",
        evidence_level=EvidenceLevelEnum.ESTABLISHED,
        sources=["Rooney et al., Frontiers in Microbiology", "NASA HRP Spaceflight Immunology"],
        linked_signals=["viral_load_ebv", "viral_load_vzv", "salivary_biomarkers"],
    ),
    ScienceContextCard(
        id="sc-circadian-light",
        title="Circadian Light Phase Regulation",
        plain_summary="Dynamic solid-state lighting schedules modulate spectral irradiance and illuminance aboard spacecraft to synchronize human circadian clocks.",
        why_it_matters="Maintains circadian phase alignment, cognitive operational readiness, and nocturnal sleep quality across orbital mission cycles.",
        evidence_level=EvidenceLevelEnum.ESTABLISHED,
        sources=["Brainard et al., Lighting Research & Technology", "NASA HRP BHP Sleep Standards"],
        linked_signals=["circadian_phase_offset", "light_lux", "blue_spectrum_irradiance", "sleep_duration"],
    ),
    ScienceContextCard(
        id="sc-radiation",
        title="Galactic Cosmic Rays & Solar Particle Event Dosimetry",
        plain_summary="Beyond low Earth orbit, crew members encounter ionizing cosmic rays and intermittent solar particle events requiring cumulative dosimetry.",
        why_it_matters="Dosimetric trend tracking provides critical environmental context to optimize active vehicle shielding and EVA scheduling under ALARA principles.",
        evidence_level=EvidenceLevelEnum.ESTABLISHED,
        sources=["Cucinotta et al., Radiation Research", "NASA Space Radiation Program Element"],
        linked_signals=["radiation_dose_rate", "cumulative_absorbed_dose", "flux_rate"],
    ),
    ScienceContextCard(
        id="sc-fluid-shift",
        title="Cephalad Fluid Redistribution",
        plain_summary="In microgravity, the absence of hydrostatic pressure gradients causes approximately two liters of body fluid to shift toward the chest and head.",
        why_it_matters="Induces central venous engorgement and physiological remodeling trends. Monitoring baseline shift guides countermeasure fluid-loading protocols.",
        evidence_level=EvidenceLevelEnum.ESTABLISHED,
        sources=["Hargens & Richardson, J. Applied Physiology", "NASA SANS Research Group"],
        linked_signals=["blood_pressure_systolic", "blood_pressure_diastolic", "jugular_vein_cross_section", "intraocular_pressure"],
    ),
    ScienceContextCard(
        id="sc-sleep",
        title="Sleep Architecture & Behavioral Rhythmicity",
        plain_summary="Microgravity, altered sleep berths, and mission operations frequently fragment restorative slow-wave and REM sleep architecture.",
        why_it_matters="Restorative sleep trends directly underpin neurobehavioral readiness, executive decision capability, and physical resilience on long-duration exploration.",
        evidence_level=EvidenceLevelEnum.ESTABLISHED,
        sources=["Basner et al., Sleep", "NASA Behavioral Health and Performance Division"],
        linked_signals=["sleep_duration", "rem_percentage", "sleep_efficiency", "fatigue"],
    ),
]


@router.get(
    "",
    response_model=ScienceContextResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Scientific Context Cards",
    description="Returns physiological mechanisms, educational background, and linked signals for decision support.",
)
async def get_science_context() -> ScienceContextResponse:
    """Mock endpoint returning science context cards."""
    return ScienceContextResponse(cards=MOCK_CARDS)
