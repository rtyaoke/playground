"""
Toy simulation: donut rupture risk in deep frying (1D radial model)

- Discretize donut radius (0..R), solve transient heat conduction
- Track moisture fraction, evaporate when T>100C (simple kinetics)
- Compute steam moles, effective void volume depends on porosity (baking powder effect)
- Pressure from ideal gas; rupture when P exceeds crust strength (after crust sets)

This is NOT a validated physical model—intended for qualitative behavior.
"""

from __future__ import annotations

import math
import numpy as np
import matplotlib.pyplot as plt


def simulate(
    *,
    R: float = 0.02,              # donut "half-thickness" radius [m] (2 cm)
    N: int = 80,                  # radial grid points
    t_end: float = 120.0,         # total time [s]
    dt: float = 0.02,             # time step [s]
    T_oil: float = 175.0 + 273.15,  # oil temp [K]
    T_init: float = 25.0 + 273.15,  # initial temp [K]
    alpha: float = 1.2e-7,        # thermal diffusivity [m^2/s] (dough-ish)
    h: float = 350.0,             # convective h at surface [W/m^2/K] (hot oil)
    k: float = 0.35,              # thermal conductivity [W/m/K]
    rho: float = 950.0,           # density [kg/m^3]
    cp: float = 2800.0,           # heat capacity [J/kg/K]
    # moisture / evaporation
    w0: float = 0.40,             # initial mass fraction of water
    evap_rate: float = 1.0e-3,    # base evaporation rate [1/s] when T>100C
    # porosity: set higher to represent baking powder / aeration
    # initial void fraction (no BP ~0.01-0.03, BP ~0.05-0.15)
    porosity: float = 0.04,
    # additional void growth per second when warm [1/s] (optional)
    porosity_growth: float = 0.0,
    # crust/rupture
    # crust "sets" when surface exceeds this [K]
    crust_set_T: float = 85.0 + 273.15,
    strength_base: float = 1.8e5,  # Pa, baseline rupture threshold after crust set
    # Pa/K, stronger when cooler; weaker when hotter (simple)
    strength_slope: float = 2.5e3,
    P_atm: float = 101325.0,      # Pa
    seed_pressure: float = 0.0,   # additional initial internal pressure [Pa]
    verbose: bool = False,
):
    """
    Returns dict with time series and rupture info.
    """
    # grid
    r = np.linspace(0.0, R, N)
    dr = r[1] - r[0]

    # Temperature field
    T = np.full(N, T_init, dtype=float)

    # moisture (mass fraction water)
    w = np.full(N, w0, dtype=float)

    # assume "internal cavity" volume where steam accumulates ~ some fraction of donut volume
    # For 1D slab/annulus, just use unit volume scaling; we care about *relative* pressure spikes.
    # We'll track per-unit-volume moles and effective void volume.
    R_gas = 8.314  # J/mol/K

    # For simplicity, define "accumulation zone" as interior (say r < 0.8R)
    inner_mask = r < 0.8 * R

    # steam moles per unit *total* volume (toy)
    n_steam = 0.0

    # time series
    steps = int(t_end / dt)
    ts = np.zeros(steps)
    T_surf = np.zeros(steps)
    T_core = np.zeros(steps)
    P_int = np.zeros(steps)
    w_avg = np.zeros(steps)
    crust_set = False
    t_crust = None
    ruptured = False
    t_rupture = None
    rupture_reason = None

    # Stability check for explicit heat conduction (rough)
    # dt <= dr^2/(2*alpha) for 1D; but we also have convection BC, so keep conservative.
    dt_stable = dr * dr / (2.0 * alpha + 1e-30)
    if dt > 0.9 * dt_stable:
        raise ValueError(
            f"dt too large for stability: dt={dt:.4g}s, suggest <= {0.9*dt_stable:.4g}s"
        )

    # helper: apply explicit heat equation in radial coordinates (cylindrical-ish)
    # We'll use a simple 1D slab approximation to keep it readable: dT/dt = alpha * d2T/dr2
    # r=0 symmetry: dT/dr=0
    # r=R convection: -k dT/dr = h (T_s - T_oil)
    for i in range(steps):
        t = i * dt

        # record
        ts[i] = t
        T_surf[i] = T[-1]
        T_core[i] = T[0]
        w_avg[i] = float(w.mean())

        # crust set?
        if (not crust_set) and (T[-1] >= crust_set_T):
            crust_set = True
            t_crust = t

        # porosity evolution (optional)
        if porosity_growth > 0.0:
            warm = max(0.0, (T.mean() - (40.0 + 273.15)) /
                       30.0)  # 0..~1 above ~40C
            porosity = min(0.35, porosity + porosity_growth * warm * dt)

        # evaporation (toy kinetics): when T>100C, water decreases and steam increases
        # Convert water mass fraction change -> moles steam increase (per unit volume)
        # water mass per unit volume = rho * w
        # d(m_water)/dt = -rho * dw/dt ; dn = -d(m_water)/Mw
        Mw = 0.018  # kg/mol
        hot = T > (100.0 + 273.15)
        if np.any(hot):
            # rate scales with superheat
            superheat = np.clip((T[hot] - (100.0 + 273.15)) / 30.0, 0.0, 3.0)
            dw = evap_rate * superheat * dt
            # limit by available water
            dw = np.minimum(dw, w[hot])
            w[hot] -= dw

            # steam generation weighted by inner region (assume steam tends to accumulate inside)
            # Take only water evaporated in inner zone contributes to internal pressure build.
            hot_inner = hot & inner_mask
            if np.any(hot_inner):
                dw_inner = (dw if hot_inner.sum() == hot.sum() else None)
                # easier: compute using full arrays
                # reconstruct dw_field
                dw_field = np.zeros_like(w)
                dw_field[hot] = dw
                # kg/m^3 (toy averaging)
                m_evap_inner = rho * dw_field[hot_inner].mean()
                dn = m_evap_inner / Mw
                n_steam += dn

        # internal pressure: ideal gas in void volume
        # effective void volume per unit total volume = porosity + (1-porosity)*gas_channels_factor
        # For "no BP", porosity small -> smaller V -> bigger pressure spikes.
        V_void = max(1e-6, porosity)  # per unit volume
        T_gas = max(250.0, float(T[inner_mask].mean()))
        P = (n_steam * R_gas * T_gas) / V_void + P_atm + seed_pressure
        P_int[i] = P

        # rupture check: only meaningful after crust set (surface hardened)
        if crust_set and (not ruptured):
            # crude strength: base minus softening with temperature above crust_set_T
            # and slightly higher when cooler
            soft = max(0.0, (T[-1] - crust_set_T))
            strength = max(5e4, strength_base - strength_slope * soft)
            if P > P_atm + strength:
                ruptured = True
                t_rupture = t
                rupture_reason = (
                    f"P_int={P/1000:.1f}kPa exceeded P_atm+strength={(P_atm+strength)/1000:.1f}kPa"
                )
                if verbose:
                    print("RUPTURE at", t_rupture, rupture_reason)

        # stop if ruptured (optional: keep sim going; here we stop to show event time cleanly)
        if ruptured:
            # truncate arrays
            ts = ts[: i + 1]
            T_surf = T_surf[: i + 1]
            T_core = T_core[: i + 1]
            P_int = P_int[: i + 1]
            w_avg = w_avg[: i + 1]
            break

        # ---- Heat conduction step (explicit) ----
        T_new = T.copy()

        # interior points
        for j in range(1, N - 1):
            d2 = (T[j + 1] - 2 * T[j] + T[j - 1]) / (dr * dr)
            T_new[j] = T[j] + alpha * dt * d2

        # r=0 symmetry: dT/dr=0 => T[-1] mirrored
        d2_center = (T[1] - T[0]) * 2.0 / (dr * dr)
        T_new[0] = T[0] + alpha * dt * d2_center

        # r=R convection BC: -k dT/dr = h (T_s - T_oil)
        # Approximate derivative: (T_s - T_{N-2})/dr
        # => -k (T_s - T_in)/dr = h (T_s - T_oil)
        # Solve for T_s (implicit BC):
        T_in = T[N - 2]
        T_s = (k * T_in / dr + h * T_oil) / (k / dr + h)
        T_new[N - 1] = T_s

        T = T_new

    return {
        "t": ts,
        "T_surf": T_surf,
        "T_core": T_core,
        "P_int": P_int,
        "w_avg": w_avg,
        "ruptured": ruptured,
        "t_crust": t_crust,
        "t_rupture": t_rupture,
        "reason": rupture_reason,
        "final_porosity": porosity,
    }


