from magic_identity import entry_matches_account
from regenerate_mn_registry_docs import regenerate_bepb, regenerate_jjti

MAPA = {
    7786: {"magic_number": 1, "comment_identity": "XAUH1BUYSTOPeof_1.8.81_MN1"},
    2084: {"magic_number": 9, "comment_identity": "EURJPYM15L_1_29_59_MN9"},
}


def _filtrado_para(mapa: dict[int, dict[str, object]], cuenta: str) -> dict[int, dict[str, object]]:
    """Mismo filtro que aplica `main()` antes de llamar a `regenerate_bepb`/`regenerate_jjti`."""
    return {legacy: entry for legacy, entry in mapa.items() if entry_matches_account(entry, cuenta)}


def test_incidente_a16_una_traduccion_scoped_a_jjti_no_contamina_el_doc_de_bepb() -> None:
    """Caso real detectado 2026-09-26: legacy 10827 -> magic 10 estaba aprobado
    solo para JJTI, pero `regenerate_mn_registry_docs.py` aplicaba el mapa
    global sin filtrar y lo tradujo tambien en el documento de BEPB."""
    mapa_global = {10827: {"magic_number": 10, "comment_identity": "X_MN10", "accounts": ["JJTI"]}}
    texto_bepb = "CustomComment: ALGO_MN10827 | MagicNumber: 10827 | X: 1\n"

    nuevo, reporte = regenerate_bepb(texto_bepb, _filtrado_para(mapa_global, "BEPB"))

    assert nuevo == texto_bepb, "10827 es de JJTI, el documento de BEPB no se toca"
    assert reporte.left_as_is == [10827]
    assert reporte.translated == {}


def test_incidente_a16_la_misma_traduccion_si_aplica_en_el_doc_de_jjti() -> None:
    mapa_global = {10827: {"magic_number": 10, "comment_identity": "X_MN10", "accounts": ["JJTI"]}}
    texto_jjti = "Identificadores: ALGO_MN10827\nMagicNumber: 10827\n"

    nuevo, reporte = regenerate_jjti(texto_jjti, _filtrado_para(mapa_global, "JJTI"))

    assert reporte.translated == {10827: "X_MN10"}
    assert "Identificadores: X_MN10\nMagicNumber: 10" in nuevo


def test_bepb_traduce_comment_y_magic_number_preservando_los_demas_campos() -> None:
    texto = (
        "Estrategia 3: XAUH1BUYSTOPeof_1.8.81 (XAUUSD,H1)\n"
        "CustomComment: XAUH1BUYSTOPeof_1.8.81_MN7786 | MagicNumber: 7786 | "
        "ProfitTargetCoef1: 4.2 | mmRiskedMoney: 200.0\n"
    )

    nuevo, reporte = regenerate_bepb(texto, MAPA)

    assert "CustomComment: XAUH1BUYSTOPeof_1.8.81_MN1 | MagicNumber: 1" in nuevo
    assert "ProfitTargetCoef1: 4.2 | mmRiskedMoney: 200.0" in nuevo, "resto de la linea intacto"
    assert "Estrategia 3: XAUH1BUYSTOPeof_1.8.81 (XAUUSD,H1)" in nuevo, "cabecera intacta"
    assert reporte.translated == {7786: "XAUH1BUYSTOPeof_1.8.81_MN1"}


def test_bepb_deja_intacto_un_magic_que_no_esta_en_el_registro() -> None:
    texto = "CustomComment: EUJPYM15BUYSTP_1.29.59_MN54856 | MagicNumber: 54856 | X: 1\n"

    nuevo, reporte = regenerate_bepb(texto, MAPA)

    assert nuevo == texto, "sin registro para 54856, no se toca nada"
    assert reporte.left_as_is == [54856]
    assert reporte.translated == {}


def test_bepb_retiene_una_entrada_cuyo_comment_y_magicnumber_ya_discrepan() -> None:
    """Si el propio documento ya se contradice (bug pre-existente del hand-write),
    no se decide cual campo es el correcto: se retiene entera y se declara."""
    texto = "CustomComment: ALGO_MN7786 | MagicNumber: 9999 | X: 1\n"

    nuevo, reporte = regenerate_bepb(texto, MAPA)

    assert nuevo == texto
    assert reporte.inconsistent == [(7786, 9999)]
    assert reporte.translated == {}


def test_bepb_tolera_un_espacio_en_el_label_tipo_documento_real() -> None:
    """Typo real encontrado en el documento (espacio en vez de guion bajo):
    no se traduce si el magic no esta en el registro, pero se cuenta."""
    texto = "CustomComment: XAUM30L 1.10.37_4.6.33_MN260726 | MagicNumber: 260726 | X: 1\n"

    nuevo, reporte = regenerate_bepb(texto, {})

    assert nuevo == texto
    assert reporte.left_as_is == [260726]


def test_jjti_traduce_identificadores_y_magicnumber_en_lineas_separadas() -> None:
    texto = (
        "ESTRATEGIA 3: EURJPY M15 (Compra)\n"
        "Identificadores: EURJPYM15L_1.29.59_MN2084\n"
        "MagicNumber: 2084\n"
        "Configuración de Indicadores:\n"
        "- QQERSI: 44\n"
    )

    nuevo, reporte = regenerate_jjti(texto, MAPA)

    assert "Identificadores: EURJPYM15L_1_29_59_MN9\nMagicNumber: 9" in nuevo
    assert "- QQERSI: 44" in nuevo, "resto del bloque intacto"
    assert reporte.translated == {2084: "EURJPYM15L_1_29_59_MN9"}


def test_jjti_deja_intacto_un_magic_fuera_del_registro() -> None:
    texto = "Identificadores: EURUSDM15S_3.76.81_MN301\nMagicNumber: 301\n"

    nuevo, reporte = regenerate_jjti(texto, MAPA)

    assert nuevo == texto
    assert reporte.left_as_is == [301]


def test_reporte_cuenta_el_total_de_entradas_vistas() -> None:
    texto = (
        "CustomComment: A_MN7786 | MagicNumber: 7786 | x\n"
        "CustomComment: B_MN1 | MagicNumber: 1 | x\n"
    )

    _, reporte = regenerate_bepb(texto, MAPA)

    assert reporte.total_seen == 2
    assert reporte.translated == {7786: "XAUH1BUYSTOPeof_1.8.81_MN1"}
    assert reporte.left_as_is == [1], "1 ya es el magic vigente de OTRO legacy, no esta como clave"
