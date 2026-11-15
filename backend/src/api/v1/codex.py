from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter(prefix="/codex", tags=["Codex & Science Knowledge Cards"])

class CodexCard(BaseModel):
    id: str
    title: str
    subtitle: str
    category: str
    icon_name: str
    evidence: str = Field(description="established, emerging, or illustrative")
    is_locked: bool
    unlock_condition: Optional[str] = None
    unlock_progress_current: Optional[int] = 0
    unlock_progress_target: Optional[int] = 0
    plain_summary: str
    why_it_matters: str
    sources: List[str]
    related_zone: str = "Whole Body"
    related_quest_id: Optional[str] = None

class UnlockResponse(BaseModel):
    card_id: str
    status: str
    is_locked: bool
    celebrate: bool
    message: str
    card: CodexCard

CODEX_CARDS_STATE: List[dict] = [
    {
        "id": "tregs",
        "title": "Regulatory T-Cells (Tregs)",
        "subtitle": "Adaptive Immune System Down-Regulation",
        "category": "Immune Stress Context",
        "icon_name": "shield",
        "evidence": "established",
        "is_locked": False,
        "unlock_condition": None,
        "unlock_progress_current": 1,
        "unlock_progress_target": 1,
        "plain_summary": "Microgravity and high-stress operational conditions elevate circulating FOXP3+ regulatory T-cells, temporarily blunting acute inflammatory cascades.",
        "why_it_matters": "While dampening autoimmune reactivity and high-strain muscle inflammation, persistent Treg elevation elevates vulnerability to subclinical viral reactivations and slows response to novel pathogens during deep-space transit.",
        "sources": [
            "NASA Twins Study: Multi-omics analysis of a yearlong human spaceflight (Science 2019, DOI: 10.1126/science.aau8650)",
            "Crucian et al., Immune System Dysregulation During Long-Duration Spaceflight (J. Interferon & Cytokine Res 2014)",
            "NASA Human Research Program Evidence Book: Risk of Adverse Health Event Due to Altered Immune Response",
        ],
        "related_zone": "Immune",
        "related_quest_id": "hydration_target",
    },
    {
        "id": "latent_viruses",
        "title": "Latent Viral Reactivation",
        "subtitle": "EBV, CMV & VZV Stress Biomarkers",
        "category": "Immune Stress Context",
        "icon_name": "drop",
        "evidence": "established",
        "is_locked": False,
        "unlock_condition": None,
        "unlock_progress_current": 1,
        "unlock_progress_target": 1,
        "plain_summary": "Subclinical shedding of Epstein-Barr Virus (EBV), Cytomegalovirus (CMV), and Varicella Zoster Virus (VZV) frequently increases without symptomatic disease during long-duration orbital missions.",
        "why_it_matters": "Viral shedding serves as a sensitive, early-stage physiological indicator of cumulative mission stress, elevated salivary cortisol, and suppressed cell-mediated immunity before overt clinical symptoms emerge.",
        "sources": [
            "Mehta et al., Reactivation of Latent Viruses in Astronauts Is Linked to Immune Dysfunction (Front. Microbiol. 2017)",
            "Rooney et al., 6-Month Spaceflight Suppresses T-Cell Function and Increases Latent Viral Shedding (J. Appl. Physiol. 2019)",
            "NASA Evidence Report: Risk of Crew Immune Dysregulation in Planetary Exploration",
        ],
        "related_zone": "Immune",
        "related_quest_id": "hydration_target",
    },
    {
        "id": "circadian_light",
        "title": "Circadian Entrainment & Dynamic Lighting",
        "subtitle": "480nm Photoreceptor Regulation",
        "category": "Sleep & Circadian",
        "icon_name": "sun",
        "evidence": "emerging",
        "is_locked": False,
        "unlock_condition": None,
        "unlock_progress_current": 1,
        "unlock_progress_target": 1,
        "plain_summary": "The rapid 90-minute orbital day/night cycle causes circadian desynchrony unless synchronized by habitat solid-state LED systems shifting between 480nm blue-enriched morning light and blue-depleted evening spectrums.",
        "why_it_matters": "Maintains natural melatonin release profiles, preserves restorative slow-wave delta sleep, and reduces microsleeps or high-speed psychomotor vigilance degradation during critical docking operations.",
        "sources": [
            "Brainard et al., Solid-State Light-Emitting Diode Lighting on the ISS (Life Sci. Space Res. 2016)",
            "Barger et al., Prevalence of Sleep Deficiency and Sleep-Inducing Drug Use in Astronauts (Lancet Neurol. 2014)",
            "NASA Human Research Program: Behavioral Health and Performance Evidence",
        ],
        "related_zone": "Brain / Sleep",
        "related_quest_id": "cognitive_vigilance",
    },
    {
        "id": "fluid_shift",
        "title": "Cephalad Fluid Shift & SANS",
        "subtitle": "Spaceflight-Associated Neuro-Ocular Syndrome",
        "category": "Vascular & Neuro",
        "icon_name": "pulse",
        "evidence": "established",
        "is_locked": False,
        "unlock_condition": None,
        "unlock_progress_current": 1,
        "unlock_progress_target": 1,
        "plain_summary": "Loss of hydrostatic gravity gradient shifts ~1.5 to 2.0 liters of venous and interstitial fluid rostrally into the chest, neck, and cranium, increasing internal jugular venous cross-sectional area.",
        "why_it_matters": "Elevated central venous pressure and disrupted glymphatic drainage contribute to optic disc edema, posterior globe flattening, and hyperopic shifts in up to 70% of long-duration ISS crew members.",
        "sources": [
            "Stenger et al., Spaceflight Associated Neuro-ocular Syndrome (NASA HRP 2017)",
            "Mader et al., Optic Disc Edema and Globe Flattening in Astronauts (Ophthalmology 2011)",
            "Marshall-Goebel et al., Assessment of Jugular Venous Blood Flow Stasis in Spaceflight (JAMA Netw Open 2019)",
        ],
        "related_zone": "Heart & Vascular",
        "related_quest_id": "hydration_target",
    },
    {
        "id": "radiation",
        "title": "Galactic Cosmic Radiation (GCR) & SPE",
        "subtitle": "High-Z/Energy (HZE) Track Damage",
        "category": "Deep Space Environment",
        "icon_name": "shield",
        "evidence": "emerging",
        "is_locked": True,
        "unlock_condition": "Complete 3 cumulative radiation dosimeter telemetry logs or reach Sol 45",
        "unlock_progress_current": 2,
        "unlock_progress_target": 3,
        "plain_summary": "High-energy heavy atomic nuclei (HZE ions like Fe-56) penetrate deep spacecraft hulls, causing dense, clustered ionization tracks and complex DNA double-strand breaks.",
        "why_it_matters": "Clustered DNA lesions challenge standard homologous recombination repair mechanisms. Real-time habitat monitoring and active water-wall storm shelter protocols mitigate acute dose limits during solar particle events (SPE).",
        "sources": [
            "Cucinotta et al., Space Radiation Cancer Risk Projections for Exploration Missions (Life Sci Space Res 2014)",
            "Zeitlin et al., Measurements of Energetic Particle Radiation in Transit to Mars on the MSL (Science 2013)",
            "NASA Space Radiation Technical Reports (TP-2013-217377)",
        ],
        "related_zone": "Whole Body",
        "related_quest_id": "ared_exercise",
    },
    {
        "id": "sleep",
        "title": "Sleep Architecture & Glymphatic Clearance",
        "subtitle": "Slow-Wave Sleep & Interstitial Flushing",
        "category": "Sleep & Neuro",
        "icon_name": "moon",
        "evidence": "illustrative",
        "is_locked": True,
        "unlock_condition": "Record 5 consecutive Sol sleep countermeasure evaluations",
        "unlock_progress_current": 4,
        "unlock_progress_target": 5,
        "plain_summary": "Microgravity alters slow-wave (N3) and REM sleep architecture, which can impair intracranial interstitial fluid convective exchange driven by the brain's glymphatic system.",
        "why_it_matters": "Restorative deep sleep is vital for clearing neuro-metabolic waste, consolidating technical flight memory, stabilizing emotional equilibrium in high-isolation habitats, and regulating autonomic cardiovascular tone.",
        "sources": [
            "Xie et al., Sleep Drives Metabolite Clearance from the Adult Brain (Science 2013)",
            "Basner et al., Mars 520-D Mission Simulation Reveals Persistent Sleep and Circadian Issues (PNAS 2013)",
            "NASA Behavioral Health Evidence Book: Risk of Performance Decrements Due to Sleep Loss",
        ],
        "related_zone": "Brain / Sleep",
        "related_quest_id": "cognitive_vigilance",
    },
]

@router.get("", response_model=List[CodexCard])
def get_all_codex_cards():
    """Returns all scientific knowledge cards with locked/unlocked state and evidence grading."""
    return CODEX_CARDS_STATE

@router.get("/{card_id}", response_model=CodexCard)
def get_codex_card(card_id: str):
    card = next((c for c in CODEX_CARDS_STATE if c["id"] == card_id), None)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Codex card with ID '{card_id}' not found.",
        )
    return card

@router.post("/{card_id}/unlock", response_model=UnlockResponse)
def unlock_codex_card(card_id: str):
    """Idempotently unlock a science codex card."""
    card = next((c for c in CODEX_CARDS_STATE if c["id"] == card_id), None)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Codex card with ID '{card_id}' not found.",
        )
    
    was_already_unlocked = not card["is_locked"]
    card["is_locked"] = False
    card["unlock_progress_current"] = card["unlock_progress_target"]

    return UnlockResponse(
        card_id=card_id,
        status="unlocked",
        is_locked=False,
        celebrate=not was_already_unlocked,
        message=f"Codex Briefing '{card['title']}' is now fully unlocked for mission reference." if not was_already_unlocked else "Card was already unlocked.",
        card=CodexCard(**card),
    )
