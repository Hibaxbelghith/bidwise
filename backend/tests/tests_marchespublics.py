from django.test import SimpleTestCase

from bs4 import BeautifulSoup

from opportunities.scraping.sources.marchespublics import MarchesPublicsScraper, extract_city


DETAIL_HTML = """
<div class="liste_appel_offre page-cms">
    <h1>Détail de l'appel d'offres</h1>
    <div class="gray-box bg-white bordered small-padding font-weight-5">
        <div class="row">
            <div class="col-sm-6 col-md-3">
                <h5 class="text-main-red font-weight-bold m-0">Objet</h5>
                <span class="medium">Acquisition de matériels roulants pour la commune de Ben Arous</span>
            </div>
            <div class="col-sm-6 col-md-3">
                <h5 class="text-main-red font-weight-bold m-0">Descriptif</h5>
                <span class="medium"></span>
            </div>
            <div class="col-sm-6 col-md-3">
                <h5 class="text-main-red font-weight-bold m-0">Date de publication</h5>
                <span class="medium">08-04-2026</span>
            </div>
        </div>
    </div>
    <div class="row">
        <div class="col-md-3">
            <div class="gray-box less-x-padding">
                <p class="medium mb-0"><strong>Numéro A.O :</strong> Tender-101425</p>
                <p class="medium mb-0"><strong>Acheteur public :</strong> Municipalité Ben Arous</p>
                <p class="medium mb-0"><strong>Procédure de passation :</strong> Appel d’offres ouvert</p>
                <p class="medium mb-0"><strong>Mode de financement :</strong> Budget</p>
                <p class="medium mb-0"><strong>Type de commande :</strong> Biens/ Autres Fournitures</p>
            </div>
            <div class="manage-btn">
                <a href="https://www.marchespublics.gov.tn/storage/tender/2026/04/08/cahier.pdf" download="cahier des charges.pdf">cahier des charges</a>
                <a href="https://www.marchespublics.gov.tn/storage/tender/2026/04/08/avis.docx" download="Avis d’appel d’offres.docx">Avis d’appel d’offres</a>
            </div>
        </div>
        <div class="col-md-9">
            <div class="row">
                <div class="col-sm-6">
                    <div class="gray-box bg-white less-x-padding text-main-blue">
                        <p class="medium mb-0"><strong class="after_points">Délais de validité des offres (en nombre de jours)</strong> 120</p>
                        <p class="medium mb-0"><strong class="after_points">Région d’exécution</strong> BEN AROUS</p>
                        <p class="medium mb-0"><strong class="after_points">Date limite de réception des offres</strong><br>11-05-2026</p>
                    </div>
                </div>
                <div class="col-sm-6">
                    <div class="gray-box bg-white less-x-padding text-main-blue">
                        <p class="medium mb-0"><strong>Lieu de réception des offres :</strong> Avenue de la république BP 77 -1054 Amilcar</p>
                    </div>
                </div>
            </div>
            <div class="row">
                <div class="col-sm-4">
                    <div class="offre-card">
                        <div class="card-head">
                            <p class="title"><span>Lot 1</span></p>
                            <div>Objet Acquisition de voitures de services</div>
                        </div>
                        <div class="card-body">
                            <span class="text">
                                Objet : Acquisition de voitures de services<br>
                                Quantité : : 4<br>
                                Région d'exécution : BEN AROUS<br>
                                Montant du cautionnement provisoire : 2500
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
"""


class MarchesPublicsScraperTests(SimpleTestCase):
    def test_extract_city_prefers_last_meaningful_city_token(self):
        self.assertEqual(extract_city("Avenue de la république BP 77 -1054 Amilcar"), "Amilcar")
        self.assertEqual(extract_city("BEN AROUS"), "Ben Arous")
        self.assertEqual(extract_city("Tunis"), "Tunis")

    def test_extract_detail_data_returns_structured_project_extra_data(self):
        scraper = MarchesPublicsScraper(fetch_details=False)
        soup = BeautifulSoup(DETAIL_HTML, "html.parser")

        parsed = scraper._extract_detail_data(soup)

        self.assertEqual(parsed["title"], "Acquisition de matériels roulants pour la commune de Ben Arous")
        self.assertEqual(parsed["organization"], "Municipalité Ben Arous")
        self.assertEqual(parsed["location"], "Amilcar")
        self.assertEqual(parsed["publication_date"], "08-04-2026")
        self.assertEqual(parsed["deadline"], "11-05-2026")
        self.assertIn("Procédure: Appel d’offres ouvert", parsed["description"])
        self.assertIn("Date limite: 11-05-2026", parsed["description"])

        extra_data = parsed["extra_data"]
        self.assertEqual(extra_data["procedure"], "Appel d’offres ouvert")
        self.assertEqual(extra_data["financement"], "Budget")
        self.assertEqual(extra_data["type_commande"], "Biens/ Autres Fournitures")
        self.assertEqual(extra_data["delai_validite"], "120")
        self.assertEqual(extra_data["region_execution"], "BEN AROUS")
        self.assertEqual(extra_data["region"], "Amilcar")
        self.assertEqual(extra_data["full_address"], "Avenue de la république BP 77 -1054 Amilcar")
        self.assertEqual(extra_data["caution"], "2500")
        self.assertTrue(extra_data["has_pdf"])
        self.assertEqual(extra_data["pdf_url"], "https://www.marchespublics.gov.tn/storage/tender/2026/04/08/avis.docx")
        self.assertEqual(
            extra_data["cahier_des_charges_url"],
            "https://www.marchespublics.gov.tn/storage/tender/2026/04/08/cahier.pdf",
        )
        self.assertEqual(len(extra_data["documents"]), 2)
        self.assertEqual(extra_data["documents"][0]["type"], "cahier_des_charges")
        self.assertEqual(
            extra_data["documents"][0]["url"],
            "https://www.marchespublics.gov.tn/storage/tender/2026/04/08/cahier.pdf",
        )
        self.assertIn("cahier", extra_data["documents"][0]["label"].lower())
        self.assertEqual(extra_data["documents"][1]["type"], "avis_appel_offres")
        self.assertEqual(
            extra_data["documents"][1]["url"],
            "https://www.marchespublics.gov.tn/storage/tender/2026/04/08/avis.docx",
        )
        self.assertIn("avis", extra_data["documents"][1]["label"].lower())
        self.assertEqual(extra_data["structured"]["financement"], "Budget")
        self.assertEqual(extra_data["structured"]["type_commande"], "Biens/ Autres Fournitures")
        self.assertEqual(extra_data["structured"]["delai_validite"], "120")
        self.assertEqual(extra_data["structured"]["region_execution"], "BEN AROUS")
        self.assertIn("offres", extra_data["structured"]["procedure"].lower())
        self.assertEqual(
            extra_data["lots"],
            [
                {
                    "lot": "Lot 1",
                    "objet": "Acquisition de voitures de services",
                    "quantite": "4",
                    "region": "Ben Arous",
                    "caution": "2500",
                }
            ],
        )
