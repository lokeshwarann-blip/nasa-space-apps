"use client";

import React, { useState, useEffect } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";

export interface CodexCardItem {
    id: string;
    title: string;
    subtitle: string;
    category: string;
    icon_name: string;
    evidence: "established" | "emerging" | "illustrative";
    is_locked: boolean;
    unlock_condition?: string | null;
    unlock_progress_current?: number;
    unlock_progress_target?: number;
    plain_summary: string;
    why_it_matters: string;
    sources: string[];
    related_zone: string;
    related_quest_id?: string | null;
}

interface CodexViewProps {
    alertLevel?: StatusLevel;
    gamificationEnabled?: boolean;
    onToggleGamification?: () => void;
    onNavigateToQuest?: (questId: string) => void;
}

const DEFAULT_CARDS: CodexCardItem[] = [
    {
        id: "tregs",
        title: "Regulatory T-Cells (Tregs)",
        subtitle: "Adaptive Immune System Down-Regulation",
        category: "Immune Stress Context",
        icon_name: "shield",
        evidence: "established",
        is_locked: false,
        unlock_condition: null,
        unlock_progress_current: 1,
        unlock_progress_target: 1,
        plain_summary:
            "Microgravity and operational stress elevate circulating FOXP3+ regulatory T-cells, temporarily blunting acute inflammatory cascades.",
        why_it_matters:
            "While dampening autoimmune reactivity, persistent Treg elevation elevates vulnerability to subclinical viral reactivations during deep-space transit.",
        sources: [
            "NASA Twins Study: Multi-omics analysis of a yearlong human spaceflight (Science 2019, DOI: 10.1126/science.aau8650)",
            "Crucian et al., Immune System Dysregulation During Long-Duration Spaceflight (J. Interferon & Cytokine Res 2014)",
            "NASA Human Research Program Evidence Book: Risk of Adverse Health Event Due to Altered Immune Response",
        ],
        related_zone: "Immune",
        related_quest_id: "hydration_target",
    },
    {
        id: "latent_viruses",
        title: "Latent Viral Reactivation",
        subtitle: "EBV, CMV & VZV Stress Biomarkers",
        category: "Immune Stress Context",
        icon_name: "drop",
        evidence: "established",
        is_locked: false,
        unlock_condition: null,
        unlock_progress_current: 1,
        unlock_progress_target: 1,
        plain_summary:
            "Subclinical shedding of Epstein-Barr Virus, Cytomegalovirus, and Varicella Zoster Virus increases without symptomatic disease during orbital missions.",
        why_it_matters:
            "Viral shedding serves as a sensitive indicator of cumulative mission stress and suppressed cell-mediated immunity before overt symptoms emerge.",
        sources: [
            "Mehta et al., Reactivation of Latent Viruses in Astronauts Is Linked to Immune Dysfunction (Front. Microbiol. 2017)",
            "Rooney et al., 6-Month Spaceflight Suppresses T-Cell Function and Increases Latent Viral Shedding (J. Appl. Physiol. 2019)",
            "NASA Evidence Report: Risk of Crew Immune Dysregulation in Planetary Exploration",
        ],
        related_zone: "Immune",
        related_quest_id: "hydration_target",
    },
    {
        id: "circadian_light",
        title: "Circadian Entrainment & Dynamic Lighting",
        subtitle: "480nm Photoreceptor Regulation",
        category: "Sleep & Circadian",
        icon_name: "sun",
        evidence: "emerging",
        is_locked: false,
        unlock_condition: null,
        unlock_progress_current: 1,
        unlock_progress_target: 1,
        plain_summary:
            "The 90-minute orbital day/night cycle causes circadian desynchrony unless synchronized by habitat LED systems shifting between 480nm morning blue light and blue-depleted evening light.",
        why_it_matters:
            "Preserves restorative slow-wave sleep and reduces microsleeps during critical docking operations.",
        sources: [
            "Brainard et al., Solid-State Light-Emitting Diode Lighting on the ISS (Life Sci. Space Res. 2016)",
            "Barger et al., Prevalence of Sleep Deficiency and Sleep-Inducing Drug Use in Astronauts (Lancet Neurol. 2014)",
            "NASA Human Research Program: Behavioral Health and Performance Evidence",
        ],
        related_zone: "Brain / Sleep",
        related_quest_id: "cognitive_vigilance",
    },
    {
        id: "radiation_dna",
        title: "Galactic Cosmic Radiation & Inversion DNA Damage",
        subtitle: "Chromosomal Aberrations & DNA Repair Kinetics",
        category: "Radiation Environment",
        icon_name: "shield",
        evidence: "established",
        is_locked: false,
        unlock_condition: null,
        unlock_progress_current: 1,
        unlock_progress_target: 1,
        plain_summary:
            "High-Z and high-energy (HZE) cosmic ray nuclei produce densely ionizing track structures, generating complex double-strand DNA breaks that challenge canonical non-homologous end joining repair.",
        why_it_matters:
            "Quantifies long-term carcinogenic risk context and dictates the necessity of passive hydrogen-rich storm shelter countermeasure deployment during solar particle events.",
        sources: [
            "Cucinotta et al., Space Radiation Risks to the Central Nervous System (Life Sci. Space Res. 2014)",
            "NASA Twins Study: Telomere length dynamics and DNA damage response (Science 2019)",
            "Chancellor et al., Space Radiation: The Number One Risk to Astronaut Health beyond Low Earth Orbit (Life 2018)",
        ],
        related_zone: "Immune",
        related_quest_id: "ared_exercise",
    },
    {
        id: "fluid_shift",
        title: "Cephalad Fluid Shift & SANS Pathophysiology",
        subtitle: "Venous Engorgement & Ocular Remodeling",
        category: "Cardiovascular & Ocular",
        icon_name: "drop",
        evidence: "established",
        is_locked: true,
        unlock_condition: "Complete 2 scheduled Lower Body Negative Pressure (LBNP) runs or ARED resistance logs",
        unlock_progress_current: 1,
        unlock_progress_target: 2,
        plain_summary:
            "Absence of hydrostatic gradient shifts approximately 1.5 to 2.0 liters of interstitial fluid toward the head, elevating internal jugular vein pressure and optic nerve sheath diameter.",
        why_it_matters:
            "Central driver of Spaceflight-Associated Neuro-ocular Syndrome (SANS), inducing hyperopic refractive shifts, cotton wool spots, and choroidal folds during long missions.",
        sources: [
            "Stenger et al., Risk of Spaceflight-Associated Neuro-ocular Syndrome (NASA HRP Evidence Report 2017)",
            "Marshall-Goebel et al., Assessment of Jugular Venous Blood Flow and Thrombosis During Spaceflight (JAMA Netw. Open 2019)",
            "Macias et al., Lower Body Negative Pressure Countermeasure for Fluid Redistribution (J. Physiol. 2020)",
        ],
        related_zone: "Cardiovascular",
        related_quest_id: "ared_exercise",
    },
    {
        id: "sleep_architecture",
        title: "Microgravity Sleep Architecture Fragmentation",
        subtitle: "REM / Delta Wave Reduction",
        category: "Sleep & Circadian",
        icon_name: "moon",
        evidence: "illustrative",
        is_locked: true,
        unlock_condition: "Submit 3 consecutive nominal morning wellness check-ins",
        unlock_progress_current: 2,
        unlock_progress_target: 3,
        plain_summary:
            "Ambient acoustics, mechanical ventilation vibration, microgravity posture instability, and elevated ambient carbon dioxide disrupt polysomnography architecture, compressing Stage 3/4 slow-wave sleep.",
        why_it_matters:
            "Progressive sleep architecture deficits directly correlate with slowed cognitive reaction latency, degraded fine-motor control, and elevated systemic sympathetic tone.",
        sources: [
            "Dijk et al., Amplitude Reduction and Phase Shifts of Circadian Rhythms in Astronauts (Am. J. Physiol. 2001)",
            "Basner et al., Psychological and Behavioral Changes During Long-Duration Spaceflight (PLoS ONE 2014)",
        ],
        related_zone: "Brain / Sleep",
        related_quest_id: "cognitive_vigilance",
    },
];

