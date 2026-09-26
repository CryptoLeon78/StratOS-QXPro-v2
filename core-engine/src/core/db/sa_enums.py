"""Instancias SQLAlchemy `Enum` compartidas: un tipo ENUM de Postgres por
enum de PARTE 5.1, reutilizado en todas las columnas que lo usan. Evita
depender del deduplicado implicito de SQLAlchemy cuando el mismo `name=`
apareceria mas de una vez (p.ej. `semaphore_state` en `Bot` y en las dos
columnas de `SemaphoreTransition`)."""

from sqlalchemy import Enum as SAEnum

from core.db.enums import (
    AccountDataOrigin,
    ActorType,
    AlertLevel,
    AssetAdmissionStatus,
    AssetSourceGroup,
    BaselineSource,
    BotOriginKind,
    BotProfile,
    BotRole,
    CemeteryCause,
    ChecklistType,
    CorrelationSource,
    DecisionStatus,
    ImpulseAction,
    ImpulseStatus,
    NewsImpact,
    PipelinePhase,
    SemaphoreState,
    TradeType,
    Verdict,
)

bot_profile = SAEnum(BotProfile, name="bot_profile")
bot_role = SAEnum(BotRole, name="bot_role")
pipeline_phase = SAEnum(PipelinePhase, name="pipeline_phase")
semaphore_state = SAEnum(SemaphoreState, name="semaphore_state")
alert_level = SAEnum(AlertLevel, name="alert_level")
baseline_source = SAEnum(BaselineSource, name="baseline_source")
verdict = SAEnum(Verdict, name="verdict")
trade_type = SAEnum(TradeType, name="trade_type")
impulse_action = SAEnum(ImpulseAction, name="impulse_action")
impulse_status = SAEnum(ImpulseStatus, name="impulse_status")
cemetery_cause = SAEnum(CemeteryCause, name="cemetery_cause")
checklist_type = SAEnum(ChecklistType, name="checklist_type")
actor_type = SAEnum(ActorType, name="actor_type")
news_impact = SAEnum(NewsImpact, name="news_impact")
decision_status = SAEnum(DecisionStatus, name="decision_status")
account_data_origin = SAEnum(AccountDataOrigin, name="account_data_origin")
bot_origin_kind = SAEnum(BotOriginKind, name="bot_origin_kind")
asset_source_group = SAEnum(AssetSourceGroup, name="asset_source_group")
asset_admission_status = SAEnum(AssetAdmissionStatus, name="asset_admission_status")
correlation_source = SAEnum(CorrelationSource, name="correlation_source")
