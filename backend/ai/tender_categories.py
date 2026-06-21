"""Closed taxonomy for public tender recommendation preferences.

The values are based on observed ``Opportunite.extra_data["type_commande"]``
records from the MarchesPublics source. Keep this module deterministic: user
input must select from these values instead of providing free text.
"""

TENDER_CATEGORIES = {
    "Biens": [
        "Autres Fournitures",
        "Autres types de matériels",
        "Equipements hydromécaniques",
        "Equipements informatiques",
        "Fournitures",
        "Fournitures agricoles",
        "Fournitures de bureau",
        "Habillement",
        "Matériel",
        "Matériel Médical",
        "Matériel agricole",
        "Matériels de Bureau",
        "Matériels de reprographie",
        "Matériels électriques",
        "Matériels électroniques",
        "Matériels informatiques",
        "Matériels roulants",
        "Matériels scientifiques",
        "Mobilier",
        "Nourriture",
        "Produits d'entretien",
        "Produits pharmaceutiques",
    ],
    "Travaux": [
        "Ascenseur",
        "Autres travaux",
        "Charpente métallique",
        "Climatisation",
        "Electricité",
        "Forages hydrauliques",
        "Fondation Spéciale",
        "Génie Civil",
        "Lac collinaire",
        "Ouvrages hydrauliques",
        "Peinture et vitrerie",
        "Pose de canalisation",
        "Réalisation des réseaux de télécommunication",
        "Revêtement routier",
        "Routes",
        "Travaux de Rehabilitation",
        "VRD",
    ],
    "Services": [
        "Autres services",
        "Maintenance",
        "Maintenance technique",
        "Nettoyage",
        "Services",
    ],
    "Etudes": [
        "Activité littéraire et artistique",
        "Autres études",
        "Etudes",
        "Etudes d'impact",
        "Formation",
    ],
    "Autre": [],
}


TENDER_CATEGORY_LABELS_EN = {
    "Biens": "Goods",
    "Travaux": "Works",
    "Services": "Services",
    "Etudes": "Studies",
    "Autre": "Other",
}


TENDER_SUBCATEGORY_LABELS_EN = {
    "Autres Fournitures": "Other Supplies",
    "Autres types de matériels": "Other Equipment",
    "Equipements hydromécaniques": "Hydromechanical Equipment",
    "Equipements informatiques": "IT Equipment",
    "Fournitures": "Supplies",
    "Fournitures agricoles": "Agricultural Supplies",
    "Fournitures de bureau": "Office Supplies",
    "Habillement": "Clothing",
    "Matériel": "Equipment",
    "Matériel Médical": "Medical Equipment",
    "Matériel agricole": "Agricultural Equipment",
    "Matériels de Bureau": "Office Equipment",
    "Matériels de reprographie": "Reprography Equipment",
    "Matériels électriques": "Electrical Equipment",
    "Matériels électroniques": "Electronic Equipment",
    "Matériels informatiques": "IT Hardware",
    "Matériels roulants": "Vehicles",
    "Matériels scientifiques": "Scientific Equipment",
    "Mobilier": "Furniture",
    "Nourriture": "Food Supplies",
    "Produits d'entretien": "Cleaning Products",
    "Produits pharmaceutiques": "Pharmaceutical Products",
    "Ascenseur": "Elevator",
    "Autres travaux": "Other Works",
    "Charpente métallique": "Metal Structure",
    "Climatisation": "Air Conditioning",
    "Electricité": "Electricity",
    "Forages hydrauliques": "Hydraulic Drilling",
    "Fondation Spéciale": "Special Foundation",
    "Génie Civil": "Civil Engineering",
    "Lac collinaire": "Hill Reservoir",
    "Ouvrages hydrauliques": "Hydraulic Works",
    "Peinture et vitrerie": "Painting and Glazing",
    "Pose de canalisation": "Pipeline Installation",
    "Réalisation des réseaux de télécommunication": "Telecommunication Networks",
    "Revêtement routier": "Road Surfacing",
    "Routes": "Roads",
    "Travaux de Rehabilitation": "Rehabilitation Works",
    "VRD": "Roads and Utilities",
    "Autres services": "Other Services",
    "Maintenance": "Maintenance",
    "Maintenance technique": "Technical Maintenance",
    "Nettoyage": "Cleaning",
    "Services": "Services",
    "Activité littéraire et artistique": "Literary and Artistic Activity",
    "Autres études": "Other Studies",
    "Etudes": "Studies",
    "Etudes d'impact": "Impact Studies",
    "Formation": "Training",
}


TENDER_SUBCATEGORY_SYNONYMS = {
    "Equipements informatiques": [
        "ordinateurs",
        "serveurs",
        "réseau",
        "équipements IT",
        "matériel informatique",
    ],
    "Matériels informatiques": [
        "ordinateurs",
        "serveurs",
        "réseau",
        "équipements IT",
        "matériel informatique",
    ],
    "Matériels roulants": [
        "véhicules",
        "engins",
        "camions",
        "transport",
    ],
    "Matériel Médical": [
        "équipement médical",
        "dispositifs médicaux",
        "matériel hospitalier",
    ],
    "Maintenance": [
        "maintenance technique",
        "entretien",
        "réparation",
    ],
    "Maintenance technique": [
        "maintenance",
        "entretien technique",
        "réparation",
    ],
    "Génie Civil": [
        "construction",
        "bâtiment",
        "infrastructure",
        "travaux publics",
    ],
    "VRD": [
        "voirie",
        "réseaux divers",
        "assainissement",
        "infrastructure",
    ],
    "Formation": [
        "formation professionnelle",
        "accompagnement",
        "renforcement des capacités",
    ],
}


def get_tender_categories() -> dict[str, list[str]]:
    return {category: list(subcategories) for category, subcategories in TENDER_CATEGORIES.items()}


def get_tender_category_label(category: str) -> str:
    return TENDER_CATEGORY_LABELS_EN.get(category, category)


def get_tender_subcategory_label(subcategory: str) -> str:
    return TENDER_SUBCATEGORY_LABELS_EN.get(subcategory, subcategory)


def get_tender_subcategory_synonyms(subcategory: str) -> list[str]:
    return list(TENDER_SUBCATEGORY_SYNONYMS.get(subcategory, []))
