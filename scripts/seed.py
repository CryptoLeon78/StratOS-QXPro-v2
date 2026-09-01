"""StratOS-QXPro Seed Generator (PARTE 13, G8).

Genera el estado historico y actual del portfolio (cuentas, bots de
produccion/cantera/graveyard, historia de trades, correlaciones, estados
derivados via los sweeps reales, y los escenarios de PARTE 13) para que el
panel sea navegable con datos coherentes sin depender de un terminal MT5
real -- y para que los criterios de aceptacion de PARTE 16 sean
verificables de forma automatica.

Uso:
    python scripts/seed.py --profile full [--reset] [--inject-audit-error]
    python scripts/seed.py --profile ci --reset

`--reset` trunca TODAS las tablas de dominio (via DATABASE_URL, el rol
propietario -- `stratos_app` no tiene DELETE en las 6 tablas inmutables de
P6/P15.3, asi que un reset limpio no puede hacerse con el rol de
aplicacion) y siembra desde cero. Sin `--reset`, si ya existe un seed del
mismo perfil (`SystemConfig["seed_profile"]`), el script no hace nada --
protege un `docker compose up` repetido en desarrollo de reseedear sin
querer.
"""

import argparse
import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import core.db.models  # noqa: F401  -- registra las 28 tablas en Base.metadata
import numpy as np
from core.config import get_settings
from core.db.base import Base, async_session_factory
from core.db.models.governance import SystemConfig
from core.redis import get_redis_client
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine

from seed_lib.accounts import seed_accounts
from seed_lib.audit_error import inject_audit_error as apply_audit_error_injection
from seed_lib.bots_pipeline import seed_pipeline_bots
from seed_lib.bots_production import full_production_roster, seed_production_bots
from seed_lib.config import profile_for
from seed_lib.derived_states import run_all_sweeps
from seed_lib.equity_curve import (
    bulk_insert_equity_snapshots,
    bulk_insert_heartbeats,
    generate_equity_snapshots,
)
from seed_lib.graveyard import seed_graveyard
from seed_lib.header_state import verify_header_state
from seed_lib.scenarios import (
    DEAD_BOT_NAME,
    RUNAWAY_BOT_NAME,
    apply_missing_sl_scenario,
    apply_watchdog_scenarios,
    insert_orphan_trades,
    normalize_recent_frequency,
    seed_impulses,
    seed_news_events,
)
from seed_lib.test_user import seed_test_user
from seed_lib.trades_history import bulk_insert_trades, generate_production_trades


async def _reset_database() -> None:
    """TRUNCATE de todas las tablas de dominio, via el rol propietario
    (DATABASE_URL) -- ver docstring del modulo. CASCADE resuelve el orden
    de FKs (incl. el ciclo bot<->baseline) sin tener que mantenerlo a mano."""
    owner_engine = create_async_engine(get_settings().database_url)
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with owner_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
    await owner_engine.dispose()


async def _already_seeded(profile_name: str) -> bool:
    async with async_session_factory() as session:
        row = (
            await session.execute(select(SystemConfig).where(SystemConfig.key == "seed_profile"))
        ).scalar_one_or_none()
        return row is not None and row.value.get("profile") == profile_name