def run_and_plot():
    # Compare "no baking powder" (low porosity) vs "with baking powder" (higher porosity)
    cases = [
        ("No BP (low porosity)", dict(porosity=0.02, strength_base=1.6e5)),
        ("With BP (higher porosity)", dict(porosity=0.10, strength_base=1.6e5)),
    ]

    plt.figure()
    for name, kwargs in cases:
        out = simulate(**kwargs)
        t = out["t"]
        # plot gauge pressure relative to atmosphere
        plt.plot(t, (out["P_int"] - 101325.0) / 1000.0, label=name)
        if out["t_rupture"] is not None:
            plt.axvline(out["t_rupture"], linestyle="--")
    plt.xlabel("time [s]")
    plt.ylabel("internal gauge pressure [kPa]")
    plt.title("Toy Donut Frying: Pressure Build-up & Rupture")
    plt.legend()
    plt.show()

    plt.figure()
    for name, kwargs in cases:
        out = simulate(**kwargs)
        t = out["t"]
        plt.plot(t, out["T_surf"] - 273.15, label=f"{name} surface")
        plt.plot(t, out["T_core"] - 273.15,
                 linestyle="--", label=f"{name} core")
    plt.xlabel("time [s]")
    plt.ylabel("temperature [°C]")
    plt.title("Temperature Rise (surface vs core)")
    plt.legend()
    plt.show()


for name, kwargs in cases:
    out = simulate(**kwargs)
    print(f"\n{name}")
    print(f"  crust set time: {out['t_crust']:.2f}s" if out["t_crust"]
          is not None else "  crust not set")
    if out["ruptured"]:
        print(f"  RUPTURE at: {out['t_rupture']:.2f}s")
        print(f"  reason: {out['reason']}")
    else:
        print("  no rupture within simulated time")
    print(f"  final porosity used: {out['final_porosity']:.3f}")


if __name__ == "__main__":
    run_and_plot()
