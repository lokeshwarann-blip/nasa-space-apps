import math
from typing import Literal
from fastapi import APIRouter, Query, status
import numpy as np
from scipy.integrate import solve_ivp

from src.schemas.astronaut import (
    CircadianResponse,
    EnvironmentProfile,
)

router = APIRouter(prefix="/circadian", tags=["Circadian Alignment"])

ENVIRONMENT_PROFILES: dict[str, dict] = {
    "spacecraft": {
        "light_lux": 450.0,
        "color_temperature_k": 4500,
        "blue_wavelength_attenuation": True,
        "temperature_c": 21.0,
        "scheduled_dark_hours": 8.0,
        "day_length_hours": 24.0,
        "intrinsic_period": 24.2,
    },
    "station": {
        "light_lux": 500.0,
        "color_temperature_k": 5000,
        "blue_wavelength_attenuation": False,
        "temperature_c": 22.0,
        "scheduled_dark_hours": 8.0,
        "day_length_hours": 24.0,
        "intrinsic_period": 24.2,
    },
    "rover": {
        "light_lux": 350.0,
        "color_temperature_k": 4000,
        "blue_wavelength_attenuation": True,
        "temperature_c": 19.5,
        "scheduled_dark_hours": 7.5,
        "day_length_hours": 24.0,
        "intrinsic_period": 24.2,
    },
    "lunar_base": {
        "light_lux": 600.0,
        "color_temperature_k": 5500,
        "blue_wavelength_attenuation": False,
        "temperature_c": 21.5,
        "scheduled_dark_hours": 8.0,
        "day_length_hours": 24.0,
        "intrinsic_period": 24.2,
    },
    "mars_base": {
        "light_lux": 500.0,
        "color_temperature_k": 4800,
        "blue_wavelength_attenuation": True,
        "temperature_c": 20.5,
        "scheduled_dark_hours": 8.2,
        "day_length_hours": 24.65,  # 24h 39m Martian sol
        "intrinsic_period": 24.65,
    },
}


def compute_circadian_ode(
    light_lux: float,
    dark_hours: float,
    day_length_hours: float = 24.0,
    intrinsic_period: float = 24.2,
    total_hours: float = 48.0,
) -> float:
    """Solves Kronauer-Forger limit-cycle oscillator via scipy ODE to estimate phase offset."""
    mu = 0.13
    omega_scale = (24.0 / intrinsic_period) ** 2

    def light_drive(t: float) -> float:
        t_mod = t % day_length_hours
        is_light = t_mod >= dark_hours
        lux = light_lux if is_light else 0.0
        return 0.05 * (lux / (lux + 100.0))

    def ode(t, y):
        x, xc = y
        b = light_drive(t)
        dxdt = (np.pi / 12.0) * (xc + b)
        dxc_dt = (np.pi / 12.0) * (mu * (xc - (4.0 / 3.0) * (xc**3)) - x * omega_scale)
        return [dxdt, dxc_dt]

    sol = solve_ivp(
        ode,
        t_span=(0.0, total_hours),
        y0=[0.0, 1.0],
        t_eval=[total_hours],
        method="RK45",
    )
    final_x = float(sol.y[0][-1])
    final_xc = float(sol.y[1][-1])
    phase_rad = math.atan2(final_xc, final_x)
    phase_offset = (phase_rad / math.pi) * (day_length_hours / 2.0)
    return round(float(phase_offset), 2)


@router.get(
    "/{id}",
    response_model=CircadianResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Circadian Phase Alignment Analysis",
    description="Solves Kronauer-Forger limit-cycle ODE from photic and sleep schedules across mission environments.",
)
async def get_circadian_status(
    id: str,
    profile: Literal["spacecraft", "station", "rover", "lunar_base", "mars_base"] = Query(
        default="station",
        description="Mission environment profile: spacecraft, station, rover, lunar_base, mars_base (24h39m sol)",
    ),
) -> CircadianResponse:
    """Calculates circadian phase offset, suggested shift, and realignment duration using scipy ODE."""
    env = ENVIRONMENT_PROFILES.get(profile.lower(), ENVIRONMENT_PROFILES["station"])
    light_lux = env["light_lux"]
    dark_hours = env["scheduled_dark_hours"]
    day_length = env["day_length_hours"]
    tau = env["intrinsic_period"]

    phase_offset = compute_circadian_ode(
        light_lux=light_lux,
        dark_hours=dark_hours,
        day_length_hours=day_length,
        intrinsic_period=tau,
    )

    # Entrainment shift recommendation (max human phase shift capacity ~ 1.5h per day)
    suggested_shift = min(1.5, max(0.5, round(abs(phase_offset) / 2.0, 2))) if abs(phase_offset) > 0.2 else 0.0
    days_to_realign = max(1, int(math.ceil(abs(phase_offset) / max(0.5, suggested_shift)))) if abs(phase_offset) > 0.2 else 0

    assumptions = [
        f"Kronauer-Forger Limit-Cycle oscillator evaluated with scipy.integrate.solve_ivp",
        f"Intrinsic circadian pacemaker period tau={tau}h for {profile} environment",
        f"Scheduled dark rest window of {dark_hours}h with {light_lux} lux nominal work illuminance",
        f"Diurnal cycle duration: {day_length}h per {'Martian sol' if profile == 'mars_base' else 'Earth day'}",
        "Check with flight surgeon for individualized schedule and melatonin protocol adjustments",
    ]

    return CircadianResponse(
        crew_id=id,
        phase_offset_hours=phase_offset,
        suggested_shift=suggested_shift,
        days_to_realign=days_to_realign,
        model="Kronauer-Forger Limit-Cycle Circadian Oscillator (scipy ODE)",
        assumptions=assumptions,
        environment_profile=EnvironmentProfile(
            light_lux=light_lux,
            color_temperature_k=env["color_temperature_k"],
            blue_wavelength_attenuation=env["blue_wavelength_attenuation"],
            temperature_c=env["temperature_c"],
            scheduled_dark_hours=dark_hours,
        ),
    )