async def run_seed(
    profile_name: str, *, reset: bool, inject_audit_error: bool, seed: int = 20260101
) -> None:
    if get_settings().deployment_profile == "operational":
        raise RuntimeError("el perfil operational prohíbe cualquier seed de fixture")
    now = datetime.now(UTC)
    profile = profile_for(profile_name, now)
    rng = np.random.default_rng(seed)

    if reset:
        host = get_settings().database_url.split("@")[-1]
        print(f"[seed] --reset: truncando todas las tablas de dominio ({host})")
        await _reset_database()
    elif await _already_seeded(profile.name):
        print(
            f"[seed] ya existe un seed del perfil {profile.name!r} -- nada que hacer (usa --reset)."
        )
        return

    start, end = profile.history_start.date(), profile.history_end.date()
    print(f"[seed] perfil={profile.name} rango={start}..{end}")

    async with async_session_factory() as session:
        accounts = await seed_accounts(session)
        roster = full_production_roster()
        bots = await seed_production_bots(session, accounts["prod"], roster, now)
        candidates = await seed_pipeline_bots(session, accounts["prod"], accounts["quarry"], now)
        graveyard = await seed_graveyard(session, accounts["prod"], now)
        test_user = await seed_test_user(session, now)
        await session.commit()
        user_status = f"sembrado ({test_user.email})" if test_user else "no configurado"
        print(
            f"[seed] cuentas: {list(accounts)} · bots produccion: {len(bots)} · "
            f"cantera: {len(candidates)} · graveyard: {len(graveyard)} · "
            f"usuario Playwright: {user_status}"
        )

        generated = generate_production_trades(
            roster,
            {name: bot.id for name, bot in bots.items()},
            profile.history_start.date(),
            profile.history_end.date(),
            Decimal("30000"),
            rng,
        )
        generated = apply_watchdog_scenarios(generated, bots, now)
        generated = normalize_recent_frequency(
            generated, roster, bots, {DEAD_BOT_NAME, RUNAWAY_BOT_NAME}, now
        )
        n_trades, n_trade_batches = await bulk_insert_trades(
            session, accounts["prod"], generated, now
        )
        await session.commit()
        print(f"[seed] trades: {n_trades} · lotes sellados (trades): {n_trade_batches}")

        equity_snapshots = generate_equity_snapshots(
            accounts["prod"].id,
            generated,
            profile.history_start.date(),
            profile.history_end.date(),
            Decimal("30000"),
        )
        n_equity, n_equity_batches = await bulk_insert_equity_snapshots(
            session, accounts["prod"], equity_snapshots
        )
        await session.commit()
        print(f"[seed] equity: {n_equity} · lotes sellados (equity): {n_equity_batches}")

        n_batches_total = n_trade_batches + n_equity_batches
        # datetime.now(UTC) FRESCO aqui, no `profile.history_end` (el `now`
        # anclado al INICIO del script, hace G9-06/ASSUMPTIONS): el ultimo
        # heartbeat es lo que header.py/execution.py comparan contra la hora
        # real de cada request para decidir "conectado"/"DATOS STALE"
        # (umbral header_heartbeat_stale_after_s=120, real y deliberadamente
        # ajustado, PARTE 16 -- no se toca). El resto del seed (huerfanos,
        # impulsos, sweeps, verificacion) sigue corriendo DESPUES de este
        # punto, y el job completo de e2e-playwright (arranque de
        # servidores, instalar Chromium, 12 specs en serie) tarda varios
        # minutos mas -- anclar al inicio del script dejaba el heartbeat ya
        # a mitad de camino de quedarse stale antes de que Playwright
        # llegara a consultarlo. Anclar a la insercion real (mas tarde,
        # mas fresco) no elimina la carrera de tiempo del todo pero la
        # reduce al minimo posible sin tocar el umbral de negocio.
        for account in accounts.values():
            n_heartbeats, n_hb_batches = await bulk_insert_heartbeats(
                session, account, datetime.now(UTC)
            )
            n_batches_total += n_hb_batches
            print(
                f"[seed] heartbeats {account.name}: {n_heartbeats} · "
                f"lotes sellados (heartbeat): {n_hb_batches}"
            )
        await session.commit()
        print(f"[seed] lotes sellados totales: {n_batches_total}")

        n_orphans = await insert_orphan_trades(session, accounts["prod"], now)
        await apply_missing_sl_scenario(session, accounts["prod"], bots["Selene MeanRev XAG"], now)
        n_impulses = await seed_impulses(session, bots, now)
        n_news = await seed_news_events(session, now)
        await session.commit()
        print(
            f"[seed] escenarios: huerfanos={n_orphans} · posicion sin SL=1 · "
            f"impulsos={n_impulses} · noticias={n_news}"
        )

        if inject_audit_error:
            await apply_audit_error_injection(session, accounts["prod"])
            await session.commit()
            print("[seed] --inject-audit-error: EquitySnapshot perturbado")

        redis = get_redis_client()
        await run_all_sweeps(session, redis, now)
        print(
            "[seed] sweeps reales: correlaciones/semaforo/kill-switch/"
            "watchdog/auditoria/impulsos/gate"
        )
        await redis.aclose()

        await verify_header_state(
            session,
            accounts["prod"],
            inject_audit_error=inject_audit_error,
            as_of=profile.history_end,
        )

        # Marca de idempotencia que `_already_seeded()` lee -- sin esta fila,
        # una segunda corrida sin --reset nunca detectaria un seed ya hecho
        # (hallazgo real: el check ya existia pero nada lo escribia).
        session.add(
            SystemConfig(
                key="seed_profile",
                value={"profile": profile.name, "seeded_at": now.isoformat()},
                updated_at=now,
            )
        )
        await session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--profile", choices=["full", "ci"], default="full")
    parser.add_argument(
        "--reset", action="store_true", help="Trunca todas las tablas antes de sembrar."
    )
    parser.add_argument(
        "--inject-audit-error",
        action="store_true",
        help="Perturba un EquitySnapshot para forzar una discrepancia de auditoria (>0,02%%).",
    )
    parser.add_argument(
        "--seed", type=int, default=20260101, help="Semilla determinista del generador."
    )
    args = parser.parse_args()
    asyncio.run(
        run_seed(
            args.profile,
            reset=args.reset,
            inject_audit_error=args.inject_audit_error,
            seed=args.seed,
        )
    )


if __name__ == "__main__":
    main()
