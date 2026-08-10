import unittest
from types import SimpleNamespace

from app.services.gemini_service import avaliar_possivel_divergencia
from app.services.regras_negocio import auditar_inscricao


def documento(categoria, dados):
    return (categoria, dados, "CONCLUIDO", None)


class TestFase2(unittest.TestCase):
    def setUp(self):
        self.candidato = SimpleNamespace(nome_completo="Maria da Silva", cpf="123.456.789-00")
        self.processo = SimpleNamespace(renda_per_capita_limite=1412)
        self.documentos = [
            documento("RG", {"nome": "Maria da Silva", "cpf": "12345678900", "legibilidade": 95, "documento_integro": True}),
            documento("RESIDENCIA", {"data_emissao": "01/08/2026", "legibilidade": 95, "documento_integro": True}),
            documento("HOLERITE", {"data_emissao": "01/08/2026", "renda_bruta": 1800, "renda_liquida": 1500, "legibilidade": 95, "documento_integro": True}),
        ]

    def test_candidato_fake_apto(self):
        resultado = auditar_inscricao(
            self.candidato,
            self.documentos,
            [SimpleNamespace(renda_declarada=500)],
            self.processo,
        )

        self.assertEqual(resultado.status_geral, "APTO")
        self.assertEqual(resultado.renda_per_capita, 1150.0)

    def test_renda_acima_do_teto(self):
        resultado = auditar_inscricao(
            self.candidato,
            self.documentos,
            [],
            SimpleNamespace(renda_per_capita_limite=1000),
        )

        self.assertEqual(resultado.status_geral, "NAO_APTO")
        self.assertEqual(resultado.renda_per_capita, 1800.0)

    def test_renda_liquida_maior_que_bruta_exige_revisao(self):
        documentos = list(self.documentos)
        documentos[2] = documento(
            "HOLERITE",
            {"data_emissao": "01/08/2026", "renda_bruta": 1500, "renda_liquida": 1800, "legibilidade": 95, "documento_integro": True},
        )

        resultado = auditar_inscricao(
            self.candidato,
            documentos,
            [],
            SimpleNamespace(renda_per_capita_limite=5000),
        )

        self.assertEqual(resultado.status_geral, "REVISAO_MANUAL")
        self.assertTrue(any("Renda líquida" in item for item in resultado.inconsistencias))

    def test_cpf_divergente_exige_revisao(self):
        documentos = list(self.documentos)
        documentos[0] = documento(
            "RG",
            {"nome": "Maria da Silva", "cpf": "99999999999", "legibilidade": 95, "documento_integro": True},
        )

        resultado = auditar_inscricao(
            self.candidato,
            documentos,
            [],
            SimpleNamespace(renda_per_capita_limite=5000),
        )

        self.assertEqual(resultado.status_geral, "REVISAO_MANUAL")
        self.assertTrue(any("CPF" in item for item in resultado.inconsistencias))

    def test_documento_vencido_exige_revisao(self):
        documentos = list(self.documentos)
        documentos[1] = documento(
            "RESIDENCIA",
            {"data_emissao": "01/01/2026", "legibilidade": 95, "documento_integro": True},
        )

        resultado = auditar_inscricao(
            self.candidato,
            documentos,
            [],
            SimpleNamespace(renda_per_capita_limite=5000),
        )

        self.assertEqual(resultado.status_geral, "REVISAO_MANUAL")
        self.assertTrue(any("RESIDENCIA" in item for item in resultado.inconsistencias))

    def test_documento_incompativel_e_detectado(self):
        dados = {"legibilidade": 95, "documento_integro": True, "renda_bruta": 1800}

        self.assertTrue(avaliar_possivel_divergencia(dados, "HOLERITE"))
        self.assertFalse(
            avaliar_possivel_divergencia(
                {"nome": "Maria", "cpf": "123", "renda_bruta": 1800, "renda_liquida": 1500},
                "HOLERITE",
            )
        )


if __name__ == "__main__":
    unittest.main()