export default function CodexView({
    onNavigateToQuest,
}: CodexViewProps) {
    const [cards, setCards] = useState<CodexCardItem[]>(DEFAULT_CARDS);
    const [selectedCard, setSelectedCard] = useState<CodexCardItem | null>(DEFAULT_CARDS[0]);
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedCategory, setSelectedCategory] = useState("All");
    const [statusFilter, setStatusFilter] = useState<"All" | "Unlocked" | "Locked">("All");
    const [activeTab, setActiveTab] = useState<"summary" | "why" | "sources">("summary");

    useEffect(() => {
        const fetchCodex = async () => {
            try {
                const res = await fetch("http://127.0.0.1:8000/api/v1/codex");
                if (res.ok) {
                    const data = await res.json();
                    if (Array.isArray(data) && data.length > 0) {
                        setCards(data);
                        if (!selectedCard) setSelectedCard(data[0]);
                    }
                }
            } catch {
                // fallback to DEFAULT_CARDS
            }
        };
        fetchCodex();
    }, []);

    const handleUnlock = async (cardId: string) => {
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/v1/codex/${cardId}/unlock`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });
            if (res.ok) {
                const updated = await res.json();
                setCards((prev) => prev.map((c) => (c.id === cardId ? { ...c, is_locked: false } : c)));
                if (selectedCard?.id === cardId) {
                    setSelectedCard({ ...selectedCard, is_locked: false });
                }
            }
        } catch {
            setCards((prev) => prev.map((c) => (c.id === cardId ? { ...c, is_locked: false } : c)));
            if (selectedCard?.id === cardId) {
                setSelectedCard({ ...selectedCard, is_locked: false });
            }
        }
    };

    const categories = ["All", ...Array.from(new Set(cards.map((c) => c.category)))];

    const filteredCards = cards.filter((c) => {
        if (statusFilter === "Unlocked" && c.is_locked) return false;
        if (statusFilter === "Locked" && !c.is_locked) return false;
        if (selectedCategory !== "All" && c.category !== selectedCategory) return false;
        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase();
            return (
                c.title.toLowerCase().includes(q) ||
                c.subtitle.toLowerCase().includes(q) ||
                c.plain_summary.toLowerCase().includes(q) ||
                c.category.toLowerCase().includes(q)
            );
        }
        return true;
    });

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px", width: "100%" }}>
            {/* Controls Bar: Search & Filter Tabs */}
            <div
                style={{
                    display: "flex",
                    flexWrap: "wrap",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "12px",
                    background: "var(--surface, rgba(6,8,14,0.86))",
                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                    borderRadius: "2px",
                    padding: "16px 20px",
                }}
            >
                {/* Search Input */}
                <div style={{ position: "relative", minWidth: "240px", flex: 1, maxWidth: "400px" }}>
                    <input
                        type="text"
                        placeholder="SEARCH SCIENCE CODEX..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{
                            width: "100%",
                            background: "var(--bg, #030307)",
                            border: "1px solid var(--line, rgba(233,228,223,0.16))",
                            borderRadius: "2px",
                            padding: "8px 12px",
                            color: "var(--text, #ECE8E3)",
                            fontSize: "11px",
                            fontFamily: "var(--font-mono, monospace)",
                            letterSpacing: "0.12em",
                            outline: "none",
                        }}
                    />
                </div>

                {/* Filter Pills */}
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                    <div style={{ display: "flex", gap: "4px" }}>
                        {(["All", "Unlocked", "Locked"] as const).map((tab) => (
                            <button
                                key={tab}
                                type="button"
                                onClick={() => setStatusFilter(tab)}
                                style={{
                                    background: statusFilter === tab ? "var(--accent, #FF4D5A)" : "transparent",
                                    color: statusFilter === tab ? "var(--accent-ink, #030307)" : "var(--muted, rgba(236,232,227,0.55))",
                                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                    borderRadius: "2px",
                                    padding: "6px 12px",
                                    fontSize: "11px",
                                    fontFamily: "var(--font-mono, monospace)",
                                    fontWeight: 600,
                                    letterSpacing: "0.14em",
                                    textTransform: "uppercase",
                                    cursor: "pointer",
                                }}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>

                    <select
                        value={selectedCategory}
                        onChange={(e) => setSelectedCategory(e.target.value)}
                        style={{
                            background: "var(--bg, #030307)",
                            border: "1px solid var(--line, rgba(233,228,223,0.16))",
                            color: "var(--text, #ECE8E3)",
                            borderRadius: "2px",
                            padding: "6px 12px",
                            fontSize: "11px",
                            fontFamily: "var(--font-mono, monospace)",
                            letterSpacing: "0.1em",
                            textTransform: "uppercase",
                            outline: "none",
                            cursor: "pointer",
                        }}
                    >
                        {categories.map((c) => (
                            <option key={c} value={c} style={{ background: "#030307", color: "#ECE8E3" }}>
                                {c.toUpperCase()}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Main Content Layout: Grid of Cards + Detail Inspection View */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr)) 440px",
                    gap: "24px",
                    alignItems: "start",
                }}
            >
                {/* Science Cards Grid */}
                <div
                    style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
                        gap: "20px",
                    }}
                >
                    {filteredCards.map((card) => {
                        const isSelected = selectedCard?.id === card.id;

                        return (
                            <article
                                key={card.id}
                                onClick={() => setSelectedCard(card)}
                                style={{
                                    position: "relative",
                                    background: "var(--surface, rgba(6,8,14,0.86))",
                                    border: isSelected
                                        ? "1px solid var(--accent, #FF4D5A)"
                                        : "1px solid var(--line, rgba(233,228,223,0.16))",
                                    borderRadius: "2px",
                                    padding: "24px",
                                    cursor: "pointer",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "14px",
                                    boxShadow: "none",
                                }}
                            >
                                {/* Top Row: Category + Evidence Badge */}
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                                    <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted, rgba(236,232,227,0.55))", textTransform: "uppercase", letterSpacing: "0.14em", fontFamily: "var(--font-mono, monospace)" }}>
                                        {card.category}
                                    </span>

                                    <span
                                        style={{
                                            display: "inline-flex",
                                            alignItems: "center",
                                            gap: "4px",
                                            padding: "2px 6px",
                                            borderRadius: "2px",
                                            fontSize: "10px",
                                            fontWeight: 600,
                                            fontFamily: "var(--font-mono, monospace)",
                                            letterSpacing: "0.12em",
                                            background: "transparent",
                                            color: card.evidence === "established" ? "var(--cool, #8FB8E8)" : "var(--warn, #FFB84D)",
                                            border: `1px solid ${card.evidence === "established" ? "var(--cool, #8FB8E8)" : "var(--warn, #FFB84D)"}`,
                                        }}
                                    >
                                        {card.evidence.toUpperCase()}
                                    </span>
                                </div>

                                {/* Title & Subtitle */}
                                <div>
                                    <h3
                                        style={{
                                            margin: "0 0 4px 0",
                                            fontSize: "16px",
                                            fontWeight: 800,
                                            color: card.is_locked ? "var(--muted, rgba(236,232,227,0.55))" : "var(--text, #ECE8E3)",
                                            fontFamily: "var(--font-display, sans-serif)",
                                            textTransform: "uppercase",
                                            letterSpacing: "-0.01em",
                                            lineHeight: 1.25,
                                        }}
                                    >
                                        {card.title}
                                    </h3>
                                    <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", display: "block", fontFamily: "var(--font-mono, monospace)" }}>
                                        {card.subtitle}
                                    </span>
                                </div>

                                {/* Summary or Locked state */}
                                {card.is_locked ? (
                                    <div
                                        style={{
                                            background: "var(--surface-2, rgba(255,255,255,0.04))",
                                            border: "1px dashed var(--line, rgba(233,228,223,0.16))",
                                            borderRadius: "2px",
                                            padding: "12px",
                                            display: "flex",
                                            flexDirection: "column",
                                            gap: "6px",
                                        }}
                                    >
                                        <div style={{ color: "var(--warn, #FFB84D)", fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.12em", fontFamily: "var(--font-mono, monospace)" }}>
                                            [Locked Briefing]
                                        </div>
                                        <p style={{ margin: 0, fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", lineHeight: 1.5, fontFamily: "var(--font-mono, monospace)" }}>
                                            {card.unlock_condition}
                                        </p>
                                    </div>
                                ) : (
                                    <p
                                        style={{
                                            margin: 0,
                                            fontSize: "12px",
                                            color: "var(--muted, rgba(236,232,227,0.55))",
                                            lineHeight: 1.6,
                                            fontFamily: "var(--font-mono, monospace)",
                                            display: "-webkit-box",
                                            WebkitLineClamp: 3,
                                            WebkitBoxOrient: "vertical",
                                            overflow: "hidden",
                                        }}
                                    >
                                        {card.plain_summary}
                                    </p>
                                )}

                                {/* Bottom Row */}
                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                        marginTop: "auto",
                                        paddingTop: "12px",
                                        borderTop: "1px solid var(--line, rgba(233,228,223,0.16))",
                                    }}
                                >
                                    <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                        Zone: {card.related_zone}
                                    </span>

                                    {card.is_locked ? (
                                        <button
                                            type="button"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleUnlock(card.id);
                                            }}
                                            style={{
                                                background: "transparent",
                                                border: "1px solid var(--warn, #FFB84D)",
                                                color: "var(--warn, #FFB84D)",
                                                borderRadius: "2px",
                                                padding: "4px 8px",
                                                fontSize: "11px",
                                                fontWeight: 600,
                                                letterSpacing: "0.1em",
                                                textTransform: "uppercase",
                                                fontFamily: "var(--font-mono, monospace)",
                                                cursor: "pointer",
                                            }}
                                        >
                                            Unlock
                                        </button>
                                    ) : (
                                        <span style={{ fontSize: "11px", color: "var(--accent, #FF4D5A)", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "var(--font-mono, monospace)" }}>
                                            Inspect →
                                        </span>
                                    )}
                                </div>
                            </article>
                        );
                    })}
                </div>

                {/* Right Side: Detailed Card View */}
                {selectedCard && (
                    <aside
                        style={{
                            background: "var(--surface, rgba(6,8,14,0.86))",
                            border: "1px solid var(--line, rgba(233,228,223,0.16))",
                            borderRadius: "2px",
                            padding: "24px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "20px",
                            position: "sticky",
                            top: "24px",
                            boxShadow: "none",
                        }}
                    >
                        {/* Header */}
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "10px" }}>
                            <div>
                                <span
                                    style={{
                                        fontSize: "11px",
                                        fontWeight: 600,
                                        textTransform: "uppercase",
                                        letterSpacing: "0.14em",
                                        color: "var(--muted, rgba(236,232,227,0.55))",
                                        display: "block",
                                        marginBottom: "4px",
                                        fontFamily: "var(--font-mono, monospace)",
                                    }}
                                >
                                    {selectedCard.category}
                                </span>
                                <h2 style={{ margin: "0 0 4px 0", fontSize: "18px", fontWeight: 800, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-display, sans-serif)", textTransform: "uppercase", letterSpacing: "-0.01em", lineHeight: 1.25 }}>
                                    {selectedCard.title}
                                </h2>
                                <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                                    {selectedCard.subtitle}
                                </span>
                            </div>

                            <span
                                style={{
                                    fontSize: "11px",
                                    fontFamily: "var(--font-mono, monospace)",
                                    letterSpacing: "0.12em",
                                    textTransform: "uppercase",
                                    color: selectedCard.is_locked ? "var(--warn, #FFB84D)" : "var(--cool, #8FB8E8)",
                                    border: `1px solid ${selectedCard.is_locked ? "var(--warn, #FFB84D)" : "var(--cool, #8FB8E8)"}`,
                                    padding: "2px 6px",
                                    borderRadius: "2px",
                                }}
                            >
                                {selectedCard.is_locked ? "Locked" : "Unlocked"}
                            </span>
                        </div>

                        {/* Unlock requirement button if locked */}
                        {selectedCard.is_locked && (
                            <div
                                style={{
                                    background: "var(--surface-2, rgba(255,255,255,0.04))",
                                    border: "1px solid var(--warn, #FFB84D)",
                                    borderRadius: "2px",
                                    padding: "14px",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "8px",
                                }}
                            >
                                <span style={{ color: "var(--warn, #FFB84D)", fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.12em", fontFamily: "var(--font-mono, monospace)" }}>
                                    Unlock Condition
                                </span>
                                <p style={{ margin: 0, fontSize: "12px", color: "var(--text, #ECE8E3)", lineHeight: 1.5, fontFamily: "var(--font-mono, monospace)" }}>
                                    {selectedCard.unlock_condition}
                                </p>
                                <button
                                    type="button"
                                    onClick={() => handleUnlock(selectedCard.id)}
                                    style={{
                                        marginTop: "4px",
                                        background: "var(--accent, #FF4D5A)",
                                        color: "var(--accent-ink, #030307)",
                                        border: "none",
                                        borderRadius: "2px",
                                        padding: "8px 14px",
                                        fontSize: "11px",
                                        fontFamily: "var(--font-mono, monospace)",
                                        fontWeight: 600,
                                        letterSpacing: "0.14em",
                                        textTransform: "uppercase",
                                        cursor: "pointer",
                                    }}
                                >
                                    Complete Unlock
                                </button>
                            </div>
                        )}

                        {/* 3-Tier Depth Tabs: Plain Summary | Why It Matters | Peer Sources */}
                        <div
                            style={{
                                display: "flex",
                                borderBottom: "1px solid var(--line, rgba(233,228,223,0.16))",
                                gap: "16px",
                            }}
                        >
                            {(
                                [
                                    { key: "summary", label: "Summary" },
                                    { key: "why", label: "Operational Context" },
                                    { key: "sources", label: "Sources" },
                                ] as const
                            ).map((tab) => (
                                <button
                                    key={tab.key}
                                    type="button"
                                    onClick={() => setActiveTab(tab.key)}
                                    style={{
                                        background: "transparent",
                                        border: "none",
                                        borderBottom: activeTab === tab.key ? "2px solid var(--accent, #FF4D5A)" : "2px solid transparent",
                                        padding: "8px 0",
                                        color: activeTab === tab.key ? "var(--accent, #FF4D5A)" : "var(--muted, rgba(236,232,227,0.55))",
                                        fontSize: "11px",
                                        fontFamily: "var(--font-mono, monospace)",
                                        fontWeight: 600,
                                        letterSpacing: "0.14em",
                                        textTransform: "uppercase",
                                        cursor: "pointer",
                                        marginBottom: "-1px",
                                    }}
                                >
                                    {tab.label}
                                </button>
                            ))}
                        </div>

                        {/* Tab Content Display */}
                        <div style={{ minHeight: "160px", display: "flex", flexDirection: "column", gap: "12px" }}>
                            {activeTab === "summary" && (
                                <p style={{ margin: 0, fontSize: "12px", color: "var(--muted, rgba(236,232,227,0.55))", lineHeight: 1.7, fontFamily: "var(--font-mono, monospace)" }}>
                                    {selectedCard.plain_summary}
                                </p>
                            )}

                            {activeTab === "why" && (
                                <p style={{ margin: 0, fontSize: "12px", color: "var(--muted, rgba(236,232,227,0.55))", lineHeight: 1.7, fontFamily: "var(--font-mono, monospace)" }}>
                                    {selectedCard.why_it_matters}
                                </p>
                            )}

                            {activeTab === "sources" && (
                                <ul style={{ margin: 0, paddingLeft: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
                                    {selectedCard.sources.map((src, idx) => (
                                        <li key={idx} style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", lineHeight: 1.5, fontFamily: "var(--font-mono, monospace)" }}>
                                            {src}
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>

                        {/* Associated Countermeasure Quest Link */}
                        {selectedCard.related_quest_id && onNavigateToQuest && (
                            <button
                                type="button"
                                onClick={() => onNavigateToQuest(selectedCard.related_quest_id!)}
                                style={{
                                    marginTop: "auto",
                                    background: "transparent",
                                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                    color: "var(--text, #ECE8E3)",
                                    borderRadius: "2px",
                                    padding: "8px 14px",
                                    fontSize: "11px",
                                    fontFamily: "var(--font-mono, monospace)",
                                    letterSpacing: "0.14em",
                                    textTransform: "uppercase",
                                    cursor: "pointer",
                                }}
                            >
                                View Related Quest →
                            </button>
                        )}
                    </aside>
                )}
            </div>
        </div>
    );
}
